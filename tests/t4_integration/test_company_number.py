"""Module suite for ploni/detect/deterministic/company_number.py: the detector as the pipeline and the batch call it.

Why: `CLAUDE.md`, Tests: every module gets a suite over its public surface. The unit matrix calls
the detector on one text at a time; this runs it as it is registered, through
`eval.detectors.detect_all`, the callable the held-out scorer and the score check use, beside the
Israeli ID detector, and through the conformance check of the T0 suite, over every text of its
fixture file.

Matrix:
  M1  every fixture text through detect_all: the places typed COMPANY_NUMBER or
      NONPROFIT_NUMBER are the fixture's, with the fixture's types
  M2  every fixture text keeps the Detector contract (tests/detector_contract.py), as a header
      part too
  M3  the detector is registered in eval.detectors.DETECTORS, after the Israeli ID detector and
      before the credit card detector of issue #35 and the IBAN and bank account detector of
      issue #34, and requires no morphology
  M4  the two detectors never claim the same span: over both fixtures, no span is typed both
      IL_ID and a company's or a non-profit's (the ID detector refuses a number that starts
      with 5; this one finds only those)
"""

import json
from pathlib import Path

from eval import detectors
from ploni.detect.base import DetectContext
from ploni.detect.deterministic.company_number import CompanyNumber
from ploni.detect.deterministic.credit_card import CreditCard
from ploni.detect.deterministic.iban import Iban
from ploni.detect.deterministic.israeli_id import IsraeliId
from tests.detector_contract import breaks, projection
from tests.invented_numbers import BANK_NUMBERS, ISRAELI_IDS, combined, read_cases

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "detect"
FIXTURE = FIXTURES / "company_number.json"
TYPE = {"company": "COMPANY_NUMBER", "nonprofit": "NONPROFIT_NUMBER"}
OURS = frozenset(TYPE.values())


def texts() -> list[tuple[str, list[tuple[int, int, str]]]]:
    """Read every fixture text, its numbers filled in, with its expected places and types."""
    positives, negatives = read_cases(FIXTURE, combined(ISRAELI_IDS, BANK_NUMBERS))
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    typed = [
        (text, [(start, end, TYPE[kind]) for (start, end), kind in zip(spans, case["types"], strict=True)])
        for (text, spans), case in zip(positives, data["positives"], strict=True)
    ]
    return typed + [(text, []) for text, _ in negatives]


def test_m1_through_detect_all() -> None:
    for text, expected in texts():
        assert [each for each in detectors.detect_all(text) if each[2] in OURS] == expected


def test_m2_the_contract_over_the_fixture() -> None:
    for text, _ in texts():
        for part in ("body", "header1"):
            assert breaks(CompanyNumber(), projection(text, part), DetectContext()) == []


def test_m3_registered_and_needs_no_morphology() -> None:
    assert [type(each) for each in detectors.DETECTORS] == [IsraeliId, CompanyNumber, CreditCard, Iban]
    assert CompanyNumber.requires_morph is False and CompanyNumber.produces == OURS


def test_m4_the_two_detectors_never_claim_one_span() -> None:
    every = [text for text, _ in texts()]
    for name in ("il_id.json", "company_number.json"):
        positives, negatives = read_cases(FIXTURES / name, combined(ISRAELI_IDS, BANK_NUMBERS))
        every += [text for text, _ in positives + negatives]
    for text in every:
        found = detectors.detect_all(text)
        ids = {(start, end) for start, end, kind in found if kind == "IL_ID"}
        assert not ids & {(start, end) for start, end, kind in found if kind in OURS}
