"""Module suite for ploni/detect/deterministic/credit_card.py: the detector as the pipeline and the batch call it.

Why: `CLAUDE.md`, Tests: every module gets a suite over its public surface. The unit matrix calls
the detector on one text at a time; this runs it as it is registered, through
`eval.detectors.detect_all`, the callable the held-out scorer and the score check use, beside
the Israeli ID detector, and through the conformance check of the T0 suite, over every text of
its fixture file (issue #35).

Matrix:
  M1  every fixture text through detect_all: the places found are the fixture's, each typed
      CREDIT_CARD; no other detector finds anything in them (no IL_ID inside a card)
  M2  every fixture text keeps the Detector contract (tests/detector_contract.py), as a header
      part too
  M3  the detector is registered in eval.detectors.DETECTORS after the Israeli ID and the company
      number detectors (issues #32 and #33), and requires no morphology
  M4  every text of the Israeli ID and the company number detectors' fixtures gives no CREDIT_CARD
"""

from pathlib import Path

from eval import detectors
from ploni.detect.base import DetectContext
from ploni.detect.deterministic.company_number import CompanyNumber
from ploni.detect.deterministic.credit_card import CreditCard
from ploni.detect.deterministic.israeli_id import IsraeliId
from tests.detector_contract import breaks, projection
from tests.invented_numbers import CARDS, ISRAELI_IDS, read_cases

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "detect"


def texts() -> list[tuple[str, list[tuple[int, int]]]]:
    """Read every fixture text, its numbers filled in, with its expected places."""
    positives, negatives = read_cases(FIXTURES / "credit_card.json", CARDS)
    return positives + negatives


def test_m1_through_detect_all() -> None:
    for text, spans in texts():
        assert detectors.detect_all(text) == [(start, end, "CREDIT_CARD") for start, end in spans]


def test_m2_the_contract_over_the_fixture() -> None:
    for text, _ in texts():
        for part in ("body", "header1"):
            assert breaks(CreditCard(), projection(text, part), DetectContext()) == []


def test_m3_registered_and_needs_no_morphology() -> None:
    assert [type(each) for each in detectors.DETECTORS] == [IsraeliId, CompanyNumber, CreditCard]
    assert CreditCard.requires_morph is False and CreditCard.produces == frozenset({"CREDIT_CARD"})


def test_m4_no_card_in_the_other_fixtures() -> None:
    for name in ("il_id.json", "company_number.json"):
        positives, negatives = read_cases(FIXTURES / name, ISRAELI_IDS)
        for text, _ in positives + negatives:
            assert CreditCard().detect(projection(text), DetectContext()) == []
