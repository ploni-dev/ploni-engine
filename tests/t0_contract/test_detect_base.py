"""The Detector protocol of ploni/detect/base.py, and the conformance suite every detector runs through.

Why: build-plan.md section 4.3 and ADR-0004: fusion knows no detector, so the protocol is the
only thing it may rely on, and "a detector conformance suite (T0) asserts every detector
returns in-range spans, declared types only, and confidence in [0, 1]". Issue #31. The check
itself is tests/detector_contract.py; this file pins the protocol, runs every detector in
DETECTORS through the check, and shows that each rule of the check can fail.

Test matrix:

The protocol:
  P1  its members are the four of section 4.3: name, produces, requires_morph, detect. No write
      path (ADR-0004: "the protocol having no write path")
  P2  each is annotated as section 4.3 writes it, compared as written: the module uses
      postponed annotations
  P3  DetectContext is built with no argument and holds nothing: the plan names it and gives
      it no field

Equivalence classes of the check:
  EC1  every detector of DETECTORS, over every text of TEXTS: no line. DETECTORS holds the
       detectors of ploni/ (none yet) and Digits, which keeps the contract
  EC2  a span that ends past the text (PastTheEnd, on a text that ends in a number)    one line
  EC3  a span that starts before the text (BeforeTheStart, on a text that starts with one)
  EC4  a span that ends before it starts (Reversed)
  EC5  a base span outside the text (BaseOutside)
  EC6  a type that is not in produces (Undeclared)
  EC7  a confidence over 1 (AboveOne)
  EC8  a confidence under 0 (BelowZero)
  EC9  one line per broken rule and per detection: two rules in one detection, one rule in each
       of two detections, each line with the index of its detection

Boundaries:
  B1  a span of the whole text, [0, len): in range
  B2  an empty span at either end, [0, 0) and [len, len): in range (Known limits of the check)
  B3  [len, len + 1) and [-1, 0): out of range
  B4  confidence 0.0 and 1.0: in; the next float above 1.0 and the next below 0.0: out
  B5  an empty text: Digits returns nothing, no line; a span [0, 0) in it: in range
  B6  a detector that returns no detection: no line
  B7  a detector that declares no type and returns one detection: one line

Adversarial:
  A1  NaN confidence (NotANumber): one line; infinity: one line
  A2  a type that differs from a declared one only in case (Undeclared) or by a trailing space
  A3  PastTheEnd in the middle of a text keeps the contract; only at the end does it break it.
      That is why the T2 property runs over generated texts
  A4  the lines carry no document text: the surface of each broken detection is not in them

Hebrew axes: the check reads offsets, types and numbers, not words, so the axes enter as the
texts the detectors run over (TEXTS): niqqud (combining marks, more code points than letters),
gershayim as " and ״, geresh as ' and ׳, final letters, Hebrew next to Latin and digits with
the RLM and LRM marks, a character outside the BMP (one code point, two UTF-16 units), a
newline. Proclitics and names that are ordinary words are not applicable: the check judges
no word. Structural axes: a part other than the body (a header); a block break is not read by
the check, so it is not an axis here.

Known limits: what the check does not judge is in tests/detector_contract.py, Known limits.
"""

import inspect
import math
import typing
from typing import ClassVar

import pytest

from ploni.detect.base import DetectContext, Detector
from ploni.types import Detection, Span, TextProjection
from tests.detector_contract import (
    AboveOne,
    BaseOutside,
    BeforeTheStart,
    BelowZero,
    Digits,
    NotANumber,
    PastTheEnd,
    Reversed,
    Undeclared,
    breaks,
    projection,
)

# Each detector of ploni/ is added here as it is written, so that it runs through EC1.
DETECTORS: tuple[Detector, ...] = (Digits(),)

