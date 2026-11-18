"""Test matrix for score_real and detect_real: E5's scorer on documents with a key made by readers.

Every sentence and every name here is made up.

One hand-made document, in each pile:
  paragraph 0  `מר משה כהן נ' רות ברק`
  paragraph 1  `כהן טען. ולברק אין טענה. השופט דן לוי קבע.`
  paragraph 2  `דוד`
Its key: `משה כהן` (p1), `רות ברק` (p2), `כהן` (p1), `ברק` behind `ול` (p2), `דן לוי` (p3,
public), `דוד` (p4). So p3 and p4 are named once.

rows_of (PREREGISTRATION.md, "How it is scored")
  EC1  private, public                        by the kind of the label
  EC2  one_word                               a name with no white space in it
  EC3  prefixed                               a name behind attached letters
  EC4  alone                                  a name that is its whole line
  EC5  lonely                                 a person named once in the document
  EC6  no_trigger                             a name the titles step does not touch when
                                              nothing is marked; a name after `מר` is not one
  EC7  a name that is not counted             in no row

score / row counts
  EC8  a detector that misses two names       all 4/6, and each row by what was missed
  EC9  the same with carry                    the name behind attached letters is found
  EC10 only named methods                     only those are scored
  E5   a key that was changed after the freeze    CorpusError, unless another key folder is named
  E1   a run file made on another text        ValueError that names the file
  E2   the closed pile without named methods, or before CHOSEN.md exists    ValueError
  EC11 the closed pile, named, CHOSEN.md there    scored

extra_places
  EC12 a marked word outside every name       listed; a title is listed as one
  EC13 a marked word inside a name, counted or not    not listed

table / record_lines / listing / write_private / main
  EC14 the table                              best recall first; a row's numbers in its columns;
                                              words marked for nothing per 1,000 words
  EC15 a record line                          the experiment, the pile, the key, the method, the
                                              rows; no word of the document
  EC16 the listing of one method              every name not found and every word marked for
                                              nothing, each with text around it
  E3   a listing inside the repository        ValueError; outside, it is written
  EC17 the command line                       the table titled with pile and key; a record line
                                              per method; the listing where it was asked for

detect_real
  EC18 the open pile                          E5's runner gets the pile's documents under the
                                              name `e6-open`
  E4   the closed pile before CHOSEN.md       ValueError, and nothing is run
  EC19 the closed pile after it               run under the name `e6-closed`
"""

import argparse
import hashlib
import json
from pathlib import Path

import docx
import pytest

import data
import detect_real
import real
import score_real

P0 = "מר משה כהן נ' רות ברק"
P1 = "כהן טען. ולברק אין טענה. השופט דן לוי קבע."
P2 = "דוד"
PARAGRAPHS = [P0, P1, P2]
HEADER = "paragraph\tfirst\tlast\ttext\tperson\tkind"
KEY = [
    "0\t1\t2\tמשה כהן\tp1\tprivate",
    "0\t4\t5\tרות ברק\tp2\tprivate",
    "1\t0\t0\tכהן\tp1\tprivate",
    "1\t2\t2\tברק\tp2\tprivate",
    "1\t6\t7\tדן לוי\tp3\tpublic",
    "2\t0\t0\tדוד\tp4\tprivate",
]


def at(paragraph: int, word: str) -> list[int]:
    """Return where a word first stands."""
    start = PARAGRAPHS[paragraph].index(word)
    return [paragraph, start, start + len(word)]


# What the made-up detector marks: four of the six names and one everyday word.
MARKED = [at(0, "משה כהן"), at(0, "רות ברק"), at(1, "כהן"), at(1, "דן לוי"), at(1, "טענה")]


