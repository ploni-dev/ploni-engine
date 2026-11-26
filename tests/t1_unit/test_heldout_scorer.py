"""Unit tests of the held-out batch's scorer, eval/heldout/scorer.py, on a batch built by hand.

Why: the scorer's numbers go into every PR from Phase 1 on, and a worse one blocks a merge
(`build-plan.md` section 7). A scorer that counts a partial overlap as a hit, or a duplicate
twice, would move those numbers without any detector changing. A batch of three short Latin
documents, written here, makes every count exact and known before the scorer runs.

Test matrix (BATCH below: three documents, four key items of two types, X and Y):

Equivalence classes:
  S1  a detector that returns nothing         every type: tp 0, fn its count, recall 0.0,
                                              precision 0.0 (nothing marked: defined as 0.0)
  S2  a detector that replays the key         recall 1.0 and precision 1.0 for every type
  S3  a detector that finds a known part (X only)   X 1.0 and 1.0, Y 0.0, total 3 of 4
  S4  the exact span with the wrong type      a fp of that type, a fn of the key's type,
                                              not partial
  S5  a span that overlaps a key item of its own type, not exactly    fp 1, fn 1, partial 1
  S6  a span that holds a key item of its type and more               partial as S5
  S7  the same detection twice                counted once
  S8  a type the batch does not hold          a row of its own, fp only
  S9  a detection in a document with no item  a fp
  S10 an exact hit beside a partial one on the same item     tp 1, fp 1, partial 1, fn 0
  S11 the detector is called once per document, with its text, in order
  S12 a detection given as a list            read as the triple

Boundaries:
  B1  a span of the whole document, and of one character at each end
  B2  a span that touches a key item without sharing a character (end == item start): not partial

Error paths (ValueError, and the message holds no text of the document):
  E1  start equal to end        E2  end past the text        E3  a negative start
  E4  not a triple              E5  a type that is not a string   E6  a position that is no int
  E7  the detector raises, with the document's text in its message: DetectorError, whose message
      names the document and the error's type only, with no error chained to it (review 1 of
      the branch, finding 2)
  E8  the detector exits with the document's text as its message: DetectorError as E7
      (scorer review 1, finding 1)
  E9  the detector raises an error of a class derived from BaseException alone, with the text:
      DetectorError (scorer review 2, finding 5)
  E10 the detector raises an error of a class of its own whose name is the document's text:
      DetectorError, whose message names no class of the detector's own
  E11 the detector raises KeyboardInterrupt with the text: KeyboardInterrupt again, with no
      message and nothing chained, so that an interrupt still stops the run

The report:
  R1  one line per type, sorted, then TOTAL; names and numbers only
  R2  no text of a document in it
  R3  a type the batch does not hold is shown as OTHER and its number, not by its name, so that
      a detector cannot print text through a type's name

A group (GROUPED below: the item of document 1 that starts at 0 is of group g; review 2 of the
generator's branch, finding 21):
  G1  its own line: tp and fn of its items only, the empty and the replay detectors; a batch
      with no group has no group line
  G2  a partial detection of a group's item is a fn of the group, and stays a fp of the type
  G3  the report shows the group's line after the types' and before TOTAL, named type:group,
      with tp, fn and recall only
  G4  a detection at a group item's exact span with another type is a fn of the group (scorer
      review 1, finding 3)

main:
  M1  no argument, two arguments, an argument without a colon: the usage line, exit 2
  M2  a module and function: the report of the batch of SEED printed, exit 0
  M3  a detector that raises: one line on the error stream, the document's index and the
      error's type, nothing on the output, exit 1
  M4  a detector that prints each document on both streams: only the report is printed

Not applicable: the Hebrew axes and the document-structure axes. The scorer compares integer
spans and type names; it never reads the text (S11 shows it only hands the text on). The Hebrew
batch is scored in tests/t4_integration/test_heldout_scorer.py.
"""

import dataclasses
import sys
from collections.abc import Iterable

import pytest

from eval.heldout import scorer
from eval.heldout.generator import GROUPS, TYPES, Batch, Item
from eval.heldout.scorer import Counts, DetectorError, report, score

