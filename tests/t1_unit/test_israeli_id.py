"""Test matrix for ploni/detect/deterministic/israeli_id.py: the Israeli ID detector of issue #32.

Why: build-plan.md Phase 1, "Israeli ID": "Nine digits, last is a check digit, Luhn-style ...
Separator-tolerant candidate regex, strip, validate. Reject trivial sequences." "Company and
non-profit numbers. Nine digits, same check digit; companies (ח.פ.) start with `5`, non-profits
(ע.ר.) with `58`." Gate: "Checksum-backed types >= 0.98 recall and >= 0.98 precision on
fixtures." The span is the held-out batch's rule for IL_ID (its span rules, which the detector
side may read by Achia's third answer on #283): "The number only: its first digit to its last,
separators between them included. Not the label."

Test matrix:

israeli_id_checksum_ok, the plan's function as written:
  C1 a valid nine-digit number                             True
  C2 the same eight digits, another check digit            False
  C3 eight digits, read with a leading zero (zfill)        the nine-digit number's answer
  C4 ten digits                                            False
  C5 a separator or a letter inside                        False
  C6 the empty string                                      False ("".isdigit() is False)

is_trivial:
  T1 nine equal digits (000000000 passes the checksum)     True
  T2 the first eight ascending by one (123456782, 012345674 pass it)    True
  T3 the first eight descending by one                     True
  T4 an ordinary number                                    False
  T5 the first seven run up by one, the eighth does not (1234567, then 9)    False

is_other_shape (the written shape of a number that is not an ID):
  S1 a landline, 0 and an area code of build-plan.md Phase 1 (0[23489]), a separator, seven digits
                                                           True, with a hyphen and with a space
  S2 a case number, five, two and two digits (Net HaMishpat style, build-plan.md Phase 1)  True
  S3 plain nine, eight and one, three-three-three          False
  S4 01-2345678: 0 then a digit that is no area code       False
  S5 0, an area code, then groups of three and four (0X-XXX-XXXX)    False: only two and seven
  S6 two and seven digits that do not start with 0 (3X-XXXXXXX)       False
T5, S5 and S6 were added after the code, for three mutants that survived Cosmic Ray (the
commit that added them names them).

The detector (`IsraeliId`):
  EC1 each written form: plain; eight and the check digit after a hyphen, a maqaf (U+05BE), an
      en dash, a slash, a space; three-three-three with hyphens, dots, spaces, no-break spaces
                                                           one detection, the span the number only
  EC2 two numbers in one text                              two detections, in order
  EC3 the label glued to the number (ת.ז.123..., a proclitic on the label, Latin "ID", a
      letter)                                              found
  EC4 the fields: part the projection's, surface the text of the span, type IL_ID, detector
      "israeli_id", base_span None, confidence CONFIDENCE, band "high", needs_review False,
      detection_id "" (ids are made after detection: Achia, 2026-11-26, #169)
  B1  the number alone, at the start and at the end of the text    found
  B2  the empty text; a text with no digit                 nothing
  A1  nine digits inside a longer number (ten digits; a valid number followed by "-5" or by a
      digit; preceded by "7-")                             nothing
  A2  two separators in a row                              nothing
  A3  a company number (5...) and a non-profit number (58...) that pass the checksum    nothing
  A4  a near miss: a valid number with another check digit  nothing
  A5  trivial numbers                                      nothing
  A6  a landline shape and a case-number shape that pass the checksum    nothing
  A7  Arabic-Indic digits                                  nothing

The fixture (tests/fixtures/detect/il_id.json; its numbers are filled in when the tests run, by
tests/invented_numbers.py):
  F1  at least 40 positive and 40 negative texts
  F2  recall and precision at or above 0.98, counted by exact span (build-plan.md Phase 1, Gate);
      the counts and every miss are printed, a miss by its case's place in the fixture, never by
      its text, which holds a number made when the tests run

Hebrew axes: gershayim as " and ״ and geresh as ' and ׳ in the labels (the fixture); a proclitic
glued to the label (ות.ז.); niqqud around the number; RLM and LRM around it; the maqaf as a
separator. Names that are ordinary words do not apply: the detector reads digits. Document
axes: a number on a line of its own; the part is the projection's.

Known limits: a landline written as nine digits with no separator (0X1234567) cannot be told from
an ID that starts with 0 and is found as one; the label before a number is not read.
"""

