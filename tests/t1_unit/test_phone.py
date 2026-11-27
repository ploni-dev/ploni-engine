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
  L3  an ID label: ת.ז., ת"ז, מספר זהות, ID                  "id"; another number's label:
      ח.פ., ע"ר, חשבון, כרטיס, דרכון, בנק, סניף               "other" (since the review of
      b2f3790, findings 1 and 2, the two kinds are told apart: the first form asked "other" of both)
  L4  no label; a label's letters inside a longer word: טלפוני, פקסים, ניידת    None
  L5  a combined label: טלפון/ת.ז., ת.ז. וטלפון               "phone"; ת.ז./ח.פ.    "id"
  L6  a digit between the label and the number; the label on the line before    None

refused (the decision of the label; the review of b2f3790, findings 1 and 2):
  RF1 no label, a phone label                                 False, whatever the number
  RF2 another number's label: a landline of nine digits       True; a mobile and a VoIP number
      (ten), a landline from abroad (eleven), a 1-800 number, a star number    False
  RF3 an ID label: a landline-shaped number that passes the ID check, written 0X-XXX-XXXX and
      plain (the ID detector takes it)                       True; the same written 0X-XXXXXXX
      (the ID detector refuses that shape under its label, #302), one that fails the check, a
      mobile                                                 False

review_reason (the decision of needs_review):
  R1  a bare run of digits (no separator, no plus, no bracket, no star) with no label    the
      reason REVIEW_REASON
  R2  the same under a phone label; written with a separator; with a plus; a star; under
      another number's label                                 None
  R3  under an ID label, bare or with separators               ID_LABEL_REASON

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
  EC12 two phones joined by a plain space, by a slash, by " / " (the review of b2f3790, finding
      3)                                                     both found; a landline and "/8" (its
      second line's last digit)                              the landline's span; a phone and a
      digit after one plain space ("<phone> 3 ילדים")         the phone (until that review, A3
      asked nothing here: it now asks more)
  EC13 from abroad with the 0 kept, "0" or "(0)" right before the area code (Achia, 2026-11-27,
      #36, "Yes, find them (Recommended)"): +972-0X-XXXXXXX, +972 (0)X XXXXXXX, +972-05X-XXXXXXX,
      +972 (0)5X-XXX-XXXX, +9720X..., 00972-0..., 972 (0)..., a VoIP number, with a phone label and
      with none                                              found, the span from the + (or the
      first 9 or 0) to the last digit (until that answer, A9 asked nothing of these: it now asks
      more)
  B1the number alone, at the start and at the end of the text    found
  B2  the empty text; a text with no digit                    nothing
  A1  an area code the plan does not name: 01X and 06X (ten digits), 01, 05, 06, 07 (nine), each
      plain and with a separator after the area code          nothing
  A2  a mobile or a landline a digit short or a digit long, plain and with a separator    nothing
  A3  a phone inside a longer number: a digit after it; "-5" after it; "7-" before it; "-8" after
      a landline; a digit and a dot before it                 nothing
  A4  two separators in a row, inside the number or after the area code    nothing
  A5  other numbers with no label: an Israeli ID that does not start with 0, a company and a
      non-profit number, plain and 5X-XXXXXXX, a card, a near miss of an ID    nothing
  A6  a date (dd.mm.yyyy, dd/mm/yy, d.m.yyyy), a case number NNNNN-MM-YY, an amount with commas,
      an IBAN-like string of groups of four, a time            nothing
  A7  Arabic-Indic digits                                     nothing
  A8  groupings no phone is written in: a mobile 4-6, a landline 3-6, a landline 8-1 (an ID with
      its check digit apart), a landline 2-4-3                nothing
  A9  from abroad with the 0 kept and a separator between it and the area code (+972-0-5X-...,
      +972 (0) 3 ...): the rule Achia chose names the 0 or (0) glued to the area code    nothing;
      an area code the plan does not name after the kept 0 (+972-01X-...)    nothing
  A10 a mobile without its 0 (5X-XXXXXXX) with no label or a phone label: a known limit, the
      question of docs/DEBT.md row 16                         nothing
  A11 a star and three digits; a star and five               nothing
  A12 under another number's label (ח.פ., חשבון, סניף הבנק, בנק, כרטיס ביקור, דרכון): a
      landline 2-7                                           nothing; a mobile 3-7, a VoIP
      number, a number from abroad, a 1-800 number           found, not flagged (the review of
      b2f3790, finding 1: the first form refused all); with a phone label too (a combined label)
      found; a phone after a refused number, in the same text    found (added after the code, for
      a mutant of Cosmic Ray that survived: the refusal's `continue` made `break`)
  A14 under an ID label (ת.ז., ת"ז, מספר זהות): a number that passes the ID check written
      0X-XXX-XXXX                                            nothing from this detector, IL_ID
      through detect_all; the same written 0X-XXXXXXX, a landline that fails the check, a mobile
      found, flagged with ID_LABEL_REASON, and no IL_ID on its span (the review of b2f3790,
      finding 2: "ת.ז. 0X-XXXXXXX" was found by no detector)
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

Known limits: those of the module, among them A3's "-8", A9 and A10.
"""

from pathlib import Path

import pytest

from eval import detectors
from ploni.detect.base import DetectContext
from ploni.detect.deterministic import phone
from ploni.detect.deterministic.phone import CANDIDATE, ID_LABEL_REASON, REVIEW_REASON, Phone, label_before, refused, review_reason
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


@pytest.mark.parametrize("label", ["ת.ז.", 'ת"ז', "מספר זהות", "ID"])
def test_l3_an_id_label(label: str) -> None:
    text = f"{label} {LANDLINE}"
    assert label_before(text, text.index(LANDLINE)) == "id"


@pytest.mark.parametrize("label", ["ח.פ.", 'ע"ר', "חשבון", "כרטיס", "דרכון", "בנק", "סניף"])
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


def test_l5_an_id_and_a_company_label() -> None:
    text = f"ת.ז./ח.פ.: {MOBILE}"
    assert label_before(text, text.index(MOBILE)) == "id"


@pytest.mark.parametrize("before", ["טלפון 3 ", "טלפון\n"], ids=["digit between", "line before"])
def test_l6_a_label_not_read(before: str) -> None:
    text = before + MOBILE
    assert label_before(text, text.index(MOBILE)) is None


@pytest.mark.parametrize("number", [MOBILE, LANDLINE, SERVICE], ids=["mobile", "landline", "service"])
def test_r1_a_bare_run_with_no_label(number: str) -> None:
    assert review_reason(number, None) == REVIEW_REASON


@pytest.mark.parametrize(
    ("raw", "label"),
    [(MOBILE, "phone"), (groups(MOBILE, (3, 7)), None), (ABROAD, None), (PHONES.short[0], None), (MOBILE, "other")],
    ids=["phone label", "separator", "plus", "star", "other label"],
)
def test_r2_no_review(raw: str, label: str | None) -> None:
    assert review_reason(raw, label) is None


@pytest.mark.parametrize("raw", [LANDLINE, groups(LANDLINE, (2, 7))], ids=["bare", "separator"])
def test_r3_under_an_id_label(raw: str) -> None:
    assert review_reason(raw, "id") == ID_LABEL_REASON


def id_landline() -> str:
    """Return an invented number that passes the ID check and has a landline's prefix (0[23489])."""
    return ISRAELI_IDS.landline[0]


def failing_landline() -> str:
    """Return that number with another last digit, so that the ID check fails it."""
    number = id_landline()
    return number[:-1] + str((int(number[-1]) + 1) % 10)


ANY_NUMBER = {"landline": groups(LANDLINE, (2, 7)), "mobile": groups(MOBILE, (3, 7)), "bare landline": LANDLINE}


@pytest.mark.parametrize("label", [None, "phone"], ids=["no label", "phone label"])
@pytest.mark.parametrize("which", ANY_NUMBER)
def test_rf1_no_label_or_a_phone_label(label: str | None, which: str) -> None:
    assert not refused(ANY_NUMBER[which], label)


UNDER_ANOTHER = {
    "landline": (groups(LANDLINE, (2, 7)), True),
    "mobile": (groups(MOBILE, (3, 7)), False),
    "voip": (groups(PHONES.voip[0], (3, 7)), False),
    "landline from abroad": (groups(PHONES.abroad_landline[0], (4, 1, 7)), False),
    "1-800": (groups(SERVICE, (1, 3, 3, 3)), False),
    "star": (PHONES.short[0], False),
}


@pytest.mark.parametrize("which", UNDER_ANOTHER)
def test_rf2_another_numbers_label(which: str) -> None:
    raw, expected = UNDER_ANOTHER[which]
    assert refused(raw, "other") is expected


def under_an_id_label() -> dict[str, tuple[str, bool]]:
    """Return candidates under an ID label, by name, each with whether it is refused."""
    passing, failing = id_landline(), failing_landline()
    return {
        "passes, 0X-XXX-XXXX": (groups(passing, (2, 3, 4)), True),
        "passes, plain": (passing, True),
        "passes, 0X-XXXXXXX": (groups(passing, (2, 7)), False),
        "fails the check": (groups(failing, (2, 3, 4)), False),
        "mobile": (groups(MOBILE, (3, 7)), False),
    }


@pytest.mark.parametrize("which", list(under_an_id_label()))
def test_rf3_an_id_label(which: str) -> None:
    raw, expected = under_an_id_label()[which]
    assert refused(raw, "id") is expected


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


@pytest.mark.parametrize("between", [" ", "/", " / "], ids=["space", "slash", "spaced slash"])
def test_ec12_two_phones_joined(between: str) -> None:
    first, second = groups(MOBILE, (3, 7)), groups(PHONES.mobile[1], (3, 7))
    text = f"טלפונים: {first}{between}{second} בלבד"
    a = text.index(first)
    b = a + len(first) + len(between)
    assert found(text) == [(a, a + len(first)), (b, b + len(second))]


@pytest.mark.parametrize("after", ["/8", " 3 ילדים"], ids=["slash and a digit", "space and a digit"])
def test_ec12_a_digit_after_a_slash_or_a_space(after: str) -> None:
    landline = groups(LANDLINE, (2, 7))
    text = f"טל' {landline}{after}"
    assert found(text) == only(text, landline)


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


@pytest.mark.parametrize("which", ["a digit after", "-5 after", "7- before", "-8 after a landline", "a digit and a dot before"])
def test_a3_inside_a_longer_number(which: str) -> None:
    written, landline = groups(MOBILE, (3, 7)), groups(LANDLINE, (2, 7))
    text = {
        "a digit after": f"{written}7",
        "-5 after": f"{written}-5",
        "7- before": f"7-{written}",
        "-8 after a landline": f"טל' {landline}-8",
        "a digit and a dot before": f"מספר 7.{written}",
    }[which]
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


def kept_zero_forms() -> dict[str, str]:
    """Return numbers from abroad with their 0 kept, as letterheads write them, by name."""
    land, other, mob, voip = PHONES.kept_zero
    return {
        "+972-0X-XXXXXXX": groups(land, (4, 2, 7)),
        "+972 (0)X XXXXXXX": f"{land[:4]} ({land[4]}){land[5]} {land[6:]}",
        "+972 0X XXX XXXX": groups(other, (4, 2, 3, 4), " "),
        "+972-05X-XXXXXXX": groups(mob, (4, 3, 7)),
        "+972 (0)5X-XXX-XXXX": f"{mob[:4]} ({mob[4]}){mob[5:7]}-{mob[7:10]}-{mob[10:]}",
        "plain": land,
        "00972-0X-XXXXXXX": groups("00" + land[1:], (5, 2, 7)),
        "972 (0)X XXXXXXX": f"{land[1:4]} ({land[4]}){land[5]} {land[6:]}",
        "voip": groups(voip, (4, 3, 7)),
    }


@pytest.mark.parametrize("before", ["Tel: ", "טלפון: ", "המשרד "], ids=["latin", "label", "no label"])
@pytest.mark.parametrize("form", list(kept_zero_forms()))
def test_ec13_from_abroad_with_the_zero_kept(form: str, before: str) -> None:
    written = kept_zero_forms()[form]
    text = f"{before}{written}, עד כאן"
    assert found(text) == only(text, written)


def test_a9_a_separator_after_the_kept_zero() -> None:
    land, _, mob, _ = PHONES.kept_zero
    for written in (f"{mob[:4]}-{mob[4]}-{mob[5:7]}-{mob[7:]}", f"{land[:4]} ({land[4]}) {land[5]}-{land[6:]}"):
        assert found(f"טלפון {written}") == []


def test_a9_an_area_code_the_plan_does_not_name_after_the_kept_zero() -> None:
    assert found(f"טלפון +972-{groups(PHONES.wrong_area[0], (3, 7))}") == []


@pytest.mark.parametrize("before", ["המספר ", "נייד "], ids=["no label", "phone label"])
def test_a10_a_mobile_without_its_zero(before: str) -> None:
    assert found(before + groups(MOBILE[1:], (2, 7))) == []


@pytest.mark.parametrize("which", ["three digits", "five digits"])
def test_a11_a_star_and_too_few_or_too_many(which: str) -> None:
    written = PHONES.short[0][:4] if which == "three digits" else PHONES.short[0] + PHONES.short[1][1]
    assert found(f"חייגו {written} מכל טלפון") == []


OTHER_LABELS = {
    "company": "ח.פ. ",
    "account": "על חשבון הנתבע, ",
    "branch": "סניף הבנק: ",
    "bank": "בנק ",
    "business card": "כרטיס ביקור: ",
    "passport": "דרכון ",
}
LONGER = {
    "mobile": groups(MOBILE, (3, 7)),
    "voip": groups(PHONES.voip[0], (3, 7)),
    "from abroad": groups(ABROAD, (4, 2, 7)),
    "1-800": groups(SERVICE, (1, 3, 3, 3)),
}


@pytest.mark.parametrize("label", OTHER_LABELS)
def test_a12_a_landline_under_another_numbers_label(label: str) -> None:
    assert found(OTHER_LABELS[label] + groups(LANDLINE, (2, 7))) == []


@pytest.mark.parametrize("label", OTHER_LABELS)
@pytest.mark.parametrize("which", LONGER)
def test_a12_a_longer_phone_under_another_numbers_label(label: str, which: str) -> None:
    text = OTHER_LABELS[label] + LONGER[which]
    [detection] = Phone().detect(projection(text), CTX)
    assert (detection.span.start, detection.span.end) == only(text, LONGER[which])[0]
    assert (detection.needs_review, detection.confidence) == (False, phone.CONFIDENCE)


def test_a12_with_a_phone_label_too() -> None:
    text = f"טלפון/ת.ז.: {groups(LANDLINE, (2, 7))}"
    assert found(text) == only(text, groups(LANDLINE, (2, 7)))


def test_a12_a_phone_after_a_refused_number() -> None:
    landline, phone_number = groups(LANDLINE, (2, 7)), groups(MOBILE, (3, 7))
    text = f"חשבון {landline}, נייד {phone_number}"
    assert found(text) == only(text, phone_number)


ID_LABELS = ("ת.ז. ", 'ת"ז: ', "מספר זהות ")


@pytest.mark.parametrize("label", ID_LABELS)
def test_a14_an_id_the_id_detector_takes(label: str) -> None:
    written = groups(id_landline(), (2, 3, 4))
    text = label + written
    assert found(text) == []
    assert detectors.detect_all(text) == [(*only(text, written)[0], "IL_ID")]


@pytest.mark.parametrize("label", ID_LABELS)
@pytest.mark.parametrize("which", ["passes, 0X-XXXXXXX", "fails the check", "mobile"])
def test_a14_a_phone_shape_the_id_detector_leaves(label: str, which: str) -> None:
    written = under_an_id_label()[which][0]
    text = label + written
    [detection] = Phone().detect(projection(text), CTX)
    assert (detection.span.start, detection.span.end) == only(text, written)[0]
    assert (detection.needs_review, detection.review_reason) == (True, ID_LABEL_REASON)
    assert [kind for _, _, kind in detectors.detect_all(text)] == ["PHONE"]


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
