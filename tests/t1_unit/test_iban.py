"""Test matrix for ploni/detect/deterministic/iban.py: the IBAN and bank account detector of issue #34.

Why: build-plan.md Phase 1, "IBAN": "`IL` plus 2 check digits plus 19 characters, 23 total,
mod-97. Plus domestic bank/branch/account triples." Gate: "Checksum-backed types >= 0.98 recall
and >= 0.98 precision on fixtures"; the triples have no check digit and report their numbers
(issue #34: "The domestic triples are pattern-only and report their numbers"). The spans and the
types are the held-out batch's span rules: IBAN, "From the two country letters to the last
character of the account, the spaces inside it included. Not a label."; BANK_ACCOUNT, "From the
first digit of the bank's number to the last digit of the account: the separators between the
three numbers are in, and so are words that name the branch and the account when they stand
between them. Not a label or a word before the first number."

Test matrix:

iban_ok (the check alone, the separators taken out):
  K1  each invented IBAN; its country in small letters           True
  K2  another last digit; two digits swapped; the empty string; four characters; a non-ASCII
      digit; a Hebrew letter; check digits one less, so the remainder is 0 (added after the
      code, for a mutant of Cosmic Ray that survived: `== 1` made `<= 1`)    False
  K3  a valid German IBAN (the check alone does not read the country)    True
  K4  the shortest: four characters that leave 1, False; five that leave 1, True; a letter Z,
      read as 35 (added after the code, for the mutants that survived on the length guard,
      `< 5` made `== 5`, `<= 5`, `< 6`, `< 4`, and on the base, 36 made 35)

bank_label_before (the labels of the grouped triple):
  L1  each label: חשבון, ח-ן, ח־ן, ח"ן, ח״ן, ח''ן, בנק, סניף, מס' חשבון, מס׳ חשבון, חשבון בנק    True
  L2  a proclitic glued to it: בחשבון, לחשבון, ובבנק              True
  L5  the account word with a possessive suffix: חשבונו, חשבונה, חשבונם, חשבוני, חשבוננו, and
      with a proclitic, בחשבונו, לחשבונה (the review of #34 at 28b6032, finding 3: found 0.000
      before)                                                    True; the plural חשבונות    False
  L3  the label's letters inside a longer word: חשבונית; no label    False
  L4  another number's label beside it: טלפון, ת.ז., ח.פ., דרכון with חשבון; a digit between
      the label and the number                                   False

is_bank_account (the decision on a match of TRIPLE):
  D1  words between the numbers, no label                        True
  D2  grouped by separators under a bank label: bank 2, branch 3, account 4 to 13    True
  D3  grouped with no bank label                                 False
  D4  grouped under a bank label: a bank of 1 or 3 digits, a branch of 1 or 2    False
  D5  grouped under a bank label in a landline's shape, 0X-XXX-XXXX    False

The detector (`Iban`), IBAN:
  EI1 each written form: 23 characters with no separator; the paper format, groups of four
      with spaces; no-break spaces; hyphens; a space after IL only; il in small letters; two
      and three spaces between groups; an RLM after IL; an LRM in each gap (the review of #34
      at 28b6032, finding 5: the plan's "Widen the regex. Never weaken the checksum"; found
      0.000 before)
                                                                 one IBAN, its span from I to
                                                                 the last digit
  EI2 each context: after "IBAN:", after חשבון, a proclitic glued before IL, in brackets, at
      the end of a sentence with a full stop; a plain space and a date after the paper format;
      a plain space and a number after the electronic format (finding 5)    found, the label
                                                                 and marks out
  EI3 the fields: part, surface, type IBAN, detector "iban", base_span None, band "high",
      confidence CONFIDENCE, needs_review False, detection_id ""
  NI1 a near miss (another last digit); IL with 20 and 22 digits; a valid German IBAN
                                                                 nothing
  NI2 edges: a Latin letter or a digit before IL; a digit, or a separator but the plain space
      and a digit (a hyphen, a dot, a no-break space), after; four spaces between two groups
                                                                 nothing
The detector, BANK_ACCOUNT:
  EA1 words between: בנק B סניף R חשבון A, with commas, colons, מס' and מספר, a proclitic on
      סניף and on חשבון, ח-ן and ח"ן for the account, the bank's name and its number in
      brackets, no word before; the account word with a possessive suffix (בחשבונו); the bank's
      name in brackets after its number (finding 3)              one BANK_ACCOUNT, from the
                                                                 bank's first digit to the
                                                                 account's last, words in
  EA2 grouped under a bank label: hyphens, slashes, dots, spaces, the maqaf, a hyphen with a
      space each side                                            one, the label out
  EA3 an account with a separator inside, 123456/78               found, the separator and the
                                                                 two digits in
  EA4 the account's length: 4 and 13 digits                       found; 3 and 14    nothing
  EA5 the fields: type BANK_ACCOUNT, band "medium", CONFIDENCE_PATTERN, needs_review True with
      its review_reason, base_span None, detection_id ""
  NA1 grouped with no label; under a phone's label; under ת.ז.; after חשבונית    nothing
  NA2 grouped under a bank label: a landline 0X-XXX-XXXX; a mobile 05X-XXX-XXXX; a date
      DD.MM.YYYY and D.M.YYYY; an amount with commas; a branch of two digits    nothing
  NA3 inside a longer number: a digit and a hyphen before the bank's number    nothing
  NA6 an amount: the account followed by a decimal part (a dot or a comma and digits), or by
      ש"ח, ש״ח, ₪ or NIS, grouped under a bank label and with words between (the review of #34
      at 28b6032, finding 7: "יתרה בחשבון 12 345 678.50 ש"ח" gave BANK_ACCOUNT)    nothing
  EA7 a list: two grouped triples after one label, a comma and no space between; an account
      followed by a comma and three digits or more (no decimal part: a decimal part is one or
      two digits that end there; pass 2 of the review, at 0f6f0e7, item 8: "ח-ן
      12-345-123456,12-345-654321" gave nothing)                each account found
      A list of three (added after the code, for two mutants of Cosmic Ray)    each found
      A list joined by ו-, וכן, a semicolon or a slash (pass 3 of the review, at a65350e,
      finding 11: the later account was found 0.000)             each found
  NA4 words between, a bank of four digits; a branch of four digits    no triple (added after the
      code, for the mutants that survived on BANK_LONGEST and BRANCH_LONGEST, 3 made 4); since
      issue #315 the branch and the account, or the account alone, after their words, are found
  EA6 the bank named by its name and no number, then the branch and the account with their
      words: בנק לאומי, סניף R, חשבון A; with a proclitic on בנק and on the words; a name of
      one, two and three words, with gershayim (בע"מ)    one BANK_ACCOUNT, from the branch's
      first digit to the account's last (the batch's rule starts at the bank's number; with
      none, at the first number) (finding 3)
  NA5 by name: no account word before the account; no account    nothing (a name of four
      words, and no bank word, are found since issue #315: EA9)

is_lone_account (the decision on a match of ALONE, issue #315):
  AD1 a branch before the account word: under no label, with a number after    True
  AD2 the account alone: labelled, nothing after, one group or two    True
  AD3 the account alone, not labelled                            False
  AD4 the account alone, another number after it                 False
  AD5 the account alone in three groups (a triple's shape, TRIPLE's to judge)    False
  AD6 the account alone in a landline's shape, 0X-XXXXXXX         False

The detector, BANK_ACCOUNT with no bank's number (issue #315, Achia, 2026-11-27, "Yes, with the
word (Recommended)": found when חשבון or ח-ן stands right before it, with or without a branch,
needs_review True):
  EA8 an account alone right after each spelling of the account word: חשבון, its possessives,
      ח-ן with a hyphen, a maqaf or an en dash, ח"ן with ", ״ or ''; with a proclitic, a colon,
      מס' or מספר, in brackets; an account of four and of thirteen digits, in two groups (a
      hyphen, a slash), an ID's nine digits after חשבון          one BANK_ACCOUNT, the account
                                                                 only, the word out
  EA9 a branch and an account: סניף B חשבון A, with commas, colons, מס', proclitics, ח-ן and
      ח"ן, a branch of one digit; after a bank's name of four words; with no bank word
                                                                 one, from the branch's first
                                                                 digit to the account's last
  EA10 the fields: type BANK_ACCOUNT, band "medium", CONFIDENCE_PATTERN, needs_review True with
      its review_reason
  NA7 the account word not right before: a word between (חשבון בנק, חשבון הבנק, חשבון מיום);
      the plural חשבונות; חשבונית; an account of three digits and of fourteen; an amount (ש"ח
      with either gershayim, ₪, NIS, שקלים, a decimal part with a dot or a comma, thousands
      with commas, "הופקדו לחשבון"); another number after it by a plain space; a landline
      0X-XXXXXXX; a mobile and a date in three groups; a case number NNNNN-MM-YY; a grouped
      triple with a bank of one digit; another number's label beside the word (ת.ז., טלפון)
                                                                 nothing
  EA11 an account found once: a triple after חשבון, a triple with words, a branch after a
      bank's name: one detection each                             (EA1, EA2, EA6, kept)
Both:
  EB1 an IBAN and a triple in one text                           both, in the order of the text
  B1  the empty text; a text with no digit                       nothing

The fixture (tests/fixtures/detect/iban.json; its numbers are filled in when the tests run, by
tests/invented_numbers.py, from BANK_NUMBERS and ISRAELI_IDS; a positive's "found" lists, for
each item, the first and the last slot it covers, and "types" the type of each, "iban" or
"bank"):
  F1  at least 40 positive and 40 negative texts
  F2  per type, recall and precision counted by exact span and type; IBAN at or above 0.98
      (build-plan.md Phase 1, Gate, checksum-backed); BANK_ACCOUNT printed, not gated
      (pattern-only, issue #34); the counts and every miss printed, a miss by its case's place
  F3  no file under tests/fixtures/detect/ holds, outside its slots, an IBAN that passes the
      check (widened from this fixture to every one by the review of #34 at 28b6032, finding 1:
      the ID and the company number fixtures held a published example IBAN, now a slot)
      The scan is the detector's IBAN_CANDIDATE, so it reads every gap the detector reads, and
      the check is the remainder computed apart (pass 2 of the review, at 0f6f0e7, item 9: an
      IBAN with en dashes passed the old scan); a test holds the scan to each gap.
  F4  the known misses: bank accounts the detector does not find on purpose, each naming the
      limit of the module's Known limits it falls under, neither a positive nor a negative; each
      is printed with what the detector gives on it (the review of #34 at 28b6032, finding 2).
      Since issue #315 two of #34's three, the account alone after חשבון and the account after
      חשבון with the bank named after the branch, are counted positives; the triple with a bank
      of one digit stays, and two misses of #315 join it: a word between חשבון and the account
      (חשבון בנק), and the second account of a list after one word

Hebrew axes: gershayim as ", ״ and two ASCII apostrophes (ח"ן); geresh as ' and ׳ (מס'); a
proclitic glued to a label and to the words between the numbers; the maqaf as a separator;
Latin IL inside Hebrew text, with a Hebrew proclitic glued to it. Names that are ordinary words
and niqqud do not apply: the detector reads digits and a few fixed words (niqqud on those words
is a Known limit of the module).
"""

