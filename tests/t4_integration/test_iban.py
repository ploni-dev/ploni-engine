"""Module suite for ploni/detect/deterministic/iban.py: the detector as the pipeline and the batch call it.

Why: `CLAUDE.md`, Tests: every module gets a suite over its public surface. The unit matrix calls
the detector on one text at a time; this runs it as it is registered, through
`eval.detectors.detect_all`, the callable the held-out scorer and the score check use, beside the
Israeli ID, the company number and the credit card detectors, and through the conformance check of the T0 suite,
over every text of its fixture file.

Matrix:
  M1  every fixture text through detect_all: the places typed IBAN or BANK_ACCOUNT are the
      fixture's, with the fixture's types, in the order of the text
  M2  every fixture text keeps the Detector contract (tests/detector_contract.py), as a header
      part too
  M3  the detector is registered in eval.detectors.DETECTORS after the credit card detector (issue
      #35) and before the phone detector (issue #36), and requires no morphology
  M4  over the four fixtures (il_id.json, company_number.json, credit_card.json, iban.json),
      no detection of this detector shares a character with one of another detector
  M5  the overlap of Known limits (issue #315): nine digits that pass the ID check right after
      ח-ן are an account alone, and the ID detector finds them too, the same span typed IL_ID;
      after חשבון only the account is found
  M6  a phone right after the account word that the phone detector takes (#36): a mobile, a
      mobile in two groups, a VoIP number, a landline after ח"ן, where the phone detector reads
      no label: PHONE only, no BANK_ACCOUNT on it; a landline of nine digits after חשבון, which
      the phone detector refuses under that label: BANK_ACCOUNT only
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
from tests.invented_numbers import BANK_NUMBERS, CARDS, ISRAELI_IDS, PHONES, combined, fill, israeli_id_checksum_ok, read_cases

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "detect"
FIXTURE = FIXTURES / "iban.json"
NUMBERS = combined(ISRAELI_IDS, BANK_NUMBERS)
TYPE = {"iban": "IBAN", "bank": "BANK_ACCOUNT"}
OURS = frozenset(TYPE.values())


def texts() -> list[tuple[str, list[tuple[int, int, str]]]]:
    """Read every fixture text, its numbers filled in, with its expected places and types, in the order of the text."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    read = []
    for case in data["positives"]:
        text, spans = fill(case["text"], NUMBERS)
        items = [(spans[first][0], spans[last][1], TYPE[kind]) for (first, last), kind in zip(case["found"], case["types"], strict=True)]
        read.append((text, sorted(items)))
    return read + [(fill(case["text"], NUMBERS)[0], []) for case in data["negatives"]]


def test_m1_through_detect_all() -> None:
    for text, expected in texts():
        assert [each for each in detectors.detect_all(text) if each[2] in OURS] == expected


def test_m2_the_contract_over_the_fixture() -> None:
    for text, _ in texts():
        for part in ("body", "header1"):
            assert breaks(Iban(), projection(text, part), DetectContext()) == []


def test_m3_registered_and_needs_no_morphology() -> None:
    assert [type(each) for each in detectors.DETECTORS] == [IsraeliId, CompanyNumber, CreditCard, Iban, Phone]
    assert Iban.requires_morph is False and Iban.produces == OURS


def test_m4_no_span_shared_with_another_detector() -> None:
    every = [text for text, _ in texts()]
    for name, numbers in (("il_id.json", NUMBERS), ("company_number.json", NUMBERS), ("credit_card.json", combined(CARDS, BANK_NUMBERS))):
        positives, negatives = read_cases(FIXTURES / name, numbers)
        every += [text for text, _ in positives + negatives]
    for text in every:
        found = detectors.detect_all(text)
        ours = [(start, end) for start, end, kind in found if kind in OURS]
        theirs = [(start, end) for start, end, kind in found if kind not in OURS]
        assert not any(a < d and c < b for a, b in ours for c, d in theirs)


def test_m5_an_id_after_the_abbreviation_is_found_twice() -> None:
    number = ISRAELI_IDS.valid[0]
    start = len("ח-ן ")
    assert detectors.detect_all(f"ח-ן {number}") == [(start, start + len(number), "IL_ID"), (start, start + len(number), "BANK_ACCOUNT")]
    start = len("חשבון ")
    assert detectors.detect_all(f"חשבון {number}") == [(start, start + len(number), "BANK_ACCOUNT")]


# A landline that fails the ID check, so that the ID detector, which reads no label in ח"ן, does
# not take it too (that overlap is M5's).
LANDLINE = next(number for number in PHONES.landline if not israeli_id_checksum_ok(number))
PHONE_AFTER_WORD = {
    "a mobile after חשבון": ("חשבון ", PHONES.mobile[1]),
    "a mobile in two groups after ח-ן": ("ח-ן ", f"{PHONES.mobile[2][:3]}-{PHONES.mobile[2][3:]}"),
    "a VoIP number after בחשבונו": ("בחשבונו ", PHONES.voip[1]),
    "a landline after ח\"ן": ('ח"ן ', LANDLINE),
}


def test_m6_a_phone_after_the_account_word_is_a_phone_only() -> None:
    for before, number in PHONE_AFTER_WORD.values():
        assert detectors.detect_all(f"{before}{number}") == [(len(before), len(before) + len(number), "PHONE")]
    number = LANDLINE
    start = len("חשבון ")
    assert detectors.detect_all(f"חשבון {number}") == [(start, start + len(number), "BANK_ACCOUNT")]
