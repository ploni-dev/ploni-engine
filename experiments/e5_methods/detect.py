"""Run one detector over one corpus of E5 and write what it marked as a person.

Why: a model takes minutes and the methods that are stacked on it take none. So the model
runs once per corpus, what it found is written to a file, and `evaluate.py` tries every
method on that file without loading a model again.

Contract: `python -I detect.py --detector KIND --model-dir M --dataset NAME --out FILE
[--sha256 HASH] [--onnx-file F] [--budget-seconds N]`, offline, in the environment of
`experiments/e2_int8_latency/requirements.txt`. KIND is `joint` (the baseline of E1 and
E4, through E1's loader), `hf` (any token-classification model that transformers loads
without code of the model's own) or `onnx` (the same, from an ONNX file given with
`--onnx-file`). The weights are hashed before the model is loaded: for `joint` they must
be the file E1 pinned, for the other kinds the file whose SHA-256 is given with
`--sha256`, and a run with other weights is refused. Writes one JSON file, see `run`.
Prints the model's hashes, its labels and which of them count as a person, so a label
that was overlooked can be seen.

With `--budget-seconds` a run is made in parts: it stops after that many seconds, and the
same command given again goes on where it stopped (`measure`).

Known limits: one run per model. Time and memory are those of this laptop on this run, with
whatever else was running. A run made in parts loads the model once per part; the seconds
it reports are those inside the detector, added over the parts.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import sys
import time
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
# `python -I` drops the script folder. E1's loader and window cutter are reused so that the
# baseline is loaded and fed exactly as in E1 and E4.
sys.path[:0] = [str(HERE), str(HERE.parent / "e1_hebrew_recall")]

import numpy
import torch
from chunking import MAX_WORDPIECES, split_into_windows
from run_model import TORCH_THREADS, document_entities, load_ner_model, pinned_model_hashes

import data

# PREREGISTRATION.md, "Which labels are a person": the label's name without its mark of
# position (B-, I-, E-, S-, L- or U-), in capitals, is one of these.
PERSON_LABELS = frozenset({"PER", "PERSON", "PRIVATE_PERSON", "FIRST_NAME", "LAST_NAME"})
POSITION_MARKS = ("B-", "I-", "E-", "S-", "L-", "U-")
# A token whose chance of being a person is below this is not written: it could never be
# chosen by a threshold the pre-registration lists, and the file stays small.
FLOOR = 0.01
# The files of a model folder whose hashes are written into a run file, when they exist.
HASHED_FILES = ("model.safetensors", "config.json", "tokenizer.json")
BYTES_PER_MB = 1024 * 1024


def is_person(label: str) -> bool:
    """Say whether a model's label means a person, by the pre-registered list.

    Why: which label counts is fixed before any model is run, so that it cannot be chosen
    by the number it gives.
    """
    bare = label[2:] if label[:2] in POSITION_MARKS else label
    return bare.upper() in PERSON_LABELS


def file_sha256(path: Path) -> str:
    """Return the SHA-256 of one file, read in pieces.

    Why: the weights of the largest candidate are 2.2 GB, more than this laptop has free;
    read whole, the hashing itself would end the run.
    """
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def checked_hashes(detector: str, model_dir: Path, onnx_file: Path | None, expected: str | None) -> dict[str, str]:
    """Refuse weights that are not the recorded ones.

    Why: PREREGISTRATION.md says a candidate whose weights do not have the recorded hash is
    not run. That is checked here, before the model is loaded, and not by a person reading
    a printed hash afterwards.

    Contract: hashes the files of the model and returns the SHA-256 of every file of
    HASHED_FILES that exists, and of the ONNX file when one is given, by file name. For `joint` the weights must be the file E1
    pinned (`run_model.pinned_model_hashes`). For the other kinds the weights file, the
    ONNX file when one is given and `model.safetensors` otherwise, must have the hash
    `expected`. Raises ValueError when they do not, or when `expected` is missing.
    """
    if detector == "joint":
        return pinned_model_hashes(model_dir)
    weights = onnx_file if onnx_file is not None else model_dir / "model.safetensors"
    files = [model_dir / name for name in HASHED_FILES] + ([onnx_file] if onnx_file is not None else [])
    hashes = {path.name: file_sha256(path) for path in files if path.is_file()}
    if expected is None or hashes.get(weights.name) != expected:
        raise ValueError(f"{weights.name} has sha256 {hashes.get(weights.name)}, and the run was told to expect {expected}")
    return hashes


def peak_memory_mb() -> float:
    """Return the most memory this process has held at once, in megabytes.

    Why: whether a model fits on a lawyer's laptop is part of what the experiment asks.

    Contract: the peak working set on Windows, the peak resident size elsewhere.
    """
    if sys.platform != "win32":
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage",
            )
        ]  # fmt: skip

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32")
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    ctypes.WinDLL("psapi").GetProcessMemoryInfo(
        wintypes.HANDLE(kernel.GetCurrentProcess()), ctypes.byref(counters), counters.cb
    )
    return counters.PeakWorkingSetSize / BYTES_PER_MB


def joint_tokens(model_dir: Path) -> tuple:
    """Build the baseline detector.

    Why: the baseline is run through E1's own loader, so that E5's baseline is the model
    of E1 and E4 fed in the same way.

    Contract: returns `(tokens, labels)`. `tokens(paragraphs)` gives one row per person
    span of the model, `[paragraph, start, end, 1.0, 1]`: the model's code gives spans and
    no chance, so every span is written as certain.
    """
    model, tokenizer = load_ner_model(model_dir)

    def tokens(paragraphs: list[str]) -> list[list]:
        found = document_entities(model, tokenizer, paragraphs).entities
        return [[item.paragraph, item.start, item.end, 1.0, 1] for item in found if is_person(item.label)]

    return tokens, ["PER"]


def _rows(index: int, shift: int, offsets: list, chances: numpy.ndarray, person_ids: list[int]) -> list[list]:
    """Turn the model's output for one window into rows of the output file.

    Contract: `chances` holds one row per token and one column per label. A row is written
    for a token that the model labels as a person, or whose summed chance over the person
    labels is at least FLOOR. A token with no characters of its own (a mark of the
    tokenizer) gives none.
    """
    person = chances[:, person_ids].sum(axis=1)
    top = chances.argmax(axis=1)
    rows = []
    for (start, end), chance, label in zip(offsets, person.tolist(), top.tolist(), strict=True):
        chosen = label in person_ids
        if end > start and (chosen or chance >= FLOOR):
            rows.append([index, shift + start, shift + end, round(chance, 4), int(chosen)])
    return rows


def _softmax(logits: numpy.ndarray) -> numpy.ndarray:
    """Turn the model's scores into chances that sum to one per token."""
    shifted = numpy.exp(logits - logits.max(axis=-1, keepdims=True))
    return shifted / shifted.sum(axis=-1, keepdims=True)