from pathlib import Path

import pytest

from ploni.detect.base import DetectContext
from ploni.detect.deterministic import israeli_id
from ploni.detect.deterministic.israeli_id import IsraeliId, is_other_shape, is_trivial, israeli_id_checksum_ok
from ploni.types import Span
from tests.detector_contract import projection
from tests.invented_numbers import ISRAELI_IDS, read_cases

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "detect" / "il_id.json"
# Invented numbers, made when the tests run (tests/invented_numbers.py): valid by the plan's
# checksum, but NEAR, which is VALID with another check digit.
VALID = ISRAELI_IDS.valid[0]
OTHER = ISRAELI_IDS.valid[3]
ZERO = ISRAELI_IDS.zeros[0]
NEAR = ISRAELI_IDS.near[0]
COMPANY = ISRAELI_IDS.company[0]
NONPROFIT = ISRAELI_IDS.nonprofit[0]
LANDLINE = ISRAELI_IDS.landline[0]
CASE = ISRAELI_IDS.case
CTX = DetectContext()


def found(text: str) -> list[tuple[int, int]]:
    """Return the places the detector finds in a text."""
    return [(each.span.start, each.span.end) for each in IsraeliId().detect(projection(text), CTX)]


def only(text: str, number: str) -> list[tuple[int, int]]:
    """Return the place of the one number in a text, as the detector should find it."""
    start = text.index(number)
    return [(start, start + len(number))]


@pytest.mark.parametrize(
    ("digits", "expected"),
    [(VALID, True), (NEAR, False), (ZERO[1:], True), (VALID + "0", False), (f"{VALID[:5]}-{VALID[6:]}", False), (f"{VALID[:5]}a{VALID[6:]}", False), ("", False)],
    ids=["c1 valid", "c2 near", "c3 eight digits", "c4 ten digits", "c5 separator", "c5 letter", "c6 empty"],
)
def test_c_the_checksum(digits: str, expected: bool) -> None:
    assert israeli_id_checksum_ok(digits) is expected


@pytest.mark.parametrize(
    ("digits", "expected"),
    [
        ("000000000", True), ("777777777", True), ("123456782", True), ("012345674", True), ("987654324", True), (VALID, False),
        ("123456791", False),
    ],
    ids=["t1 zeros", "t1 sevens", "t2 ascending", "t2 ascending from 0", "t3 descending", "t4 ordinary", "t5 seven run"],
)
def test_t_trivial(digits: str, expected: bool) -> None:
    assert is_trivial(digits) is expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (f"{LANDLINE[:2]}-{LANDLINE[2:]}", True), (f"{LANDLINE[:2]} {LANDLINE[2:]}", True), (f"{CASE[:5]}-{CASE[5:7]}-{CASE[7:]}", True), (VALID, False),
        (f"{VALID[:8]}-{VALID[8]}", False), (f"{VALID[:3]}-{VALID[3:6]}-{VALID[6:]}", False), ("01-2345678", False), (f"{LANDLINE[:2]}-{LANDLINE[2:5]}-{LANDLINE[5:]}", False), (f"3{LANDLINE[1]}-{LANDLINE[2:]}", False),
    ],
    ids=["s1 hyphen", "s1 space", "s2 case", "s3 plain", "s3 eight and one", "s3 threes", "s4 no area code", "s5 three and four", "s6 no 0"],
)  # fmt: skip
def test_s_other_shapes(raw: str, expected: bool) -> None:
    assert is_other_shape(raw) is expected


FORMS = {
    "plain": VALID,
    "hyphen": f"{VALID[:8]}-{VALID[8]}",
    "maqaf": f"{VALID[:8]}־{VALID[8]}",
    "en dash": f"{VALID[:8]}–{VALID[8]}",
    "slash": f"{VALID[:8]}/{VALID[8]}",
    "space": f"{VALID[:8]} {VALID[8]}",
    "threes hyphen": f"{VALID[:3]}-{VALID[3:6]}-{VALID[6:]}",
    "threes dot": f"{VALID[:3]}.{VALID[3:6]}.{VALID[6:]}",
    "threes space": f"{VALID[:3]} {VALID[3:6]} {VALID[6:]}",
    "threes no-break space": f"{VALID[:3]} {VALID[3:6]} {VALID[6:]}",
}


