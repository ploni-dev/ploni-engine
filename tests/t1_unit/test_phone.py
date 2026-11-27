"""Test matrix for ploni/detect/deterministic/phone.py: the Israeli phone detector of issue #36.

Why: build-plan.md Phase 1, "Israeli phone": "Landline `0[23489]`, mobile `05\\d`, VoIP `07[2-9]`,
`+972` forms, `*NNNN` service numbers." Issue #36: "T1 with at least 40 positive and 40 negative
examples, in Hebrew context, with separator and gershayim variants ... Gate: none. A pattern-only
type reports its measured recall and precision." The span is the held-out batch's rule for PHONE
(its span rules, which the detector side may read by Achia's third answer on #283): "The number
from its first character to its last digit: a leading plus sign of an international prefix, a
leading star, and brackets around the area code are in; separators are in. Not the label." Every
phone number here is made when the tests run (tests/invented_numbers.py, PHONES; Achia,
2026-11-27, #32, "Make them fresh too (Recommended)"); none is written in this file, and no test
id holds one.

Test matrix:

label_before (the label before the number, on its line, within israeli_id.LABEL_WINDOW
characters, after the last digit there, as israeli_id.window_before reads it):
  L1  each phone label: טלפון, טל', טל׳, טל., נייד, נייד:, פלאפון, פקס, מס' טלפון, מס׳ טלפון,
      מספר טלפון                                             "phone"
  L2  a proclitic glued to it: בטלפון, ובטלפון, לפקס, הנייד, מהפלאפון    "phone"
  L3  another number's label: ת.ז., ת"ז, ח.פ., ע"ר, חשבון, כרטיס, דרכון, ID    "other"
  L4  no label; a label's letters inside a longer word: טלפוני, פקסים, ניידת    None
  L5  a combined label: טלפון/ת.ז., ת.ז. וטלפון               "phone"
  L6  a digit between the label and the number; the label on the line before    None

review_reason (the decision of needs_review):
  R1  a bare run of digits (no separator, no plus, no bracket, no star) with no label    the
      reason REVIEW_REASON
  R2  the same under a phone label; written with a separator; with a plus; a star    None

The detector (`Phone`):
  EC1 each written form of a mobile: plain; 3-7 with a hyphen, a space, a no-break space, a dot,
      a maqaf (U+05BE), an en dash, the Unicode hyphen (U+2010); 3-3-4 with hyphens and with
      spaces; 3-3-2-2; the area code in brackets, with a space, with none, with a hyphen and 3-4
      one detection, the span the number as written, brackets in
  EC2 a landline of each area code 02 03 04 08 09: 2-7, 2-3-4, plain, in brackets    found
  EC3 a VoIP number of 07[2-9]                                found
  EC4 the forms from abroad: +972-5X-XXXXXXX, +972 5X XXX XXXX, +9725XXXXXXXX, +9725X-XXXXXXX,
      972-5X-XXXXXXX, 00972-5X-XXXXXXX, +972-X-XXXXXXX (a landline of each area code), +972 (5X)
      XXXXXXX, a VoIP number                                  found, the span from the + (or
      the 9, or the first 0) to the last digit
  EC5 the 1-800 and 1-700 numbers: 1-800-XXX-XXX, 1800-XXX-XXX, 1-700-XX-XX-XX, 1800XXXXXX,
      1800 XXXXXX                                            found
  EC6 a short number, a star and four digits                  found, the star in the span
  EC7 two phones in one text                                  two detections, in order
  EC8 the fields: part the projection's, surface the text of its span, type PHONE, detector
      "phone", band "high", base_span None, detection_id "" (ids are made after detection:
      Achia, 2026-11-26, #169), needs_review False under a label
  EC9 the confidence: CONFIDENCE_LABELLED after a phone label, CONFIDENCE with none
  EC10 needs_review: a bare run with no label True, with REVIEW_REASON; a mobile, a landline
      and a 1-800 number so; with a separator, or under a label, False
  EC11 the label glued to the number (טלפון:), a proclitic on the label, a letter glued to the
      number (ב...), the number in brackets as a whole ((03-...)): found, the span the number only
  B1  the number alone, at the start and at the end of the text    found
  B2  the empty text; a text with no digit                    nothing
  A1  an area code the plan does not name: 01X and 06X (ten digits), 01, 05, 06, 07 (nine), each
      plain and with a separator after the area code          nothing
  A2  a mobile or a landline a digit short or a digit long, plain and with a separator    nothing
  A3  a phone inside a longer number: a digit after it; "-5" after it; "7-" before it; a digit
      after one plain space (a known limit)                   nothing
  A4  two separators in a row, inside the number or after the area code    nothing
  A5  other numbers with no label: an Israeli ID that does not start with 0, a company and a
      non-profit number, plain and 5X-XXXXXXX, a card, a near miss of an ID    nothing
  A6  a date (dd.mm.yyyy, dd/mm/yy, d.m.yyyy), a case number NNNNN-MM-YY, an amount with commas,
      an IBAN-like string of groups of four, a time            nothing
  A7  Arabic-Indic digits                                     nothing
  A8  groupings no phone is written in: a mobile 4-6, a landline 3-6, a landline 8-1 (an ID with
      its check digit apart), a landline 2-4-3                nothing
  A9  from abroad with the 0 kept (+972-05X-...): a known limit    nothing
  A10 a mobile without its 0 (5X-XXXXXXX) with no label or a phone label: a known limit, the
      question of docs/DEBT.md row 16                         nothing
  A11 a star and three digits; a star and five               nothing
  A12 under another number's label: an ID label before a landline 2-3-4 and 2-7, a company
      label, a bank account's, a card's                      nothing; with a phone label too
      (a combined label)                                     found; a phone after a refused
      number, in the same text                               found (added after the code, for
      a mutant of Cosmic Ray that survived: the refusal's `continue` made `break`)
  A13 CANDIDATE itself: each prefix of the plan matches whole; 01X, 06X and a mobile a digit
      long do not

The fixture (tests/fixtures/detect/phone.json; its numbers are filled in when the tests run):
  F1  at least 40 positive and 40 negative texts
  F2  recall and precision, counted by exact span, printed with every miss by its case's place
      in the fixture, never by its text; the plan sets PHONE no gate (issue #36: "Gate: none"),
      so the test asks that every case is as the fixture says, which is Claude's choice and only
      narrows

Hebrew axes: gershayim as " and ״ in the text around the number (ע"י, ע״י, עו"ד); geresh as '
and ׳ in a label (טל', טל׳, מס' טלפון, מס׳ טלפון); a proclitic glued to the label and a letter
glued to the number; niqqud before it; RLM and LRM around it; the maqaf as a separator. Names
that are ordinary words do not apply but one: טל, a name, is no label without its geresh (L4 asks
of טלפוני, the fixture of טל). Document axes: a number on a line of its own, in a table row;
the part is the projection's.

Known limits: those of the module, among them A3's digit after a plain space, A9 and A10.
"""