TEXTS = (
    "",
    "7",
    "ת.ז. 123456782",
    "123456782 הוא מספר הזהות",
    "עו\"ד כהן, ת\"א 12345-01-20",
    "עו״ד כהן, ת״א 12345-01-20",
    "כב' השופט לוי, ע׳ 3",
    "שָׁלוֹם 42 עֲלֵיכֶם 7",
    "ך ם ן ף ץ 1",
    "‏תיק 55‎ ID 99 ‏",
    "📄 12 📄",
    "שורה 1\nשורה 2",
)

CTX = DetectContext()


class Fixed:
    """Return the detections it was given, whatever the text."""

    name: ClassVar[str] = "fixed"
    produces: ClassVar[frozenset[str]] = frozenset({"NUMBER"})
    requires_morph: ClassVar[bool] = False

    def __init__(self, detections: list[Detection]) -> None:
        self.detections = detections

    def detect(self, proj: TextProjection, ctx: DetectContext) -> list[Detection]:
        """Return the given detections."""
        return self.detections


class DeclaresNothing(Fixed):
    """Declare no type."""

    produces: ClassVar[frozenset[str]] = frozenset()


def detection(span: Span, *, entity_type: str = "NUMBER", confidence: float = 1.0) -> Detection:
    """Build a detection of the fixed detector at a place."""
    return Detection("d", "body", span, "x", entity_type, confidence, "high", "fixed", None)


def lines(detections: list[Detection], text: str = "12345") -> list[str]:
    """Return the lines of the check for fixed detections over a text."""
    return breaks(Fixed(detections), projection(text), CTX)


def test_p1_the_members_are_the_four_of_section_4_3() -> None:
    assert typing.get_protocol_members(Detector) == {"name", "produces", "requires_morph", "detect"}


def test_p2_the_members_are_annotated_as_section_4_3_writes_them() -> None:
    assert Detector.__annotations__ == {
        "name": "ClassVar[str]",
        "produces": "ClassVar[frozenset[str]]",
        "requires_morph": "ClassVar[bool]",
    }
    signature = inspect.signature(Detector.detect)
    assert [(each.name, each.annotation) for each in signature.parameters.values()] == [
        ("self", inspect.Parameter.empty),
        ("proj", "TextProjection"),
        ("ctx", "DetectContext"),
    ]
    assert signature.return_annotation == "list[Detection]"


def test_p3_the_context_is_built_with_no_argument_and_holds_nothing() -> None:
    assert vars(DetectContext()) == {}
    with pytest.raises(TypeError):
        DetectContext("x")


@pytest.mark.parametrize("detector", DETECTORS, ids=lambda each: each.name)
@pytest.mark.parametrize("text", TEXTS)
def test_ec1_every_detector_keeps_the_contract(detector: Detector, text: str) -> None:
    assert breaks(detector, projection(text), CTX) == []


def test_ec1_the_texts_give_digits_something_to_find() -> None:
    assert sum(len(Digits().detect(projection(text), CTX)) for text in TEXTS) >= len(TEXTS)


@pytest.mark.parametrize(
    ("detector", "text", "expected"),
    [
        (PastTheEnd(), "ת.ז. 123", "digits: detection 0: span [5, 9) is not inside a text of 8 characters"),
        (BeforeTheStart(), "123 ש\"ח", "digits: detection 0: span [-1, 3) is not inside a text of 7 characters"),
        (Reversed(), "תיק 55", "digits: detection 0: span [6, 4) is not inside a text of 6 characters"),
        (BaseOutside(), "תיק 55", "digits: detection 0: base span [4, 7) is not inside a text of 6 characters"),
        (Undeclared(), "תיק 55", "digits: detection 0: type 'number' is not in produces ['NUMBER']"),
        (AboveOne(), "תיק 55", "digits: detection 0: confidence 1.5 is not in [0, 1]"),
        (BelowZero(), "תיק 55", "digits: detection 0: confidence -0.5 is not in [0, 1]"),
    ],
    ids=["ec2", "ec3", "ec4", "ec5", "ec6", "ec7", "ec8"],
)
def test_ec2_to_ec8_each_broken_rule_gives_one_line(detector: Detector, text: str, expected: str) -> None:
    assert breaks(detector, projection(text), CTX) == [expected]


