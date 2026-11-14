"""Test matrix for run.check_corpus.

The model is not loaded here; `main` is exercised by the run itself.

check_corpus
  EC1  the committed corpus                       -> passes
  EC2  a corpus with too few mentions in all      -> TemplateError
  EC3  enough in all, one bucket under the minimum -> TemplateError naming the bucket
  B1   every bucket full, 980 mentions in all     -> TemplateError naming the total

write_worksheets
  EC4  writes a worksheet page and a span list for the four documents of the second
       part and for no other, in E1's formats
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


def test_b1_nine_hundred_mentions_with_every_bucket_full():
    forms = ["full", "given", "surname", "title_surname", "initial_surname", "group_brothers"]
    gold = [mention(form) for form in forms for _ in range(150)]
    gold += [mention("given", classes=frozenset()) for _ in range(40)]
    gold += [mention("title_surname") for _ in range(40)]
    assert len(gold) == 980
    with pytest.raises(TemplateError, match="980 mentions"):
        run.check_corpus(one_document(gold))


def test_ec4_worksheets_for_the_second_part(tmp_path: Path):
    documents = corpus(HERE / "templates", HERE / "names.tsv")
    first = documents[0]
    name = first.gold[0]
    entities = {document.doc_id: [] for document in documents}
    entities["doc01"] = [run.Entity(name.paragraph, name.start, name.end, "PER")]
    run.write_worksheets(documents, entities, tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(
        f"{doc_id}{suffix}" for doc_id in ("doc01", "doc11", "doc21", "doc31") for suffix in (".html", "_spans.csv")
    )
    page = (tmp_path / "doc01.html").read_text(encoding="utf-8")
    assert f"<sup>1</sup>{name.name}</mark>" in page
    rows = (tmp_path / "doc01_spans.csv").read_text(encoding="utf-8-sig").splitlines()
    assert rows[0] == "highlight,paragraph,start,end,text" and len(rows) == 2 and rows[1].endswith(name.name)
    assert (tmp_path / "doc11_spans.csv").read_text(encoding="utf-8-sig").splitlines() == ["highlight,paragraph,start,end,text"]