from pathlib import Path

import pytest

from ploni.detect.base import DetectContext
from ploni.detect.deterministic import phone
from ploni.detect.deterministic.phone import CANDIDATE, REVIEW_REASON, Phone, label_before, review_reason
from ploni.types import Span
from tests.detector_contract import projection
from tests.invented_numbers import CARDS, ISRAELI_IDS, PHONES, read_cases

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "detect" / "phone.json"
CTX = DetectContext()
MOBILE = PHONES.mobile[0]
LANDLINE = PHONES.landline[0]
ABROAD = PHONES.abroad_mobile[0]
SERVICE = PHONES.service[0]


def found(text: str) -> list[tuple[int, int]]:
    """Return the places the detector finds in a text."""
    return [(each.span.start, each.span.end) for each in Phone().detect(projection(text), CTX)]


def only(text: str, number: str) -> list[tuple[int, int]]:
    """Return the place of the one number in a text, as the detector should find it."""
    start = text.index(number)
    return [(start, start + len(number))]


def groups(number: str, sizes: tuple[int, ...], separator: str = "-") -> str:
    """Write a number in groups of the given sizes, joined by the separator."""
    at, out = 0, []
    for size in sizes:
        out.append(number[at : at + size])
        at += size
    return separator.join(out)


def bracketed(number: str, area: int, rest: str) -> str:
    """Write a number with its area code of `area` digits in brackets, then `rest` and the rest."""
    return f"({number[:area]}){rest}{number[area:]}"


