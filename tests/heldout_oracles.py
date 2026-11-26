"""Oracles for the held-out batch's tests: whether a text is a valid item of a type, written here.

Why: a key whose positives are not items, or whose near misses are, would make every score of
every PR wrong, and nobody who writes the detectors may look. These checks are written from
build-plan.md Phase 1 and from the span rules, not read from the generator, so that a change of
a maker that turns a near miss into an item fails a test (review 1 of the branch, finding 4).
Every function returns a bool or a number and never text, so that a failing test that calls one
prints no identifier.

Contract: `valid(batch, item)` says whether the item's text, in its document, is a valid item of
its type; `digest(batch)` is a sha256 of the documents and of every span; `before(batch, item, n)`
is the text of up to n code points before an item.

Known limits: the oracles of the pattern-only types and of IL_PLATE read the words just before
the number, which are the plan's cues; the PERSON oracles judge a name by the name lists of the
generator, which are a lexicon and not a rule.
"""

import hashlib
import re

from eval.heldout.generator import CITIES, FAMILY, GIVEN, STREETS, Batch, Item

MARKS = str.maketrans({"״": '"', "׳": "'"})
CHECKSUM_TYPES = ("IL_ID", "COMPANY_NUMBER", "NONPROFIT_NUMBER", "IBAN", "CREDIT_CARD")
ID_SEPARATORS = "- ."
# build-plan.md Phase 1, Trigger words.
TRIGGERS = ("מר", "גב'", 'עו"ד', 'ד"ר', "פרופ'", 'רו"ח', "התובע", "הנתבע", "המבקש", "המשיב", "העד", "כב' השופט", 'ב"כ')
PARTY_TRIGGERS = ("התובע", "הנתבע", "המבקש", "המשיב", "העד")
NAMES = set(GIVEN) | set(FAMILY)
# build-plan.md Phase 1, Trigger words: names that are ordinary Hebrew words. Alone and with no
# title, such a word is no name by the plan's rule: "lexicon membership ... never creates a
# PERSON detection alone".
ORDINARY_WORD_NAMES = frozenset({"אור", "שחר", "רון", "ברק", "יונה", "שרון", "עדן", "טל", "גל", "שקד", "ים", "תום", "עומר", "נועם", "דקל", "חן", "שירה"})
# The group of the names that stand once with no title (build-plan.md section 7).
UNTITLED = "untitled"
# build-plan.md Phase 1, placeholders; real Hebrew abbreviations of the same shape as initials.
PLACEHOLDER_WORDS = ("פלוני", "אלמוני", "פלונית", "פלוני אלמוני")
REAL_ABBREVIATIONS = ("ת.ז.", "ח.פ.", "ע.ר.", "מ.א.", "ת.ד.", "ד.נ.", "ע.מ.")
CURRENCY = ("₪", 'ש"ח', "שקל", "NIS", "$", "€")
GREGORIAN = ("ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר")
HEBREW_MONTHS = ("תשרי", "חשון", "כסלו", "טבת", "שבט", "אדר", "ניסן", "אייר", "סיון", "תמוז", "אב", "אלול")
MONTH_WORD = re.compile(r"(^|\s)ב(" + "|".join(GREGORIAN + HEBREW_MONTHS) + r")\s")
NUMERIC_DATE = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2}|\d{4})")
# The words just before a number that the plan's pattern-only kinds and plates are found by.
CUE_BEFORE = {
    "IL_PLATE": re.compile(r"(רישוי |רכב מס' )$"),
    "HEALTH_FUND_ID": re.compile(r"(החולים: |חבר |קופ\"ח )$"),
    "MILITARY_ID": re.compile(r"(מ\.א\. |אישי:? )$"),
    "PASSPORT_NUMBER": re.compile(r"(דרכון מס' |הדרכון: |שמספרו )$"),
}
PATTERN_SHAPES = {"HEALTH_FUND_ID": r"\d{6,9}", "MILITARY_ID": r"\d{7}", "PASSPORT_NUMBER": r"\d{8}|[A-Z]{2}\d{7}"}


def before(batch: Batch, item: Item, size: int) -> str:
    """Return up to size code points of the document before an item, marks read as ASCII."""
    return batch.documents[item.doc][max(0, item.start - size) : item.start].translate(MARKS)


def digest(batch: Batch) -> str:
    """Return a sha256 of the batch's documents and of every span of its key and near misses."""
    spans = ";".join(f"{i.doc},{i.start},{i.end},{i.type}" for i in batch.key + batch.near_misses)
    return hashlib.sha256(("\x1f".join(batch.documents) + "\x1e" + spans).encode("utf-8")).hexdigest()


def plan_id_ok(digits: str) -> bool:
    """The Israeli ID check exactly as build-plan.md Phase 1 prints it."""
    if len(digits) > 9 or not digits.isdigit():
        return False
    d = digits.zfill(9)
    total = 0
    for i, ch in enumerate(d):
        n = int(ch) * (1 if i % 2 == 0 else 2)
        total += n if n < 10 else n - 9
    return total % 10 == 0