def paragraph_rows(index: int, paragraph: str, tokenizer, scores: Callable[[dict], numpy.ndarray], person_ids: list[int], budget: int = MAX_WORDPIECES) -> list[list]:
    """Return the rows of one paragraph, cut into windows where it is longer than the model takes.

    Why: a model reads a limited number of pieces at once. A window's places are counted
    from the window's own start, and a wrong shift back would move every span after the
    first window, so the shift is in one function that a test can reach without a model.

    Contract: the paragraph is cut at sentence ends into windows of at most `budget`
    pieces, as in E1 (`chunking.split_into_windows`). `tokenizer(text,
    return_offsets_mapping=True, return_tensors="np")` gives the pieces of a window with
    their places in it; `scores` gives one row of scores per piece. The rows are as
    `_rows` writes them, their places counted from the start of the paragraph. Raises
    ValueError when a window has more than `budget` + 2 positions.
    """
    rows = []
    for window in split_into_windows(paragraph, lambda word: len(tokenizer.tokenize(word)), budget):
        encoded = dict(tokenizer(paragraph[window.start : window.end], return_offsets_mapping=True, return_tensors="np"))
        offsets = encoded.pop("offset_mapping")[0].tolist()
        if len(offsets) > budget + 2:
            raise ValueError(f"a window has {len(offsets)} positions, more than {budget + 2}")
        rows += _rows(index, window.start, offsets, _softmax(scores(encoded)), person_ids)
    return rows


