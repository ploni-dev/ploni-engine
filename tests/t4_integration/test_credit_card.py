"""Module suite for ploni/detect/deterministic/credit_card.py: the detector as the pipeline and the batch call it.

Why: `CLAUDE.md`, Tests: every module gets a suite over its public surface. The unit matrix calls
the detector on one text at a time; this runs it as it is registered, through
`eval.detectors.detect_all`, the callable the held-out scorer and the score check use, beside
the Israeli ID detector, and through the conformance check of the T0 suite, over every text of
its fixture file (issue #35).

Matrix:
  M1  every fixture text through detect_all: the places found are the fixture's, each typed
      CREDIT_CARD; no other detector finds anything in them (no IL_ID inside a card), but the
      bank account triple one negative writes, a slot filled from BANK_NUMBERS after חשבון, which
      the IBAN and bank account detector finds, typed BANK_ACCOUNT, one in all (issue #34), and
      the phone detector's, whose detections the fixture's phone line holds (issue #36);
      tests/t4_integration/test_phone.py, M5, pins those
  M2  every fixture text keeps the Detector contract (tests/detector_contract.py), as a header
      part too
  M3  the detector is registered in eval.detectors.DETECTORS after the Israeli ID and the company
      number detectors (issues #32 and #33) and before the IBAN and bank account detector (issue
      #34) and the phone detector (issue #36), and requires no morphology
  M4  every text of the Israeli ID and the company number detectors' fixtures gives no CREDIT_CARD
"""

import json
from pathlib import Path

from eval import detectors
from ploni.detect.base import DetectContext
from ploni.detect.deterministic.company_number import CompanyNumber
from ploni.detect.deterministic.credit_card import CreditCard
from ploni.detect.deterministic.iban import Iban
from ploni.detect.deterministic.israeli_id import IsraeliId
from ploni.detect.deterministic.phone import Phone
from tests.detector_contract import breaks, projection
from tests.invented_numbers import BANK_NUMBERS, CARDS, ISRAELI_IDS, combined, read_cases, typed_slots

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "detect"
# The cards, and the bank account triple one negative writes (issue #34), filled when the tests run.
NUMBERS = combined(CARDS, BANK_NUMBERS)


def texts() -> list[tuple[str, list[tuple[int, int]]]]:
    """Read every fixture text, its numbers filled in, with its expected places."""
    positives, negatives = read_cases(FIXTURES / "credit_card.json", NUMBERS)
    return positives + negatives


def test_m1_through_detect_all() -> None:
    data = json.loads((FIXTURES / "credit_card.json").read_text(encoding="utf-8"))
    templates = [case["text"] for case in data["positives"] + data["negatives"]]
    triples = 0
    for template, (text, spans) in zip(templates, texts(), strict=True):
        triple = typed_slots(template, NUMBERS, {"account": "BANK_ACCOUNT"})
        found = [each for each in detectors.detect_all(text) if each[2] != "PHONE"]
        assert found == [(start, end, "CREDIT_CARD") for start, end in spans] + triple
        triples += len(triple)
    assert triples == 1


def test_m2_the_contract_over_the_fixture() -> None:
    for text, _ in texts():
        for part in ("body", "header1"):
            assert breaks(CreditCard(), projection(text, part), DetectContext()) == []


def test_m3_registered_and_needs_no_morphology() -> None:
    assert [type(each) for each in detectors.DETECTORS] == [IsraeliId, CompanyNumber, CreditCard, Iban, Phone]
    assert CreditCard.requires_morph is False and CreditCard.produces == frozenset({"CREDIT_CARD"})


def test_m4_no_card_in_the_other_fixtures() -> None:
    for name in ("il_id.json", "company_number.json"):
        positives, negatives = read_cases(FIXTURES / name, combined(ISRAELI_IDS, BANK_NUMBERS))
        for text, _ in positives + negatives:
            assert CreditCard().detect(projection(text), DetectContext()) == []