DOCUMENTS = ("alpha beta gamma", "delta epsilon", "zeta")
KEY = (
    Item(0, 0, 5, "X", "alpha"),
    Item(0, 11, 16, "Y", "gamma"),
    Item(1, 0, 5, "X", "delta"),
    Item(1, 6, 13, "X", "epsilon"),
)
BATCH = Batch(DOCUMENTS, KEY, ())
GROUPED = Batch(DOCUMENTS, (*KEY[:2], dataclasses.replace(KEY[2], group="g"), KEY[3]), ())


def detector_of(found: dict[str, list[tuple[int, int, str]]]) -> scorer.Detector:
    """A detector that returns, for a document's text, the detections listed for it."""

    def detect(text: str) -> Iterable[tuple[int, int, str]]:
        return found.get(text, [])

    return detect


def replay(items: Iterable[Item]) -> scorer.Detector:
    """A detector that returns the spans of the items given, each in its own document."""
    listed: dict[str, list[tuple[int, int, str]]] = {}
    for item in items:
        listed.setdefault(DOCUMENTS[item.doc], []).append((item.start, item.end, item.type))
    return detector_of(listed)


def counts(tp: int = 0, fp: int = 0, fn: int = 0, partial: int = 0) -> Counts:
    """A Counts with the four numbers given."""
    return Counts(tp=tp, fp=fp, fn=fn, partial=partial)


def test_s1_nothing_found() -> None:
    scores = score(detector_of({}), BATCH)
    assert scores.per_type == {"X": counts(fn=3), "Y": counts(fn=1)}
    assert scores.total == counts(fn=4)
    assert (scores.total.recall, scores.total.precision) == (0.0, 0.0)
    assert all(row.recall == 0.0 and row.precision == 0.0 for row in scores.per_type.values())


def test_s2_the_key_replayed() -> None:
    scores = score(replay(KEY), BATCH)
    assert scores.per_type == {"X": counts(tp=3), "Y": counts(tp=1)}
    assert all(row.recall == 1.0 and row.precision == 1.0 for row in scores.per_type.values())
    assert (scores.total.recall, scores.total.precision) == (1.0, 1.0)


def test_s3_a_known_part() -> None:
    scores = score(replay(item for item in KEY if item.type == "X"), BATCH)
    assert scores.per_type == {"X": counts(tp=3), "Y": counts(fn=1)}
    assert scores.total.recall == 0.75
    assert scores.total.precision == 1.0


def test_s4_the_wrong_type() -> None:
    scores = score(detector_of({DOCUMENTS[0]: [(11, 16, "X")]}), BATCH)
    assert scores.per_type["X"] == counts(fp=1, fn=3)
    assert scores.per_type["Y"] == counts(fn=1)


def test_s5_a_partial_overlap() -> None:
    scores = score(detector_of({DOCUMENTS[0]: [(1, 7, "X")]}), BATCH)
    assert scores.per_type["X"] == counts(fp=1, fn=3, partial=1)


def test_s6_a_span_that_holds_the_item_and_more() -> None:
    scores = score(detector_of({DOCUMENTS[1]: [(0, 13, "X")]}), BATCH)
    assert scores.per_type["X"] == counts(fp=1, fn=3, partial=1)


def test_s7_a_duplicate_is_counted_once() -> None:
    scores = score(detector_of({DOCUMENTS[0]: [(0, 5, "X"), (0, 5, "X")]}), BATCH)
    assert scores.per_type["X"] == counts(tp=1, fn=2)


def test_s8_a_type_the_batch_does_not_hold() -> None:
    scores = score(detector_of({DOCUMENTS[2]: [(0, 4, "Z")]}), BATCH)
    assert scores.per_type["Z"] == counts(fp=1)
    assert list(scores.per_type) == ["X", "Y", "Z"]


def test_s9_a_document_with_no_item() -> None:
    scores = score(detector_of({DOCUMENTS[2]: [(0, 4, "X")]}), BATCH)
    assert scores.per_type["X"] == counts(fp=1, fn=3)


