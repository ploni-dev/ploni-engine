"""Run experiment E4: generate the corpus, run the model over it, score it against the gold.

Why: Achia asked for a check with a ground truth in place of a check by a person. The
prediction, the threshold and the scoring rule are in PREREGISTRATION.md, committed
before the templates were written and before this script was first run.

Contract: `python -I run.py --model-dir M`, offline, in the environment of
`experiments/e1_hebrew_recall/requirements.txt`. Prints the model hashes, the commit,
the library versions, the size of the corpus and the report of `score.format_report`.
With `--list-errors` it also prints every mention that was not found, with its
paragraph: allowed here because every sentence and every name is generated. Raises
ValueError before the model is loaded if the weights are not the pinned file, and
`generate.TemplateError` if the committed corpus is smaller than the pre-registration
promises.

Known limits: one run. The model is deterministic on one machine; another machine or
thread count could in principle move a borderline word.
"""

from __future__ import annotations

import argparse
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

import generate
import score


def check_corpus(documents: list[generate.Document]) -> None:
    """Refuse a corpus smaller than the pre-registration promises.

    Why: a bucket with a handful of mentions would print a percentage nobody should
    read, and the tests may not have been run before the model is.

    Contract: raises generate.TemplateError naming every bucket under
    MIN_PER_BUCKET, or the total under MIN_COUNTED_MENTIONS.
    """
    counts = generate.bucket_counts(documents)
    short = [name for name, count in counts.items() if name != "all" and count < generate.MIN_PER_BUCKET]
    if counts["all"] < generate.MIN_COUNTED_MENTIONS or short:
        raise generate.TemplateError(f"corpus too small: {counts['all']} mentions, short buckets {short}")


def main(model_dir: Path, list_errors: bool) -> None:
    """Generate, run, score and print.

    Contract: see the module docstring. The corpus is generated and checked before
    the model is loaded, so a broken template stops the run before any number exists.
    """
    torch.set_num_threads(TORCH_THREADS)
    documents = generate.corpus(HERE / "templates", HERE / "names.tsv")
    check_corpus(documents)
    code = code_revision()
    hashes = pinned_model_hashes(model_dir)
    model, tokenizer = load_ner_model(model_dir)

    print(f"E4 planted names, model revision {model_dir.name}")
    for name, digest in hashes.items():
        print(f"{name} sha256 {digest}")
    print(f"code {code['commit']}{', uncommitted changes' if code['dirty'] else ''}")
    print(f"torch {torch.__version__}, transformers {transformers.__version__}, threads {TORCH_THREADS}")
    counted = sum(gold.counted for document in documents for gold in document.gold)
    not_counted = sum(not gold.counted for document in documents for gold in document.gold)
    print(f"corpus: {len(documents)} documents, {sum(len(d.paragraphs) for d in documents)} paragraphs, "
          f"{counted} counted mentions, {not_counted} names that are not counted, seed {generate.SEED}")

    started = time.perf_counter()
    outcomes = {}
    windows = cut_paragraphs = hard_cuts = unknown_pieces = 0
    for document in documents:
        result = document_entities(model, tokenizer, document.paragraphs)
        outcomes[document.doc_id] = score.score_document(document, result.entities)
        windows += result.windows
        cut_paragraphs += result.cut_paragraphs
        hard_cuts += result.hard_cuts
        unknown_pieces += result.unknown_pieces
    print(f"windows {windows}, cut paragraphs {cut_paragraphs}, hard cuts {hard_cuts}, "
          f"unknown pieces {unknown_pieces}, seconds {time.perf_counter() - started:.1f}")
    print(score.format_report(documents, outcomes))
    if list_errors:
        print("mentions not found:")
        for document in documents:
            for item in outcomes[document.doc_id]:
                if item.verdict != "found":
                    gold = item.gold
                    print(f"  {document.doc_id} {document.template} ¶{gold.paragraph} {item.verdict}"
                          f"{' other_label' if item.other_label else ''} {gold.form} "
                          f"[{gold.prefix}{gold.name}] :: {document.paragraphs[gold.paragraph][:160]}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--list-errors", action="store_true")
    arguments = parser.parse_args()
    main(arguments.model_dir, arguments.list_errors)
