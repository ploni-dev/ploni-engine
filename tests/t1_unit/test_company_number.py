"""Test matrix for ploni/detect/deterministic/company_number.py: the company and non-profit number detector of issue #33.

Why: build-plan.md Phase 1, "Company and non-profit numbers": "Nine digits, same check digit;
companies (ח.פ.) start with `5`, non-profits (ע.ר.) with `58`. Public-registry facts, so
default is detect and flag, not replace." Gate: "Checksum-backed types >= 0.98 recall and >= 0.98
precision on fixtures." The span and the types are the held-out batch's span rules (which the
detector side may read by Achia's third answer on #283): COMPANY_NUMBER and NONPROFIT_NUMBER,
"The number only, as for IL_ID. Not the label, not the company's name."

Test matrix:

number_type (the decision alone; label as label_before gives it, beside as NUMBER_AFTER finds):
  N1  a company number (51 to 54), no label, nothing beside      COMPANY_NUMBER
  N2  a non-profit number (58)                                   NONPROFIT_NUMBER
  N3  a company number written 2-6-1 (dd-dddddd-d) and 3-3-3    COMPANY_NUMBER
  N4  the company number's eight digits, another check digit    None
  N5  a valid ID, which does not start with 5                   None
  N6  eight digits, a short form of the ID detector              None; eight digits that start
      with 5 and pass the check padded with a zero (added after the code, for a mutant of
      Cosmic Ray that survived: the length check made `> 9`)    None
  N7  under the label of another number                          None
  N8  another number after it by a plain space, no company label    None; under a company
      label                                                      COMPANY_NUMBER
  N9  written as a case number, NNNNN-MM-YY                      None
  N10 555555555: it fails the checksum, so no nine-digit number starting with 5 is trivial in
      is_trivial's sense (eight running up or down by one cannot start at 5), and the detector
      does not ask                                               None

label_before:
  L1  each company label: ח.פ., ח.פ, ח. פ., ח"פ, ח״פ, ח''פ, ע.ר., ע"ר, ע״ר, ע''ר    "company"
  L2  a proclitic glued to it (וח.פ., לע"ר)                     "company"
  L3  the label of another number: טלפון, חשבון, דרכון, קופת חולים, מספר אישי    "other"
  L4  an ID label (ת.ז., ID), or no label                        None
  L5  a combined label: ת.ז./ח.פ., ח.פ./טלפון                    "company"
  L6  a digit between the label and the number                   None

The detector (`CompanyNumber`):
  EC1 each written form after ח.פ.: plain, 2-6-1, 2-7, 3-3-3 with hyphens, dots and spaces,
      eight and one                                              one detection, the span the
                                                                 number only
  EC2 a company and a non-profit number in one text              two, in order, each its type
  EC3 the fields: part, surface, type, detector "company_number", base_span None, band "high",
      needs_review False, detection_id ""; confidence CONFIDENCE_LABELLED under a company label,
      CONFIDENCE with none (the ID detector's constants)
  EC4 under ח.פ., a date after it by a plain space                found; with no label, a count
      after it                                                   nothing
  B1  the number alone, at the start and at the end of the text   found
  B2  the empty text; a text with no digit                       nothing
  A1  inside a longer number: ten digits, "7-" before, "-5" after    nothing
  A2  a valid ID after ת.ז.                                      nothing
  A3  a company number under a phone's and a bank account's label    nothing

The fixture (tests/fixtures/detect/company_number.json; its numbers are filled in when the tests
run, by tests/invented_numbers.py; a positive's "types" names the type of each slot it finds):
  F1  at least 40 positive and 40 negative texts
  F2  recall and precision at or above 0.98, counted by exact span and type (build-plan.md
      Phase 1, Gate); the counts and every miss printed, a miss by its case's place

Hebrew axes: gershayim as ", ״ and two ASCII apostrophes; a proclitic glued to the label; niqqud
before the number; the maqaf as a separator. Names that are ordinary words do not apply: the
detector reads digits.

Known limits: the type is read from the digits, not the label (ע.ר. before a 51 number gives
COMPANY_NUMBER).
"""

import json
from pathlib import Path

import pytest

from ploni.detect.base import DetectContext
from ploni.detect.deterministic import company_number, israeli_id
from ploni.detect.deterministic.company_number import CompanyNumber, number_type
from ploni.types import Span
from tests.detector_contract import projection
from tests.invented_numbers import ISRAELI_IDS, complete, read_cases

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "detect" / "company_number.json"
# Invented numbers, made when the tests run (tests/invented_numbers.py).
COMPANY = ISRAELI_IDS.company[0]
OTHER_COMPANY = ISRAELI_IDS.company[1]
NONPROFIT = ISRAELI_IDS.nonprofit[0]
ID = ISRAELI_IDS.valid[0]
NEAR = COMPANY[:8] + str((int(COMPANY[8]) + 1) % 10)
# Eight digits from 5 that pass the check once padded with a zero, as the plan's check pads them.
EIGHT_FROM_5 = complete("05" + COMPANY[2:8], israeli_id.israeli_id_checksum_ok)[1:]
CTX = DetectContext()
TYPE = {"company": "COMPANY_NUMBER", "nonprofit": "NONPROFIT_NUMBER"}