import json
import re
from pathlib import Path

import pytest

from ploni.detect.base import DetectContext
from ploni.detect.deterministic import iban, israeli_id
from ploni.detect.deterministic.iban import TRIPLE, Iban, bank_label_before, iban_ok, is_bank_account
from ploni.types import Span
from tests.detector_contract import projection
from tests.invented_numbers import BANK_NUMBERS, ISRAELI_IDS, combined, fill, with_check
from tests.invented_numbers import iban_remainder as remainder

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "detect" / "iban.json"
# Invented numbers, made when the tests run (tests/invented_numbers.py).
IBAN = BANK_NUMBERS.iban[0]
PAPER = " ".join(IBAN[i : i + 4] for i in range(0, 23, 4))
ACCOUNT = BANK_NUMBERS.account[0]
BANK, BRANCH, NUMBER = ACCOUNT[:2], ACCOUNT[2:5], ACCOUNT[5:11]
GROUPED = f"{BANK}-{BRANCH}-{NUMBER}"
NUMBERS = combined(BANK_NUMBERS, ISRAELI_IDS)
CTX = DetectContext()
TYPE = {"iban": "IBAN", "bank": "BANK_ACCOUNT"}


def found(text: str) -> list[tuple[int, int, str]]:
    """Return the places and types the detector finds in a text."""
    return [(each.span.start, each.span.end, each.entity_type) for each in Iban().detect(projection(text), CTX)]