LABELS = ("טלפון", "טל'", "טל׳", "טל.", "נייד", "נייד:", "פלאפון", "פקס", "מס' טלפון", "מס׳ טלפון", "מספר טלפון")


@pytest.mark.parametrize("label", LABELS)
def test_l1_each_phone_label(label: str) -> None:
    text = f"{label} {MOBILE}"
    assert label_before(text, text.index(MOBILE)) == "phone"


@pytest.mark.parametrize("label", ["בטלפון", "ובטלפון", "לפקס", "הנייד", "מהפלאפון"])
def test_l2_a_proclitic_on_the_label(label: str) -> None:
    text = f"ניתן להשיג אותו {label} {MOBILE}"
    assert label_before(text, text.index(MOBILE)) == "phone"


@pytest.mark.parametrize("label", ["ת.ז.", 'ת"ז', "ח.פ.", 'ע"ר', "חשבון", "כרטיס", "דרכון", "ID"])
def test_l3_another_numbers_label(label: str) -> None:
    text = f"{label} {LANDLINE}"
    assert label_before(text, text.index(LANDLINE)) == "other"


@pytest.mark.parametrize("before", ["התקשרו אל ", "טלפוני ", "פקסים ", "ניידת "])
def test_l4_no_label(before: str) -> None:
    text = before + MOBILE
    assert label_before(text, text.index(MOBILE)) is None


@pytest.mark.parametrize("label", ["טלפון/ת.ז.", "ת.ז. וטלפון"])
def test_l5_a_combined_label(label: str) -> None:
    text = f"{label}: {MOBILE}"
    assert label_before(text, text.index(MOBILE)) == "phone"


@pytest.mark.parametrize("before", ["טלפון 3 ", "טלפון\n"], ids=["digit between", "line before"])
def test_l6_a_label_not_read(before: str) -> None:
    text = before + MOBILE
    assert label_before(text, text.index(MOBILE)) is None


@pytest.mark.parametrize("number", [MOBILE, LANDLINE, SERVICE], ids=["mobile", "landline", "service"])
def test_r1_a_bare_run_with_no_label(number: str) -> None:
    assert review_reason(number, None) == REVIEW_REASON


@pytest.mark.parametrize(
    ("raw", "label"),
    [(MOBILE, "phone"), (groups(MOBILE, (3, 7)), None), (ABROAD, None), (PHONES.short[0], None)],
    ids=["phone label", "separator", "plus", "star"],
)
def test_r2_no_review(raw: str, label: str | None) -> None:
    assert review_reason(raw, label) is None


MOBILE_FORMS = {
    "plain": MOBILE,
    "3-7 hyphen": groups(MOBILE, (3, 7)),
    "3-7 space": groups(MOBILE, (3, 7), " "),
    "3-7 no-break space": groups(MOBILE, (3, 7), " "),
    "3-7 dot": groups(MOBILE, (3, 7), "."),
    "3-7 maqaf": groups(MOBILE, (3, 7), "־"),
    "3-7 en dash": groups(MOBILE, (3, 7), "–"),
    "3-7 unicode hyphen": groups(MOBILE, (3, 7), "‐"),
    "3-3-4 hyphens": groups(MOBILE, (3, 3, 4)),
    "3-3-4 spaces": groups(MOBILE, (3, 3, 4), " "),
    "3-3-2-2": groups(MOBILE, (3, 3, 2, 2)),
    "brackets and a space": bracketed(MOBILE, 3, " "),
    "brackets and nothing": bracketed(MOBILE, 3, ""),
    "brackets, a hyphen, 3-4": f"({MOBILE[:3]})-{MOBILE[3:6]}-{MOBILE[6:]}",
}


@pytest.mark.parametrize("form", MOBILE_FORMS)
def test_ec1_each_written_form_of_a_mobile(form: str) -> None:
    text = f"מספר הנייד של המבקש: {MOBILE_FORMS[form]}."
    assert found(text) == only(text, MOBILE_FORMS[form])


LANDLINE_SHAPES = {
    "2-7": lambda n: groups(n, (2, 7)),
    "2-3-4": lambda n: groups(n, (2, 3, 4), " "),
    "plain": lambda n: n,
    "brackets": lambda n: bracketed(n, 2, " "),
}


