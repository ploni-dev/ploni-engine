"""Test matrix for eval/detectors.py: every detector of ploni/, run as the held-out scorer calls a detector.

Why: the scorer takes "a callable from a document's text to a list of (start, end, type)"
(the scorer's contract, PR #288). The score check of issue 170 scores main and the PR with the
same function, so the function must exist on main before the workflow that calls it. Its list
holds the detectors of ploni/, the Israeli ID detector first (issue #32), then the credit card
detector (issue #35).

Test matrix:

Equivalence classes:
  EC1  the detectors of DETECTORS: the Israeli ID detector, then the credit card detector
                                                     their detections, by default; the
                                                     placeholder number 123456782 is not one;
                                                     an ID and a card, each typed by its detector
  EC2  one detector given                            its detections as (start, end, type), in its order
  EC3  two detectors given                           the first one's, then the second one's
  EC4  the projection a detector gets                part "body"; the whole text; one anchor over it

Boundaries:
  B1  the empty text                                 no anchor; [] from Digits
  B2  a detector that finds nothing                  []

Hebrew axes: offsets are code points of the text as given: a number after a word with niqqud
(combining marks, more code points than letters) is placed by code point; text with RLM and LRM
marks. Proclitics and the document axes do not apply: the function hands over the text and
passes the detectors' places on as they are.

Known limits: a detection outside the text is passed on unchanged; the scorer raises
ValueError on it, and the T0 conformance suite is where a detector is held to its spans.
"""

from typing import ClassVar

from eval import detectors
from ploni.detect.base import DetectContext, Detector
from ploni.types import Anchor, Detection, Span, TextProjection
from tests.detector_contract import Digits
from tests.invented_numbers import CARDS, ISRAELI_IDS


class Seen:
    """Record the projection it is given; find nothing."""

    name: ClassVar[str] = "seen"
    produces: ClassVar[frozenset[str]] = frozenset({"NUMBER"})
    requires_morph: ClassVar[bool] = False

    def __init__(self) -> None:
        self.projections: list[TextProjection] = []

    def detect(self, proj: TextProjection, ctx: DetectContext) -> list[Detection]:
        """Keep the projection."""
        self.projections.append(proj)
        return []


class Words:
    """Find the word ת.ז. as a LABEL."""

    name: ClassVar[str] = "words"
    produces: ClassVar[frozenset[str]] = frozenset({"LABEL"})
    requires_morph: ClassVar[bool] = False

    def detect(self, proj: TextProjection, ctx: DetectContext) -> list[Detection]:
        """Return the label where it stands."""
        start = proj.text.find("ת.ז.")
        if start < 0:
            return []
        return [Detection("w0", proj.part, Span(start, start + 4), "ת.ז.", "LABEL", 1.0, "high", self.name, None)]


TEXT = "שָׁלוֹם, ת.ז. 123456782 ו-‏55‎"


def test_ec1_the_detectors_of_ploni() -> None:
    assert [type(each).__name__ for each in detectors.DETECTORS] == ["IsraeliId", "CreditCard"]
    assert detectors.detect_all(TEXT) == []
    text = "ת.ז. " + ISRAELI_IDS.valid[0]
    assert detectors.detect_all(text) == [(5, 14, "IL_ID")]
    both = f"ת.ז. {ISRAELI_IDS.valid[0]}, כרטיס {CARDS.visa[0]}"
    assert detectors.detect_all(both) == [(5, 14, "IL_ID"), (22, 38, "CREDIT_CARD")]


def test_ec2_one_detector() -> None:
    first, second = TEXT.index("123456782"), TEXT.index("55")
    assert detectors.detect_all(TEXT, (Digits(),)) == [(first, first + 9, "NUMBER"), (second, second + 2, "NUMBER")]


def test_ec3_two_detectors_in_their_order() -> None:
    label, number = TEXT.index("ת.ז."), TEXT.index("123456782")
    found = detectors.detect_all(TEXT, (Words(), Digits()))
    assert found[:2] == [(label, label + 4, "LABEL"), (number, number + 9, "NUMBER")]
    assert len(found) == 3


def test_ec4_the_projection_a_detector_gets() -> None:
    seen = Seen()
    detectors.detect_all(TEXT, (seen,))
    [proj] = seen.projections
    assert (proj.part, proj.text, proj.anchors, proj.block_breaks, proj.table_cells) == (
        "body", TEXT, [Anchor(0, len(TEXT), "text", 0)], [], []
    )  # fmt: skip


def test_b1_the_empty_text() -> None:
    seen = Seen()
    assert detectors.detect_all("", (seen, Digits())) == []
    assert seen.projections[0].anchors == []


def test_b2_a_detector_that_finds_nothing() -> None:
    nothing: tuple[Detector, ...] = (Seen(),)
    assert detectors.detect_all(TEXT, nothing) == []
