"""Run experiment E4: generate the corpus, run the model over it, score it against the gold.

Why: Achia asked for a check with a ground truth in place of a check by a person. The
prediction, the threshold and the scoring rule are in PREREGISTRATION.md, committed
before the templates were written and before this script was first run.

Contract: `python -I run.py --model-dir M [--list-errors] [--worksheets-dir W]`,
offline, in the environment of `experiments/e1_hebrew_recall/requirements.txt`. Prints
the model hashes, the commit, the library versions, the size of the corpus and the
report of `score.format_report`. With `--list-errors` it also prints every mention that
was not found, with the text around it: allowed here because every sentence and every
name is generated. With `--worksheets-dir` it writes, for the four documents of the
second part, the worksheet and the span list E1's readers worked from. Raises
ValueError before the model is loaded if the weights are not the pinned file, and
`generate.TemplateError` if the corpus is smaller than the pre-registration promises.

Known limits: one run. The model is deterministic on one machine; another machine or
thread count could in principle move a borderline word.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
# `python -I` drops the script folder. E1's loader is reused so the model is loaded and
# fed the same way in every experiment; importing it also forces offline mode.
sys.path[:0] = [str(HERE), str(HERE.parent / "e1_hebrew_recall")]

import torch
import transformers
from run_model import TORCH_THREADS, code_revision, document_entities, load_ner_model, pinned_model_hashes
from worksheet import SPAN_COLUMNS, Entity, person_span_rows, render_document

import generate
import score

# How much of the paragraph is printed on each side of a mention that was not found.
ERROR_CONTEXT_CHARACTERS = 70


def check_corpus(documents: list[generate.Document]) -> None:
    """Refuse a corpus smaller than the pre-registration promises.

    Why: a row with a handful of mentions would print a percentage nobody should read,
    and the tests may not have been run before the model is.

    Contract: raises generate.TemplateError naming the total when it is under
    MIN_COUNTED_MENTIONS, and every row that carries a prediction and is under
    MIN_PER_BUCKET. `given_also_word` carries none and is not checked.
    """
    counts = generate.bucket_counts(documents)
    short = [
        name
        for name, count in counts.items()
        if name not in ("all", "given_also_word") and count < generate.MIN_PER_BUCKET
    ]
    if counts["all"] < generate.MIN_COUNTED_MENTIONS or short:
        raise generate.TemplateError(f"corpus too small: {counts['all']} mentions, short rows {short}")


def write_worksheets(documents: list[generate.Document], entities: dict[str, list[Entity]], out_dir: Path) -> None:
    """Write what a reader of the second part works from, in E1's formats.

    Why: the second part compares a Claude reader's count with the gold. The reader
    gets the model's highlights and never the gold, which stays in the generator.

    Contract: for each document of generate.PART_TWO_DOCUMENTS, writes `docNN.html`
    and `docNN_spans.csv` into `out_dir`, as `e1_hebrew_recall/run_model.py` does.
    `entities` maps a document's id to the model's entities for it. Nothing else is
    written, and no file holds a gold position.
    """
    for document in documents:
        if document.doc_id not in generate.PART_TWO_DOCUMENTS:
            continue
        spans = entities[document.doc_id]
        (out_dir / f"{document.doc_id}.html").write_text(
            render_document(document.doc_id, document.paragraphs, spans), encoding="utf-8"
        )
        with (out_dir / f"{document.doc_id}_spans.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            csv.writer(handle).writerows([SPAN_COLUMNS, *person_span_rows(document.paragraphs, spans)])


def run_model(documents: list[generate.Document], model, tokenizer) -> tuple[dict[str, list[Entity]], str]:
    """Run the model over every document.

    Contract: returns the entities per document id, and one line of counts for the
    report: windows, cut paragraphs, hard cuts, unknown pieces, seconds.
    """
    started = time.perf_counter()
    entities = {}
    totals = dict.fromkeys(("windows", "cut_paragraphs", "hard_cuts", "unknown_pieces"), 0)
    for document in documents:
        result = document_entities(model, tokenizer, document.paragraphs)
        entities[document.doc_id] = result.entities
        for name in totals:
            totals[name] += getattr(result, name)
    counts = ", ".join(f"{name.replace('_', ' ')} {count}" for name, count in totals.items())
    return entities, f"{counts}, seconds {time.perf_counter() - started:.1f}"


def error_lines(documents: list[generate.Document], outcomes: dict[str, list[score.Outcome]]) -> list[str]:
    """List every mention that was not found, with the text around it.

    Contract: one line per partial or missed mention, in corpus order: document,
    template, paragraph, verdict, `other_label` where it applies, form, the prefix
    and name in brackets, then ERROR_CONTEXT_CHARACTERS of the paragraph on each side.
    """
    lines = []
    for document in documents:
        for item in outcomes[document.doc_id]:
            if item.verdict == "found":
                continue
            gold = item.gold
            text = document.paragraphs[gold.paragraph]
            window = text[max(0, gold.start - ERROR_CONTEXT_CHARACTERS) : gold.end + ERROR_CONTEXT_CHARACTERS]
            lines.append(
                f"  {document.doc_id} {document.template} ¶{gold.paragraph} {item.verdict}"
                f"{' other_label' if item.other_label else ''} {gold.form} [{gold.prefix}{gold.name}] :: {window}"
            )
    return lines


def main(model_dir: Path, list_errors: bool, worksheets_dir: Path | None) -> None:
    """Print the E4 report for the pinned model.

    Contract: see the module docstring. The corpus is generated and checked, and the
    worksheet folder is made, before the model is loaded, so a broken template or a
    bad folder stops the run before any number exists.
    """
    torch.set_num_threads(TORCH_THREADS)
    documents = generate.corpus(HERE / "templates", HERE / "names.tsv")
    check_corpus(documents)
    if worksheets_dir is not None:
        # Before the model is loaded: a folder that cannot be made must not cost a run.
        worksheets_dir.mkdir(parents=True, exist_ok=True)
    code = code_revision()
    hashes = pinned_model_hashes(model_dir)
    model, tokenizer = load_ner_model(model_dir)

    print(f"E4 planted names, model revision {model_dir.name}")
    for name, digest in hashes.items():
        print(f"{name} sha256 {digest}")
    print(f"code {code['commit']}{', uncommitted changes' if code['dirty'] else ''}")
    print(f"torch {torch.__version__}, transformers {transformers.__version__}, threads {TORCH_THREADS}")
    gold = [item for document in documents for item in document.gold]
    print(
        f"corpus: {len(documents)} documents, {sum(len(document.paragraphs) for document in documents)} paragraphs, "
        f"{sum(item.counted for item in gold)} counted mentions, "
        f"{sum(not item.counted for item in gold)} names that are not counted, seed {generate.SEED}"
    )
    entities, counts = run_model(documents, model, tokenizer)
    print(counts)
    outcomes = {document.doc_id: score.score_document(document, entities[document.doc_id]) for document in documents}
    print(score.format_report(documents, outcomes))
    if list_errors:
        print("mentions not found:", *error_lines(documents, outcomes), sep="\n")
    if worksheets_dir is not None:
        write_worksheets(documents, entities, worksheets_dir)
        print(f"worksheets written for {', '.join(generate.PART_TWO_DOCUMENTS)}")


if __name__ == "__main__":
    # `python -I` ignores PYTHONUTF8, and a Windows pipe would get the ANSI code page.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--list-errors", action="store_true")
    parser.add_argument("--worksheets-dir", type=Path)
    arguments = parser.parse_args()
    main(arguments.model_dir, arguments.list_errors, arguments.worksheets_dir)