def only(text: str, item: str, kind: str) -> list[tuple[int, int, str]]:
    """Return the place of the one item in a text, with its type."""
    start = text.index(item)
    return [(start, start + len(item), kind)]


def test_k1_valid_ibans() -> None:
    assert all(iban_ok(each) for each in BANK_NUMBERS.iban)
    assert iban_ok("il" + IBAN[2:])


SWAPPED = next(IBAN[:i] + IBAN[i + 1] + IBAN[i] + IBAN[i + 2 :] for i in range(4, 22) if IBAN[i] != IBAN[i + 1])
FAILING = {
    "another last digit": BANK_NUMBERS.iban_near[0],
    "two digits swapped": SWAPPED,
    "empty": "",
    "four characters": IBAN[:4],
    "arabic-indic digit": IBAN[:-1] + "٣",
    "hebrew letter": IBAN[:-1] + "א",
    "remainder zero": f"{IBAN[:2]}{int(IBAN[2:4]) - 1:02d}{IBAN[4:]}",
}


@pytest.mark.parametrize("which", FAILING)
def test_k2_these_fail(which: str) -> None:
    assert not iban_ok(FAILING[which])


def test_k3_the_check_alone_does_not_read_the_country() -> None:
    assert all(iban_ok(each) for each in BANK_NUMBERS.iban_foreign)


def test_k2_the_remainder_zero_case_is_what_it_says() -> None:
    assert remainder(FAILING["remainder zero"]) == 0


def test_k4_the_shortest_and_a_letter_z() -> None:
    four = next(f"IL{cd:02d}" for cd in range(100) if remainder(f"IL{cd:02d}") == 1)
    assert not iban_ok(four)
    five = next(f"IL{cd:02d}{last}" for cd in range(100) for last in "0123456789" if remainder(f"IL{cd:02d}{last}") == 1)
    assert iban_ok(five)
    with_z = with_check("XK", "Z" + ACCOUNT)
    assert remainder(with_z) == 1 and iban_ok(with_z)


LABELS = ["חשבון ", "ח-ן ", "ח־ן ", 'ח"ן ', "ח״ן ", "ח''ן ", "בנק ", "סניף ", "מס' חשבון ", "מס׳ חשבון ", "חשבון בנק: "]
POSSESSIVES = ["חשבונו ", "חשבונה ", "חשבונם ", "חשבוני ", "חשבוננו ", "בחשבונו ", "לחשבונה "]


@pytest.mark.parametrize("before", LABELS)
def test_l1_bank_labels(before: str) -> None:
    assert bank_label_before(before + GROUPED, len(before))


@pytest.mark.parametrize("before", ["בחשבון ", "לחשבון ", "ובבנק "])
def test_l2_a_proclitic_on_the_label(before: str) -> None:
    assert bank_label_before(before + GROUPED, len(before))


@pytest.mark.parametrize("before", POSSESSIVES)
def test_l5_a_possessive_account_word(before: str) -> None:
    assert bank_label_before(before + GROUPED, len(before))


def test_l5_the_plural_is_no_label() -> None:
    assert not bank_label_before("חשבונות " + GROUPED, len("חשבונות "))


@pytest.mark.parametrize("before", ["חשבונית ", "", "המספר "])
def test_l3_no_label(before: str) -> None:
    assert not bank_label_before(before + GROUPED, len(before))


@pytest.mark.parametrize("before", ["חשבון טלפון ", "ת.ז. בעל החשבון ", "ח.פ. חשבון ", "חשבון דרכון ", "חשבון 3 "])
def test_l4_another_label_or_a_digit_between(before: str) -> None:
    assert not bank_label_before(before + GROUPED, len(before))


