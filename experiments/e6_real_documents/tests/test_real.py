"""Test matrix for real: the draw of the two piles, the worksheet, the labels, the loader.

Every sentence and every name here is made up. No word of the twenty decisions is in a test.

draw (PREREGISTRATION.md, "The two piles")
  EC1  the twenty ids with their topics       the table that is committed in DOCUMENTS
  EC2  each topic                             half open, half closed
  EC3  the ids in another order               the same piles
  EC4  another seed                           another table
  B1   a topic of three documents             one open, two closed: the odd one is closed

runs / worksheet
  EC5  a paragraph                            every run without white space, with its place
  EC6  a worksheet                            `¶K` then each run behind its number
  B2   no paragraph                           an empty worksheet

parse_labels (a label is paragraph, first run, last run, name, person, kind)
  EC7  a bare name in one run                 its place; no attached letters; counted; its kind
  EC8  a full name over two runs              one name
  EC9  a name behind attached letters         the name without them; the letters as `prefix`
  EC10 a comma after the name, a bracket before the initial    the name only
  EC11 an initial with a surname, either geresh                one name with the initial
  EC12 a geresh inside a name, a maqaf inside a name           the name as written
  EC13 a name that is not counted             not counted, no person, no kind
  EC14 a public person                        the kind `public`
  EC15 a name alone on its line, after a list number           `alone`
  EC16 lines in any order                     the names in reading order
  EC17 the same name twice in a paragraph     two names, told apart by their runs
  B3   the first and the last run of a paragraph
  E1   the name is not in the runs
  E2   the name stands twice in the runs, or twice inside one run
  E3   a run or a paragraph that does not exist, the last run before the first, not a number
  E4   a kind that is not one of the three
  E5   a counted name with no person
  E6   one person with two kinds
  E7   two labels on the same characters
  E8   a name that begins or ends inside a word
  E9   another header, a line with a column too few
  E10  runs that reach further than the name
  A1   the error names the document and line numbers, and holds no word of the file

load / read_document
  EC18 a pile                                 its documents in id order, as E5's scorer reads them
  EC19 the digest of E5                       works on them, and changes with the text
  EC20 a document listed as deleted           left out
  EC21 the frozen check switched off           the key is read as it is, from any folder
  E11  a file with another hash than the committed one
  E12  a file that is missing and not listed as deleted
  E13  no key file for a document
  E14  a key file with another hash than the frozen one; no frozen table at all; a document
       that the frozen table does not name
  E15  a pile that does not exist
  E16  a corpus folder inside the repository
"""

import hashlib
from pathlib import Path

import docx
import pytest

import data
import real

P0 = "1. משה כהן"
P1 = "מר משה כהן אמר לכהן, ולגב' לוי (א' ברק) כי ג'ון בן־גוריון הלך."
P2 = "כהן וכהן"
P3 = "שמעון לוין"
PARAGRAPHS = [P0, P1, P2, P3]
HEADER = "paragraph\tfirst\tlast\ttext\tperson\tkind"
GOOD = [
    "0\t1\t2\tמשה כהן\tp1\tprivate",
    "1\t1\t2\tמשה כהן\tp1\tprivate",
    "1\t4\t4\tכהן\tp1\tprivate",
    "1\t6\t6\tלוי\tp2\tprivate",
    "1\t7\t8\tא' ברק\tp3\tpublic",
    "1\t10\t11\tג'ון בן־גוריון\tp4\tprivate",
    "2\t0\t0\tכהן\tp1\tprivate",
    "2\t1\t1\tכהן\tp1\tprivate",
]
TOPICS = {doc_id: topic for doc_id, (topic, _, _) in real.DOCUMENTS.items()}


def labels(*lines: str) -> str:
    """Build the text of a label file."""
    return "\n".join([HEADER, *lines]) + "\n"


def parsed(*lines: str) -> list:
    """Parse label lines against the hand-made paragraphs."""
    return real.parse_labels("t01", labels(*lines), PARAGRAPHS)