def _scorer(model_dir: Path, onnx_file: Path | None) -> Callable[[dict], numpy.ndarray]:
    """Load a token-classification model and return the function that scores one window.

    Contract: from safetensors only and with no code of the model's own, or, with
    `onnx_file`, run by onnxruntime on the processor.
    """
    if onnx_file is not None:
        import onnxruntime

        session = onnxruntime.InferenceSession(str(onnx_file), providers=["CPUExecutionProvider"])
        wanted = {item.name for item in session.get_inputs()}
        return lambda encoded: session.run(None, {name: value for name, value in encoded.items() if name in wanted})[0][0]
    from transformers import AutoModelForTokenClassification

    model = AutoModelForTokenClassification.from_pretrained(model_dir, local_files_only=True, use_safetensors=True).eval()

    def scores(encoded: dict) -> numpy.ndarray:
        with torch.inference_mode():
            return model(**{name: torch.tensor(value) for name, value in encoded.items()}).logits[0].numpy()

    return scores


def classifier_tokens(model_dir: Path, onnx_file: Path | None) -> tuple:
    """Build a detector from a token-classification model.

    Why: every candidate but the baseline is such a model, and one runner for all of them
    keeps their numbers comparable.

    Contract: returns `(tokens, labels)`. `tokens(paragraphs)` gives rows `[paragraph,
    start, end, chance, chosen]`, one per token, see `paragraph_rows`. Raises ValueError
    when no label of the model is a person.
    """
    from transformers import AutoConfig, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    labels = AutoConfig.from_pretrained(model_dir, local_files_only=True).id2label
    person_ids = [index for index, label in labels.items() if is_person(label)]
    if not person_ids:
        raise ValueError(f"no label of this model is a person: {sorted(labels.values())}")
    scores = _scorer(model_dir, onnx_file)

    def tokens(paragraphs: list[str]) -> list[list]:
        return [row for index, paragraph in enumerate(paragraphs) for row in paragraph_rows(index, paragraph, tokenizer, scores, person_ids)]

    return tokens, [labels[index] for index in sorted(labels)]


def part_state(part: Path, identity: dict) -> dict:
    """Return what earlier parts of a run left, or the state of a run not yet begun.

    Why: a part file that belongs to another model, another corpus, or the same corpus
    before a template changed would mix two runs into one result with no error.

    Contract: `part` is the file a run that stopped at its budget wrote. `identity` says
    what the run is: the kind of detector, the model folder's name, the name of the
    weights file, the corpus and the digest of its text. The state holds that `identity`,
    `tokens` for the documents done, the `seconds` spent on them, the largest `peak_mb` of
    any part, and the number of `parts`. Raises ValueError when the file is of a run with
    another identity.
    """
    if not part.is_file():
        return {"identity": identity, "tokens": {}, "seconds": 0.0, "peak_mb": 0, "parts": 0}
    state = json.loads(part.read_text(encoding="utf-8"))
    # A part file of the first harness has no identity at all; it is refused like any other.
    if state.get("identity") != identity:
        raise ValueError(f"{part.name} is of another run: {state.get('identity')}")
    return state


def measure(tokens: Callable[[list[str]], list[list]], documents: list, state: dict, budget: float | None, clock: Callable[[], float] = time.perf_counter) -> bool:
    """Run a detector over the documents that are not done yet, for as long as the budget allows.

    Why: this laptop cannot hold a long, heavy run: with little memory free a long command
    is stopped from outside. So a run can be made in parts of a few minutes, each of
    which takes up where the last one stopped.

    Contract: `state` is as `part_state` gives it and is changed in place: the rows of
    each document done are added to `tokens`, and the time spent inside `tokens(...)`, and
    only that, to `seconds`. A document is begun only while less than `budget` seconds of
    this call have passed; `None` is no limit. One document is done in every call,
    whatever the budget. Returns whether every document is done.
    """
    started = clock()
    begun = False
    for document in documents:
        if document.doc_id in state["tokens"]:
            continue
        if begun and budget is not None and clock() - started >= budget:
            return False
        before = clock()
        state["tokens"][document.doc_id] = tokens(document.paragraphs)
        state["seconds"] += clock() - before
        begun = True
    return True


