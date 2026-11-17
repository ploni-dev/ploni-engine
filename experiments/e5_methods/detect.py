"""Run one detector over one corpus of E5 and write what it marked as a person.

Why: a model takes minutes and the methods that are stacked on it take none. So the model
runs once per corpus, what it found is written to a file, and `evaluate.py` tries every
method on that file without loading a model again.

Contract: `python -I detect.py --detector KIND --model-dir M --dataset NAME --out FILE`,
offline, in the environment of `requirements.txt`. KIND is `joint` (the baseline of E1 and
E4, through E1's loader), `hf` (any token-classification model that transformers loads
without code of the model's own) or `onnx` (the same, from an ONNX file given with
`--onnx-file`). Writes one JSON file, see `run`. Prints the model's hashes, its labels and
which of them count as a person, so a label that was overlooked can be seen.

Known limits: one run per model. Time and memory are those of this laptop on this run, with
whatever else was running.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import sys
import time
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
# `python -I` drops the script folder. E1's loader and window cutter are reused so that the
# baseline is loaded and fed exactly as in E1 and E4.
sys.path[:0] = [str(HERE), str(HERE.parent / "e1_hebrew_recall")]

import numpy
import torch
from chunking import MAX_WORDPIECES, split_into_windows
from run_model import TORCH_THREADS, document_entities, load_ner_model

import data

# PREREGISTRATION.md, "Which labels are a person": the label's name without its B-, I-, E-,
# S-, L- or U- mark, in capitals, is one of these.
PERSON_LABELS = frozenset({"PER", "PERSON", "PRIVATE_PERSON", "FIRST_NAME", "LAST_NAME"})
# A token whose chance of being a person is below this is not written: it could never be
# chosen by a threshold the pre-registration lists, and the file stays small.
FLOOR = 0.01
# The weights of a model come in one of these files; whichever exists is hashed.
WEIGHT_FILES = ("model.safetensors", "config.json", "tokenizer.json")
BYTES_PER_MB = 1024 * 1024


def is_person(label: str) -> bool:
    """Say whether a model's label means a person, by the pre-registered list."""
    bare = label.split("-", 1)[1] if label[:2] in ("B-", "I-", "E-", "S-", "L-", "U-") else label
    return bare.upper() in PERSON_LABELS


def file_hashes(paths: list[Path]) -> dict[str, str]:
    """Return the SHA-256 of every file that exists, by its name."""
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path.is_file()}


def peak_memory_mb() -> float:
    """Return the most memory this process has held at once, in megabytes.

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


def classifier_tokens(model_dir: Path, onnx_file: Path | None) -> tuple:
    """Build a detector from a token-classification model.

    Contract: returns `(tokens, labels)`. The model is loaded from `model_dir` with no code
    of its own and from safetensors only, or, with `onnx_file`, run by onnxruntime on the
    processor. `tokens(paragraphs)` gives rows `[paragraph, start, end, chance, chosen]`,
    one per token, see `_rows`. A paragraph longer than the model takes is cut into windows
    at sentence ends, as in E1. Raises ValueError when no label of the model is a person,
    or when a window turns out longer than was counted.
    """
    from transformers import AutoConfig, AutoModelForTokenClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    labels = AutoConfig.from_pretrained(model_dir, local_files_only=True).id2label
    person_ids = [index for index, label in labels.items() if is_person(label)]
    if not person_ids:
        raise ValueError(f"no label of this model is a person: {sorted(labels.values())}")
    if onnx_file is None:
        model = AutoModelForTokenClassification.from_pretrained(model_dir, local_files_only=True, use_safetensors=True).eval()
    else:
        import onnxruntime

        session = onnxruntime.InferenceSession(str(onnx_file), providers=["CPUExecutionProvider"])
        wanted = {item.name for item in session.get_inputs()}

    def scores(encoded: dict) -> numpy.ndarray:
        if onnx_file is None:
            with torch.inference_mode():
                return model(**{name: torch.tensor(value) for name, value in encoded.items()}).logits[0].numpy()
        return session.run(None, {name: value for name, value in encoded.items() if name in wanted})[0][0]

    def tokens(paragraphs: list[str]) -> list[list]:
        rows = []
        for index, paragraph in enumerate(paragraphs):
            for window in split_into_windows(paragraph, lambda word: len(tokenizer.tokenize(word))):
                encoded = dict(tokenizer(paragraph[window.start : window.end], return_offsets_mapping=True, return_tensors="np"))
                offsets = encoded.pop("offset_mapping")[0].tolist()
                if len(offsets) > MAX_WORDPIECES + 2:
                    raise ValueError(f"a window has {len(offsets)} positions, more than {MAX_WORDPIECES + 2}")
                rows += _rows(index, window.start, offsets, _softmax(scores(encoded)), person_ids)
        return rows

    return tokens, [labels[index] for index in sorted(labels)]


def run(detector: str, model_dir: Path, dataset: str, out: Path, onnx_file: Path | None = None) -> None:
    """Run one detector over one corpus and write the result.

    Contract: writes a JSON object to `out`: `detector`, `model` (the folder's name),
    `hashes`, `dataset`, `labels`, `person_labels`, `seconds` (for the whole corpus, the
    loading of the model left out), `load_seconds`, `peak_mb`, `threads`, and `tokens`,
    which maps a document's id to its rows. The corpus is generated before the model is
    loaded, so a broken template stops the run before any time is spent.
    """
    torch.set_num_threads(TORCH_THREADS)
    documents = data.load(dataset)
    started = time.perf_counter()
    tokens, labels = joint_tokens(model_dir) if detector == "joint" else classifier_tokens(model_dir, onnx_file)
    loaded = time.perf_counter()
    found = {document.doc_id: tokens(document.paragraphs) for document in documents}
    seconds = time.perf_counter() - loaded
    hashes = file_hashes([model_dir / name for name in WEIGHT_FILES] + ([onnx_file] if onnx_file else []))
    result = {
        "detector": detector,
        "model": model_dir.name,
        "hashes": hashes,
        "dataset": dataset,
        "labels": labels,
        "person_labels": [label for label in labels if is_person(label)],
        "seconds": round(seconds, 1),
        "load_seconds": round(loaded - started, 1),
        "peak_mb": round(peak_memory_mb()),
        "threads": TORCH_THREADS,
        "tokens": found,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print(f"{detector} {model_dir.name} on {dataset}: {len(documents)} documents")
    for name, digest in hashes.items():
        print(f"{name} sha256 {digest}")
    print(f"labels: {labels}")
    print(f"person labels: {result['person_labels']}")
    print(f"seconds {result['seconds']}, load {result['load_seconds']}, peak {result['peak_mb']} MB, threads {TORCH_THREADS}")
    print(f"rows written: {sum(len(rows) for rows in found.values())}")


if __name__ == "__main__":
    # `python -I` ignores PYTHONUTF8, and a Windows pipe would get the ANSI code page.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--detector", choices=("joint", "hf", "onnx"), required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--dataset", choices=sorted(data.DATASETS), required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--onnx-file", type=Path)
    arguments = parser.parse_args()
    if (arguments.detector == "onnx") != (arguments.onnx_file is not None):
        parser.error("--onnx-file goes with --detector onnx, and only with it")
    run(arguments.detector, arguments.model_dir, arguments.dataset, arguments.out, arguments.onnx_file)