def decide(raw: str, labelled: bool) -> bool:
    """Return the decision on the one match of TRIPLE that covers the whole of `raw`."""
    match = TRIPLE.fullmatch(raw)
    assert match is not None
    return is_bank_account(match, labelled)


DECISIONS = {
    "d1 words, no label": (f"{BANK} סניף {BRANCH} חשבון {NUMBER}", False, True),
    "d1 the branch word only": (f"{BANK} סניף {BRANCH}-{NUMBER}", False, True),
    "d2 grouped, labelled": (GROUPED, True, True),
    "d2 grouped, the shortest account": (f"{BANK}-{BRANCH}-{NUMBER[:4]}", True, True),
    "d2 grouped, the longest account": (f"{BANK}-{BRANCH}-{ACCOUNT[5:]}{ACCOUNT[:4]}", True, True),
    "d3 grouped, no label": (GROUPED, False, False),
    "d4 a bank of one digit": (f"{BANK[0]}-{BRANCH}-{NUMBER}", True, False),
    "d4 a bank of three digits": (f"{BANK}{BRANCH[0]}-{BRANCH}-{NUMBER}", True, False),
    "d4 a branch of one digit": (f"{BANK}-{BRANCH[0]}-{NUMBER}", True, False),
    "d4 a branch of two digits": (f"{BANK}-{BRANCH[:2]}-{NUMBER}", True, False),
    "d5 a landline's shape": (f"03-{BRANCH}-{NUMBER[:4]}", True, False),
}


@pytest.mark.parametrize("case", DECISIONS)
def test_d_the_decision(case: str) -> None:
    raw, labelled, expected = DECISIONS[case]
    assert decide(raw, labelled) is expected


IBAN_FORMS = {
    "electronic": IBAN,
    "paper": PAPER,
    "no-break spaces": PAPER.replace(" ", " "),
    "hyphens": PAPER.replace(" ", "-"),
    "a space after IL": f"{IBAN[:2]} {IBAN[2:]}",
    "small letters": "il" + IBAN[2:],
    "two spaces between groups": PAPER.replace(" ", "  "),
    "three spaces between groups": PAPER.replace(" ", "   "),
    "an RLM after IL": IBAN[:2] + "\u200f" + PAPER[2:],
    "an LRM in each gap": PAPER.replace(" ", "\u200e "),
}


@pytest.mark.parametrize("form", IBAN_FORMS)
def test_ei1_each_written_form(form: str) -> None:
    text = f"נא להעביר לחשבון {IBAN_FORMS[form]} עד מחר."
    assert found(text) == only(text, IBAN_FORMS[form], "IBAN")


IBAN_CONTEXTS = {
    "after IBAN:": f"IBAN: {PAPER}",
    "after חשבון": f"מספר חשבון {IBAN}",
    "a proclitic glued": f"הכסף הועבר ב{IBAN} אתמול",
    "in brackets": f"החשבון ({PAPER}) נסגר",
    "a full stop after": f"החשבון הוא {PAPER}.",
    "a space and a date after": f"החשבון {PAPER} 12.3.2020 נפתח",
    "a space and a number after": f"IBAN {IBAN} 2 עותקים",
}


@pytest.mark.parametrize("context", IBAN_CONTEXTS)
def test_ei2_each_context(context: str) -> None:
    text = IBAN_CONTEXTS[context]
    item = PAPER if PAPER in text else IBAN
    assert found(text) == only(text, item, "IBAN")


def test_ei3_the_fields_of_an_iban() -> None:
    proj = projection(f"שָׁלוֹם, IBAN {IBAN}.", part="header1")
    [detection] = Iban().detect(proj, CTX)
    start = proj.text.index(IBAN)
    assert detection.span == Span(start, start + 23)
    assert (detection.part, detection.surface, detection.entity_type, detection.detector) == ("header1", IBAN, "IBAN", "iban")
    assert (detection.confidence, detection.band, detection.base_span) == (iban.CONFIDENCE, "high", None)
    assert (detection.detection_id, detection.needs_review, detection.review_reason) == ("", False, None)


NOT_IBANS = {
    "near miss": BANK_NUMBERS.iban_near[0],
    "twenty digits": BANK_NUMBERS.iban_lengths[0],
    "twenty-two digits": BANK_NUMBERS.iban_lengths[1],
    "german": BANK_NUMBERS.iban_foreign[0],
    "a latin letter before": "X" + IBAN,
    "a digit before": "7" + IBAN,
    "a digit after": IBAN + "4",
    "a hyphen and a digit after": IBAN + "-4",
    "a dot and a digit after": IBAN + ".4",
    "a no-break space and a digit after": IBAN + "\u00a04",
    "four spaces between two groups": PAPER.replace(" ", "    ", 1),
}


@pytest.mark.parametrize("case", NOT_IBANS)
def test_ni_not_an_iban(case: str) -> None:
    assert found(f"חשבון {NOT_IBANS[case]} ") == []


WORDED = {
    "plain": f"בנק {BANK} סניף {BRANCH} חשבון {NUMBER}",
    "commas and colons": f"בנק: {BANK}, סניף: {BRANCH}, חשבון: {NUMBER}",
    "מס' and מספר": f"בנק {BANK} סניף מס' {BRANCH} מספר חשבון {NUMBER}",
    "proclitics": f"בבנק {BANK} בסניף {BRANCH} ובחשבון {NUMBER}",
    "ח-ן": f"בנק {BANK} סניף {BRANCH} ח-ן {NUMBER}",
    'ח"ן': f'בנק {BANK} סניף {BRANCH} ח"ן {NUMBER}',
    "ח״ן": f"בנק {BANK} סניף {BRANCH} ח״ן {NUMBER}",
    "the bank's name and number in brackets": f"בנק לאומי ({BANK}), סניף {BRANCH}, חשבון {NUMBER}",
    "no word before": f"{BANK} סניף {BRANCH} חשבון {NUMBER}",
    "a possessive account word": f"בנק {BANK} סניף {BRANCH} בחשבונו {NUMBER}",
    "the bank's name in brackets after its number": f"בנק {BANK} (לאומי) סניף {BRANCH} חשבון {NUMBER}",
}


