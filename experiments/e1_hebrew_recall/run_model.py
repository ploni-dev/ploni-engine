"""Run the pinned NER model over the E1 documents and write the counting worksheets.

Why: build-plan.md section 11, E1. This is the only step of the experiment that
touches the real documents, so it is also where the rules about them are
enforced: both directories must be outside the repository, the process is
offline, and stdout carries document ids and counts, never text or file names.

Contract: `python -I run_model.py --corpus-dir D --out-dir O --model-dir M`.
Reads every `.txt` and `.docx` in D. Writes into O, per document, a
`docNN.html` worksheet and `docNN_spans.csv` (every PERSON span with its
offsets and text); and once, `index.csv` (document id to file name),
`tally.csv` (blank hand count) and `run_meta.json` (versions and per-document
counts). Refuses to start if O already holds a `tally.csv`.

Known limits: the worksheets, the span files and `index.csv` hold document text
and file names.
They are deliberate output in a directory the user chose, not logs, and
`ploni/safety/` does not exist yet to write them through. One window per
forward pass, so a long document is slow on a small machine.
"""

from __future__ import annotations

import os

# Set before transformers is imported, so no code path can reach the hub.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
# `python -I` leaves the script's own folder off the import path; this puts
# back only that folder, never the model or corpus directories.
sys.path.insert(0, str(HERE))

import torch
import transformers
from transformers import AutoTokenizer

from chunking import MAX_WORDPIECES, split_into_windows
from corpus import document_id, is_inside, list_documents, read_checked, unread_characters
from tally import write_template
from vendored.dictabert_joint.BertForJointParsing import BertForJointParsing
from worksheet import SPAN_COLUMNS, Entity, count_person_highlights, person_span_rows, render_document

REPO_ROOT = HERE.parent.parent
MAX_POSITIONS = MAX_WORDPIECES + 2  # [CLS] and [SEP]
# Fixed so timings are comparable between runs; four leaves this laptop usable.
TORCH_THREADS = 4
# Only the syntax head can be left out with the model's code as shipped, both
# observed on 2026-11-11 with transformers 5.22.2 at the pinned commit:
# `do_lex=False` raises ValueError in post_init, because the tied weights
# declared at BertForJointParsing.py:53-56 lose their target; and with syntax,
# morph and prefix all off, forward raises UnboundLocalError at line 192,
# because only those three heads assign `loss`.
SWITCHED_OFF_HEADS = ("do_syntax",)


class WindowTooLongError(ValueError):
    """A window would be truncated by the tokenizer.

    Why: truncation is silent in the model's own code, and a truncated name
    would be counted as a model miss.

    Contract: raised before the forward pass; carries lengths, never text.
    """


class DocumentResult(NamedTuple):
    """What one document produced, in numbers plus the located entities.

    Why: the counts are what may be printed and committed; the entities are
    what the private worksheet is drawn from.

    Contract: `cut_paragraphs` counts paragraphs that needed more than one
    window; `hard_cuts` counts cuts that were not at a sentence end;
    `unknown_pieces` counts pieces the tokenizer could not represent, each of
    which hides at least one word from the model.
    """

    entities: list[Entity]
    windows: int
    cut_paragraphs: int
    hard_cuts: int
    unknown_pieces: int


def load_ner_model(model_dir: Path, *, all_heads: bool = False):
    """Load the pinned model and tokenizer from a local directory, offline.

    Why: the model's own Python is needed to run it. The class comes from the
    copy vendored in `vendored/dictabert_joint/`, read and hash-pinned, so no
    code is fetched from the hub or trusted from the download folder; the
    weights come from `model.safetensors`, never from a pickle.

    Contract: returns `(model, tokenizer)` with the model in eval mode. With
    `all_heads` False the syntax head is left out, which skips the dependency
    tree decoding E1 has no use for; True builds every head, which the smoke
    check uses to show the NER output does not depend on it. Raises whatever
    transformers raises if the directory is incomplete.
    """
    head_switches = {} if all_heads else dict.fromkeys(SWITCHED_OFF_HEADS, False)
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = BertForJointParsing.from_pretrained(
        model_dir,
        local_files_only=True,
        use_safetensors=True,
        **head_switches,
    )
    return model.eval(), tokenizer


def window_entities(model, tokenizer, text: str) -> list[tuple[int, int, str]]:
    """Return the model's entities for one window as (start, end, label).

    Why: the single place the model is called, so the truncation guard cannot
    be skipped.

    Contract: offsets are characters of `text`, end exclusive; `label` has no
    B-/I- prefix. Labels are the model's own argmax grouping with no threshold
    or post-processing. Raises WindowTooLongError if `text` encodes to more
    than MAX_POSITIONS positions.
    """
    positions = len(tokenizer(text)["input_ids"])
    if positions > MAX_POSITIONS:
        raise WindowTooLongError(f"window encodes to {positions} positions, limit {MAX_POSITIONS}")
    # The model's forward rejects any non-None value here when the syntax head
    # is off (BertForJointParsing.py:126-127), and predict defaults it to True.
    syntax_mst = None if model.syntax is None else True
    with torch.inference_mode():
        parsed = model.predict(
            text, tokenizer, compute_syntax_mst=syntax_mst, output_style="json"
        )
    return [(entity["start"], entity["end"], entity["label"]) for entity in parsed["ner_entities"]]