@pytest.mark.parametrize("area", range(5), ids=["02", "03", "04", "08", "09"])
@pytest.mark.parametrize("shape", LANDLINE_SHAPES)
def test_ec2_a_landline_of_each_area_code(area: int, shape: str) -> None:
    written = LANDLINE_SHAPES[shape](PHONES.landline[2 * area])
    text = f"משרדי החברה, טל' {written}, פתוחים בבוקר"
    assert found(text) == only(text, written)


@pytest.mark.parametrize("index", range(6))
def test_ec3_a_voip_number(index: int) -> None:
    written = groups(PHONES.voip[index], (3, 7))
    text = f"לבירורים: {written}"
    assert found(text) == only(text, written)


ABROAD_FORMS = {
    "+972-5X-XXXXXXX": groups(ABROAD, (4, 2, 7)),
    "+972 5X XXX XXXX": groups(ABROAD, (4, 2, 3, 4), " "),
    "plain": ABROAD,
    "+9725X-XXXXXXX": groups(ABROAD, (6, 7)),
    "972-5X-XXXXXXX": groups(ABROAD[1:], (3, 2, 7)),
    "00972-5X-XXXXXXX": groups(PHONES.double_zero[0], (5, 2, 7)),
    "+972 (5X) XXXXXXX": f"{ABROAD[:4]} ({ABROAD[4:6]}) {ABROAD[6:]}",
    "voip": groups(PHONES.abroad_voip[0], (4, 2, 7)),
    **{f"landline {area}": groups(PHONES.abroad_landline[i], (4, 1, 7)) for i, area in enumerate("23489")},
}


@pytest.mark.parametrize("form", ABROAD_FORMS)
def test_ec4_the_forms_from_abroad(form: str) -> None:
    text = f'ע"י הנתבע, מחו"ל: {ABROAD_FORMS[form]}'
    assert found(text) == only(text, ABROAD_FORMS[form])


SERVICE_FORMS = {
    "1-800-XXX-XXX": groups(SERVICE, (1, 3, 3, 3)),
    "1800-XXX-XXX": groups(SERVICE, (4, 3, 3)),
    "1-X00-XX-XX-XX": groups(PHONES.service[1], (1, 3, 2, 2, 2)),
    "plain": SERVICE,
    "1800 XXXXXX": groups(SERVICE, (4, 6), " "),
}


@pytest.mark.parametrize("form", SERVICE_FORMS)
def test_ec5_the_service_numbers(form: str) -> None:
    text = f"מוקד שירות הלקוחות ({SERVICE_FORMS[form]}) זמין"
    assert found(text) == only(text, SERVICE_FORMS[form])


@pytest.mark.parametrize("index", range(4))
def test_ec6_a_short_number(index: int) -> None:
    text = f"חייגו {PHONES.short[index]} מכל טלפון"
    assert found(text) == only(text, PHONES.short[index])


def test_ec7_two_phones() -> None:
    first, second = groups(MOBILE, (3, 7)), groups(LANDLINE, (2, 7))
    text = f"טלפון {first}, פקס {second}."
    a, b = text.index(first), text.index(second)
    assert found(text) == [(a, a + len(first)), (b, b + len(second))]


def test_ec8_the_fields() -> None:
    written = groups(MOBILE, (3, 7))
    proj = projection(f"שָׁלוֹם, נייד ‏{written}‎.", part="header1")
    [detection] = Phone().detect(proj, CTX)
    assert detection.span == Span(proj.text.index(written), proj.text.index(written) + len(written))
    assert (detection.part, detection.surface, detection.entity_type, detection.detector) == ("header1", written, "PHONE", "phone")
    assert (detection.confidence, detection.band, detection.base_span) == (phone.CONFIDENCE_LABELLED, "high", None)
    assert (detection.detection_id, detection.needs_review, detection.review_reason) == ("", False, None)


@pytest.mark.parametrize(("before", "confidence"), [("טלפון ", "CONFIDENCE_LABELLED"), ("ניתן להתקשר ", "CONFIDENCE"), ("", "CONFIDENCE")])
def test_ec9_the_confidence(before: str, confidence: str) -> None:
    [detection] = Phone().detect(projection(before + groups(MOBILE, (3, 7))), CTX)
    assert detection.confidence == getattr(phone, confidence)