def found(text: str) -> list[tuple[int, int, str]]:
    """Return the places and types the detector finds in a text."""
    return [(each.span.start, each.span.end, each.entity_type) for each in CompanyNumber().detect(projection(text), CTX)]


def only(text: str, number: str, kind: str = "COMPANY_NUMBER") -> list[tuple[int, int, str]]:
    """Return the place of the one number in a text, with its type."""
    start = text.index(number)
    return [(start, start + len(number), kind)]


DECISIONS = {
    "n1 company": (COMPANY, None, False, "COMPANY_NUMBER"),
    "n2 nonprofit": (NONPROFIT, None, False, "NONPROFIT_NUMBER"),
    "n3 two six one": (f"{COMPANY[:2]}-{COMPANY[2:8]}-{COMPANY[8]}", None, False, "COMPANY_NUMBER"),
    "n3 threes": (f"{COMPANY[:3]} {COMPANY[3:6]} {COMPANY[6:]}", None, False, "COMPANY_NUMBER"),
    "n4 near miss": (NEAR, None, False, None),
    "n5 an id": (ID, None, False, None),
    "n6 eight digits": (COMPANY[1:], None, False, None),
    "n6 eight digits from five": (EIGHT_FROM_5, "company", False, None),
    "n7 another number's label": (COMPANY, "other", False, None),
    "n8 beside, no company label": (COMPANY, None, True, None),
    "n8 beside, a company label": (COMPANY, "company", True, "COMPANY_NUMBER"),
    "n9 a case number's shape": (f"{COMPANY[:5]}-{COMPANY[5:7]}-{COMPANY[7:]}", None, False, None),
    "n10 nine fives": ("555555555", None, False, None),
}


@pytest.mark.parametrize("case", DECISIONS)
def test_n_the_decision(case: str) -> None:
    raw, label, beside, expected = DECISIONS[case]
    assert number_type(raw, label, beside) == expected


def test_n10_nine_fives_fail_the_checksum() -> None:
    assert not israeli_id.israeli_id_checksum_ok("555555555")
    assert len(EIGHT_FROM_5) == 8 and EIGHT_FROM_5[0] == "5" and israeli_id.israeli_id_checksum_ok(EIGHT_FROM_5)


def label(before: str) -> str | None:
    """Return the kind of label the detector reads before a number that follows `before`."""
    result: str | None = company_number.label_before(before + COMPANY, len(before))
    return result


COMPANY_LABELS = ["ח.פ. ", "ח.פ ", "ח. פ. ", "ח\"פ ", "ח״פ ", "ח''פ ", "ע.ר. ", "ע\"ר ", "ע״ר ", "ע''ר "]


@pytest.mark.parametrize("before", COMPANY_LABELS)
def test_l1_company_labels(before: str) -> None:
    assert label(before) == "company"


@pytest.mark.parametrize("before", ["וח.פ. ", "לע\"ר "])
def test_l2_a_proclitic_on_the_label(before: str) -> None:
    assert label(before) == "company"


@pytest.mark.parametrize("before", ["טלפון ", "חשבון ", "דרכון ", "קופת חולים ", "מספר אישי "])
def test_l3_labels_of_other_numbers(before: str) -> None:
    assert label(before) == "other"


@pytest.mark.parametrize("before", ["ת.ז. ", "ID ", "", "החברה "])
def test_l4_an_id_label_or_none(before: str) -> None:
    assert label(before) is None


@pytest.mark.parametrize("before", ["ת.ז./ח.פ. ", "ח.פ./טלפון "])
def test_l5_a_combined_label(before: str) -> None:
    assert label(before) == "company"


def test_l6_a_digit_between() -> None:
    assert label("ח.פ. 3 ") is None


FORMS = {
    "plain": COMPANY,
    "two six one": f"{COMPANY[:2]}-{COMPANY[2:8]}-{COMPANY[8]}",
    "two seven": f"{COMPANY[:2]}-{COMPANY[2:]}",
    "threes hyphen": f"{COMPANY[:3]}-{COMPANY[3:6]}-{COMPANY[6:]}",
    "threes dot": f"{COMPANY[:3]}.{COMPANY[3:6]}.{COMPANY[6:]}",
    "threes space": f"{COMPANY[:3]} {COMPANY[3:6]} {COMPANY[6:]}",
    "eight and one maqaf": f"{COMPANY[:8]}־{COMPANY[8]}",
}


