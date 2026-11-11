"""Run experiment E3: segment each hand-written form and score the replacement.

Why: build-plan.md section 11, E3. The prediction, the threshold and the
scoring rule are in PREREGISTRATION.md and scoring.py, committed before this
script was first run.

Contract: `python -I run.py --model-dir M`, offline. Prints the per-category
counts, the verdict and every failing form. Prints Hebrew text, which is
allowed here because every sentence in forms.tsv was invented for this
experiment. Raises LookupError if the model splits a sentence so that the
target is not exactly one token: a harness fault, never counted as a miss.

Known limits: one batch, one run. The model is deterministic on one machine,
so a second run adds nothing; another machine or thread count could in
principle move a borderline token.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
# `python -I` drops the script folder. E1's loader is reused so the model is
# loaded one way in every experiment; importing it also forces offline mode.
sys.path[:0] = [str(HERE), str(HERE.parent / "e1_hebrew_recall")]

import torch
from run_model import TORCH_THREADS, load_ner_model

import scoring


def segment_all(model, tokenizer, sentences: list[str]) -> list[list[dict]]:
    """Return the model's token list for every sentence, in order.

    Contract: one forward pass over all sentences. The syntax head is off, so
    the tree decoding flag must be None (see e1_hebrew_recall/run_model.py).
    """
    with torch.inference_mode():
        parsed = model.predict(sentences, tokenizer, compute_syntax_mst=None, output_style="json")
    return [sentence["tokens"] for sentence in parsed]


def main(model_dir: Path) -> None:
    """Score every form and print the report."""
    torch.set_num_threads(TORCH_THREADS)
    forms = scoring.load_forms(HERE / "forms.tsv")
    model, tokenizer = load_ner_model(model_dir)
    token_lists = segment_all(model, tokenizer, [form.sentence for form in forms])

    strict, prefix_only, failures = Counter(), Counter(), []
    for form, tokens in zip(forms, token_lists):
        try:
            seg, suffix = scoring.model_segments(tokens, form.target)
        except LookupError as error:
            raise LookupError(f"{form.id}: {error}") from None
        produced = scoring.replace_base(seg, form.surrogate)
        prefix_only[form.category] += produced == form.prefix + form.surrogate
        if scoring.is_correct(form, seg, suffix):
            strict[form.category] += 1
        else:
            failures.append((form, seg, suffix, produced))

    print(f"E3 prefix-preserving replacement, model revision {model_dir.name}")
    print(f"torch {torch.__version__}, threads {TORCH_THREADS}")
    print(f"{'category':<16} {'strict':>7} {'prefix only':>12}")
    for category, size in scoring.FORMS_PER_CATEGORY.items():
        print(f"{category:<16} {strict[category]:>4}/{size:<2} {prefix_only[category]:>9}/{size:<2}")
    correct = sum(strict.values())
    print(f"{'total':<16} {correct:>4}/{len(forms)} {sum(prefix_only.values()):>8}/{len(forms)}")
    print(f"verdict: {scoring.verdict(correct, len(forms))}")
    errors = Counter(form.category for form, *_ in failures)
    print(f"more than half of errors in construct and possessive_like: {scoring.breaks_where_predicted(errors)}")
    print("failures (id, category, target, model seg, suffix, produced, expected):")
    for form, seg, suffix, produced in failures:
        print(f"  {form.id} {form.category} {form.target} {'+'.join(seg)} {suffix} "
              f"{produced} {form.prefix + form.surrogate}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-dir", type=Path, required=True)
    main(parser.parse_args().model_dir)