@pytest.mark.parametrize("form", WORDED)
def test_ea1_words_between(form: str) -> None:
    text = f"{WORDED[form]} לטובת התובע."
    start = text.index(BANK)
    end = text.index(NUMBER) + len(NUMBER)
    assert found(text) == [(start, end, "BANK_ACCOUNT")]


GROUPINGS = {
    "hyphens": GROUPED,
    "slashes": f"{BANK}/{BRANCH}/{NUMBER}",
    "dots": f"{BANK}.{BRANCH}.{NUMBER}",
    "spaces": f"{BANK} {BRANCH} {NUMBER}",
    "maqaf": f"{BANK}־{BRANCH}־{NUMBER}",
    "a hyphen with spaces": f"{BANK} - {BRANCH} - {NUMBER}",
}


@pytest.mark.parametrize("form", GROUPINGS)
def test_ea2_grouped_under_a_label(form: str) -> None:
    text = f"פרטי חשבון הבנק: {GROUPINGS[form]}."
    assert found(text) == only(text, GROUPINGS[form], "BANK_ACCOUNT")


def test_ea3_an_account_with_a_separator_inside() -> None:
    item = f"{BANK} סניף {BRANCH} חשבון {NUMBER}/{ACCOUNT[11:13]}"
    text = f"בנק {item}, כפי שנמסר."
    assert found(text) == only(text, item, "BANK_ACCOUNT")


@pytest.mark.parametrize(("length", "is_found"), [(4, True), (13, True), (3, False), (14, False)], ids=["four", "thirteen", "three", "fourteen"])
def test_ea4_the_accounts_length(length: int, is_found: bool) -> None:
    account = (ACCOUNT[5:] + ACCOUNT)[:length]
    item = f"{BANK} סניף {BRANCH} חשבון {account}"
    text = f"בנק {item} "
    assert found(text) == (only(text, item, "BANK_ACCOUNT") if is_found else [])


def test_ea5_the_fields_of_an_account() -> None:
    proj = projection(f"חשבון: {GROUPED}", part="footnotes")
    [detection] = Iban().detect(proj, CTX)
    assert (detection.span, detection.surface, detection.entity_type, detection.part) == (Span(7, 7 + len(GROUPED)), GROUPED, "BANK_ACCOUNT", "footnotes")
    assert (detection.confidence, detection.band, detection.base_span, detection.detection_id) == (iban.CONFIDENCE_PATTERN, "medium", None, "")
    assert detection.needs_review is True and detection.review_reason == iban.REVIEW_REASON


NOT_ACCOUNTS = {
    "grouped, no label": f"המספר {GROUPED} נמסר",
    "under a phone's label": f"טלפון {GROUPED}",
    "under an id label": f"ת.ז. {GROUPED}",
    "after חשבונית": f"חשבונית {GROUPED}",
    "a landline": "חשבון 03-123-4567",
    "a mobile": "חשבון 052-123-4567",
    "a date": "חשבון מיום 12.03.2020",
    "a short date": "חשבון מיום 1.1.2020",
    "an amount with commas": "בחשבון יתרה של 12,345,678 ש\"ח",
    "a branch of two digits": f"חשבון {BANK}-{BRANCH[:2]}-{NUMBER}",
    "inside a longer number": f"חשבון 7-{GROUPED}",
    "na6 a decimal part with a dot": 'יתרה בחשבון 12 345 678.50 ש"ח',
    "na6 a decimal part with a comma": "יתרה בחשבון 12 345 6789,50",
    "na6 shekels after": 'יתרה בחשבון 12 345 6789 ש"ח',
    "na6 shekels after, the Hebrew gershayim": "יתרה בחשבון 12 345 6789 ש״ח",
    "na6 the shekel sign after": "בחשבון 12-345-6789 ₪",
    "na6 NIS after": "balance בחשבון 12 345 67890 NIS",
    "na6 words between, the shekel sign after": f"בנק {BANK} סניף {BRANCH} חשבון {NUMBER} ₪",
    "na6 a decimal part of one digit, then a word": f"יתרה בחשבון {BANK} {BRANCH} {NUMBER[:4]},5 נוספים",
}


@pytest.mark.parametrize("case", NOT_ACCOUNTS)
def test_na_not_an_account(case: str) -> None:
    assert found(NOT_ACCOUNTS[case]) == []


BY_NAME = {
    "one word": f"בנק לאומי, סניף {BRANCH}, חשבון {NUMBER}",
    "two words, proclitics": f"בבנק הפועלים בסניף {BRANCH} בחשבון מס' {NUMBER}",
    "three words, ח-ן": f"בנק מזרחי טפחות בע\"מ סניף {BRANCH} ח-ן {NUMBER}",
    "colons, a possessive": f"בנק דיסקונט, סניף: {BRANCH}, חשבונו: {NUMBER}",
}