def test_ec9_one_line_per_rule_and_per_detection() -> None:
    assert lines([detection(Span(0, 9), entity_type="ID"), detection(Span(1, 2), confidence=2.0)]) == [
        "fixed: detection 0: span [0, 9) is not inside a text of 5 characters",
        "fixed: detection 0: type 'ID' is not in produces ['NUMBER']",
        "fixed: detection 1: confidence 2.0 is not in [0, 1]",
    ]


@pytest.mark.parametrize(("start", "end"), [(0, 5), (0, 0), (5, 5)], ids=["b1 whole", "b2 empty at 0", "b2 empty at len"])
def test_b1_b2_the_whole_text_and_an_empty_span_at_either_end_are_in_range(start: int, end: int) -> None:
    assert lines([detection(Span(start, end))]) == []


@pytest.mark.parametrize(("start", "end"), [(5, 6), (-1, 0)])
def test_b3_one_past_either_end_is_out_of_range(start: int, end: int) -> None:
    assert lines([detection(Span(start, end))]) == [
        f"fixed: detection 0: span [{start}, {end}) is not inside a text of 5 characters"
    ]


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_b4_confidence_0_and_1_are_in_range(confidence: float) -> None:
    assert lines([detection(Span(0, 1), confidence=confidence)]) == []


@pytest.mark.parametrize("confidence", [math.nextafter(1.0, 2.0), math.nextafter(0.0, -1.0)])
def test_b4_the_next_float_past_either_end_is_out_of_range(confidence: float) -> None:
    assert lines([detection(Span(0, 1), confidence=confidence)]) == [
        f"fixed: detection 0: confidence {confidence!r} is not in [0, 1]"
    ]


def test_b5_an_empty_text() -> None:
    assert breaks(Digits(), projection(""), CTX) == []
    assert lines([detection(Span(0, 0))], text="") == []


def test_b6_no_detection_gives_no_line() -> None:
    assert lines([]) == []


def test_b7_a_detector_that_declares_no_type() -> None:
    assert breaks(DeclaresNothing([detection(Span(0, 1))]), projection("12345"), CTX) == [
        "fixed: detection 0: type 'NUMBER' is not in produces []"
    ]


@pytest.mark.parametrize("confidence", [math.nan, math.inf], ids=["nan", "inf"])
def test_a1_nan_and_infinity_are_out_of_range(confidence: float) -> None:
    assert lines([detection(Span(0, 1), confidence=confidence)]) == [
        f"fixed: detection 0: confidence {confidence!r} is not in [0, 1]"
    ]
    assert breaks(NotANumber(), projection("תיק 55"), CTX) == ["digits: detection 0: confidence nan is not in [0, 1]"]


@pytest.mark.parametrize("entity_type", ["number", "NUMBER ", " NUMBER", "Number"])
def test_a2_a_type_close_to_a_declared_one_is_not_declared(entity_type: str) -> None:
    assert lines([detection(Span(0, 1), entity_type=entity_type)]) == [
        f"fixed: detection 0: type {entity_type!r} is not in produces ['NUMBER']"
    ]


def test_a3_past_the_end_breaks_the_contract_only_at_the_end() -> None:
    assert breaks(PastTheEnd(), projection("ת.ז. 123 נמסר"), CTX) == []
    assert breaks(PastTheEnd(), projection("ת.ז. 123"), CTX) != []


def test_a4_the_lines_carry_no_document_text() -> None:
    document = "שָׁלוֹם 987654321"
    found = breaks(PastTheEnd(), projection(document), CTX) + breaks(Undeclared(), projection(document), CTX)
    assert len(found) == 2
    assert not any("987654321" in line or "שָׁלוֹם" in line for line in found)