def place(paragraph: int, name: str, nth: int = 0) -> tuple[int, int, int]:
    """Return where the nth occurrence of a name stands in a hand-made paragraph."""
    start = -1
    for _ in range(nth + 1):
        start = PARAGRAPHS[paragraph].index(name, start + 1)
    return paragraph, start, start + len(name)


def where(gold) -> tuple[int, int, int]:
    """Return the place of a parsed name."""
    return gold.paragraph, gold.start, gold.end


def test_ec1_the_committed_table_is_what_the_rule_gives() -> None:
    assert len(real.DOCUMENTS) == 20
    assert real.draw(TOPICS) == {doc_id: pile for doc_id, (_, pile, _) in real.DOCUMENTS.items()}


def test_ec2_each_topic_is_halved() -> None:
    piles = real.draw(TOPICS)
    for topic, size in (("sale", 6), ("defamation", 6), ("tenancy", 6), ("accident", 2)):
        ids = [doc_id for doc_id, name in TOPICS.items() if name == topic]
        assert len(ids) == size
        assert sum(piles[doc_id] == real.OPEN for doc_id in ids) == size // 2


def test_ec3_the_order_of_the_ids_does_not_matter() -> None:
    assert real.draw(dict(reversed(TOPICS.items()))) == real.draw(TOPICS)


def test_ec4_another_seed_gives_another_table() -> None:
    assert real.draw(TOPICS, seed="another") != real.draw(TOPICS)


def test_b1_the_odd_document_of_a_topic_is_closed() -> None:
    piles = real.draw({"a": "t", "b": "t", "c": "t"})
    assert sorted(piles.values()) == [real.CLOSED, real.CLOSED, real.OPEN]


def test_ec5_runs() -> None:
    assert real.runs("אב  גד, ה") == [(0, 2), (4, 7), (8, 9)]
    assert real.runs("") == []


def test_ec6_b2_worksheet() -> None:
    assert real.worksheet(["אב גד,", "ה"]) == "¶0\n[0]אב [1]גד,\n¶1\n[0]ה\n"
    assert real.worksheet([]) == ""


def test_ec7_ec8_a_name_in_one_run_and_over_two() -> None:
    surname, full = parsed(GOOD[3], GOOD[1])[::-1]
    assert where(full) == place(1, "משה כהן") and full.name == "משה כהן"
    assert where(surname) == place(1, "לוי") and surname.name == "לוי"
    assert (surname.prefix, surname.counted, surname.person, surname.classes) == ("", True, "p2", frozenset({"private"}))
    assert surname.form == "full" and not surname.alone


def test_ec9_ec10_attached_letters_and_punctuation() -> None:
    (behind,) = parsed(GOOD[2])
    assert where(behind) == place(1, "כהן", 1) and behind.prefix == "ל"
    assert P1[behind.end] == ","
    (second,) = parsed(GOOD[7])
    assert where(second) == place(2, "כהן", 1) and second.prefix == "ו"


@pytest.mark.parametrize("geresh", ["'", "׳"])
def test_ec11_ec14_an_initial_with_a_surname(geresh: str) -> None:
    paragraphs = [f"השופט (א{geresh} ברק) קבע"]
    (gold,) = real.parse_labels("t01", labels(f"0\t1\t2\tא{geresh} ברק\tp1\tpublic"), paragraphs)
    assert paragraphs[0][gold.start : gold.end] == f"א{geresh} ברק"
    assert gold.prefix == "" and gold.classes == frozenset({"public"})


def test_ec12_a_geresh_and_a_maqaf_inside_a_name() -> None:
    (gold,) = parsed(GOOD[5])
    assert where(gold) == place(1, "ג'ון בן־גוריון")


def test_ec13_a_name_that_is_not_counted() -> None:
    (gold,) = parsed("1\t6\t6\tלוי\t-\tnot_counted")
    assert (gold.counted, gold.person, gold.classes) == (False, "*", frozenset())


def test_ec15_alone_on_its_line() -> None:
    alone, not_alone = parsed(GOOD[0], GOOD[1])
    assert alone.alone and not not_alone.alone


