"""Test matrix for run.check_corpus.

The model is not loaded here; `main` is exercised by the run itself.

check_corpus
  EC1  the committed corpus                       -> passes
  EC2  a corpus with too few mentions in all      -> TemplateError
  EC3  enough in all, one bucket under the minimum -> TemplateError naming the bucket
  B1   every row full, 980 mentions in all        -> TemplateError naming the total
  B2   a row with 29 mentions                      -> TemplateError; with 30 it passes
  EC5  the rows that carry a prediction are all checked: given_plain, prefix_on_name,
       prefix_on_title; given_also_word is not

error_lines
  EC6  a mention that was not found is listed with the text around it, also when it
       stands late in a long paragraph; a found mention is not listed

main
  EC7  the worksheet folder is made before the model is loaded, so a bad folder
       cannot cost a run

write_worksheets
  EC4  writes a worksheet page and a span list for the four documents of the second
       part and for no other, in E1's formats
  EC8  asked for every document (the third part), writes them for all 40

main
  E1   `all_documents` without a worksheet folder -> ValueError before the model is loaded
"""

from __future__ import annotations

from pathlib import Path

import pytest

import run  # first, so that its path set-up runs before `generate` is imported by name
import score
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


def test_b1_under_a_thousand_mentions_with_every_row_full():
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


def full_corpus_gold(**overrides: int) -> list[Gold]:
    """Gold with every checked row at 200 mentions unless `overrides` gives another count."""
    sizes = {"full": 200, "given_plain": 200, "given_ordinary": 200, "surname": 200, "title_surname": 200,
             "initial_surname": 200, "group_brothers": 200}
    sizes.update(overrides)
    gold = []
    for form, count in sizes.items():
        if form == "given_plain":
            gold += [mention("given", classes=frozenset()) for _ in range(count)]
        elif form == "given_ordinary":
            gold += [mention("given") for _ in range(count)]
        else:
            gold += [mention(form) for _ in range(count)]
    return gold


def test_b2_twenty_nine_is_short_and_thirty_is_enough():
    run.check_corpus(one_document(full_corpus_gold(group_brothers=30)))
    with pytest.raises(TemplateError, match="group"):
        run.check_corpus(one_document(full_corpus_gold(group_brothers=29)))


@pytest.mark.parametrize(
    ("changes", "row"),
    [({"given_plain": 0}, "given_plain"), ({"title_surname": 0}, "prefix_on_title")],
)
def test_ec5_every_row_with_a_prediction_is_checked(changes: dict, row: str):
    with pytest.raises(TemplateError, match=row):
        run.check_corpus(one_document(full_corpus_gold(**changes)))


def test_ec5_prefix_on_name_is_checked():
    gold = [entry._replace(prefix="") if entry.form in ("full", "given", "surname", "initial_surname") else entry
            for entry in full_corpus_gold()]
    with pytest.raises(TemplateError, match="prefix_on_name"):
        run.check_corpus(one_document(gold))


def test_ec6_error_lines():
    paragraph = "א" * 200 + " יעקב כהן " + "ב" * 200
    late = Gold(paragraph=0, start=201, end=209, name="יעקב כהן", person="A", form="full", prefix="", alone=False,
                classes=frozenset(), counted=True)
    early = late._replace(paragraph=1, start=0, end=3, name="לוי", form="surname")
    documents = [Document(doc_id="doc01", template="t", kind="letter", filling=1, paragraphs=[paragraph, "לוי בא"], gold=[late, early])]
    outcomes = {"doc01": [score.Outcome(late, "missed", True), score.Outcome(early, "found", False)]}
    (line,) = run.error_lines(documents, outcomes)
    assert line.startswith("  doc01 t ¶0 missed other_label full [יעקב כהן] :: ")
    assert " יעקב כהן " in line and len(line.split(" :: ")[1]) == 70 + 8 + 70


def test_ec7_the_worksheet_folder_is_made_before_the_model_is_loaded(tmp_path: Path, monkeypatch):
    def stop(model_dir):
        raise RuntimeError("the model would be loaded now")

    # No git, no hashing and no model: the test must also pass from a copy outside a checkout.
    monkeypatch.setattr(run, "code_revision", lambda: {"commit": "none", "dirty": False})
    monkeypatch.setattr(run, "pinned_model_hashes", lambda model_dir: {})
    monkeypatch.setattr(run, "load_ner_model", stop)
    target = tmp_path / "new" / "folder"
    with pytest.raises(RuntimeError, match="would be loaded"):
        run.main(tmp_path, False, target)
    assert target.is_dir()


def test_ec8_worksheets_for_every_document(tmp_path: Path):
    documents = corpus(HERE / "templates", HERE / "names.tsv")
    entities = {document.doc_id: [] for document in documents}
    run.write_worksheets(documents, entities, tmp_path, [document.doc_id for document in documents])
    assert sorted(path.name for path in tmp_path.iterdir()) == sorted(
        f"doc{number:02d}{suffix}" for number in range(1, 41) for suffix in (".html", "_spans.csv")
    )


def test_e1_all_documents_needs_a_worksheet_folder(tmp_path: Path, monkeypatch):
    def stop(model_dir):
        raise RuntimeError("the model would be loaded now")

    monkeypatch.setattr(run, "code_revision", lambda: {"commit": "none", "dirty": False})
    monkeypatch.setattr(run, "pinned_model_hashes", lambda model_dir: {})
    monkeypatch.setattr(run, "load_ner_model", stop)
    with pytest.raises(ValueError, match="worksheet folder"):
        run.main(tmp_path, False, None, True)