def luhn_ok(digits: str) -> bool:
    """The Luhn check, every second digit from the right doubled."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return digits.isdigit() and total % 10 == 0


def card_brand_ok(digits: str) -> bool:
    """Brand prefix sanity: Visa, Mastercard (51 to 55, 2221 to 2720) and American Express."""
    visa = digits.startswith("4") and len(digits) in (13, 16, 19)
    master = (51 <= int(digits[:2]) <= 55 or 2221 <= int(digits[:4]) <= 2720) and len(digits) == 16
    amex = digits[:2] in ("34", "37") and len(digits) == 15
    return visa or master or amex


def iban_ok(value: str) -> bool:
    """An Israeli IBAN: IL, 21 digits, and mod-97 of the rearranged number is 1 (ISO 13616)."""
    compact = value.replace(" ", "")
    if len(compact) != 23 or not compact.startswith("IL") or not compact[2:].isdigit():
        return False
    return int(compact[4:] + "1821" + compact[2:4]) % 97 == 1


def stripped(value: str) -> str:
    """The value without the separators an ID or a card may carry."""
    return "".join(ch for ch in value if ch not in ID_SEPARATORS)


def checksum_valid(kind: str, value: str) -> bool:
    """Whether a value is a valid identifier of a checksum type: shape, prefix and check."""
    digits = stripped(value)
    if kind == "IBAN":
        return iban_ok(value)
    if kind == "CREDIT_CARD":
        return digits.isdigit() and len(digits) >= 4 and luhn_ok(digits) and card_brand_ok(digits)
    if not digits.isdigit() or len(set(digits.zfill(9))) == 1:
        return False
    if kind == "IL_ID":
        return len(digits) in (8, 9) and plan_id_ok(digits)
    shape = len(digits) == 9 and plan_id_ok(digits)
    if kind == "COMPANY_NUMBER":
        return shape and digits.startswith("5") and not digits.startswith("58")
    return shape and digits.startswith("58")


def _phone_ok(text: str) -> bool:
    """A phone of build-plan.md Phase 1: landline, mobile, VoIP, +972, or a *NNNN service number."""
    number = "0" + text[4:] if text.startswith("+972") else text
    number = re.sub(r"[-\s()]", "", number)
    return re.fullmatch(r"0[23489]\d{7}|05\d{8}|07[2-9]\d{7}|\*[1-9]\d{3}", number) is not None


def _date_ok(text: str) -> bool:
    """A date: a day and month that exist read either way round, or a month's name after ב."""
    match = NUMERIC_DATE.fullmatch(text)
    if match:
        first, second = int(match[1]), int(match[2])
        return (1 <= first <= 31 and 1 <= second <= 12) or (1 <= second <= 31 and 1 <= first <= 12)
    return MONTH_WORD.search(" " + text + " ") is not None


def _address_ok(text: str) -> bool:
    """A street of the lexicon followed by a number, and a city of the lexicon."""
    has_street = any(re.search(re.escape(street) + r" \d", text) for street in STREETS)
    return has_street and any(city in text for city in CITIES)


def _name_ok(text: str, words: int | None) -> bool:
    """Whether every word is a name of the lexicon, and there are `words` of them when given."""
    parts = text.split()
    return all(part in NAMES for part in parts) and (words is None or len(parts) == words)


def _untitled_ok(text: str) -> bool:
    """A name that stands alone: two names of the lexicon, or one family name that is no ordinary word."""
    parts = text.split()
    pair = len(parts) == 2 and all(part in NAMES for part in parts)
    lone = len(parts) == 1 and parts[0] in FAMILY and parts[0] not in ORDINARY_WORD_NAMES
    return pair or lone


def _placeholder_ok(text: str) -> bool:
    """A placeholder of the plan's list, a run of underscores, or initials that are no abbreviation."""
    initials = re.fullmatch(r"[א-ת]\.[א-ת]\.", text) is not None and text not in REAL_ABBREVIATIONS
    return text in PLACEHOLDER_WORDS or re.fullmatch(r"_{3,}", text) is not None or initials


def _shape(kind: str, text: str, cue: str) -> bool:
    """Whether a number has its kind's shape and stands right after one of its cues."""
    shape = re.fullmatch(PATTERN_SHAPES.get(kind, r"\d{7,8}"), text) is not None
    return shape and CUE_BEFORE[kind].search(cue) is not None


def valid(batch: Batch, item: Item) -> bool:
    """Whether an item's text, in its document, is a valid item of its type."""
    text, kind = item.text.translate(MARKS), item.type
    if kind in CHECKSUM_TYPES:
        return checksum_valid(kind, text)
    checks = {
        "BANK_ACCOUNT": lambda: re.fullmatch(r"\d{2}[-/]\d{3}[-/]\d{6,9}|\d{2} סניף \d{3} חשבון \d{6,9}", text) is not None,
        "PHONE": lambda: _phone_ok(text),
        "EMAIL": lambda: re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s.]+", text) is not None,
        "URL": lambda: re.fullmatch(r"(https?://|www\.)\S+", text) is not None,
        "IP_ADDRESS": lambda: len(parts := text.split(".")) == 4 and all(p.isdigit() and int(p) <= 255 for p in parts),
        "IL_PLATE": lambda: re.fullmatch(r"\d{2}-\d{3}-\d{2}|\d{3}-\d{2}-\d{3}", text) is not None or _shape(kind, text, before(batch, item, 20)),
        "CASE_NUMBER": lambda: re.fullmatch(r"\S+ (\d{1,5}-(0[1-9]|1[0-2])-\d{2}|\d{1,5}/\d{2})", text) is not None,
        "GUSH_HELKA": lambda: re.fullmatch(r"גוש \d+,? חלקה \d+( תת[- ]חלקה \d+)?", text) is not None,
        "DATE": lambda: _date_ok(text),
        "AMOUNT": lambda: any(sign in text for sign in CURRENCY),
        "ADDRESS": lambda: _address_ok(text),
        "PERSON": lambda: _untitled_ok(text) if item.group == UNTITLED else _name_ok(text, None),
        "PLACEHOLDER": lambda: _placeholder_ok(text),
    }
    if kind in checks:
        return bool(checks[kind]())
    return _shape(kind, text, before(batch, item, 20))