@pytest.mark.parametrize(
    ("text", "review"),
    [
        (f"התקשרו {MOBILE}", True),
        (f"התקשרו {LANDLINE}", True),
        (f"התקשרו {SERVICE}", True),
        (f"התקשרו {groups(MOBILE, (3, 7))}", False),
        (f"נייד {MOBILE}", False),
    ],
    ids=["bare mobile", "bare landline", "bare service", "separator", "label"],
)
def test_ec10_needs_review(text: str, review: bool) -> None:
    [detection] = Phone().detect(projection(text), CTX)
    assert (detection.needs_review, detection.review_reason) == (review, REVIEW_REASON if review else None)


GLUED = {
    "glued": (f"טלפון:{groups(MOBILE, (3, 7))}", groups(MOBILE, (3, 7))),
    "proclitic": (f"ובטלפון {groups(MOBILE, (3, 7))}", groups(MOBILE, (3, 7))),
    "letter": (f"ב{groups(LANDLINE, (2, 7))}", groups(LANDLINE, (2, 7))),
    "whole in brackets": (f"המשרד ({groups(LANDLINE, (2, 7))})", groups(LANDLINE, (2, 7))),
}


@pytest.mark.parametrize("case", GLUED)
def test_ec11_the_label_or_a_letter_glued(case: str) -> None:
    text, written = GLUED[case]
    assert found(text) == only(text, written)


@pytest.mark.parametrize("where", ["alone", "start", "end"])
def test_b1_at_either_end(where: str) -> None:
    written = groups(MOBILE, (3, 7))
    text = {"alone": written, "start": f"{written} הוא מספר הנייד", "end": f"מספר הנייד הוא {written}"}[where]
    assert found(text) == only(text, written)


@pytest.mark.parametrize("text", ["", "אין כאן מספר כלל.", "\n"])
def test_b2_nothing_to_find(text: str) -> None:
    assert found(text) == []


@pytest.mark.parametrize("index", range(12))
def test_a1_an_area_code_the_plan_does_not_name(index: int) -> None:
    number = PHONES.wrong_area[index]
    area = 3 if len(number) == 10 else 2
    for written in (number, groups(number, (area, len(number) - area))):
        assert found(f"טלפון {written}") == []


@pytest.mark.parametrize("index", range(8))
def test_a2_a_digit_short_or_long(index: int) -> None:
    number = (PHONES.short_line + PHONES.long_line)[index]
    area = 3 if number[:2] == "05" else 2
    for written in (number, groups(number, (area, len(number) - area))):
        assert found(f"טלפון {written}") == []


@pytest.mark.parametrize("which", ["a digit after", "-5 after", "7- before", "a digit after a space"])
def test_a3_inside_a_longer_number(which: str) -> None:
    written = groups(MOBILE, (3, 7))
    text = {"a digit after": f"{written}7", "-5 after": f"{written}-5", "7- before": f"7-{written}", "a digit after a space": f"{written} 3 ילדים"}[which]
    assert found(text) == []


@pytest.mark.parametrize("which", ["inside", "after the area code", "space and hyphen"])
def test_a4_two_separators_in_a_row(which: str) -> None:
    written = {
        "inside": f"{MOBILE[:6]}--{MOBILE[6:]}",
        "after the area code": f"{MOBILE[:3]}--{MOBILE[3:]}",
        "space and hyphen": f"{MOBILE[:3]} -{MOBILE[3:]}",
    }[which]
    assert found(f"טלפון {written}") == []


def other_numbers() -> dict[str, str]:
    """Return numbers of other kinds, each written as it is written, by a name."""
    person = next(n for n in ISRAELI_IDS.valid if n[0] != "0")
    company = ISRAELI_IDS.company[0]
    return {
        "id": person,
        "id near miss": next(n for n in ISRAELI_IDS.near if n[0] != "0"),
        "company": company,
        "company 2-7": groups(company, (2, 7)),
        "nonprofit 2-7": groups(ISRAELI_IDS.nonprofit[0], (2, 7)),
        "card": groups(CARDS.visa[0], (4, 4, 4, 4), " "),
    }


@pytest.mark.parametrize("which", list(other_numbers()))
def test_a5_other_numbers_with_no_label(which: str) -> None:
    assert found(f"המספר {other_numbers()[which]} נרשם") == []


def iban_like() -> str:
    """Return IL, two digits and nineteen, in groups of four, made of an invented card's digits."""
    digits = CARDS.visa19[0][:2] + CARDS.visa19[1]
    return "IL" + groups(digits, (2, 4, 4, 4, 4, 3), " ")