def test_ec16_ec17_b3_reading_order_and_the_same_name_twice() -> None:
    gold = parsed(*reversed(GOOD))
    assert [where(item) for item in gold] == sorted(where(item) for item in gold)
    assert [where(item) for item in gold[-2:]] == [place(2, "כהן"), place(2, "כהן", 1)]
    assert where(gold[0]) == place(0, "משה כהן") and gold[0].end == len(P0)
    assert len(gold) == len(GOOD)


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        ("1\t3\t3\tלוי\tp1\tprivate", "E1"),
        ("2\t0\t1\tכהן\tp1\tprivate", "E2"),
        ("1\t13\t13\tהלך\tp1\tprivate", "E3 run"),
        ("4\t0\t0\tכהן\tp1\tprivate", "E3 paragraph"),
        ("1\t2\t1\tכהן\tp1\tprivate", "E3 order"),
        ("1\tx\t1\tכהן\tp1\tprivate", "E3 number"),
        ("1\t-1\t1\tמשה\tp1\tprivate", "E3 negative"),
        ("1\t6\t6\tלוי\tp1\tperson", "E4"),
        ("1\t6\t6\tלוי\t-\tprivate", "E5 dash"),
        ("1\t6\t6\tלוי\t\tprivate", "E5 empty"),
        ("3\t0\t0\tון\tp1\tprivate", "E8 begins inside a word"),
        ("3\t1\t1\tלוי\tp1\tprivate", "E8 ends inside a word"),
        ("1\t6\t6\tלוי\tp1", "E9 columns"),
        ("1\t6\t8\tלוי\tp2\tprivate", "E10 the last run is not touched"),
        ("1\t5\t6\tלוי\tp2\tprivate", "E10 the first run is not touched"),
        ("1\t6\t6\t\tp1\tprivate", "an empty name"),
    ],
)
def test_e1_to_e10_a_bad_line_is_refused(line: str, reason: str) -> None:
    with pytest.raises(real.LabelError, match=r"t01: .*\b3\b") as caught:
        parsed(GOOD[1], line)
    assert not any("א" <= character <= "ת" for character in str(caught.value)), reason


def test_e6_e7_one_person_with_two_kinds_and_two_labels_on_one_place() -> None:
    with pytest.raises(real.LabelError, match="t01"):
        parsed(GOOD[1], "1\t6\t6\tלוי\tp1\tpublic")
    with pytest.raises(real.LabelError, match=r"t01: .*\b3\b"):
        parsed(GOOD[1], "1\t2\t2\tכהן\tp1\tprivate")


def test_e9_another_header() -> None:
    with pytest.raises(real.LabelError, match="t01"):
        real.parse_labels("t01", "paragraph\ttext\n", PARAGRAPHS)


def test_a1_every_bad_line_is_named_at_once() -> None:
    with pytest.raises(real.LabelError, match=r"\b2\b.*\b4\b"):
        parsed("1\t3\t3\tלוי\tp1\tprivate", GOOD[1], "1\t6\t6\tלוי\tp1\tperson")