@pytest.mark.parametrize("form", BY_NAME)
def test_ea6_the_bank_by_its_name(form: str) -> None:
    text = f"{BY_NAME[form]}, כמוסכם."
    start = text.index(BRANCH)
    end = text.index(NUMBER, start) + len(NUMBER)
    assert found(text) == [(start, end, "BANK_ACCOUNT")]
    [detection] = Iban().detect(projection(text), CTX)
    assert detection.needs_review is True and detection.band == "medium"


NOT_BY_NAME = {
    "no account word": f"בנק לאומי סניף {BRANCH} {NUMBER}",
    "no account": f"בנק לאומי סניף {BRANCH} ברחוב הרצל",
}


@pytest.mark.parametrize("case", NOT_BY_NAME)
def test_na5_not_by_name(case: str) -> None:
    assert found(NOT_BY_NAME[case]) == []


@pytest.mark.parametrize("which", ["bank", "branch"])
def test_na4_four_digits_with_words_between(which: str) -> None:
    bank, branch = (ACCOUNT[:4], BRANCH) if which == "bank" else (BANK, ACCOUNT[:4])
    text = f"בנק {bank} סניף {branch} חשבון {NUMBER}"
    # Issue #315: with no triple, what follows סניף and חשבון is found by itself.
    start = text.index(f"סניף {BRANCH}") + len("סניף ") if which == "bank" else text.rindex(NUMBER)
    assert found(text) == [(start, text.rindex(NUMBER) + len(NUMBER), "BANK_ACCOUNT")]


def decide_alone(text: str, labelled: bool, beside: bool) -> bool:
    """Return the decision on the first match of ALONE in `text`."""
    match = iban.ALONE.search(text)
    assert match is not None
    return iban.is_lone_account(match, labelled, beside)


LANDLINE = ISRAELI_IDS.landline[0]
ALONE_DECISIONS = {
    "ad1 a branch, no label, a number after": (f"סניף {BRANCH} חשבון {NUMBER}", False, True, True),
    "ad2 alone, one group": (f"חשבון {NUMBER}", True, False, True),
    "ad2 alone, two groups": (f"חשבון {BRANCH}-{NUMBER}", True, False, True),
    "ad3 alone, not labelled": (f"חשבון {NUMBER}", False, False, False),
    "ad4 alone, a number after": (f"חשבון {NUMBER}", True, True, False),
    "ad5 alone, three groups": (f"חשבון {BRANCH}-{NUMBER[:3]}-{NUMBER[3:]}", True, False, False),
    "ad6 alone, a landline's shape": (f"חשבון {LANDLINE[:2]}-{LANDLINE[2:]}", True, False, False),
}


@pytest.mark.parametrize("case", ALONE_DECISIONS)
def test_ad_the_decision_on_an_account_alone(case: str) -> None:
    text, labelled, beside, expected = ALONE_DECISIONS[case]
    assert decide_alone(text, labelled, beside) is expected


ACCOUNT_WORDS = {
    "חשבון": "חשבון ",
    "a colon": "חשבון: ",
    "מס'": "חשבון מס' ",
    "מס׳": "חשבון מס׳ ",
    "מספר before": "מספר חשבון ",
    "מס' before, a colon": "מס' חשבון: ",
    "a proclitic ב": "בחשבון ",
    "a proclitic ל": "לחשבון ",
    "a proclitic ה": "בעל החשבון ",
    "a possessive": "חשבונו ",
    "a possessive and proclitics": "ובחשבונה ",
    "ח-ן": "ח-ן ",
    "ח־ן, a maqaf": "ח־ן ",
    "ח–ן, an en dash": "ח–ן ",
    'ח"ן': 'ח"ן ',
    "ח״ן": "ח״ן ",
    "ח''ן": "ח''ן ",
    "in brackets": "(חשבון ",
}


@pytest.mark.parametrize("word", ACCOUNT_WORDS)
def test_ea8_an_account_alone_after_each_word(word: str) -> None:
    text = f"הכסף הועבר {ACCOUNT_WORDS[word]}{NUMBER} אתמול."
    assert found(text) == only(text, NUMBER, "BANK_ACCOUNT")


ALONE_FORMS = {
    "four digits": NUMBER[:4],
    "thirteen digits": ACCOUNT[1:],
    "two groups, a hyphen": f"{BRANCH}-{NUMBER}",
    "two groups, a slash": f"{NUMBER}/{ACCOUNT[11:13]}",
    "an id's nine digits": ISRAELI_IDS.valid[0],
}


@pytest.mark.parametrize("form", ALONE_FORMS)
def test_ea8_each_form_of_an_account_alone(form: str) -> None:
    text = f"נא להעביר לחשבון {ALONE_FORMS[form]}, כמוסכם."
    assert found(text) == only(text, ALONE_FORMS[form], "BANK_ACCOUNT")


BRANCHED = {
    "plain": f"סניף {BRANCH} חשבון {NUMBER}",
    "commas and colons": f"סניף: {BRANCH}, חשבון: {NUMBER}",
    "מס' and proclitics": f"בסניף מס' {BRANCH} בחשבון מס' {NUMBER}",
    "ח-ן": f"סניף {BRANCH} ח-ן {NUMBER}",
    'ח"ן': f'סניף {BRANCH}, ח"ן {NUMBER}',
    "a branch of one digit": f"סניף {BRANCH[0]} חשבון {NUMBER}",
    "after a bank's name of four words": f"בנק אחד שתיים שלוש ארבע סניף {BRANCH} חשבון {NUMBER}",
    "after another bank word": f"בבנק סניף {BRANCH} חשבונו {NUMBER}",
}


