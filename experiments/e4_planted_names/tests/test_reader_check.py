"""Test matrix for reader_check: read_reader_files, compare, agreement_verdict.

The rule under test is PREREGISTRATION.md, "The second part, fixed before the run". Every
document, highlight and reader file here is made for the test.

The document: three paragraphs.
  ¶0  "מר יעקב כהן פגש את רחל לוי"     counted: יעקב כהן (3..11), רחל לוי (19..26)
  ¶1  "כהן שילם לרחל ולרחל"             counted: כהן (0..3), רחל (10..13), רחל (16..19)
  ¶2  "ראו גבאי נ' פרץ"                 not counted: גבאי (4..8), פרץ (12..15)

compare, a reader who makes no mistake
  EC1  a mention under one highlight marked found                 -> agrees
  EC2  a full name under two highlights, found and surplus         -> agrees
  EC3  a highlight on part of a name, marked partial, with its line -> agrees
  EC4  a mention with no highlight, and a miss line for it          -> agrees
  EC5  a name that is not counted, its highlight marked not_person  -> agrees
  EC6  a name that is not counted and has no highlight              -> agrees

compare, a reader who is wrong
  EC7  the reader marks a partial highlight found                   -> that mention disagrees
  EC8  the reader has no miss line for a missed mention             -> that mention disagrees
  EC9  the reader marks found a highlight on a name that is not counted
       -> that item disagrees, and one reader-only item is added
  EC10 the same with `extra` 1                                     -> two reader-only items in all
  EC11 a found highlight on one counted mention with `extra` 1      -> one reader-only item
  EC12 a miss line that fits no mention                             -> one reader-only item
  EC13 a highlight on plain text marked found                       -> one reader-only item
  EC14 a miss line for a mention the model found                    -> the line is left over

Pairing of miss lines
  B1   two missed mentions with the same name, one line             -> one agrees, one does not
  B2   two missed mentions with the same name, two lines            -> both agree
  B3   the line's text holds prefix letters around the name         -> paired
  B4   a line whose text is exactly the name is paired before a wider one,
       whatever the order in the file
  B5   a line of another paragraph                                  -> not paired, left over
  B6   a miss line is never paired with a name that is not counted  -> left over

read_reader_files, a file that does not follow the guide
  E1   the marks do not cover every highlight exactly once          -> ReaderFileError
  E2   an unknown verdict, or an `extra` that is not a whole number -> ReaderFileError
  E3   a partial line without a highlight number, or with one that does not exist
  E4   a highlight marked partial with no partial line, or the other way round
  E5   a miss line of an unknown kind

compare, a span list that is not of this document
  E7   a highlight whose text is not what the document holds at its position -> ReaderFileError

More cases, added after the review of the script and before any reader's file was opened
  EC15 every reader-only item has a line in the list of disagreements
  EC16 two partial lines that name one highlight, which covers part of two names -> accepted
  EC17 two names under one highlight: `extra` 1 -> no reader-only item; `extra` 0 -> still
       agrees (a known limit: people short of the gold are not counted)
  EC18 a name that is not counted under a highlight marked surplus or partial -> disagrees
  EC19 a partial highlight on plain text is one reader-only item plus its `extra`; `extra`
       on a partial highlight that overlaps a mention adds nothing; a surplus highlight
       on plain text adds nothing
  EC20 a highlight marked partial and another marked found on one name -> the reader says partial
  B9   exact text first, with two different names: mentions `כהן` then `יעקב כהן` in one
       paragraph, lines `יעקב כהן` then `לכהן` -> both paired
  B10  a line whose text lies inside the name (`כהן` for `יעקב כהן`) -> paired
  B11  a highlight that ends where the name starts, or starts where it ends -> no overlap
  E8   a highlight marked twice; an empty `extra`; a miss line with no text; a paragraph
       that is not a number; a missed line that carries a highlight number
  E9   a file whose header lacks a column it needs, or with no header at all
  E11  a row with more cells than the header (a comma in a note or in a text, with no
       quotes; a comma too many at the end of a row) -> ReaderFileError
  B13  a header with spaces after its commas -> accepted
  E10  a span list with a paragraph the document does not have -> ReaderFileError
  B12  a highlight with a space at its edge is of this document
  EC21 main prints the pooled line over the four documents, reader-only items in the
       denominator, and lists them

agreement_verdict (98 percent or more predicted; below 95 crosses the threshold)
  B7   98 of 100 -> inside_prediction; 97 of 100 -> outside_prediction
  B8   95 of 100 -> outside_prediction; 94 of 100 -> threshold_crossed
  E6   nothing compared -> ValueError
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generate import Document, Gold
import reader_check
from generate import corpus
from reader_check import ReaderFileError, agreement_verdict, compare, read_reader_files

HERE = Path(__file__).resolve().parent.parent

PARAGRAPHS = ["מר יעקב כהן פגש את רחל לוי", "כהן שילם לרחל ולרחל", "ראו גבאי נ' פרץ"]


def gold(paragraph: int, start: int, end: int, counted: bool = True) -> Gold:
    return Gold(paragraph=paragraph, start=start, end=end, name=PARAGRAPHS[paragraph][start:end], person="A",
                form="full", prefix="", alone=False, classes=frozenset(), counted=counted)


GOLD = [gold(0, 3, 11), gold(0, 19, 26), gold(1, 0, 3), gold(1, 10, 13), gold(1, 16, 19),
        gold(2, 4, 8, counted=False), gold(2, 12, 15, counted=False)]
DOCUMENT = Document(doc_id="doc01", template="t", kind="letter", filling=1, paragraphs=PARAGRAPHS, gold=GOLD)

# The model's highlights for the faultless case: number, paragraph, start, end.
#   1 יעקב   2 כהן (¶0)   3 רחל of "רחל לוי"   4 כהן (¶1)   5 גבאי (not counted)
# The two רחל of ¶1 have no highlight, and פרץ has none.
SPANS = [(1, 0, 3, 7), (2, 0, 8, 11), (3, 0, 19, 22), (4, 1, 0, 3), (5, 2, 4, 8)]
MARKS = {1: ("found", 0), 2: ("surplus", 0), 3: ("partial", 0), 4: ("found", 0), 5: ("not_person", 0)}
MISSES = [(0, "רחל לוי", "partial", 3), (1, "רחל", "missed", None), (1, "רחל", "missed", None)]


def write(folder: Path, spans=SPANS, marks=MARKS, misses=MISSES) -> Path:
    lines = ["highlight,paragraph,start,end,text"]
    lines += [f"{number},{paragraph},{start},{end},{PARAGRAPHS[paragraph][start:end]}" for number, paragraph, start, end in spans]
    (folder / "doc01_spans.csv").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    lines = ["highlight,verdict,group,extra,note"]
    lines += [f"{number},{verdict},{'-' if verdict == 'not_person' else 'private'},{extra}," for number, (verdict, extra) in marks.items()]
    (folder / "doc01_marks.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    lines = ["doc_id,paragraph,text,kind,group,other_label,category,highlight"]
    lines += [f"doc01,{paragraph},{text},{kind},private,no,other,{'' if number is None else number}" for paragraph, text, kind, number in misses]
    (folder / "doc01_misses.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return folder


def result(folder: Path, **changes):
    return compare(DOCUMENT, read_reader_files(write(folder, **changes), "doc01"))


def test_ec1_to_ec6_a_reader_who_makes_no_mistake(tmp_path: Path):
    outcome = result(tmp_path)
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 7, 0)
    assert outcome.disagreements == []


def test_ec7_a_partial_marked_found(tmp_path: Path):
    marks = {**MARKS, 3: ("found", 0)}
    outcome = result(tmp_path, marks=marks, misses=MISSES[1:])
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 6, 0)
    assert len(outcome.disagreements) == 1 and "רחל לוי" in outcome.disagreements[0]


def test_ec8_b1_one_line_for_two_missed_mentions(tmp_path: Path):
    outcome = result(tmp_path, misses=MISSES[:2])
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 6, 0)


def test_b2_two_lines_for_two_missed_mentions(tmp_path: Path):
    assert result(tmp_path).agreeing == 7


def test_ec9_ec10_found_on_a_name_that_is_not_counted(tmp_path: Path):
    outcome = result(tmp_path, marks={**MARKS, 5: ("found", 0)})
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 6, 1)
    outcome = result(tmp_path, marks={**MARKS, 5: ("found", 1)})
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 6, 2)


def test_ec11_extra_beyond_the_mention_under_the_highlight(tmp_path: Path):
    outcome = result(tmp_path, marks={**MARKS, 4: ("found", 1)})
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 7, 1)


def test_ec12_b5_a_miss_line_that_fits_nothing(tmp_path: Path):
    outcome = result(tmp_path, misses=[*MISSES, (1, "דוד", "missed", None)])
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 7, 1)
    moved = [MISSES[0], (2, "רחל", "missed", None), MISSES[2]]
    outcome = result(tmp_path, misses=moved)
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 6, 1)


def test_ec13_found_on_plain_text(tmp_path: Path):
    spans = [*SPANS, (6, 1, 4, 8)]
    outcome = result(tmp_path, spans=spans, marks={**MARKS, 6: ("found", 0)})
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 7, 1)
    outcome = result(tmp_path, spans=spans, marks={**MARKS, 6: ("not_person", 0)})
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 7, 0)


def test_ec14_a_miss_line_for_a_found_mention(tmp_path: Path):
    outcome = result(tmp_path, misses=[*MISSES, (1, "כהן", "missed", None)])
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 7, 1)


def test_b3_the_line_holds_prefix_letters(tmp_path: Path):
    misses = [MISSES[0], (1, "לרחל", "missed", None), (1, "ולרחל", "missed", None)]
    assert result(tmp_path, misses=misses).agreeing == 7


def test_b4_exact_text_is_paired_first(tmp_path: Path):
    # The wide line comes first in the file. It must not take the place of an exact one:
    # with one wide and one exact line, both mentions are paired whichever comes first.
    for misses in ([MISSES[0], (1, "לרחל ולרחל", "missed", None), (1, "רחל", "missed", None)],
                   [MISSES[0], (1, "רחל", "missed", None), (1, "לרחל ולרחל", "missed", None)]):
        outcome = result(tmp_path, misses=misses)
        assert (outcome.agreeing, outcome.reader_only) == (7, 0)


def test_b6_a_miss_line_for_a_name_that_is_not_counted(tmp_path: Path):
    outcome = result(tmp_path, misses=[*MISSES, (2, "פרץ", "missed", None)])
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 7, 1)


@pytest.mark.parametrize(
    "changes",
    [
        {"marks": {number: mark for number, mark in MARKS.items() if number != 2}},
        {"marks": {**MARKS, 6: ("found", 0)}},
        {"marks": {**MARKS, 1: ("certain", 0)}},
        {"marks": {**MARKS, 1: ("found", "x")}},
        {"marks": {**MARKS, 1: ("found", -1)}},
        {"misses": [(0, "רחל לוי", "partial", None), *MISSES[1:]]},
        {"misses": [(0, "רחל לוי", "partial", 9), *MISSES[1:]]},
        {"misses": MISSES[1:]},
        {"marks": {**MARKS, 3: ("found", 0)}},
        {"misses": [*MISSES, (1, "רחל", "overlooked", None)]},
        {"marks": {**MARKS, 1: ("found", "")}},
        {"misses": [*MISSES, (1, "", "missed", None)]},
        {"misses": [*MISSES, ("x", "רחל", "missed", None)]},
        {"misses": [MISSES[0], (1, "רחל", "missed", 4), MISSES[2]]},
    ],
    ids=["e1_mark_missing", "e1_mark_for_no_highlight", "e2_unknown_verdict", "e2_extra_not_a_number", "e2_extra_negative",
         "e3_partial_line_without_number", "e3_partial_line_unknown_number", "e4_partial_mark_without_line",
         "e4_partial_line_without_mark", "e5_unknown_kind", "e8_empty_extra", "e8_line_without_text",
         "e8_paragraph_not_a_number", "e8_missed_line_with_a_highlight"],
)
def test_e1_to_e5_files_that_do_not_follow_the_guide(tmp_path: Path, changes: dict):
    with pytest.raises(ReaderFileError):
        read_reader_files(write(tmp_path, **changes), "doc01")


@pytest.mark.parametrize(
    ("agreeing", "expected"),
    [(100, "inside_prediction"), (98, "inside_prediction"), (97, "outside_prediction"), (95, "outside_prediction"),
     (94, "threshold_crossed")],
)
def test_b7_b8_agreement_verdict(agreeing: int, expected: str):
    assert agreement_verdict(agreeing, 100) == expected


def test_e6_nothing_compared():
    with pytest.raises(ValueError):
        agreement_verdict(0, 0)


def test_e7_a_span_list_of_another_document(tmp_path: Path):
    files = read_reader_files(write(tmp_path), "doc01")
    other = DOCUMENT._replace(paragraphs=["x" * 30, PARAGRAPHS[1], PARAGRAPHS[2]])
    with pytest.raises(ReaderFileError, match="not of this document"):
        compare(other, files)


def test_ec15_reader_only_items_are_listed(tmp_path: Path):
    outcome = result(tmp_path, marks={**MARKS, 5: ("found", 1)}, misses=[*MISSES, (1, "דוד", "missed", None)])
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 6, 3)
    assert len(outcome.disagreements) == 3
    assert any("גבאי" in line and "not counted" in line for line in outcome.disagreements)
    assert any("highlight 5" in line and "2 reader-only" in line for line in outcome.disagreements)
    assert any("דוד" in line and "miss line" in line for line in outcome.disagreements)


def test_ec16_two_partial_lines_for_one_highlight(tmp_path: Path):
    # Highlight 3 now runs from the end of one name into the start of the next: "כהן פגש את רחל".
    spans = [SPANS[0], (2, 0, 8, 22), SPANS[3], SPANS[4]]
    marks = {1: ("partial", 0), 2: ("partial", 0), 4: ("found", 0), 5: ("not_person", 0)}
    misses = [(0, "יעקב כהן", "partial", 1), (0, "רחל לוי", "partial", 2), (0, "יעקב כהן", "partial", 2), *MISSES[1:]]
    files = read_reader_files(write(tmp_path, spans=spans, marks=marks, misses=misses), "doc01")
    assert sorted(line.highlight for line in files.misses if line.kind == "partial") == [1, 2, 2]


def test_ec17_two_names_under_one_highlight(tmp_path: Path):
    spans = [(1, 0, 3, 26), SPANS[3], SPANS[4]]
    for extra in (1, 0):
        marks = {1: ("found", extra), 4: ("found", 0), 5: ("not_person", 0)}
        outcome = result(tmp_path, spans=spans, marks=marks, misses=MISSES[1:])
        assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 7, 0)
    outcome = result(tmp_path, spans=spans, marks={1: ("found", 2), 4: ("found", 0), 5: ("not_person", 0)}, misses=MISSES[1:])
    assert (outcome.agreeing, outcome.reader_only) == (7, 1)


@pytest.mark.parametrize("verdict", ["surplus", "partial"])
def test_ec18_a_name_that_is_not_counted_under_another_verdict(tmp_path: Path, verdict: str):
    misses = [*MISSES, (2, "גבאי", "partial", 5)] if verdict == "partial" else MISSES
    outcome = result(tmp_path, marks={**MARKS, 5: (verdict, 0)}, misses=misses)
    assert (outcome.items, outcome.agreeing) == (7, 6)
    assert outcome.reader_only == (1 if verdict == "partial" else 0)


def test_ec19_reader_only_items_by_verdict(tmp_path: Path):
    spans = [*SPANS, (6, 1, 4, 8)]

    def reader_only(verdict: str, extra: int, base=MARKS) -> int:
        misses = [*MISSES, (1, "שילם", "partial", 6)] if verdict == "partial" else MISSES
        return result(tmp_path, spans=spans, marks={**base, 6: (verdict, extra)}, misses=misses).reader_only

    assert reader_only("partial", 0) == 1
    assert reader_only("partial", 2) == 3
    assert reader_only("surplus", 0) == 0
    assert reader_only("surplus", 3) == 0
    # `extra` on the partial highlight 3, which overlaps a counted mention, adds nothing.
    assert reader_only("not_person", 0, base={**MARKS, 3: ("partial", 2)}) == 0


def test_ec20_partial_wins_over_found_on_one_name(tmp_path: Path):
    marks = {**MARKS, 1: ("partial", 0), 2: ("found", 0)}
    misses = [(0, "יעקב כהן", "partial", 1), *MISSES]
    outcome = result(tmp_path, marks=marks, misses=misses)
    assert (outcome.items, outcome.agreeing) == (7, 6)
    assert any("יעקב כהן" in line and "reader partial" in line for line in outcome.disagreements)


TWO_NAMES = ["כהן פגש את יעקב כהן"]
TWO_GOLD = [
    Gold(paragraph=0, start=0, end=3, name="כהן", person="A", form="surname", prefix="", alone=False, classes=frozenset(), counted=True),
    Gold(paragraph=0, start=11, end=19, name="יעקב כהן", person="B", form="full", prefix="", alone=False, classes=frozenset(), counted=True),
]
TWO_DOCUMENT = Document(doc_id="doc01", template="t", kind="letter", filling=1, paragraphs=TWO_NAMES, gold=TWO_GOLD)


def two_names(folder: Path, misses: list, spans=(), marks=None):
    lines = ["highlight,paragraph,start,end,text", *(f"{n},{p},{s},{e},{TWO_NAMES[p][s:e]}" for n, p, s, e in spans)]
    (folder / "doc01_spans.csv").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    lines = ["highlight,verdict,group,extra,note", *(f"{n},{v},private,{x}," for n, (v, x) in (marks or {}).items())]
    (folder / "doc01_marks.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    lines = ["doc_id,paragraph,text,kind,group,other_label,category,highlight"]
    lines += [f"doc01,0,{text},missed,private,no,other," for text in misses]
    (folder / "doc01_misses.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return compare(TWO_DOCUMENT, read_reader_files(folder, "doc01"))


def test_b9_exact_text_first_with_two_different_names(tmp_path: Path):
    for misses in (["יעקב כהן", "לכהן"], ["לכהן", "יעקב כהן"]):
        outcome = two_names(tmp_path, misses)
        assert (outcome.items, outcome.agreeing, outcome.reader_only) == (2, 2, 0)


def test_b10_a_line_whose_text_lies_inside_the_name(tmp_path: Path):
    outcome = two_names(tmp_path, ["כהן", "כהן"])
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (2, 2, 0)


def test_b11_a_highlight_that_only_touches_a_name(tmp_path: Path):
    # "כהן" is 0..3 and "יעקב כהן" is 11..19. The highlights 3..10 and 10..11 touch them and overlap neither.
    outcome = two_names(tmp_path, ["כהן", "יעקב כהן"], spans=[(1, 0, 3, 10), (2, 0, 10, 11)],
                        marks={1: ("not_person", 0), 2: ("not_person", 0)})
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (2, 2, 0)
    outcome = two_names(tmp_path, ["כהן", "יעקב כהן"], spans=[(1, 0, 3, 10), (2, 0, 10, 11)],
                        marks={1: ("found", 0), 2: ("found", 0)})
    assert (outcome.agreeing, outcome.reader_only) == (2, 2)


def test_e8_a_highlight_marked_twice(tmp_path: Path):
    folder = write(tmp_path)
    marks = folder / "doc01_marks.csv"
    marks.write_text(marks.read_text(encoding="utf-8") + "1,found,private,0,\n", encoding="utf-8")
    with pytest.raises(ReaderFileError):
        read_reader_files(folder, "doc01")


NO_PARTIALS = {"marks": {**MARKS, 3: ("found", 0)}, "misses": MISSES[1:]}
MARK_ROWS_WITHOUT_EXTRA = "".join(f"{number},found,private,\n" for number in MARKS)


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("doc01_misses.csv", "doc01,1,רחל,missed,private,no,other,\n"),
        ("doc01_misses.csv", ""),
        ("doc01_misses.csv", "doc_id,paragraph,words,kind,group,other_label,category,highlight\n"),
        ("doc01_marks.csv", "highlight,verdict,group,note\n" + MARK_ROWS_WITHOUT_EXTRA),
        ("doc01_spans.csv", "highlight,paragraph,start,text\n1,0,3,יעקב\n"),
    ],
    ids=["misses_without_header", "misses_empty_file", "misses_wrong_column", "marks_without_extra", "spans_without_end"],
)
def test_e9_a_file_without_the_columns_it_needs(tmp_path: Path, name: str, content: str):
    # The set has no partial highlight, so that a misses file read as empty is not refused for another reason.
    folder = write(tmp_path, **NO_PARTIALS)
    read_reader_files(folder, "doc01")
    (folder / name).write_text(content, encoding="utf-8")
    with pytest.raises(ReaderFileError, match="column"):
        read_reader_files(folder, "doc01")


def test_e10_b12_spans_at_the_edges(tmp_path: Path):
    folder = write(tmp_path, spans=[*SPANS, (6, 0, 15, 19)], marks={**MARKS, 6: ("not_person", 0)})
    assert PARAGRAPHS[0][15:19] == " את "
    outcome = compare(DOCUMENT, read_reader_files(folder, "doc01"))
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 7, 0)
    spans = folder / "doc01_spans.csv"
    # Paragraph 3 is the first the document does not have.
    spans.write_text(spans.read_text(encoding="utf-8-sig").replace("6,0,15,19", "6,3,15,19"), encoding="utf-8-sig")
    with pytest.raises(ReaderFileError, match="not of this document"):
        compare(DOCUMENT, read_reader_files(folder, "doc01"))


def test_ec21_main_prints_the_pooled_line(tmp_path: Path, capsys):
    documents = {document.doc_id: document for document in corpus(HERE / "templates", HERE / "names.tsv")}
    for doc_id in ("doc01", "doc11", "doc21", "doc31"):
        (tmp_path / f"{doc_id}_spans.csv").write_text("highlight,paragraph,start,end,text\n", encoding="utf-8-sig")
        (tmp_path / f"{doc_id}_marks.csv").write_text("highlight,verdict,group,extra,note\n", encoding="utf-8")
        lines = ["doc_id,paragraph,text,kind,group,other_label,category,highlight"]
        lines += [f'{doc_id},{gold.paragraph},"{gold.name}",missed,private,no,other,' for gold in documents[doc_id].gold if gold.counted]
        if doc_id == "doc01":
            del lines[1]  # the reader overlooks one mention, so agreeing and gold items differ
        if doc_id == "doc21":
            lines.append(f"{doc_id},0,שלום,missed,private,no,other,")
        (tmp_path / f"{doc_id}_misses.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    reader_check.main(tmp_path)
    printed = capsys.readouterr().out
    assert "reader against gold, pooled: 122/124 = 98.39%" in printed
    assert "doc01: gold items 30, agreeing 29, reader-only 0, agreement 29/30 = 96.67%" in printed
    assert "script missed, reader nothing" in printed
    assert "verdict: inside_prediction (prediction 98 percent or more, threshold below 95 percent)" in printed
    assert "doc21: gold items 28, agreeing 28, reader-only 1, agreement 28/29 = 96.55%" in printed
    assert "miss line" in printed and "שלום" in printed
    assert "  none" not in printed


@pytest.mark.parametrize(
    ("name", "row"),
    [
        ("doc01_marks.csv", "1,found,private,0,second highlight, same name\n"),
        ("doc01_marks.csv", "1,found,private,0,,\n"),
        ("doc01_misses.csv", "doc01,1,רחל, שוב,missed,private,no,other,\n"),
    ],
    ids=["comma_in_a_note", "comma_too_many", "comma_in_a_text"],
)
def test_e11_a_row_with_more_cells_than_the_header(tmp_path: Path, name: str, row: str):
    folder = write(tmp_path, **NO_PARTIALS)
    with (folder / name).open("a", encoding="utf-8") as handle:
        handle.write(row)
    with pytest.raises(ReaderFileError, match="more cells"):
        read_reader_files(folder, "doc01")


def test_b13_a_header_with_spaces(tmp_path: Path):
    folder = write(tmp_path)
    for name, header in (("doc01_marks.csv", "highlight, verdict, group, extra, note"),
                         ("doc01_misses.csv", "doc_id, paragraph, text, kind, group, other_label, category, highlight")):
        lines = (folder / name).read_text(encoding="utf-8").splitlines()
        (folder / name).write_text("\n".join([header, *lines[1:]]) + "\n", encoding="utf-8")
    outcome = compare(DOCUMENT, read_reader_files(folder, "doc01"))
    assert (outcome.items, outcome.agreeing, outcome.reader_only) == (7, 7, 0)