def test_s10_an_exact_hit_beside_a_partial_one() -> None:
    scores = score(detector_of({DOCUMENTS[0]: [(0, 5, "X"), (0, 3, "X")]}), BATCH)
    assert scores.per_type["X"] == counts(tp=1, fp=1, fn=2, partial=1)


def test_s11_called_once_per_document_in_order() -> None:
    seen: list[str] = []

    def spy(text: str) -> list[tuple[int, int, str]]:
        seen.append(text)
        return []

    score(spy, BATCH)
    assert seen == list(DOCUMENTS)


def test_s12_a_detection_given_as_a_list() -> None:
    def as_lists(text: str) -> list[list[object]]:
        return [[0, 5, "X"]] if text == DOCUMENTS[0] else []

    assert score(as_lists, BATCH).per_type["X"] == counts(tp=1, fn=2)


def test_b1_spans_at_the_ends_of_a_document() -> None:
    whole = score(detector_of({DOCUMENTS[2]: [(0, 4, "Z"), (0, 1, "Z"), (3, 4, "Z")]}), BATCH)
    assert whole.per_type["Z"] == counts(fp=3)


def test_b2_a_span_that_only_touches_an_item() -> None:
    scores = score(detector_of({DOCUMENTS[0]: [(5, 11, "Y")]}), BATCH)
    assert scores.per_type["Y"] == counts(fp=1, fn=1)


@pytest.mark.parametrize(
    "detection",
    [
        (3, 3, "X"),
        (0, 17, "X"),
        (-1, 3, "X"),
        (0, 3),
        "alpha",
        (0, 3, 7),
        (0.0, 3, "X"),
        (True, 3, "X"),
    ],
    ids=["E1 empty", "E2 past the end", "E3 negative", "E4 a pair", "E4 a string", "E5 type", "E6 float", "E6 bool"],
)
def test_e_a_detection_that_is_not_a_span_of_the_text(detection: object) -> None:
    with pytest.raises(ValueError, match="document 0, detection 0") as raised:
        score(lambda text: [detection] if text == DOCUMENTS[0] else [], BATCH)
    assert not any(word in str(raised.value) for word in DOCUMENTS[0].split())


def test_r1_the_report_lines() -> None:
    lines = report(score(replay(KEY[:1]), BATCH))
    assert [line.split()[0] for line in lines] == ["X", "Y", "TOTAL"]
    assert lines[0].split() == ["X", "tp", "1", "fp", "0", "fn", "2", "partial", "0", "recall", "0.333", "precision", "1.000"]
    assert lines[2].split() == ["TOTAL", "tp", "1", "fp", "0", "fn", "3", "partial", "0", "recall", "0.250", "precision", "1.000"]


def test_r2_the_report_holds_no_text() -> None:
    shown = "\n".join(report(score(replay(KEY), BATCH)))
    assert not any(word in shown for document in DOCUMENTS for word in document.split())


