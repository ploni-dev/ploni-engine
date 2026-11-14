"""Test matrix for list_check: name_variants, listed_places, coverage, list_verdict, report, main.

The rule under test is PREREGISTRATION.md, "the third part". Every document and span here
is made for the test.

The document: four paragraphs. The model highlighted the two full names of ¶0 and, wrongly,
the word `פנו` in ¶2. Every other planted name is missed.
  ¶0  "מר יעקב כהן פגש את גב' רחל לוי"            found: יעקב כהן, רחל לוי
  ¶1  "כהן שילם לרחל, וכשרחל באה שילם גם יעקב"    missed: כהן, רחל (ל), רחל (וכש), יעקב
  ¶2  "משפחת לוי והאחים כהן פנו אל עו"ד פרץ"       missed: לוי, כהן, פרץ
  ¶3  "דנה ואחיה פנו שוב"                          missed: דנה. `פנו` is no name.
The list: 4 rows in ¶1, 3 in ¶2 (פרץ by the title), 1 in ¶3 (`פנו`). 8 rows, 7 on a missed
mention. 8 missed mentions, 7 on the list; `דנה` is off it.

name_variants
  EC1  two words                                  -> both
  EC2  a hyphen or a maqaf between words          -> both words
  EC3  punctuation at the edges of a word         -> taken off; inside a word it stays
  EC4  a word of one letter after that            -> left out
  EC5  leading prefix letters                     -> the word, and the word without them
  B1   taking a prefix letter off leaves three letters -> added; two -> not
  B2   up to three prefix letters are taken off; the cut stops at a letter that is no prefix
  B3   an empty text                              -> nothing

listed_places
  EC6  a name word outside a highlight            -> listed as name_word, prefix letters inside the row
  EC7  a name word under a highlight, or touched by one -> not listed
  EC8  the name word of a highlight in another paragraph -> listed
  EC9  the word after a title, not highlighted    -> listed as after_title
  EC10 a title after a title                      -> neither the second title nor the word after it is
       listed: the search goes on after the second title, as in the throwaway script
  EC11 the word after a title, highlighted        -> not listed
  EC12 a place that is a name word and stands after a title -> one row, name_word
  EC13 rows are in reading order
  B4   one, two and three prefix letters before a name word -> listed; four -> not
  B5   a Hebrew letter straight before or after the name word -> not listed
  B6   up to two prefix letters before a title    -> listed; the other geresh (U+05F3) in a title
  B7   a document with no highlight and no title  -> no row

coverage
  EC14 the document above                         -> 8 rows, 7 on an item, 8 items, 1 off the list
  EC15 a partial mention                          -> not an item
  EC16 a missed full name with a row on one of its words -> on the list
  B8   a row that ends where a missed name starts -> not on the list

read_spans
  EC17 the span list `run.py` writes              -> the spans
  E1   a span list of another document            -> ReaderFileError

list_verdict (90 percent or more predicted; below 80 crosses the threshold)
  B9   90 of 100 -> inside_prediction; 89 of 100 -> outside_prediction
  B10  80 of 100 -> outside_prediction; 79 of 100 -> threshold_crossed
  E2   no missed mention -> ValueError

report, main
  EC18 the report of the document above and of a second document with nothing missed
  EC19 main reads the span lists of a folder and prints that report
"""

from __future__ import annotations

from pathlib import Path

import pytest

import list_check
from generate import Document, Gold
from list_check import Place, Span, coverage, list_verdict, listed_places, name_variants, read_spans, report
from reader_check import ReaderFileError

PARAGRAPHS = [
    "מר יעקב כהן פגש את גב' רחל לוי",
    "כהן שילם לרחל, וכשרחל באה שילם גם יעקב",
    'משפחת לוי והאחים כהן פנו אל עו"ד פרץ',
    "דנה ואחיה פנו שוב",
]


def at(paragraph: int, word: str, nth: int = 0) -> tuple[int, int]:
    """Start and end of the nth standing of `word` in a paragraph."""
    start = -1
    for _ in range(nth + 1):
        start = PARAGRAPHS[paragraph].index(word, start + 1)
    return start, start + len(word)


def gold(paragraph: int, name: str, form: str, nth: int = 0, prefix: str = "", classes: frozenset = frozenset()) -> Gold:
    start, end = at(paragraph, name, nth)
    return Gold(paragraph=paragraph, start=start, end=end, name=name, person="X", form=form, prefix=prefix, alone=False,
                classes=classes, counted=True)


ORDINARY = frozenset({"ordinary"})
GOLD = [
    gold(0, "יעקב כהן", "full"),
    gold(0, "רחל לוי", "full"),
    gold(1, "כהן", "surname"),
    gold(1, "רחל", "given", 0, "ל", ORDINARY),
    gold(1, "רחל", "given", 1, "וכש", ORDINARY),
    gold(1, "יעקב", "given"),
    gold(2, "לוי", "group_family"),
    gold(2, "כהן", "group_brothers"),
    gold(2, "פרץ", "title_surname"),
    gold(3, "דנה", "given"),
]
DOCUMENT = Document(doc_id="doc01", template="letter_test", kind="letter", filling=1, paragraphs=PARAGRAPHS, gold=GOLD)