def write_docx(path: Path, paragraphs: list[str]) -> str:
    """Write paragraphs as a Word file and return the SHA-256 of the file."""
    document = docx.Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    document.save(str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Make a corpus of three made-up documents, two open and one closed, with a frozen key."""
    folder = tmp_path / "corpus"
    (folder / "docs").mkdir(parents=True)
    (folder / "key").mkdir()
    table = {}
    frozen = []
    for doc_id, pile, lines in (("t01", real.OPEN, GOOD), ("t02", real.CLOSED, GOOD[:2]), ("t03", real.OPEN, [])):
        table[doc_id] = ("sale", pile, write_docx(folder / "docs" / f"{doc_id}.docx", PARAGRAPHS))
        key = folder / "key" / f"{doc_id}.tsv"
        key.write_text(labels(*lines), encoding="utf-8", newline="\n")
        frozen.append(f"{doc_id}\t{hashlib.sha256(key.read_bytes()).hexdigest()}")
    (tmp_path / "frozen.tsv").write_text("\n".join(frozen) + "\n", encoding="utf-8")
    monkeypatch.setattr(real, "DOCUMENTS", table)
    monkeypatch.setattr(real, "FROZEN", tmp_path / "frozen.tsv")
    return folder


def test_ec18_a_pile_in_the_shape_of_e5(corpus: Path) -> None:
    documents = real.load(corpus, real.OPEN)
    assert [document.doc_id for document in documents] == ["t01", "t03"]
    first = documents[0]
    assert (first.template, first.kind, first.paragraphs) == ("sale", "judgment", PARAGRAPHS)
    assert len(first.gold) == len(GOOD) and documents[1].gold == []
    assert [document.doc_id for document in real.load(corpus, real.CLOSED)] == ["t02"]


def test_ec19_the_digest_of_e5(corpus: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    before = data.digest(real.load(corpus, real.OPEN))
    assert before == data.digest(real.load(corpus, real.OPEN))
    table = dict(real.DOCUMENTS)
    table["t03"] = ("sale", real.OPEN, write_docx(corpus / "docs" / "t03.docx", [P0]))
    monkeypatch.setattr(real, "DOCUMENTS", table)
    assert data.digest(real.load(corpus, real.OPEN)) != before


def test_ec20_e12_a_document_that_is_gone(corpus: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (corpus / "docs" / "t03.docx").unlink()
    with pytest.raises(real.CorpusError, match="t03"):
        real.load(corpus, real.OPEN)
    monkeypatch.setattr(real, "DELETED", frozenset({"t03"}))
    assert [document.doc_id for document in real.load(corpus, real.OPEN)] == ["t01"]


def test_e11_a_file_with_another_hash(corpus: Path) -> None:
    write_docx(corpus / "docs" / "t01.docx", [P0])
    with pytest.raises(real.CorpusError, match="t01"):
        real.load(corpus, real.OPEN)


def test_e13_e14_ec21_the_key_must_be_the_frozen_one(corpus: Path) -> None:
    key = corpus / "key" / "t01.tsv"
    key.write_text(labels(*GOOD[:3]), encoding="utf-8", newline="\n")
    with pytest.raises(real.CorpusError, match="t01"):
        real.load(corpus, real.OPEN)
    assert len(real.load(corpus, real.OPEN, frozen=False)[0].gold) == 3
    key.unlink()
    with pytest.raises(real.CorpusError, match="t01"):
        real.load(corpus, real.OPEN, frozen=False)


def test_e14_no_frozen_table(corpus: Path) -> None:
    real.FROZEN.unlink()
    with pytest.raises(real.CorpusError, match="frozen"):
        real.load(corpus, real.OPEN)


def test_ec21_another_key_folder(corpus: Path) -> None:
    amended = corpus / "key_amended"
    amended.mkdir()
    for doc_id in ("t01", "t03"):
        (amended / f"{doc_id}.tsv").write_text(labels(*GOOD[:1]), encoding="utf-8", newline="\n")
    assert [len(document.gold) for document in real.load(corpus, real.OPEN, key_dir=amended, frozen=False)] == [1, 1]


def test_e15_a_pile_that_does_not_exist(corpus: Path) -> None:
    with pytest.raises(ValueError, match="pile"):
        real.load(corpus, "both")


def test_e2_the_name_twice_inside_one_run() -> None:
    with pytest.raises(real.LabelError, match=r"t01: .*\b2\b"):
        real.parse_labels("t01", labels("0\t0\t0\tכהן\tp1\tprivate"), ["כהן־כהן"])


def test_e14_a_document_that_the_frozen_table_does_not_name(corpus: Path) -> None:
    lines = real.FROZEN.read_text(encoding="utf-8").splitlines()
    real.FROZEN.write_text("\n".join(line for line in lines if not line.startswith("t03")) + "\n", encoding="utf-8")
    with pytest.raises(real.CorpusError, match="t03"):
        real.load(corpus, real.OPEN)


def test_e16_a_corpus_folder_inside_the_repository() -> None:
    with pytest.raises(real.CorpusError, match="repository"):
        real.read_document(real.HERE / "tests", "r01")