@pytest.mark.parametrize("form", BRANCHED)
def test_ea9_a_branch_and_an_account(form: str) -> None:
    text = f"{BRANCHED[form]} לטובת התובע."
    start = text.index(BRANCH[0] if form == "a branch of one digit" else BRANCH)
    end = text.index(NUMBER, start) + len(NUMBER)
    assert found(text) == [(start, end, "BANK_ACCOUNT")]


def test_ea10_the_fields_of_an_account_alone() -> None:
    proj = projection(f"ח-ן {NUMBER}", part="footnotes")
    [detection] = Iban().detect(proj, CTX)
    assert (detection.span, detection.surface, detection.entity_type, detection.part) == (Span(4, 4 + len(NUMBER)), NUMBER, "BANK_ACCOUNT", "footnotes")
    assert (detection.confidence, detection.band, detection.base_span, detection.detection_id) == (iban.CONFIDENCE_PATTERN, "medium", None, "")
    assert detection.needs_review is True and detection.review_reason == iban.REVIEW_REASON


CASE = ISRAELI_IDS.case
NOT_ALONE = {
    "a word between, בנק": f"חשבון בנק {NUMBER}",
    "a word between, הבנק": f"חשבון הבנק {NUMBER}",
    "a word between, מיום": f"חשבון מיום {NUMBER}",
    "the plural": f"חשבונות {NUMBER}",
    "an invoice": f"חשבונית {NUMBER}",
    "three digits": f"חשבון {NUMBER[:3]} ",
    "fourteen digits": f"חשבון {ACCOUNT}",
    "shekels": f'הופקדו לחשבון {NUMBER} ש"ח',
    "shekels, the Hebrew gershayim": f"הופקדו לחשבון {NUMBER} ש״ח",
    "the shekel sign": f"לחשבון {NUMBER} ₪",
    "NIS": f"לחשבון {NUMBER} NIS",
    "שקלים": f"לחשבון {NUMBER} שקלים",
    "a decimal part with a dot": f"יתרה בחשבון {NUMBER}.50",
    "a decimal part with a comma": f"יתרה בחשבון {NUMBER},50",
    "thousands with commas": 'הופקדו לחשבון 12,345 ש"ח',
    "thousands with commas, no currency": "הופקדו לחשבון 1,234,567",
    "a number after by a plain space": f"חשבון {NUMBER} 3 עותקים",
    "an amount grouped by spaces": f"יתרה בחשבון {NUMBER[:4]} {NUMBER[4:]}",
    "a landline": f"חשבון {LANDLINE[:2]}-{LANDLINE[2:]}",
    "a mobile in three groups": "חשבון 052-123-4567",
    "a date in three groups": "חשבון 12/03/2020",
    "a case number": f"חשבון {CASE[:5]}-{CASE[5:7]}-{CASE[7:]}",
    "a triple with a bank of one digit": f"חשבון {BANK[0]}-{BRANCH}-{NUMBER}",
    "an id label beside": f"ת.ז. בעל החשבון {NUMBER}",
    "a phone label beside": f"טלפון החשבון {NUMBER}",
}


@pytest.mark.parametrize("case", NOT_ALONE)
def test_na7_not_an_account_alone(case: str) -> None:
    assert found(NOT_ALONE[case]) == []


SECOND = BANK_NUMBERS.account[1]
SECOND_GROUPED = f"{SECOND[:2]}-{SECOND[2:5]}-{SECOND[5:11]}"


def test_ea7_a_list_after_one_label() -> None:
    text = f"ח-ן {GROUPED},{SECOND_GROUPED}"
    first, second = text.index(GROUPED), text.rindex(SECOND_GROUPED)
    assert found(text) == [(first, first + len(GROUPED), "BANK_ACCOUNT"), (second, second + len(SECOND_GROUPED), "BANK_ACCOUNT")]


def test_ea7_a_list_of_three() -> None:
    # Added after the code, for two mutants of Cosmic Ray that survived: the last accepted triple,
    # places[-1], made the first, places[0] (by `not 1` and by `- 0`).
    third = BANK_NUMBERS.account[2]
    items = [GROUPED, SECOND_GROUPED, f"{third[:2]}-{third[2:5]}-{third[5:11]}"]
    text = "ח-ן " + ",".join(items)
    starts = [text.index(item) for item in items]
    assert found(text) == [(start, start + len(item), "BANK_ACCOUNT") for start, item in zip(starts, items, strict=True)]


LISTS = {
    "a, b ו-c": "ח-ן {0}, {1} ו-{2}",
    "a ו-b": "ח-ן {0} ו-{1}",
    "a וכן b": "ח-ן {0} וכן {1}",
    "a; b": "ח-ן {0}; {1}",
    "a / b": "ח-ן {0} / {1}",
}


@pytest.mark.parametrize("form", LISTS)
def test_ea7_a_list_joined_by_a_word_or_a_mark(form: str) -> None:
    # Pass 3 of the review of #34, at a65350e, finding 11: the account after ו-, וכן, ; or / was
    # found 0.000 of the time.
    third = BANK_NUMBERS.account[2]
    items = [GROUPED, SECOND_GROUPED, f"{third[:2]}-{third[2:5]}-{third[5:11]}"]
    text = LISTS[form].format(*items)
    written = [item for item in items if item in text]
    assert found(text) == [(text.index(item), text.index(item) + len(item), "BANK_ACCOUNT") for item in written]


def test_ea7_a_comma_and_three_digits_after() -> None:
    text = f"חשבון {GROUPED},{SECOND[5:8]} ו-{SECOND[8:11]}"
    assert found(text) == only(text, GROUPED, "BANK_ACCOUNT")