NOT_PHONES = {
    "date dd.mm.yyyy": "ביום 12.03.2024 התקיים דיון",
    "date dd/mm/yy": "ביום 08/11/23 התקיים דיון",
    "date d.m.yyyy": "ביום 2.3.2024 התקיים דיון",
    "case number": f"ת\"א {groups(ISRAELI_IDS.case, (5, 2, 2))}",
    "amount": 'סך של 1,800,000 ש"ח',
    "time": "בשעה 09:30 בבוקר",
}


@pytest.mark.parametrize("which", [*NOT_PHONES, "iban-like"])
def test_a6_dates_cases_amounts_and_ibans(which: str) -> None:
    text = NOT_PHONES[which] if which != "iban-like" else f"חשבון מס' {iban_like()}"
    assert found(text) == []


def test_a7_arabic_indic_digits() -> None:
    assert found("טלפון " + "".join(chr(0x0660 + int(d)) for d in MOBILE)) == []


GROUPINGS = {
    "mobile 4-6": (MOBILE, (4, 6)),
    "landline 3-6": (LANDLINE, (3, 6)),
    "landline 8-1": (LANDLINE, (8, 1)),
    "landline 2-4-3": (LANDLINE, (2, 4, 3)),
}


@pytest.mark.parametrize("grouping", GROUPINGS)
def test_a8_groupings_no_phone_is_written_in(grouping: str) -> None:
    number, sizes = GROUPINGS[grouping]
    assert found(f"המספר {groups(number, sizes)} נרשם") == []


def test_a9_from_abroad_with_the_zero_kept() -> None:
    assert found(f"טלפון +972-{groups(MOBILE, (3, 7))}") == []


@pytest.mark.parametrize("before", ["המספר ", "נייד "], ids=["no label", "phone label"])
def test_a10_a_mobile_without_its_zero(before: str) -> None:
    assert found(before + groups(MOBILE[1:], (2, 7))) == []


@pytest.mark.parametrize("which", ["three digits", "five digits"])
def test_a11_a_star_and_too_few_or_too_many(which: str) -> None:
    written = PHONES.short[0][:4] if which == "three digits" else PHONES.short[0] + PHONES.short[1][1]
    assert found(f"חייגו {written} מכל טלפון") == []


UNDER_OTHER = {
    "id label, 2-3-4": ("ת.ז. ", groups(LANDLINE, (2, 3, 4))),
    "id label, 2-7": ("ת.ז. ", groups(LANDLINE, (2, 7))),
    "company label": ("ח.פ. ", groups(MOBILE, (3, 7))),
    "bank account": ("חשבון ", groups(LANDLINE, (2, 7))),
    "card": ("כרטיס ", groups(MOBILE, (3, 7))),
}


@pytest.mark.parametrize("case", UNDER_OTHER)
def test_a12_under_another_numbers_label(case: str) -> None:
    before, written = UNDER_OTHER[case]
    assert found(before + written) == []


def test_a12_with_a_phone_label_too() -> None:
    text = f"טלפון/ת.ז.: {groups(LANDLINE, (2, 7))}"
    assert found(text) == only(text, groups(LANDLINE, (2, 7)))


def test_a12_a_phone_after_a_refused_number() -> None:
    refused, phone_number = groups(LANDLINE, (2, 7)), groups(MOBILE, (3, 7))
    text = f"ת.ז. {refused}, נייד {phone_number}"
    assert found(text) == only(text, phone_number)


def test_a13_the_candidate_pattern() -> None:
    for number in (MOBILE, LANDLINE, PHONES.voip[0], SERVICE, PHONES.short[0], ABROAD, PHONES.double_zero[0]):
        assert CANDIDATE.fullmatch(number)
    for number in (*PHONES.wrong_area, PHONES.long_line[0]):
        assert CANDIDATE.search(number) is None


def cases() -> tuple[list[tuple[str, set[tuple[int, int]]]], int, int]:
    """Read the fixture, its numbers filled in: each text with its expected places, and the counts of positive and negative texts."""
    positives, negatives = read_cases(FIXTURE, PHONES)
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
    # Issue #36: "Gate: none"; every case as the fixture says it (the module docstring of this file).
    assert misses == [] and wrong == []
