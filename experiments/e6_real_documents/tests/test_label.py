"""Test matrix for label: the worksheets, the two labellers put side by side, the frozen key.

Every sentence and every name here is made up.

One hand-made document:
  paragraph 0  `מר משה כהן נ' חברת לוי בע"מ`
  paragraph 1  `כהן טען. גב' רות ברק השיבה לכהן וללוי.`

differences (PREREGISTRATION.md, "How the two are put together")
  EC1  the same labels                        nothing
  EC2  a label only one of the two has        listed, with the kind on its side only
  EC3  the same place with another kind       listed with both kinds
  EC4  two labels that overlap                each listed by itself
  EC5  a place with no difference             not listed

agreement
  EC6  counted names at the same place        the number both have, and the number either has;
                                              a name one of them does not count is not shared
  B1   no label at all                        0 of 0

places (the two lists of places to look at)
  EC7  a word of a labelled name, counted or not, elsewhere    listed as `carry`, also behind
                                              attached letters
  EC8  the word after a title                 listed as `title`
  EC9  a place inside a label, counted or not not listed
  EC14 a word of which a label covers only a part (a name behind attached letters)    not listed
  B2   nothing labelled                       only the words after titles
  EC16 a name labelled only behind attached letters    its bare form elsewhere is listed, and its
                                              form behind other letters (review 1, finding 5)
  EC17 a title of E1's list that E5's list lacks (`הנשיא`, `הנשיאה`, `כב'`), also behind ל    the word after it
                                              is listed (review 1, finding 4)
  EC18 a name particle, an initial            no place of its own

person_splits (review 1, finding 9)
  EC19 places that one labeller gives to one person and the other to two    listed, each once
  EC20 the same persons under other keys      nothing

key_faults (review 1, finding 7)
  EC21 a key made by the rule                 0 and 0
  EC22 a key label that neither labeller has and no list names    counted in the first
  EC23 a label both have that the key lacks, or has with another kind    counted in the second
  EC24 a key label inside a listed place, or on a place only one labeller has    no fault

run_span
  EC10 a place inside one run, over two runs  the numbers of its first and last run

write_worksheets / compare / freeze (on a made-up corpus folder)
  EC11 worksheets                             one per document, of both piles, with no word
                                              that says which pile
  EC12 compare                                per document: how many each has, how many
                                              differ, how many places; a file with a line per
                                              difference and per place
  E1   a labeller's file that is missing      CorpusError that names the document
  EC13 freeze                                 the id and the SHA-256 of every key file
  E2   freeze, a key that breaks the rule     CorpusError that names the document and the two counts
  E3   freeze, a key that cannot be read      LabelError
  EC25 the three commands                     counts only on the screen; freeze writes the table
  E4   freeze, when the table is already there    ValueError, and the table is as it was
  EC15 check                                  per document: how many labels its file holds, or
                                              the bad lines by number, or that there is no file;
                                              nothing stops at the first bad file
"""

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

import docx
import pytest

# The harness is a folder of scripts, not a package: its folder goes on the import path here,
# and `real` adds the three experiments whose code it reuses. No pytest settings file is needed.
sys.path[:0] = [str(Path(__file__).resolve().parents[1])]

import real

import label

P0 = "מר משה כהן נ' חברת לוי בע\"מ"
P1 = "כהן טען. גב' רות ברק השיבה לכהן וללוי."
PARAGRAPHS = [P0, P1]
HEADER = "paragraph\tfirst\tlast\ttext\tperson\tkind"
FULL = "0\t1\t2\tמשה כהן\tp1\tprivate"
FIRM = "0\t5\t5\tלוי\t-\tnot_counted"
SURNAME = "1\t0\t0\tכהן\tp1\tprivate"
WITNESS = "1\t3\t4\tרות ברק\tp2\tprivate"


def gold(*lines: str) -> list:
    """Parse label lines against the hand-made document."""
    return real.parse_labels("t01", "\n".join([HEADER, *lines]) + "\n", PARAGRAPHS)


def at(paragraph: int, word: str, nth: int = 0) -> tuple[int, int, int]:
    """Return where the nth occurrence of a word stands."""
    start = -1
    for _ in range(nth + 1):
        start = PARAGRAPHS[paragraph].index(word, start + 1)
    return paragraph, start, start + len(word)


def test_ec1_ec5_the_same_labels() -> None:
    assert label.differences(gold(FULL, SURNAME), gold(SURNAME, FULL)) == []


def test_ec2_a_label_only_one_has() -> None:
    assert label.differences(gold(FULL, SURNAME), gold(FULL)) == [(*at(1, "כהן"), "private", "")]
    assert label.differences(gold(FULL), gold(FULL, FIRM)) == [(*at(0, "לוי"), "", "not_counted")]


def test_ec3_the_same_place_with_another_kind() -> None:
    public = WITNESS.replace("private", "public")
    assert label.differences(gold(WITNESS), gold(public)) == [(*at(1, "רות ברק"), "private", "public")]
    counted = FIRM.replace("-\tnot_counted", "p3\tprivate")
    assert label.differences(gold(FIRM), gold(counted)) == [(*at(0, "לוי"), "not_counted", "private")]