def document_entities(model, tokenizer, paragraphs: list[str]) -> DocumentResult:
    """Run the model over every paragraph of one document.

    Why: moves each entity from window coordinates back to paragraph
    coordinates, which is what the worksheet and the hand count are read in.

    Contract: returns entities in reading order with the cut statistics.
    Raises WindowTooLongError as `window_entities` does.
    """
    entities: list[Entity] = []
    window_count = cut_paragraphs = hard_cuts = unknown_pieces = 0
    for index, paragraph in enumerate(paragraphs):
        windows = split_into_windows(paragraph, lambda word: len(tokenizer.tokenize(word)))
        window_count += len(windows)
        cut_paragraphs += len(windows) > 1
        hard_cuts += sum(window.hard_cut for window in windows)
        unknown_pieces += tokenizer.tokenize(paragraph).count(tokenizer.unk_token)
        for window in windows:
            for start, end, label in window_entities(
                model, tokenizer, paragraph[window.start : window.end]
            ):
                entities.append(Entity(index, window.start + start, window.start + end, label))
    return DocumentResult(entities, window_count, cut_paragraphs, hard_cuts, unknown_pieces)


def check_private_directories(corpus_dir: Path, out_dir: Path) -> None:
    """Refuse directories that would put real document text in the repository.

    Why: CLAUDE.md, hard constraints: no real client documents in the repo, in
    any form. A worksheet is the document in another form.

    Contract: raises ValueError if either directory is inside REPO_ROOT, and
    FileExistsError if `out_dir` already holds a tally, so a hand count is
    never overwritten and never mixed with a different run's highlights.
    """
    for name, directory in (("corpus", corpus_dir), ("output", out_dir)):
        if is_inside(directory, REPO_ROOT):
            raise ValueError(f"the {name} directory is inside the repository; move it outside")
    if (out_dir / "tally.csv").exists():
        raise FileExistsError("the output directory already holds tally.csv; use a new directory")


def code_revision() -> dict[str, object]:
    """Report the commit the harness ran from and whether the tree was clean.

    Why: the findings note cites the code a number was measured with.

    Contract: returns `{"commit": str, "dirty": bool}`. Raises
    CalledProcessError if git is unavailable.
    """

    def git(*arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments], cwd=REPO_ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()

    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}


def run(corpus_dir: Path, out_dir: Path, model_dir: Path) -> None:
    """Process every document and write the private output files.

    Why: see the module docstring.

    Contract: prints one line of counts per document, keyed by document id.
    Raises as `check_private_directories`, `list_documents`, `read_checked`
    and `window_entities` do; nothing is caught, so a failed document stops the
    run instead of shrinking it.
    """
    check_private_directories(corpus_dir, out_dir)
    documents = list_documents(corpus_dir)
    # Asked first: a git failure after the model has run would cost a whole re-run.
    code = code_revision()
    out_dir.mkdir(parents=True, exist_ok=True)
    # Written first, so a document that fails under its id can be looked up.
    with (out_dir / "index.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle).writerows(
            [document_id(position), path.name] for position, path in enumerate(documents, start=1)
        )
    torch.set_num_threads(TORCH_THREADS)
    model, tokenizer = load_ner_model(model_dir)

    per_document = {}
    for position, path in enumerate(documents, start=1):
        doc_id = document_id(position)
        started = time.perf_counter()
        paragraphs = read_checked(doc_id, path)
        result = document_entities(model, tokenizer, paragraphs)
        (out_dir / f"{doc_id}.html").write_text(
            render_document(doc_id, paragraphs, result.entities), encoding="utf-8"
        )
        with (out_dir / f"{doc_id}_spans.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            csv.writer(handle).writerows([SPAN_COLUMNS, *person_span_rows(paragraphs, result.entities)])
        per_document[doc_id] = {
            "paragraphs": len(paragraphs),
            "windows": result.windows,
            "cut_paragraphs": result.cut_paragraphs,
            "hard_cuts": result.hard_cuts,
            "unknown_pieces": result.unknown_pieces,
            "unread_chars": unread_characters(path),
            "per_highlights": count_person_highlights(result.entities),
            "all_entities": len(result.entities),
            "seconds": round(time.perf_counter() - started, 1),
        }
        print(doc_id, json.dumps(per_document[doc_id]), flush=True)

    write_template(
        out_dir / "tally.csv",
        {doc_id: counts["per_highlights"] for doc_id, counts in per_document.items()},
    )
    meta = {
        "model_dir": model_dir.name,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "torch_threads": TORCH_THREADS,
        "code": code,
        "documents": per_document,
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in meta.items() if key != "documents"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in ("--corpus-dir", "--out-dir", "--model-dir"):
        parser.add_argument(flag, type=Path, required=True)
    arguments = parser.parse_args()
    run(arguments.corpus_dir, arguments.out_dir, arguments.model_dir)