def span(number: int, paragraph: int, word: str, nth: int = 0) -> Span:
    start, end = at(paragraph, word, nth)
    return Span(number, paragraph, start, end, word)


SPANS = [span(1, 0, "יעקב כהן"), span(2, 0, "רחל לוי"), span(3, 2, "פנו")]

OTHER = Document(doc_id="doc02", template="letter_test", kind="letter", filling=2, paragraphs=["מר דוד לוי"],
                 gold=[Gold(paragraph=0, start=3, end=10, name="דוד לוי", person="Y", form="full", prefix="", alone=False,
                            classes=frozenset(), counted=True)])
OTHER_SPANS = [Span(1, 0, 3, 10, "דוד לוי")]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("יעקב כהן", {"יעקב", "כהן"}),
        ("בן־דוד", {"בן", "דוד"}),
        ("בן-דוד", {"בן", "דוד"}),
        ('"כהן",', {"כהן"}),
        ("ח'טיב", {"ח'טיב"}),
        ("ר' שפירא", {"שפירא", "פירא"}),
        ("שלום", {"שלום", "לום"}),
        ("לוי", {"לוי"}),
        ("ולדימיר", {"ולדימיר", "לדימיר", "דימיר"}),
        ("", set()),
    ],
    ids=["ec1_two_words", "ec2_maqaf", "ec2_hyphen", "ec3_edge_punctuation", "ec3_geresh_inside", "ec4_one_letter_word",
         "b1_three_letters_left", "b1_two_letters_left", "b2_two_prefix_letters_then_none", "b3_empty"],
)
def test_name_variants(text: str, expected: set[str]):
    assert name_variants(text) == expected


def test_ec6_to_ec13_the_list_of_the_document():
    assert listed_places(PARAGRAPHS, SPANS) == [
        Place("name_word", 1, *at(1, "כהן")),
        Place("name_word", 1, *at(1, "לרחל")),
        Place("name_word", 1, *at(1, "וכשרחל")),
        Place("name_word", 1, *at(1, "יעקב")),
        Place("name_word", 2, *at(2, "לוי")),
        Place("name_word", 2, *at(2, "כהן")),
        Place("after_title", 2, *at(2, "פרץ")),
        Place("name_word", 3, *at(3, "פנו")),
    ]


def places(paragraph: str, highlighted: list[str] = (), other: str = "") -> list[tuple[str, str]]:
    """The list of a document of one or two paragraphs, as (kind, text). Highlights are in the first."""
    paragraphs = [paragraph, other] if other else [paragraph]
    spans = []
    for number, word in enumerate(highlighted, start=1):
        start = paragraph.index(word)
        spans.append(Span(number, 0, start, start + len(word), word))
    return [(place.kind, paragraphs[place.paragraph][place.start : place.end]) for place in listed_places(paragraphs, spans)]


def test_ec7_a_name_word_touched_by_a_highlight_is_not_listed():
    # The model highlighted `רחל` and left the prefix letter out: the place `לרחל` shares its characters.
    assert places("לרחל שילמו", ["רחל"]) == []


def test_ec8_the_name_word_of_another_paragraph():
    assert places("רחל לוי באה", ["רחל לוי"], other="אחר כך שילם לוי") == [("name_word", "לוי")]


def test_ec10_a_title_after_a_title():
    assert places("לפני כב' השופט כהן") == []
    assert places("לפני השופט כהן") == [("after_title", "כהן")]


def test_ec11_the_word_after_a_title_under_a_highlight():
    assert places("מר כהן בא", ["כהן"]) == []


def test_ec12_a_name_word_after_a_title_is_one_row():
    assert places("כהן בא, ומר כהן הלך", ["כהן"]) == [("name_word", "כהן")]


@pytest.mark.parametrize(
    ("word", "listed"),
    [("לרחל", True), ("ולרחל", True), ("וכשרחל", True), ("וכשלרחל", False), ("רחלי", False), ("ארחל", False)],
    ids=["b4_one", "b4_two", "b4_three", "b4_four", "b5_letter_after", "b5_letter_before"],
)
def test_b4_b5_letters_around_a_name_word(word: str, listed: bool):
    assert places("רחל באה", ["רחל"], other=f"שילמו {word} היום") == ([("name_word", word)] if listed else [])