def test_ec4_two_labels_that_overlap() -> None:
    short = "1\t4\t4\tברק\tp2\tprivate"
    assert label.differences(gold(WITNESS), gold(short)) == [(*at(1, "רות ברק"), "private", ""), (*at(1, "ברק"), "", "private")]


def test_ec6_b1_agreement() -> None:
    counted = FIRM.replace("-\tnot_counted", "p3\tprivate")
    assert label.agreement(gold(FULL, SURNAME, FIRM), gold(FULL, WITNESS, counted)) == (1, 4)
    assert label.agreement(gold(FULL), gold(FULL)) == (1, 1)
    assert label.agreement([], []) == (0, 0)


def test_ec7_ec8_ec9_places() -> None:
    found = label.places(PARAGRAPHS, gold(FULL, FIRM))
    assert (*at(1, "כהן"), "carry") in found
    assert (*at(1, "לכהן"), "carry") in found
    assert (*at(1, "רות"), "title") in found
    assert (*at(1, "וללוי"), "carry") in found
    assert len(found) == 4
    assert not any(place[:3] == at(0, "לוי") for place in found)
    assert not any(place[:3] == at(0, "משה") or place[:3] == at(0, "כהן") for place in found)


def test_b2_nothing_labelled() -> None:
    assert label.places(PARAGRAPHS, []) == [(*at(0, "משה"), "title"), (*at(1, "רות"), "title")]


def test_ec10_run_span() -> None:
    assert label.run_span(P1, *at(1, "רות ברק")[1:]) == (3, 4)
    assert label.run_span(P1, *at(1, "כהן", 1)[1:]) == (6, 6)