def _write(path: Path, content: dict) -> None:
    """Write a JSON file so that a run stopped in the middle of the write leaves the old file whole."""
    temporary = path.with_name(path.name + ".writing")
    temporary.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def run(detector: str, model_dir: Path, dataset: str, out: Path, onnx_file: Path | None = None, budget: float | None = None, sha256: str | None = None) -> None:
    """Run one detector over one corpus.

    Why: the one entry point of a measurement, so that every candidate is run, timed and
    recorded in the same way.

    Contract: writes a JSON object to `out`: `detector`, `model` (the folder's name),
    `hashes`, `dataset`, `corpus_sha256` (`data.digest` of the text that was run),
    `labels`, `person_labels`, `seconds` (the time inside the detector for the whole
    corpus; the loading of the model is left out), `load_seconds` (of the last part),
    `peak_mb` (the largest of any part), `parts`, `threads`, and `tokens`, which maps a
    document's id to its rows. With `budget`, the run stops when that many seconds have
    passed and writes what it has to `<out>.part`; the same command, given again, goes on
    from there, and the last part removes that file. The corpus is generated and the
    weights are hashed before the model is loaded, so a broken template or other weights
    stop the run before any time is spent. Raises ValueError as `checked_hashes` and
    `part_state` do.
    """
    torch.set_num_threads(TORCH_THREADS)
    documents = data.load(dataset)
    hashes = checked_hashes(detector, model_dir, onnx_file, sha256)
    identity = {
        "detector": detector, "model": model_dir.name, "weights": onnx_file.name if onnx_file is not None else "model.safetensors",
        "dataset": dataset, "corpus_sha256": data.digest(documents),
    }  # fmt: skip
    part = out.with_name(out.name + ".part")
    state = part_state(part, identity)
    started = time.perf_counter()
    tokens, labels = joint_tokens(model_dir) if detector == "joint" else classifier_tokens(model_dir, onnx_file)
    loaded = time.perf_counter()
    done = measure(tokens, documents, state, budget)
    state["peak_mb"] = max(state["peak_mb"], round(peak_memory_mb()))
    state["parts"] += 1
    out.parent.mkdir(parents=True, exist_ok=True)
    if not done:
        _write(part, state)
        print(f"{detector} {model_dir.name} on {dataset}: {len(state['tokens'])} of {len(documents)} documents done; give the same command again")
        return
    result = {
        **identity,
        "hashes": hashes,
        "labels": labels,
        "person_labels": [label for label in labels if is_person(label)],
        "seconds": round(state["seconds"], 1),
        "load_seconds": round(loaded - started, 1),
        "peak_mb": state["peak_mb"],
        "parts": state["parts"],
        "threads": TORCH_THREADS,
        "tokens": state["tokens"],
    }
    _write(out, result)
    part.unlink(missing_ok=True)
    print(f"{detector} {model_dir.name} on {dataset}: {len(documents)} documents, in {state['parts']} part(s)")
    for name, digest in hashes.items():
        print(f"{name} sha256 {digest}")
    print(f"corpus sha256 {identity['corpus_sha256']}")
    print(f"labels: {labels}")
    print(f"person labels: {result['person_labels']}")
    print(f"seconds {result['seconds']}, load {result['load_seconds']}, peak {result['peak_mb']} MB, threads {TORCH_THREADS}")
    print(f"rows written: {sum(len(rows) for rows in state['tokens'].values())}")


if __name__ == "__main__":
    # `python -I` ignores PYTHONUTF8, and a Windows pipe would get the ANSI code page.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--detector", choices=("joint", "hf", "onnx"), required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--dataset", choices=sorted(data.DATASETS), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--onnx-file", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--budget-seconds", type=float)
    arguments = parser.parse_args()
    if (arguments.detector == "onnx") != (arguments.onnx_file is not None):
        parser.error("--onnx-file goes with --detector onnx, and only with it")
    run(arguments.detector, arguments.model_dir, arguments.dataset, arguments.out, arguments.onnx_file, arguments.budget_seconds, arguments.sha256)
