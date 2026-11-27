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
  M3  the detector is registered in eval.detectors.DETECTORS, last, after the Israeli ID, the
      company number, the credit card and the IBAN and bank account detectors (issues #32, #33,
      #35 and #34), and requires no morphology
  M4  over the five fixtures (the IBAN detector's, iban.json, since issue #34), no PHONE span
      shares a character with a COMPANY_NUMBER, NONPROFIT_NUMBER, CREDIT_CARD, IBAN or
      BANK_ACCOUNT one; a PHONE span that shares one with an IL_ID is the
      same span, a bare run of digits with no label, flagged with REVIEW_REASON (the ID
      detector's known limit: a landline written as nine digits with no separator and no phone
      label)
  M5  the PHONE detections on the other four fixtures are exactly PLACES, by fixture, case
      (its place in the fixture, positives first), start, end and needs_review, offsets only,
      each read when it was pinned (the review of b2f3790, finding 4, in place of a count):
      the ID fixture's phones under a phone label, landlines in groups with no label, and two
      under an ID label that the ID detector does not take, flagged; the company fixture's two
      under a phone label and an ID written as nine bare digits from 0[23489], flagged; the
      card fixture's two under phone labels; the IBAN fixture's three, numbers it writes in a
      phone's shape as no bank account's (05X-XXX-XXXX after חשבון, 05X-XXXXXXX after הנייד:,
      0X-XXX-XXXX after טלפון סניף הבנק:), found by no other detector. So the ID suite's M4 and the card suite's M1, which
      leave PHONE out, leave nothing unjudged
"""

import json
from pathlib import Path

from eval import detectors
from ploni.detect.base import DetectContext
from ploni.detect.deterministic.company_number import CompanyNumber
from ploni.detect.deterministic.credit_card import CreditCard
from ploni.detect.deterministic.iban import Iban
from ploni.detect.deterministic.israeli_id import IsraeliId
from ploni.detect.deterministic.phone import REVIEW_REASON, Phone
from tests.detector_contract import breaks, projection
from tests.invented_numbers import BANK_NUMBERS, CARDS, ISRAELI_IDS, PHONES, combined, fill, read_cases

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "detect"
# The other detectors' fixtures, each with the numbers its slots name (since issue #34, an IBAN or
# a bank account in the ID, company and card fixtures too: tests.invented_numbers.combined).
IDS_AND_BANK = combined(ISRAELI_IDS, BANK_NUMBERS)
OTHERS = {
    "il_id.json": IDS_AND_BANK, "company_number.json": IDS_AND_BANK, "credit_card.json": combined(CARDS, BANK_NUMBERS),
    "iban.json": IDS_AND_BANK,
}  # fmt: skip
NEVER_SHARED = frozenset({"COMPANY_NUMBER", "NONPROFIT_NUMBER", "CREDIT_CARD", "IBAN", "BANK_ACCOUNT"})
# The PHONE detections of the other fixtures, each read (M5 of the module docstring).
PLACES = [
    ("il_id.json", 47, 6, 16, False),
    ("il_id.json", 112, 4, 14, False),
    ("il_id.json", 113, 7, 17, False),
    ("il_id.json", 114, 4, 14, False),
    ("il_id.json", 115, 5, 16, False),
    ("il_id.json", 154, 5, 14, True),
    ("il_id.json", 162, 10, 21, False),
    ("il_id.json", 163, 16, 27, False),
    ("il_id.json", 164, 7, 18, False),
    ("il_id.json", 165, 10, 21, False),
    ("il_id.json", 166, 5, 15, True),
    ("company_number.json", 64, 0, 9, True),
    ("company_number.json", 66, 4, 14, False),
    ("company_number.json", 67, 5, 16, False),
    ("credit_card.json", 103, 6, 16, False),
    ("credit_card.json", 103, 22, 32, False),
    ("iban.json", 59, 6, 18, False),
    ("iban.json", 60, 7, 18, False),
    ("iban.json", 77, 17, 28, False),
]


def texts() -> list[tuple[str, list[tuple[int, int]]]]:
    """Read every fixture text, its numbers filled in, with its expected places."""
    positives, negatives = read_cases(FIXTURES / "phone.json", PHONES)
    return positives + negatives


def every_text() -> dict[str, list[str]]:
    """Return the texts of the five fixtures, filled in, by fixture, positives first."""
    found = {"phone.json": [text for text, _ in texts()]}
    for name, numbers in OTHERS.items():
        data = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
        found[name] = [fill(case["text"], numbers)[0] for case in data["positives"] + data["negatives"]]
    return found


def test_m1_through_detect_all() -> None:
    for text, spans in texts():
        assert [each for each in detectors.detect_all(text) if each[2] == "PHONE"] == [(start, end, "PHONE") for start, end in spans]


def test_m2_the_contract_over_the_fixture() -> None:
    for text, _ in texts():
        for part in ("body", "header1"):
            assert breaks(Phone(), projection(text, part), DetectContext()) == []


def test_m3_registered_and_needs_no_morphology() -> None:
    assert [type(each) for each in detectors.DETECTORS] == [IsraeliId, CompanyNumber, CreditCard, Iban, Phone]
    assert Phone.requires_morph is False and Phone.produces == frozenset({"PHONE"})


def test_m4_no_span_claimed_by_a_phone_and_another_number() -> None:
    for fixture_texts in every_text().values():
        for text in fixture_texts:
            others = [each for each in detectors.detect_all(text) if each[2] != "PHONE"]
            for found in Phone().detect(projection(text), DetectContext()):
                start, end = found.span.start, found.span.end
                shared = [(s, e, kind) for s, e, kind in others if s < end and start < e]
                assert not [kind for _, _, kind in shared if kind in NEVER_SHARED]
                if shared:
                    assert [(s, e) for s, e, _ in shared] == [(start, end)] and found.review_reason == REVIEW_REASON


def test_m5_the_phones_on_the_other_fixtures() -> None:
    texts_of = every_text()
    got = [
        (name, case, found.span.start, found.span.end, found.needs_review)
        for name in OTHERS
        for case, text in enumerate(texts_of[name])
        for found in Phone().detect(projection(text), DetectContext())
    ]
    assert got == PLACES
