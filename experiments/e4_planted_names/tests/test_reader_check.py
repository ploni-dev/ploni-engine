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

agreement_verdict (98 percent or more predicted; below 95 crosses the threshold)
  B7   98 of 100 -> inside_prediction; 97 of 100 -> outside_prediction
  B8   95 of 100 -> outside_prediction; 94 of 100 -> threshold_crossed
  E6   nothing compared -> ValueError
"""

from __future__ import annotations

from pathlib import Path

import pytest

from generate import Document, Gold
from reader_check import ReaderFileError, agreement_verdict, compare, read_reader_files

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
        {"misses": [(0, "רחל לוי", "partial", 3), (0, "רחל לוי", "partial", 3), *MISSES[1:]]},
    ],
    ids=["e1_mark_missing", "e1_mark_for_no_highlight", "e2_unknown_verdict", "e2_extra_not_a_number", "e2_extra_negative",
         "e3_partial_line_without_number", "e3_partial_line_unknown_number", "e4_partial_mark_without_line",
         "e4_partial_line_without_mark", "e5_unknown_kind", "e4_two_lines_for_one_partial"],
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