@pytest.mark.parametrize("form", FORMS)
def test_ec1_each_written_form(form: str) -> None:
    text = f"ח.פ. {FORMS[form]} נרשמה."
    assert found(text) == only(text, FORMS[form])


def test_ec2_a_company_and_a_nonprofit() -> None:
    text = f"החברה (ח.פ. {COMPANY}) והעמותה (ע.ר. {NONPROFIT})"
    first, second = text.index(COMPANY), text.index(NONPROFIT)
    assert found(text) == [(first, first + 9, "COMPANY_NUMBER"), (second, second + 9, "NONPROFIT_NUMBER")]


def test_ec3_the_fields() -> None:
    proj = projection(f"שָׁלוֹם, ח״פ {COMPANY}.", part="header1")
    [detection] = CompanyNumber().detect(proj, CTX)
    start = proj.text.index(COMPANY)
    assert detection.span == Span(start, start + 9)
    assert (detection.part, detection.surface, detection.entity_type, detection.detector) == ("header1", COMPANY, "COMPANY_NUMBER", "company_number")
    assert (detection.confidence, detection.band, detection.base_span) == (israeli_id.CONFIDENCE_LABELLED, "high", None)
    assert (detection.detection_id, detection.needs_review, detection.review_reason) == ("", False, None)
    [plain] = CompanyNumber().detect(projection(f"המספר {COMPANY}"), CTX)
    assert plain.confidence == israeli_id.CONFIDENCE


def test_ec4_another_number_after_it() -> None:
    text = f"ח.פ. {COMPANY} 1.1.2020"
    assert found(text) == only(text, COMPANY)
    assert found(f"{COMPANY} 3 עובדים") == []


@pytest.mark.parametrize("text", [COMPANY, f"{COMPANY} הוא המספר", f"המספר הוא {COMPANY}"], ids=["alone", "start", "end"])
def test_b1_at_either_end(text: str) -> None:
    assert found(text) == only(text, COMPANY)


@pytest.mark.parametrize("text", ["", "אין כאן מספר כלל."], ids=["empty", "no digit"])
def test_b2_nothing_to_find(text: str) -> None:
    assert found(text) == []


@pytest.mark.parametrize("text", [f"{COMPANY}0", f"7-{COMPANY}", f"מספר {COMPANY}-5"], ids=["ten digits", "preceded by 7-", "followed by -5"])
def test_a1_inside_a_longer_number(text: str) -> None:
    assert found(text) == []


def test_a2_an_id_is_not_a_company_number() -> None:
    assert found(f"ת.ז. {ID}") == []


@pytest.mark.parametrize("before", ["טלפון ", "חשבון "])
def test_a3_under_another_numbers_label(before: str) -> None:
    assert found(before + OTHER_COMPANY) == []


def cases() -> tuple[list[tuple[str, set[tuple[int, int, str]]]], int, int]:
    """Read the fixture, its numbers filled in: each text with its expected places and types, and the counts."""
    positives, negatives = read_cases(FIXTURE, ISRAELI_IDS)
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    typed = [(text, {(start, end, TYPE[kind]) for (start, end), kind in zip(spans, case["types"], strict=True)}) for (text, spans), case in zip(positives, data["positives"], strict=True)]
    return typed + [(text, set()) for text, _ in negatives], len(positives), len(negatives)


def test_f1_the_fixture_has_enough_cases() -> None:
    read, n_pos, n_neg = cases()
    assert n_pos >= 40 and n_neg >= 40
    assert all(spans for _, spans in read[:n_pos]) and not any(spans for _, spans in read[n_pos:])


def test_f2_recall_and_precision_on_the_fixture(capsys: pytest.CaptureFixture[str]) -> None:
    read, n_pos, n_neg = cases()
    misses: list[str] = []
    wrong: list[str] = []
    tp = 0
    for case, (text, expected) in enumerate(read):
        got = set(found(text))
        tp += len(expected & got)
        misses += [f"case {case} {span}" for span in sorted(expected - got)]
        wrong += [f"case {case} {span}" for span in sorted(got - expected)]
    recall = tp / (tp + len(misses))
    precision = tp / (tp + len(wrong)) if tp + len(wrong) else 0.0
    with capsys.disabled():
        print(f"\nprecision {precision:.3f}  recall {recall:.3f}  n_pos {n_pos}  n_neg {n_neg}  spans {tp + len(misses)}")
        print("false negatives:", misses)
        print("false positives:", wrong)
    # build-plan.md Phase 1, Gate: checksum-backed types at or above 0.98 recall and precision.
    assert recall >= 0.98 and precision >= 0.98