@pytest.mark.parametrize("argv", [[], ["a:b", "c:d"], ["no_colon"]])
def test_m1_wrong_arguments(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert scorer.main(argv) == 2
    assert capsys.readouterr().err.strip() == scorer.USAGE


def nothing(text: str) -> list[tuple[int, int, str]]:
    """The empty detector, for main to load by name."""
    return []


def test_m2_main_prints_the_report(capsys: pytest.CaptureFixture[str]) -> None:
    assert scorer.main([f"{__name__}:nothing"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[-1].split()[:2] == ["TOTAL", "tp"]
    assert lines[-1].split()[2] == "0"


def raises_with_text(text: str) -> list[tuple[int, int, str]]:
    """A detector that raises with the start of the document's text in its message."""
    raise ValueError(text[:60])


def prints_text(text: str) -> list[tuple[int, int, str]]:
    """A detector that prints each document's text on both streams."""
    print(text)
    sys.stderr.write(text)
    return []


def test_e7_the_detector_raises() -> None:
    with pytest.raises(DetectorError) as raised:
        score(raises_with_text, BATCH)
    error = raised.value
    shown = (str(error), error.__cause__ is None, error.__suppress_context__)
    assert shown == ("document 0: the detector raised ValueError", True, True)


def test_m3_main_on_a_detector_that_raises(capsys: pytest.CaptureFixture[str]) -> None:
    code = scorer.main([f"{__name__}:raises_with_text"])
    streams = capsys.readouterr()
    assert (code, streams.out, streams.err.strip()) == (1, "", "document 0: the detector raised ValueError")


def test_m4_main_holds_back_what_the_detector_prints(capsys: pytest.CaptureFixture[str]) -> None:
    code = scorer.main([f"{__name__}:prints_text"])
    streams = capsys.readouterr()
    lines = streams.out.splitlines()
    shown = (code, len(lines), streams.err, streams.out.isascii())
    assert shown == (0, len(TYPES) + len(GROUPS) + 1, "", True)


def test_g1_a_group_has_its_own_line() -> None:
    assert score(detector_of({}), GROUPED).per_group == {"X:g": counts(fn=1)}
    assert score(replay(GROUPED.key), GROUPED).per_group == {"X:g": counts(tp=1)}
    assert score(replay(KEY), BATCH).per_group == {}


def test_g2_a_partial_detection_of_a_groups_item() -> None:
    scores = score(detector_of({DOCUMENTS[1]: [(0, 3, "X")]}), GROUPED)
    assert (scores.per_group["X:g"], scores.per_type["X"]) == (counts(fn=1), counts(fp=1, fn=3, partial=1))


def test_g3_the_report_shows_the_group() -> None:
    lines = report(score(replay(GROUPED.key), GROUPED))
    assert [line.split()[0] for line in lines] == ["X", "Y", "X:g", "TOTAL"]
    assert lines[2].split() == ["X:g", "tp", "1", "fn", "0", "recall", "1.000"]


def test_g4_the_right_span_with_another_type() -> None:
    assert score(detector_of({DOCUMENTS[1]: [(0, 5, "Y")]}), GROUPED).per_group == {"X:g": counts(fn=1)}


def exits_with_text(text: str) -> list[tuple[int, int, str]]:
    """A detector that exits with the start of the document's text as its message."""
    sys.exit(text[:60])


class Outside(BaseException):
    """An error of a class derived from BaseException alone."""


def raises_outside(text: str) -> list[tuple[int, int, str]]:
    """A detector that raises an error outside Exception, with the start of the text."""
    raise Outside(text[:60])


def raises_named(text: str) -> list[tuple[int, int, str]]:
    """A detector that raises an error of a class named by the start of the text."""
    raise type(text.split()[0], (Exception,), {})()


def interrupts(text: str) -> list[tuple[int, int, str]]:
    """A detector that raises KeyboardInterrupt with the start of the text."""
    raise KeyboardInterrupt(text[:60])


def test_e9_an_error_outside_exception() -> None:
    with pytest.raises(DetectorError) as raised:
        score(raises_outside, BATCH)
    shown = (str(raised.value), raised.value.__cause__ is None, raised.value.__suppress_context__)
    assert shown == ("document 0: the detector raised an error of its own class", True, True)


def test_e10_an_error_of_a_class_named_by_the_text() -> None:
    with pytest.raises(DetectorError) as raised:
        score(raises_named, BATCH)
    assert str(raised.value) == "document 0: the detector raised an error of its own class"


def test_e11_an_interrupt_stops_the_run_without_its_message() -> None:
    with pytest.raises(KeyboardInterrupt) as raised:
        score(interrupts, BATCH)
    shown = (raised.value.args, raised.value.__cause__ is None, raised.value.__suppress_context__)
    assert shown == ((), True, True)


def test_r3_a_type_the_batch_does_not_hold_is_not_named() -> None:
    lines = report(score(detector_of({DOCUMENTS[2]: [(0, 4, "zeta words"), (0, 1, "Z")]}), BATCH))
    assert [line.split()[0] for line in lines] == ["X", "Y", "OTHER_1", "OTHER_2", "TOTAL"]
    assert not any(word in "\n".join(lines) for word in ("zeta", "words"))


def test_e8_the_detector_exits() -> None:
    with pytest.raises(DetectorError) as raised:
        score(exits_with_text, BATCH)
    error = raised.value
    shown = (str(error), error.__cause__ is None, error.__suppress_context__)
    assert shown == ("document 0: the detector raised SystemExit", True, True)