def write_docx(path: Path) -> str:
    """Write the hand-made document as a Word file and return the SHA-256 of the file."""
    document = docx.Document()
    for paragraph in PARAGRAPHS:
        document.add_paragraph(paragraph)
    document.save(str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Make a corpus of one made-up document per pile, a frozen key and a detector's run files."""
    folder = tmp_path / "corpus"
    (folder / "docs").mkdir(parents=True)
    (folder / "key").mkdir()
    (tmp_path / "runs").mkdir()
    table = {}
    frozen = []
    for doc_id, pile in (("t01", real.OPEN), ("t02", real.CLOSED)):
        table[doc_id] = ("sale", pile, write_docx(folder / "docs" / f"{doc_id}.docx"))
        key = folder / "key" / f"{doc_id}.tsv"
        key.write_text("\n".join([HEADER, *KEY]) + "\n", encoding="utf-8", newline="\n")
        frozen.append(f"{doc_id}\t{hashlib.sha256(key.read_bytes()).hexdigest()}")
    (tmp_path / "frozen.tsv").write_text("\n".join(frozen) + "\n", encoding="utf-8")
    monkeypatch.setattr(real, "DOCUMENTS", table)
    monkeypatch.setattr(real, "FROZEN", tmp_path / "frozen.tsv")
    monkeypatch.setattr(real, "CHOSEN", tmp_path / "CHOSEN.md")
    for doc_id, pile in (("t01", real.OPEN), ("t02", real.CLOSED)):
        run = {
            "dataset": f"e6-{pile}", "corpus_sha256": data.digest(real.load(folder, pile)), "model": "m", "hashes": {"model.safetensors": "abc"},
            "seconds": 2.0, "peak_mb": 100, "tokens": {doc_id: [[*span, 1.0, 1] for span in MARKED]},
        }  # fmt: skip
        (tmp_path / "runs" / f"d.e6-{pile}.json").write_text(json.dumps(run), encoding="utf-8")
    return folder


def test_ec1_to_ec7_rows_of(corpus: Path) -> None:
    (document,) = real.load(corpus, real.OPEN)
    assert score_real.rows_of(document) == {
        "private": {0, 1, 2, 3, 5}, "public": {4}, "one_word": {2, 3, 5}, "prefixed": {3},
        "alone": {5}, "lonely": {4, 5}, "no_trigger": {1, 2, 3, 5},
    }  # fmt: skip


def test_ec7_a_name_that_is_not_counted_is_in_no_row(corpus: Path, tmp_path: Path) -> None:
    key = corpus / "key" / "t01.tsv"
    key.write_text("\n".join([HEADER, *KEY[:5], "2\t0\t0\tדוד\t-\tnot_counted"]) + "\n", encoding="utf-8", newline="\n")
    (document,) = real.load(corpus, real.OPEN, frozen=False)
    assert all(5 not in indexes for indexes in score_real.rows_of(document).values())


def test_ec8_ec9_a_detector_alone_and_with_carry(corpus: Path, tmp_path: Path) -> None:
    results, methods, _, documents = score_real.score(corpus, tmp_path / "runs", real.OPEN, [])
    assert [document.doc_id for document in documents] == ["t01"]
    alone = results["d + whole words"]
    assert alone["real_rows"] == {
        "all": [4, 6], "private": [3, 5], "public": [1, 1], "one_word": [1, 3], "prefixed": [0, 1],
        "alone": [0, 1], "lonely": [1, 2], "no_trigger": [2, 4],
    }  # fmt: skip
    assert (alone["extra"], alone["extra_no_title"]) == (1, 1)
    carried = results["d + carry"]
    assert carried["real_rows"]["all"] == [5, 6] and carried["real_rows"]["prefixed"] == [1, 1]
    assert "d + list" not in methods


def test_ec10_only_named_methods(corpus: Path, tmp_path: Path) -> None:
    results, *_ = score_real.score(corpus, tmp_path / "runs", real.OPEN, ["d + carry"])
    assert list(results) == ["d + carry"]


def test_e1_a_run_file_made_on_another_text(corpus: Path, tmp_path: Path) -> None:
    path = tmp_path / "runs" / "d.e6-open.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({**run, "corpus_sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(ValueError, match="d.e6-open.json"):
        score_real.score(corpus, tmp_path / "runs", real.OPEN, [])


def test_e2_ec11_the_closed_pile(corpus: Path, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="CHOSEN"):
        score_real.score(corpus, tmp_path / "runs", real.CLOSED, ["d + carry"])
    real.CHOSEN.write_text("chosen\n", encoding="utf-8")
    with pytest.raises(ValueError, match="named"):
        score_real.score(corpus, tmp_path / "runs", real.CLOSED, [])
    results, *_ = score_real.score(corpus, tmp_path / "runs", real.CLOSED, ["d + carry"])
    assert results["d + carry"]["real_rows"]["all"] == [5, 6]


def test_ec12_ec13_extra_places(corpus: Path) -> None:
    (document,) = real.load(corpus, real.OPEN)
    spans = [tuple(at(1, "טענה")), tuple(at(0, "מר")), tuple(at(0, "משה")), tuple(at(1, "ולברק"))]
    assert score_real.extra_places(document, spans) == [(*at(0, "מר"), True), (*at(1, "טענה"), False)]
    assert score_real.extra_places(document, []) == []


def test_ec14_the_table(corpus: Path, tmp_path: Path) -> None:
    results, *_ = score_real.score(corpus, tmp_path / "runs", real.OPEN, ["d + whole words", "d + carry"])
    lines = score_real.table("open", results).splitlines()
    assert lines[0] == "### open"
    assert lines[2].split(" | ")[:4] == ["| method", "recall", "found", "private"]
    assert lines[4].startswith("| d + carry | 83.33% | 5/6 | 4/5 | 1/1 | 2/3 | 1/1 | 0/1 | 1/2 | 3/4 | ")
    assert lines[5].startswith("| d + whole words | 66.67% | 4/6 | 3/5 | 1/1 | 1/3 | 0/1 | 0/1 | 1/2 | 2/4 | 1 | 1 | ")
    words = sum(len(paragraph.split()) for paragraph in PARAGRAPHS)
    assert f"| {1000 / words:.2f} |" in lines[5]


def test_ec15_a_record_line(corpus: Path, tmp_path: Path) -> None:
    results, methods, runs, *_ = score_real.score(corpus, tmp_path / "runs", real.OPEN, ["d + carry"])
    (line,) = score_real.record_lines(real.OPEN, "frozen", results, methods, runs)
    entry = json.loads(line)
    assert (entry["experiment"], entry["dataset"], entry["key"], entry["method"]) == ("e6", "open", "frozen", "d + carry")
    assert entry["rows"]["all"] == [5, 6] and entry["steps"] == ["carry"]
    assert entry["detectors"] == [{"name": "d", "model": "m", "hashes": {"model.safetensors": "abc"}}]
    assert not any("א" <= character <= "ת" for character in line)


def test_ec16_the_listing_of_one_method(corpus: Path, tmp_path: Path) -> None:
    results, methods, runs, documents = score_real.score(corpus, tmp_path / "runs", real.OPEN, ["d + carry"])
    lines = score_real.listing("d + carry", methods["d + carry"], documents, runs, results["d + carry"])
    assert len(lines) == 3
    assert sum("דוד" in line and "missed" in line for line in lines) == 1
    assert sum("extra" in line and "[טענה]" in line for line in lines) == 1


def test_e3_a_listing_is_never_written_inside_the_repository(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="repository"):
        score_real.write_private(score_real.HERE / "results" / "errors.txt", ["x"])
    assert not (score_real.HERE / "results" / "errors.txt").exists()
    score_real.write_private(tmp_path / "lists" / "errors.txt", ["x", "y"])
    assert (tmp_path / "lists" / "errors.txt").read_text(encoding="utf-8") == "x\ny\n"


def test_ec17_the_command_line(corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    arguments = argparse.Namespace(
        corpus=corpus, runs_dir=tmp_path / "runs", pile=real.OPEN, only=["d + carry", "d + whole words"], key_dir=None,
        record=tmp_path / "record.jsonl", lists_to=tmp_path / "lists.txt",
    )  # fmt: skip
    score_real.main(arguments)
    printed = capsys.readouterr().out
    assert "### e6 open, frozen key" in printed and "| d + carry | 83.33% |" in printed
    assert not any("א" <= character <= "ת" for character in printed)
    assert len((tmp_path / "record.jsonl").read_text(encoding="utf-8").splitlines()) == 2
    assert "[טענה]" in (tmp_path / "lists.txt").read_text(encoding="utf-8")


def test_ec17_the_command_line_with_another_key(corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    amended = corpus / "key_amended"
    amended.mkdir()
    (amended / "t01.tsv").write_text("\n".join([HEADER, *KEY[:5]]) + "\n", encoding="utf-8", newline="\n")
    arguments = argparse.Namespace(
        corpus=corpus, runs_dir=tmp_path / "runs", pile=real.OPEN, only=["d + carry"], key_dir=amended, record=None, lists_to=None
    )
    score_real.main(arguments)
    printed = capsys.readouterr().out
    assert "### e6 open, key of key_amended, not the frozen one" in printed and "| d + carry | 100.00% | 5/5 |" in printed


def test_ec18_e4_ec19_detect_real(corpus: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(detect_real.detect, "run_documents", lambda *arguments: calls.append(arguments))
    detect_real.run(corpus, real.OPEN, "joint", tmp_path / "m", tmp_path / "out.json")
    detector, model_dir, dataset, documents, out, *rest = calls[0]
    assert (detector, model_dir, dataset, out) == ("joint", tmp_path / "m", "e6-open", tmp_path / "out.json")
    assert [document.doc_id for document in documents] == ["t01"] and rest == [None, None, None]
    with pytest.raises(ValueError, match="CHOSEN"):
        detect_real.run(corpus, real.CLOSED, "joint", tmp_path / "m", tmp_path / "out.json")
    assert len(calls) == 1
    real.CHOSEN.write_text("chosen\n", encoding="utf-8")
    detect_real.run(corpus, real.CLOSED, "hf", tmp_path / "m", tmp_path / "out.json", None, 420.0, "abc")
    assert calls[1][2] == "e6-closed" and calls[1][5:] == (None, 420.0, "abc")


def test_e5_a_key_that_was_changed_after_the_freeze(corpus: Path, tmp_path: Path) -> None:
    key = corpus / "key" / "t01.tsv"
    key.write_text("\n".join([HEADER, *KEY[:5]]) + "\n", encoding="utf-8", newline="\n")
    with pytest.raises(real.CorpusError, match="t01"):
        score_real.score(corpus, tmp_path / "runs", real.OPEN, [])
    results, *_ = score_real.score(corpus, tmp_path / "runs", real.OPEN, ["d + carry"], corpus / "key")
    assert results["d + carry"]["real_rows"]["all"] == [5, 5]