@pytest.mark.parametrize("form", FORMS)
def test_ec1_each_written_form(form: str) -> None:
    text = f"ת.ז. {FORMS[form]} צורפה."
    assert found(text) == only(text, FORMS[form])


def test_ec2_two_numbers() -> None:
    text = f"בעל ת.ז. {VALID} ובעלת ת.ז. {OTHER}"
    first, second = text.index(VALID), text.index(OTHER)
    assert found(text) == [(first, first + 9), (second, second + 9)]


@pytest.mark.parametrize("text", [f"ת.ז.{VALID}", f"ות.ז. {VALID}", f"ID {VALID}", f"ב{VALID}"], ids=["glued", "proclitic", "latin", "letter"])
def test_ec3_the_label_or_a_letter_glued(text: str) -> None:
    assert found(text) == only(text, VALID)


def test_ec4_the_fields() -> None:
    proj = projection(f"שָׁלוֹם, ת״ז {ZERO}‎.", part="header1")
    [detection] = IsraeliId().detect(proj, CTX)
    assert detection.span == Span(proj.text.index(ZERO), proj.text.index(ZERO) + 9)
    assert (detection.part, detection.surface, detection.entity_type, detection.detector) == ("header1", ZERO, "IL_ID", "israeli_id")
    assert (detection.confidence, detection.band, detection.base_span) == (israeli_id.CONFIDENCE, "high", None)
    assert (detection.detection_id, detection.needs_review, detection.review_reason) == ("", False, None)


@pytest.mark.parametrize("text", [VALID, f"{VALID} הוא המספר", f"המספר הוא {VALID}"], ids=["alone", "start", "end"])
def test_b1_at_either_end(text: str) -> None:
    assert found(text) == only(text, VALID)


@pytest.mark.parametrize("text", ["", "אין כאן מספר כלל.", "\n"])
def test_b2_nothing_to_find(text: str) -> None:
    assert found(text) == []


@pytest.mark.parametrize(
    "text",
    [f"{VALID}0", f"מספר {VALID}-5", f"{VALID}3 ארוך", f"7-{VALID}"],
    ids=["ten digits", "followed by -5", "followed by a digit", "preceded by 7-"],
)
def test_a1_inside_a_longer_number(text: str) -> None:
    assert found(text) == []


def test_a2_two_separators_in_a_row() -> None:
    assert found(f"ת.ז. {VALID[:3]}--{VALID[3:]}") == []


@pytest.mark.parametrize("number", [COMPANY, NONPROFIT, f"{ISRAELI_IDS.company[1][:2]}-{ISRAELI_IDS.company[1][2:]}"], ids=["company", "non-profit", "company with a hyphen"])
def test_a3_company_and_nonprofit_numbers(number: str) -> None:
    assert israeli_id_checksum_ok(number.replace("-", ""))
    assert found(f"ח.פ. {number}") == []


def test_a4_a_near_miss() -> None:
    assert found(f"ת.ז. {NEAR}") == []


@pytest.mark.parametrize("number", ["000000000", "123456782", "012345674"])
def test_a5_trivial_numbers(number: str) -> None:
    assert israeli_id_checksum_ok(number)
    assert found(f"ת.ז. {number}") == []


@pytest.mark.parametrize(
    "text",
    [f"טל' {LANDLINE[:2]}-{LANDLINE[2:]}", f"טלפון {LANDLINE[:2]} {LANDLINE[2:]}", f"ת\"א {CASE[:5]}-{CASE[5:7]}-{CASE[7:]}"],
    ids=["landline hyphen", "landline space", "case number"],
)
def test_a6_other_shapes(text: str) -> None:
    assert israeli_id_checksum_ok(LANDLINE) and israeli_id_checksum_ok(CASE)
    assert found(text) == []


def test_a7_arabic_indic_digits() -> None:
    assert found("ת.ז. " + "".join(chr(0x0660 + int(d)) for d in VALID)) == []


def cases() -> tuple[list[tuple[str, set[tuple[int, int]]]], int, int]:
    """Read the fixture, its numbers filled in: each text with its expected places, and the counts of positive and negative texts."""
    positives, negatives = read_cases(FIXTURE, ISRAELI_IDS)
    read = [(text, set(spans)) for text, spans in positives + negatives]
    return read, len(positives), len(negatives)


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
