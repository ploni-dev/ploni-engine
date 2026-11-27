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
      en dash, a slash, a space; three-three-three with hyphens, dots, spaces, no-break spaces;
      and the hyphens of word processors and PDF text: the Unicode hyphen (U+2010), the
      non-breaking hyphen (U+2011), the figure dash (U+2012), the em dash (U+2014) and the minus
      sign (U+2212)
                                                           one detection, the span the number only
  EC2 two numbers in one text                              two detections, in order
  EC3 the label glued to the number (ת.ז.123..., a proclitic on the label, Latin "ID", a
      letter)                                              found
  EC4 the fields: part the projection's, surface the text of the span, type IL_ID, detector
      "israeli_id", base_span None, confidence CONFIDENCE_LABELLED (the text has an ID label),
      band "high", needs_review False,
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
  A8  CANDIDATE itself: nine digits match it whole; ten, plain and with a hyphen, do not
      (added after the code, for seven mutants that survived Cosmic Ray: the checksum refuses
      more than nine digits too, so the detector's output alone cannot tell them apart)

label_before (the labels before a number, on its line, within LABEL_WINDOW characters, after
the last digit there; build-plan.md Phase 1: company and non-profit numbers are their own type,
and forms write the label of a number before it):
  L1 each ID label: ת.ז., ת.ז, ת"ז, ת״ז, תעודת זהות, תעודת הזהות, מס' זהות, מס׳ זהות, מספר
     זהות, מספר תעודת זהות, ID, I.D.                       "id"
  L2 each label of another number: ח.פ., ח"פ, ע.ר., ע״ר, דרכון, חשבון, טלפון, טל', טל׳, פקס,
     נייד, קופת חולים, מס' חבר, מספר אישי, מ.א., רישיון    "other"
  L3 no label                                              None
  L4 an ID label and the label of another number: the ID label counts, either way round (issue
     #299, finding 1: until then the nearer one counted, and "ת.ז. או דרכון" was "other")
  L5 a label further than LABEL_WINDOW before the number  None
  L5b the window's edge: a label that starts exactly LABEL_WINDOW characters before the number
      counts, one that starts a character earlier does not; far into a text as at its start
      (added after the code, for three mutants that survived Cosmic Ray)
  L6 a label on the line before                            None
  L7 a digit between the label and the number              None
  L8 a proclitic glued to a label (ות.ז., לת"ז, ובדרכון)   its kind
  L9 a label's letters inside a longer word (מתזמן, טלפונית)    not a label
  L10 a combined form label, an ID's and another number's, with a slash or "או": ת.ז./דרכון,
      ת"ז/דרכון, ת״ז/ח.פ., מספר זהות/דרכון, מס' זהות/דרכון, ת.ז./ח.פ., תעודת זהות/דרכון,
      ת.ז. או דרכון                                         "id" (issue #299, finding 1)
  L11 an ID label, a digit, then the label of another number: only the labels after the last
      digit count                                          "other"
The detector, with labels:
  EC5 a valid number after a label of another number      nothing (the fixture has each kind)
  EC6 after an ID label: CONFIDENCE_LABELLED; with no label: CONFIDENCE
  EC7 a valid number after a combined form label (L10)    found, CONFIDENCE_LABELLED; a company
      number after ת.ז./ח.פ.                                nothing (it starts with 5)
The detector, an ID written without its leading zeros (build-plan.md Phase 1's checksum pads
with zeros, `digits.zfill(9)`, so a number of fewer digits is an ID read with them):
  SH1 eight digits after an ID label                       found, the span the digits as written
  SH2 seven digits after an ID label                       found
  SH3 eight digits with a separator after an ID label (7-1, 4-4)    found
  SH4 eight digits with no label, and after a label of another number    nothing
  SH5 six digits after an ID label (SHORT_LENGTH is the fewest)    nothing
  SH6 a short near miss after an ID label                  nothing
  SH7 seven zeros after an ID label (trivial once padded)  nothing
  SH8 eight digits followed by two separators and a digit, after an ID label: part of a longer
      number                                               nothing

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

Known limits: a landline written as nine digits with no separator (0X1234567) and with no phone
label before it cannot be told from an ID that starts with 0, and is found as one.
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
    "unicode hyphen": f"{VALID[:3]}‐{VALID[3:6]}‐{VALID[6:]}",
    "non-breaking hyphen": f"{VALID[:8]}‑{VALID[8]}",
    "figure dash": f"{VALID[:8]}‒{VALID[8]}",
    "em dash": f"{VALID[:8]}—{VALID[8]}",
    "minus sign": f"{VALID[:8]}−{VALID[8]}",
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
    assert (detection.confidence, detection.band, detection.base_span) == (israeli_id.CONFIDENCE_LABELLED, "high", None)
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


@pytest.mark.parametrize("number", [f"{VALID}0", f"{VALID[:8]}-{VALID[8]}0"], ids=["ten digits", "ten with a hyphen"])
def test_a8_a_candidate_is_at_most_nine_digits(number: str) -> None:
    assert israeli_id.CANDIDATE.fullmatch(VALID)
    assert israeli_id.CANDIDATE.fullmatch(number) is None


def label(before: str) -> str | None:
    """Return the kind of label the detector reads before a number that follows `before`."""
    text = before + VALID
    result: str | None = israeli_id.label_before(text, len(before))
    return result


ID_LABELS = ["ת.ז. ", "ת.ז ", "ת\"ז ", "ת״ז ", "תעודת זהות ", "תעודת הזהות ", "מס' זהות ", "מס׳ זהות ", "מספר זהות: ", "מספר תעודת זהות ", "ID ", "I.D. "]
OTHER_LABELS = [
    "ח.פ. ", "ח\"פ ", "ע.ר. ", "ע״ר ", "דרכון ", "חשבון ", "טלפון ", "טל' ", "טל׳ ", "פקס ", "נייד ", "קופת חולים ", "מס' חבר ",
    "מספר אישי ", "מ.א. ", "רישיון ",
]  # fmt: skip


@pytest.mark.parametrize("before", ID_LABELS)
def test_l1_id_labels(before: str) -> None:
    assert label(before) == "id"


@pytest.mark.parametrize("before", OTHER_LABELS)
def test_l2_labels_of_other_numbers(before: str) -> None:
    assert label(before) == "other"


@pytest.mark.parametrize("before", ["", "המספר ", "שָׁלוֹם, "])
def test_l3_no_label(before: str) -> None:
    assert label(before) is None


@pytest.mark.parametrize("before", ["דרכון ות.ז. ", "ת.ז. או דרכון "], ids=["id nearer", "other nearer"])
def test_l4_the_id_label_counts_either_way_round(before: str) -> None:
    assert label(before) == "id"


def test_l5_a_label_too_far_before() -> None:
    assert label("ת.ז. " + "א" * israeli_id.LABEL_WINDOW + " ") is None
    assert label("ת.ז. " + "א" * (israeli_id.LABEL_WINDOW - 10) + " ") == "id"


@pytest.mark.parametrize("lead", ["", "שָׁלוֹם רב, המבקש פלוני אלמוני; "], ids=["at the start", "far into the text"])
def test_l5b_the_windows_edge(lead: str) -> None:
    # "ת.ז." is four characters; spaces fill the rest of the window after it.
    exactly = lead + "ת.ז." + " " * (israeli_id.LABEL_WINDOW - 4)
    one_more = lead + "ת.ז." + " " * (israeli_id.LABEL_WINDOW - 3)
    assert israeli_id.LABEL_WINDOW == 20
    assert label(exactly) == "id"
    assert label(one_more) is None


def test_l6_a_label_on_the_line_before() -> None:
    assert label("ת.ז.\n") is None


def test_l7_a_digit_between() -> None:
    assert label("ת.ז. 3 ו") is None


@pytest.mark.parametrize(("before", "kind"), [("ות.ז. ", "id"), ("לת\"ז ", "id"), ("ובדרכון ", "other")])
def test_l8_a_proclitic_on_the_label(before: str, kind: str) -> None:
    assert label(before) == kind


@pytest.mark.parametrize("before", ["מתזמן ", "טלפונית "])
def test_l9_letters_inside_a_longer_word(before: str) -> None:
    assert label(before) is None


COMBINED_LABELS = [
    "ת.ז./דרכון ", "ת\"ז/דרכון ", "ת״ז/ח.פ. ", "מספר זהות/דרכון: ", "מס' זהות/דרכון ", "ת.ז./ח.פ. ", "תעודת זהות/דרכון ",
    "ת.ז. או דרכון ",
]  # fmt: skip


@pytest.mark.parametrize("before", COMBINED_LABELS)
def test_l10_a_combined_form_label(before: str) -> None:
    assert label(before) == "id"


def test_l11_only_the_labels_after_the_last_digit_count() -> None:
    assert label("ת.ז. 3 דרכון ") == "other"


@pytest.mark.parametrize("before", OTHER_LABELS)
def test_ec5_a_valid_number_after_a_label_of_another_number(before: str) -> None:
    assert found(before + VALID) == []


@pytest.mark.parametrize(("before", "confidence"), [("ת.ז. ", "CONFIDENCE_LABELLED"), ("המספר ", "CONFIDENCE")])
def test_ec6_the_confidence(before: str, confidence: str) -> None:
    [detection] = IsraeliId().detect(projection(before + VALID), CTX)
    assert detection.confidence == getattr(israeli_id, confidence)
    assert israeli_id.CONFIDENCE < israeli_id.CONFIDENCE_LABELLED <= 1.0


@pytest.mark.parametrize("before", COMBINED_LABELS)
def test_ec7_a_valid_number_after_a_combined_form_label(before: str) -> None:
    detections = IsraeliId().detect(projection(before + VALID), CTX)
    assert [(each.span.start, each.span.end, each.confidence) for each in detections] == [(len(before), len(before) + 9, israeli_id.CONFIDENCE_LABELLED)]


def test_ec7_a_company_number_after_a_combined_form_label() -> None:
    assert israeli_id_checksum_ok(COMPANY)
    assert found("ת.ז./ח.פ. " + COMPANY) == []


# ZERO without its leading zero (eight digits), and an invented valid number with two (seven).
EIGHT = ZERO[1:]
SEVEN = ISRAELI_IDS.two_zeros[0][2:]


@pytest.mark.parametrize("before", ["ת.ז. ", "ת\"ז ", "מס' זהות ", "תעודת זהות "])
def test_sh1_eight_digits_after_an_id_label(before: str) -> None:
    assert israeli_id_checksum_ok(EIGHT)
    assert found(before + EIGHT) == [(len(before), len(before) + 8)]


def test_sh2_seven_digits_after_an_id_label() -> None:
    assert israeli_id_checksum_ok(SEVEN) and israeli_id_checksum_ok("00" + SEVEN)
    assert found("ת.ז. " + SEVEN) == [(5, 12)]


@pytest.mark.parametrize("written", [f"{EIGHT[:7]}-{EIGHT[7]}", f"{EIGHT[:4]} {EIGHT[4:]}"], ids=["7-1", "4-4"])
def test_sh3_eight_digits_with_a_separator(written: str) -> None:
    assert found("ת.ז. " + written) == [(5, 5 + len(written))]


@pytest.mark.parametrize("before", ["", "המספר ", "דרכון "])
def test_sh4_eight_digits_with_no_id_label(before: str) -> None:
    assert found(before + EIGHT) == []


def test_sh5_six_digits_after_an_id_label() -> None:
    six = next(f"{n:06d}" for n in range(100000, 999999) if israeli_id_checksum_ok(f"{n:06d}"))
    assert israeli_id.SHORT_LENGTH == 7
    assert found("ת.ז. " + six) == []


def test_sh6_a_short_near_miss() -> None:
    near = EIGHT[:-1] + str((int(EIGHT[-1]) + 1) % 10)
    assert not israeli_id_checksum_ok(near)
    assert found("ת.ז. " + near) == []


def test_sh7_seven_zeros() -> None:
    assert israeli_id_checksum_ok("0000000")
    assert found("ת.ז. 0000000") == []


@pytest.mark.parametrize("tail", ["--5", " - 5", "‑‑5"], ids=["two hyphens", "spaced hyphen", "two non-breaking hyphens"])
def test_sh8_a_short_form_inside_a_longer_number(tail: str) -> None:
    assert israeli_id_checksum_ok(EIGHT)
    assert found("ת.ז. " + EIGHT + tail) == []


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