def test_eb1_an_iban_and_an_account_in_one_text() -> None:
    text = f"חשבון {GROUPED}, ובחו\"ל {PAPER}."
    first, second = text.index(GROUPED), text.index(PAPER)
    assert found(text) == [(first, first + len(GROUPED), "BANK_ACCOUNT"), (second, second + len(PAPER), "IBAN")]
    reverse = f"{PAPER} או בנק {BANK} סניף {BRANCH} חשבון {NUMBER}"
    assert [kind for _, _, kind in found(reverse)] == ["IBAN", "BANK_ACCOUNT"]


@pytest.mark.parametrize("text", ["", "אין כאן מספר כלל."], ids=["empty", "no digit"])
def test_b1_nothing_to_find(text: str) -> None:
    assert found(text) == []


def cases() -> tuple[list[tuple[str, set[tuple[int, int, str]]]], int, int]:
    """Read the fixture, its numbers filled in: each text with its expected places and types, and the counts."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    read = []
    for case in data["positives"]:
        text, spans = fill(case["text"], NUMBERS)
        items = {(spans[first][0], spans[last][1], TYPE[kind]) for (first, last), kind in zip(case["found"], case["types"], strict=True)}
        read.append((text, items))
    read += [(fill(case["text"], NUMBERS)[0], set()) for case in data["negatives"]]
    return read, len(data["positives"]), len(data["negatives"])


def test_f1_the_fixture_has_enough_cases() -> None:
    read, n_pos, n_neg = cases()
    assert n_pos >= 40 and n_neg >= 40
    assert all(items for _, items in read[:n_pos]) and not any(items for _, items in read[n_pos:])
    kinds = [kind for _, items in read[:n_pos] for _, _, kind in items]
    assert kinds.count("IBAN") >= 20 and kinds.count("BANK_ACCOUNT") >= 20


def test_f4_the_known_misses_are_listed_and_not_counted(capsys: pytest.CaptureFixture[str]) -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    misses = data["known_misses"]
    counted = {case["text"] for case in data["positives"] + data["negatives"]}
    assert misses and all(case["limit"] and "Known limits" in case["limit"] for case in misses)
    assert not counted & {case["text"] for case in misses}
    with capsys.disabled():
        for place, case in enumerate(misses):
            print(f"\nknown miss {place}: {case['limit']}: found {[kind for _, _, kind in found(fill(case['text'], NUMBERS)[0])]}")


def score(read: list[tuple[str, set[tuple[int, int, str]]]], kind: str) -> tuple[float, float, list[str], list[str]]:
    """Return recall, precision, the misses and the wrong finds of one type over the cases, each by its case's place."""
    misses: list[str] = []
    wrong: list[str] = []
    tp = 0
    for case, (text, expected) in enumerate(read):
        want = {each for each in expected if each[2] == kind}
        got = {each for each in found(text) if each[2] == kind}
        tp += len(want & got)
        misses += [f"case {case} {span}" for span in sorted(want - got)]
        wrong += [f"case {case} {span}" for span in sorted(got - want)]
    recall = tp / (tp + len(misses)) if tp + len(misses) else 0.0
    precision = tp / (tp + len(wrong)) if tp + len(wrong) else 0.0
    return recall, precision, misses, wrong


def test_f2_recall_and_precision_on_the_fixture(capsys: pytest.CaptureFixture[str]) -> None:
    read, n_pos, n_neg = cases()
    results = {kind: score(read, kind) for kind in ("IBAN", "BANK_ACCOUNT")}
    with capsys.disabled():
        for kind, (recall, precision, misses, wrong) in results.items():
            print(f"\n{kind}: precision {precision:.3f}  recall {recall:.3f}  n_pos {n_pos}  n_neg {n_neg}")
            print("false negatives:", misses)
            print("false positives:", wrong)
    recall, precision, _, _ = results["IBAN"]
    # build-plan.md Phase 1, Gate: checksum-backed types at or above 0.98 recall and precision.
    assert recall >= 0.98 and precision >= 0.98


# What an IBAN may carry between its characters, as the detector reads it: the ID detector's
# separators and the two marks of direction.
SCAN_GAP = re.compile("[" + re.escape(israeli_id.SEPARATORS + "\u200e\u200f") + "]")


def literal_ibans(literal: str) -> list[str]:
    """Return the runs of a text the detector's IBAN candidate reads, each with its separators and marks taken out."""
    return [SCAN_GAP.sub("", match.group()) for match in iban.IBAN_CANDIDATE.finditer(literal)]


def test_f3_no_fixture_holds_a_valid_iban_as_a_literal() -> None:
    files = sorted(FIXTURE.parent.glob("*.json"))
    assert FIXTURE in files and len(files) >= 4
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for case in [case for value in data.values() if isinstance(value, list) for case in value]:
            literal = re.sub(r"\{[^}]*\}", "", case["text"])
            assert not any(remainder(chars) == 1 for chars in literal_ibans(literal)), path.name


def test_f3_the_scan_reads_every_iban_the_detector_finds() -> None:
    # Pass 2 of the review of #34, at 0f6f0e7, item 9: an IBAN with en dashes passed the scan.
    groups = [IBAN[i : i + 4] for i in range(0, 23, 4)]
    for gap in [*israeli_id.SEPARATORS, "\u200e", "\u200f", "  ", " \u200f"]:
        text = f"חשבון {gap.join(groups)} נפתח"
        assert found(text), repr(gap)
        assert IBAN in literal_ibans(text), repr(gap)
