"""Module suite for ploni/detect/deterministic/phone.py: the detector as the pipeline and the batch call it.

Why: `CLAUDE.md`, Tests: every module gets a suite over its public surface. The unit matrix calls
the detector on one text at a time; this runs it as it is registered, through
`eval.detectors.detect_all`, the callable the held-out scorer and the score check use, beside the
Israeli ID, company number and credit card detectors, and through the conformance check of the
T0 suite, over every text of its fixture file and of theirs (issue #36).

Matrix:
  M1  every fixture text through detect_all: the places typed PHONE are the fixture's
  M2  every fixture text keeps the Detector contract (tests/detector_contract.py), as a header
      part too
  M3  the detector is registered in eval.detectors.DETECTORS after the Israeli ID, the company
      number and the credit card detectors (issues #32, #33 and #35), and requires no morphology
  M4  over the four fixtures, no PHONE span shares a character with a COMPANY_NUMBER,
      NONPROFIT_NUMBER or CREDIT_CARD one; a PHONE span that shares one with an IL_ID is the
      same span, a bare run of digits with no label, flagged for review (the ID detector's
      known limit: a landline written as nine digits with no separator and no phone label);
      and each of the other three fixtures gives at least one PHONE (each holds phone lines),
      so that the check is not run on nothing
"""

from pathlib import Path

from eval import detectors
from ploni.detect.base import DetectContext
from ploni.detect.deterministic.company_number import CompanyNumber
from ploni.detect.deterministic.credit_card import CreditCard
from ploni.detect.deterministic.israeli_id import IsraeliId
from ploni.detect.deterministic.phone import REVIEW_REASON, Phone
from tests.detector_contract import breaks, projection
from tests.invented_numbers import CARDS, ISRAELI_IDS, PHONES, read_cases

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "detect"
OTHERS = {"il_id.json": ISRAELI_IDS, "company_number.json": ISRAELI_IDS, "credit_card.json": CARDS}
NEVER_SHARED = frozenset({"COMPANY_NUMBER", "NONPROFIT_NUMBER", "CREDIT_CARD"})


def texts() -> list[tuple[str, list[tuple[int, int]]]]:
    """Read every fixture text, its numbers filled in, with its expected places."""
    positives, negatives = read_cases(FIXTURES / "phone.json", PHONES)
    return positives + negatives


def every_text() -> dict[str, list[str]]:
    """Return the texts of the four fixtures, filled in, by fixture."""
    found = {"phone.json": [text for text, _ in texts()]}
    for name, numbers in OTHERS.items():
        positives, negatives = read_cases(FIXTURES / name, numbers)
        found[name] = [text for text, _ in positives + negatives]
    return found


def test_m1_through_detect_all() -> None:
    for text, spans in texts():
        assert [each for each in detectors.detect_all(text) if each[2] == "PHONE"] == [(start, end, "PHONE") for start, end in spans]


def test_m2_the_contract_over_the_fixture() -> None:
    for text, _ in texts():
        for part in ("body", "header1"):
            assert breaks(Phone(), projection(text, part), DetectContext()) == []


def test_m3_registered_and_needs_no_morphology() -> None:
    assert [type(each) for each in detectors.DETECTORS] == [IsraeliId, CompanyNumber, CreditCard, Phone]
    assert Phone.requires_morph is False and Phone.produces == frozenset({"PHONE"})


def test_m4_no_span_claimed_by_a_phone_and_another_number() -> None:
    phones_in = {}
    for name, fixture_texts in every_text().items():
        phones_in[name] = 0
        for text in fixture_texts:
            phones = Phone().detect(projection(text), DetectContext())
            phones_in[name] += len(phones)
            others = [each for each in detectors.detect_all(text) if each[2] != "PHONE"]
            for found in phones:
                start, end = found.span.start, found.span.end
                shared = [(s, e, kind) for s, e, kind in others if s < end and start < e]
                assert not [kind for _, _, kind in shared if kind in NEVER_SHARED]
                if shared:
                    assert [(s, e) for s, e, _ in shared] == [(start, end)] and found.review_reason == REVIEW_REASON
    assert min(phones_in[name] for name in OTHERS) >= 1