def write_docx(path: Path) -> str:
    """Write the hand-made document as a Word file and return the SHA-256 of the file."""
    document = docx.Document()
    for paragraph in PARAGRAPHS:
        document.add_paragraph(paragraph)
    document.save(str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Make a corpus of two made-up documents, one in each pile, with two labellers' files."""
    folder = tmp_path / "corpus"
    (folder / "docs").mkdir(parents=True)
    table = {}
    for doc_id, pile in (("t01", real.OPEN), ("t02", real.CLOSED)):
        table[doc_id] = ("sale", pile, write_docx(folder / "docs" / f"{doc_id}.docx"))
    monkeypatch.setattr(real, "DOCUMENTS", table)
    for name, lines in (("labels_a", [FULL, SURNAME]), ("labels_b", [FULL, WITNESS])):
        (folder / name).mkdir()
        for doc_id in table:
            (folder / name / f"{doc_id}.tsv").write_text("\n".join([HEADER, *lines]) + "\n", encoding="utf-8", newline="\n")
    return folder


def test_ec11_worksheets(corpus: Path) -> None:
    assert label.write_worksheets(corpus) == 2
    for doc_id in ("t01", "t02"):
        text = (corpus / "worksheets" / f"{doc_id}.txt").read_text(encoding="utf-8")
        assert text == real.worksheet(PARAGRAPHS)
        assert real.OPEN not in text and real.CLOSED not in text


def test_ec12_compare(corpus: Path) -> None:
    counts = label.compare(corpus, corpus / "labels_a", corpus / "labels_b")
    assert counts == {doc_id: {"a": 2, "b": 2, "same": 1, "either": 3, "differ": 2, "persons": 0, "places": 1} for doc_id in ("t01", "t02")}
    lines = (corpus / "compare" / "t01.tsv").read_text(encoding="utf-8").splitlines()
    assert lines[0] == "paragraph\tfirst\tlast\ttext\ta\tb\twhy"
    assert "1\t0\t0\tכהן\tprivate\t\tdiffer" in lines
    assert "1\t3\t4\tרות ברק\t\tprivate\tdiffer" in lines
    assert "1\t6\t6\tלכהן\t\t\tcarry" in lines
    assert len(lines) == 4


def test_e1_a_labellers_file_that_is_missing(corpus: Path) -> None:
    (corpus / "labels_b" / "t02.tsv").unlink()
    with pytest.raises(real.CorpusError, match="t02"):
        label.compare(corpus, corpus / "labels_a", corpus / "labels_b")


def test_ec13_freeze(corpus: Path) -> None:
    shutil.copytree(corpus / "labels_a", corpus / "key")
    lines = label.freeze(corpus, corpus / "labels_a", corpus / "labels_b")
    expected = hashlib.sha256((corpus / "key" / "t01.tsv").read_bytes()).hexdigest()
    assert lines == [f"t01\t{expected}", f"t02\t{expected}"]


def test_ec14_a_word_that_a_label_covers_in_part() -> None:
    behind = "1\t6\t6\tכהן\tp1\tprivate"
    found = label.places(PARAGRAPHS, gold(FULL, SURNAME, behind))
    assert not any(place[:3] == at(1, "לכהן") for place in found)
    assert [place[3] for place in found] == ["title"]


def test_ec15_check(corpus: Path) -> None:
    (corpus / "labels_a" / "t02.tsv").write_text(HEADER + "\n1\t9\t9\tכהן\tp1\tprivate\n", encoding="utf-8", newline="\n")
    (corpus / "labels_b" / "t02.tsv").unlink()
    assert label.check(corpus, corpus / "labels_a") == {"t01": "2 labels", "t02": "t02: bad lines 2 (no such runs)"}
    assert label.check(corpus, corpus / "labels_b") == {"t01": "2 labels", "t02": "t02: no label file in labels_b"}


def test_ec16_a_name_labelled_only_behind_attached_letters() -> None:
    paragraphs = ["אמר לכהן דבר", "כהן הלך הביתה", "וכהן חזר"]
    labels = real.parse_labels("t01", HEADER + "\n0\t1\t1\tכהן\tp1\tprivate\n", paragraphs)
    assert label.places(paragraphs, labels) == [(1, 0, 3, "carry"), (2, 0, 4, "carry")]


@pytest.mark.parametrize("title", ["הנשיא", "הנשיאה", "כב'", "לנשיא"])
def test_ec17_a_title_of_e1s_list(title: str) -> None:
    paragraphs = [f"{title} ברק קבע"]
    assert label.places(paragraphs, []) == [(0, len(title) + 1, len(title) + 4, "title")]


def test_ec18_a_particle_and_an_initial_give_no_place() -> None:
    paragraphs = ["י' בן דוד בא", "בן אמר לי' כי בא"]
    labels = real.parse_labels("t01", HEADER + "\n0\t0\t2\tי' בן דוד\tp1\tprivate\n", paragraphs)
    assert label.places(paragraphs, labels) == []


def test_ec19_ec20_person_splits() -> None:
    one = gold(FULL, SURNAME, WITNESS)
    other_keys = gold(FULL.replace("p1", "x"), SURNAME.replace("p1", "x"), WITNESS.replace("p2", "y"))
    assert label.person_splits(one, other_keys) == []
    two = gold(FULL, SURNAME.replace("p1", "p9"), WITNESS)
    expected = [(*at(0, "משה כהן"), "p1", "p1"), (*at(1, "כהן"), "p1", "p9")]
    assert label.person_splits(one, two) == expected
    assert label.person_splits(two, one) == [(*place, second, first) for *place, first, second in expected]


def test_ec21_to_ec24_key_faults() -> None:
    a, b = gold(FULL, SURNAME), gold(FULL, WITNESS)
    behind = "1\t6\t6\tכהן\tp1\tprivate"
    assert label.key_faults(PARAGRAPHS, a, b, gold(FULL, SURNAME, WITNESS, behind)) == (0, 0)
    assert label.key_faults(PARAGRAPHS, a, b, gold(FULL)) == (0, 0)
    assert label.key_faults(PARAGRAPHS, a, b, gold(FULL, "1\t5\t5\tהשיבה\tp7\tprivate")) == (1, 0)
    assert label.key_faults(PARAGRAPHS, a, b, gold(SURNAME)) == (0, 1)
    assert label.key_faults(PARAGRAPHS, a, b, gold(FULL.replace("private", "public"))) == (0, 1)


def test_e2_e3_freeze_refuses_a_key_that_breaks_the_rule(corpus: Path) -> None:
    shutil.copytree(corpus / "labels_a", corpus / "key")
    (corpus / "key" / "t02.tsv").write_text(HEADER + "\n" + SURNAME + "\n1\t5\t5\tהשיבה\tp7\tprivate\n", encoding="utf-8", newline="\n")
    with pytest.raises(real.CorpusError, match=r"t02: 1 .* 1 "):
        label.freeze(corpus, corpus / "labels_a", corpus / "labels_b")
    (corpus / "key" / "t02.tsv").write_text(HEADER + "\n1\t9\t9\tכהן\tp1\tprivate\n", encoding="utf-8", newline="\n")
    with pytest.raises(real.LabelError, match="t02"):
        label.freeze(corpus, corpus / "labels_a", corpus / "labels_b")


def test_ec25_e4_the_three_commands(corpus: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    monkeypatch.setattr(real, "FROZEN", tmp_path / "frozen.tsv")
    arguments = {"corpus": corpus, "a": corpus / "labels_a", "b": corpus / "labels_b"}
    label.main(argparse.Namespace(command="worksheets", **arguments))
    label.main(argparse.Namespace(command="compare", **arguments))
    label.main(argparse.Namespace(command="check", **arguments))
    shutil.copytree(corpus / "labels_a", corpus / "key")
    label.main(argparse.Namespace(command="freeze", **arguments))
    printed = capsys.readouterr().out
    assert "worksheets written: 2" in printed and "2 of 6 = 33.33%" in printed and "t01 2 labels" in printed
    assert not any("א" <= character <= "ת" for character in printed)
    assert real.FROZEN.read_text(encoding="utf-8").splitlines() == label.freeze(corpus, corpus / "labels_a", corpus / "labels_b")
    before = real.FROZEN.read_bytes()
    with pytest.raises(ValueError, match="already"):
        label.main(argparse.Namespace(command="freeze", **arguments))
    assert real.FROZEN.read_bytes() == before
