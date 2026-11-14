"""Test matrix for run.check_corpus.

The model is not loaded here; `main` is exercised by the run itself.

check_corpus
  EC1  the committed corpus                       -> passes
  EC2  a corpus with too few mentions in all      -> TemplateError
  EC3  enough in all, one bucket under the minimum -> TemplateError naming the bucket
"""

from __future__ import annotations

from pathlib import Path

import pytest

import run  # first, so that its path set-up runs before `generate` is imported by name
from generate import Document, Gold, TemplateError, corpus

HERE = Path(__file__).resolve().parent.parent


def mention(form: str, **changes) -> Gold:
    base = Gold(paragraph=0, start=0, end=3, name="כהן", person="A", form=form, prefix="ל", alone=True,
                classes=frozenset({"ordinary"}), counted=True)
    return base._replace(**changes)


def one_document(gold: list[Gold]) -> list[Document]:
    return [Document(doc_id="doc01", template="t", kind="letter", filling=1, paragraphs=["כהן"], gold=gold)]


def test_ec1_the_committed_corpus_passes():
    run.check_corpus(corpus(HERE / "templates", HERE / "names.tsv"))


def test_ec2_too_few_mentions():
    with pytest.raises(TemplateError, match="corpus too small"):
        run.check_corpus(one_document([mention("full")]))


def test_ec3_one_bucket_short():
    forms = ["full", "given", "surname", "title_surname", "initial_surname"]
    gold = [mention(form) for form in forms for _ in range(250)]
    with pytest.raises(TemplateError, match="group"):
        run.check_corpus(one_document(gold))