@pytest.mark.parametrize(
    ("paragraph", "expected"),
    [
        ('פנו לעו"ד פרץ', [("after_title", "פרץ")]),
        ('פנו ולעו"ד פרץ', [("after_title", "פרץ")]),
        ('פנו וכשעו"ד פרץ', []),
        ("פנו אל גב׳ פרץ", [("after_title", "פרץ")]),
        ("שום דבר כאן", []),
    ],
    ids=["b6_one_prefix", "b6_two_prefixes", "b6_three_prefixes", "b6_other_geresh", "b7_nothing"],
)
def test_b6_b7_titles(paragraph: str, expected: list):
    assert places(paragraph) == expected


def test_ec14_coverage_of_the_document():
    result = coverage(DOCUMENT, SPANS)
    assert (result.rows, result.rows_on_items, len(result.items)) == (8, 7, 8)
    assert [item.name for item in result.off_list] == ["דנה"]


def test_ec15_a_partial_mention_is_not_an_item():
    start, end = at(1, "כהן")
    result = coverage(DOCUMENT, [*SPANS, Span(4, 1, start, end - 1, "כה")])
    assert len(result.items) == 7 and "כהן" not in [item.name for item in result.items if item.paragraph == 1]


def test_ec16_b8_a_row_on_one_word_of_a_missed_full_name():
    paragraphs = ["רחל לוי באה", "יעקב לוי שילם"]
    full = Gold(paragraph=1, start=0, end=8, name="יעקב לוי", person="Z", form="full", prefix="", alone=False,
                classes=frozenset(), counted=True)
    document = Document(doc_id="doc01", template="t", kind="letter", filling=1, paragraphs=paragraphs, gold=[full])
    result = coverage(document, [Span(1, 0, 0, 7, "רחל לוי")])
    assert (result.rows, result.rows_on_items, len(result.items), result.off_list) == (1, 1, 1, [])
    # The row on `לוי` ends at 8. A planted span that starts at 8 touches it and shares no character.
    after = full._replace(start=8, end=13, name=" שילם", form="given")
    result = coverage(document._replace(gold=[after]), [Span(1, 0, 0, 7, "רחל לוי")])
    assert (result.rows_on_items, [item.name for item in result.off_list]) == (0, [" שילם"])


def write_spans(folder: Path, doc_id: str, paragraphs: list[str], spans: list[Span]) -> None:
    lines = ["highlight,paragraph,start,end,text"]
    lines += [f"{s.number},{s.paragraph},{s.start},{s.end},{paragraphs[s.paragraph][s.start:s.end]}" for s in spans]
    (folder / f"{doc_id}_spans.csv").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def test_ec17_read_spans(tmp_path: Path):
    write_spans(tmp_path, "doc01", PARAGRAPHS, SPANS)
    assert read_spans(tmp_path, DOCUMENT) == SPANS


def test_e1_a_span_list_of_another_document(tmp_path: Path):
    write_spans(tmp_path, "doc02", PARAGRAPHS, SPANS)
    with pytest.raises(ReaderFileError, match="not of this document"):
        read_spans(tmp_path, OTHER)


@pytest.mark.parametrize(
    ("on_list", "items", "expected"),
    [(90, 100, "inside_prediction"), (89, 100, "outside_prediction"), (80, 100, "outside_prediction"),
     (79, 100, "threshold_crossed"), (9, 10, "inside_prediction")],
)
def test_b9_b10_list_verdict(on_list: int, items: int, expected: str):
    assert list_verdict(on_list, items) == expected


def test_e2_no_missed_mention():
    with pytest.raises(ValueError, match="no missed mention"):
        list_verdict(0, 0)


EXPECTED_REPORT = [
    "doc01: list rows 8, on a missed mention 7; missed mentions 8, on the list 7",
    "doc02: list rows 0, on a missed mention 0; missed mentions 0, on the list 0",
    "strict PERSON recall from the span lists: 3/11 = 27.27%",
    "cross-check lists: 8 rows (name_word 7, after_title 1) in 1 of 2 documents; 7 of them on a missed mention",
    "missed mentions on the list, pooled: 7/8 = 87.50%",
    "verdict: outside_prediction (prediction 90 percent or more, threshold below 80 percent)",
    "by kind:",
    "  family  1/1 = 100.00%",
    "  brothers  1/1 = 100.00%",
    "  given_ordinary  2/2 = 100.00%",
    "  rest  3/4 = 75.00%",
    "missed mentions off the list:",
    "  doc01 letter_test ¶3 given [דנה] :: דנה ואחיה פנו שוב",
]


def test_ec18_report():
    lines = report([DOCUMENT, OTHER], {"doc01": SPANS, "doc02": OTHER_SPANS}).splitlines()
    assert lines == EXPECTED_REPORT


def test_ec19_main(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(list_check.generate, "corpus", lambda templates, names: [DOCUMENT, OTHER])
    write_spans(tmp_path, "doc01", PARAGRAPHS, SPANS)
    write_spans(tmp_path, "doc02", OTHER.paragraphs, OTHER_SPANS)
    list_check.main(tmp_path)
    assert capsys.readouterr().out.splitlines() == EXPECTED_REPORT
