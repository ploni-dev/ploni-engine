"""Build the invented part of the held-out batch of Phase 1 in memory, from a fixed seed.

Why: every PR from Phase 1 on carries the batch's numbers, and a worse one blocks (build-plan.md
section 7, "The held-out batch"; Phase 1, "Tests added"). Achia decided on 2026-11-26 (issue 283)
that a session that never sees the detector code writes it, and that the documents are "Made
fresh each run": no file holds a document, an identifier or the key. The seed and this code are
the batch. Checksum-valid ID and card numbers are made here and live only in memory.

Contract: `build(seed)` returns a Batch: the documents' text; the key, every item a correct
detector must find, as its document's index, its span [start, end) in code points of that
document's text, its type and its text; and the near misses, items a correct detector must not
find, typed by the type they imitate. The same seed gives the same batch on any machine with the
same Python. Nothing is written to disk, logged or printed.

The types, one name each, from build-plan.md (line numbers at 85db608). What a span covers is
written, in words, in eval/heldout/SPAN_RULES.md (Achia, 2026-11-26, "Yes, the rules only").

| Type             | Plan line                                              |
|------------------|--------------------------------------------------------|
| IL_ID            | 608 Israeli ID                                         |
| COMPANY_NUMBER   | 622 company numbers (ח.פ.)                             |
| NONPROFIT_NUMBER | 622 non-profit numbers (ע.ר.)                          |
| IBAN             | 624 IBAN                                               |
| BANK_ACCOUNT     | 624 domestic bank/branch/account triples               |
| CREDIT_CARD      | 626 Credit card                                        |
| PHONE            | 628 Israeli phone                                      |
| EMAIL            | 630 Email                                              |
| URL              | 630 URL                                                |
| IP_ADDRESS       | 630 IP                                                 |
| IL_PLATE         | 632 License plate                                      |
| CASE_NUMBER      | 634 Court case numbers                                 |
| GUSH_HELKA       | 636 Gush / Helka                                       |
| DATE             | 638 Dates                                              |
| AMOUNT           | 640 Amounts                                            |
| ADDRESS          | 642 Addresses                                          |
| PERSON           | 644 Trigger words: a name after a trigger              |
| PLACEHOLDER      | 646 Already-anonymized placeholders                    |
| HEALTH_FUND_ID   | 648 Health fund member numbers                         |
| MILITARY_ID      | 648 military IDs                                       |
| PASSPORT_NUMBER  | 648 passport numbers                                   |

One group, of PERSON items: "untitled", the names that stand once in their document with no
title before them (build-plan.md line 404, section 7; Achia, 2026-11-16, "Yes, as its own line
from the start"). Its items are PERSON, as a detector returns them; the group is a mark on the
item, for a line of its own in the scores, and no type.

Each type, and the group, has one maker: given the random generator and whether a near miss is
wanted, it returns a sentence frame with {} where the value stands, and the value. The gershayim and geresh
of a sentence are ASCII or Hebrew, chosen per sentence. Plain sentences with no item stand
between the items, as in real text.

Known limits:
- Plain text only: no runs, headers, tables or footnotes; Phase 2 brings documents with those.
- The sentences are templates, the same few per type, mixed into documents of six genres; a
  sentence does not depend on its document's genre.
- No item stands inside another: a name or a case number inside a URL's path is not planted,
  since the key holds no nested spans and the scorer counts none.
- Hebrew years are written without final letters (תש"פ, not תש"ף).
"""

import random
import re
from collections.abc import Callable
from dataclasses import dataclass, field

# The seed of the batch: the day Achia chose "Made fresh each run" (issue 283).
SEED = 20261126
# CLAUDE.md, Tests: detectors 40 positive and 40 negative; ten more of each leave room.
PER_SIDE = 50
# Twelve items a document; with the plain sentences between them, a few hundred code points,
# a small part of a page (a median of 662 measured on the batch of SEED, before review 2).
ITEMS_PER_DOCUMENT = 12
# The share of items followed by a plain sentence with no item in it.
FILLER_SHARE = 0.4
# An even split between two forms of a sentence or a value, as between ASCII and Hebrew marks.
HALF = 0.5
HEBREW_MARK_TABLE = str.maketrans({'"': "״", "'": "׳"})
# Of the near misses of a checksum type, the share of the right length that fail the checksum
# only; the rest have a wrong length or prefix. Enough that 20 of 50 is far below the mean.
CHECKSUM_MISS_SHARE = 0.7
# The share of each rarer form (a service number, a plate with no trigger, an amount in words).
SMALL_SHARE = 0.2
# IL_ID near misses that are nine zeros, which pass the check (Phase 1: "Reject trivial sequences").
TRIVIAL_SHARE = 0.1
# The bounds below of a random draw (days, house numbers, pages) are plausible sizes of what they
# draw; the bounds that make a near miss fail are named.
DIGITS = "0123456789"
NONZERO = DIGITS[1:]
# build-plan.md Phase 1, Israeli ID: nine digits; an ID check zero-fills a shorter number, so a
# group of 7 to 9 digits can pass it on its own.
ID_LENGTH = 9
ID_PART_SHORTEST = 7
# A near miss one digit too long: the check digit's place and one digit more.
ID_TOO_LONG_TAIL = 2
# ISO 13616: "IL" read as digits, I = 18 and L = 21; the remainder that marks a valid IBAN.
IL_DIGITS = "1821"
IBAN_MOD = 97
IBAN_BBAN = 19
# The Hebrew calendar: from January to the autumn, the Hebrew year is the Gregorian one plus
# 3760 (5785 ran from the autumn of 2024 to the autumn of 2025).
HEBREW_YEAR_OFFSET = 3760

Frame = tuple[str, str]
Maker = Callable[[random.Random, bool], Frame]


@dataclass(frozen=True)
class Item:
    """One planted item: where it stands in which document, and of which type.

    Why: the key and the near misses are lists of these. The text, kept for the tests of the
    span, is left out of the repr, so a message that prints an item shows no identifier.
    Contract: doc indexes Batch.documents; [start, end) is the span in code points of that
    document's text; type is one of TYPES; text equals the text of the span; group is "" or one
    of GROUPS, a mark of the items scored on a line of their own.
    """

    doc: int
    start: int
    end: int
    type: str
    text: str = field(repr=False)
    group: str = ""


@dataclass(frozen=True)
class Batch:
    """The documents of the batch with its key and its near misses.

    Why: the scorer needs the three together; the repr shows none, so a batch printed by mistake
    prints no document. Contract: documents is a tuple of texts; key and near_misses are tuples
    of Item, in the order of the documents and, within one, of their start.
    """

    documents: tuple[str, ...] = field(repr=False)
    key: tuple[Item, ...] = field(repr=False)
    near_misses: tuple[Item, ...] = field(repr=False)


def _num(rng: random.Random, length: int, first: str = DIGITS) -> str:
    """Return a random digit string of a length, its first digit drawn from `first`."""
    return rng.choice(first) + "".join(rng.choice(DIGITS) for _ in range(length - 1))


def _group(digits: str, sizes: tuple[int, ...], separator: str) -> str:
    """Return the digits cut into groups of the sizes, joined by the separator; the rest follows."""
    parts, at = [], 0
    for size in sizes:
        parts.append(digits[at : at + size])
        at += size
    return separator.join([*parts, digits[at:]] if digits[at:] else parts)


def _id_ok(digits: str) -> bool:
    """Say whether digits pass the Israeli ID check, as build-plan.md Phase 1 writes it."""
    if len(digits) > ID_LENGTH or not digits.isdigit():
        return False
    total = 0
    for index, digit in enumerate(digits.zfill(ID_LENGTH)):
        product = int(digit) * (1 if index % 2 == 0 else 2)
        total += product if product < 10 else product - 9
    return total % 10 == 0


def _luhn_ok(digits: str) -> bool:
    """Say whether digits pass the Luhn check, every second digit from the right doubled."""
    total = 0
    for index, digit in enumerate(reversed(digits)):
        product = int(digit) * (2 if index % 2 else 1)
        total += product - 9 if product > 9 else product
    return total % 10 == 0


def _id_check_digit(body: str) -> str:
    """Return the digit that completes eight digits into a number that passes the ID check."""
    return next(digit for digit in DIGITS if _id_ok(body + digit))


def _luhn_check_digit(body: str) -> str:
    """Return the digit that completes a body into a number that passes the Luhn check."""
    return next(digit for digit in DIGITS if _luhn_ok(body + digit))


def _iban(bban: str) -> str:
    """Return the Israeli IBAN of an account part, its two check digits computed by mod-97."""
    check = IBAN_MOD + 1 - int(bban + IL_DIGITS + "00") % IBAN_MOD
    return f"IL{check:02d}{bban}"


def _part_passes(value: str) -> bool:
    """Say whether a value that fails the ID check holds a group of 7 to 9 digits that passes it.

    Why: a detector that splits on separators, as the plan's zero-fill allows, could rightly
    flag such a near miss, so it is drawn again.
    """
    parts = re.split(r"\D+", value)
    lone = any(ID_PART_SHORTEST <= len(part) <= ID_LENGTH and len(set(part)) > 1 and _id_ok(part) for part in parts)
    return lone and not _id_ok("".join(parts))


UNITS = ("", "א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט")
TENS = ("", "י", "כ", "ל", "מ", "נ", "ס", "ע", "פ", "צ")
HUNDREDS = ("", "ק", "ר", "ש", "ת", "תק", "תר", "תש", "תת", "תתק")
# 15 and 16 are written with tet, so that no number spells a name of God.
TET = {15: "טו", 16: "טז"}


def _hebrew_number(number: int) -> str:
    """Return 1 to 999 in Hebrew letters: a geresh after one letter, gershayim before the last of more."""
    tail = number % 100
    letters = HUNDREDS[number // 100] + TET.get(tail, TENS[tail // 10] + UNITS[tail % 10])
    return letters + "'" if len(letters) == 1 else f'{letters[:-1]}"{letters[-1]}'


def _pick(rng: random.Random, frames: tuple[str, ...], value: str) -> Frame:
    """Return a frame drawn from frames, with the value to stand at its {}."""
    return rng.choice(frames), value


# Israeli ID, company and non-profit numbers (build-plan.md Phase 1). A personal ID starts 0 to
# 3 here, the 5 of companies and non-profits stays theirs; one with a leading 0 may drop it.
ID_FRAMES = ('הלקוח, נושא ת"ז {}, חתם על ההסכם.', "מספר תעודת הזהות של המצהירה הוא {}.", "ת.ז. {} צורפה לבקשה.", "בעלת תעודת זהות מס' {} התייצבה במשרד.")
COMPANY_FRAMES = ('חברת הדוגמה בע"מ, ח"פ {}, הגישה את הדוח.', "החברה (ח.פ. {}) היא צד להסכם.", "מספר החברה ברשם החברות: {}.")
NONPROFIT_FRAMES = ('עמותת הדוגמה (ע"ר {}) פנתה לבית המשפט.', "העמותה, ע.ר. {}, אישרה את הדוחות.", "מספר העמותה ברשם העמותות: {}.")
ID_HEADS = ("01", "02", "03", "1", "2", "3")
COMPANY_HEADS = tuple(f"5{digit}" for digit in "1234679")
NONPROFIT_HEADS = ("58",)
ID_GROUPS = ((9,), (8,), (3, 3), (2, 6))


def _nine(rng: random.Random, head: str, near: bool) -> str:
    """Return nine digits from head that pass the ID check, not one digit repeated; a near miss fails it.

    A near miss has a wrong check digit, or one digit too many.
    """
    body = head + _num(rng, ID_LENGTH - 1 - len(head))
    if not near:
        digits = body + _id_check_digit(body)
        return digits if len(set(digits)) > 1 else _nine(rng, head, near)
    if rng.random() < CHECKSUM_MISS_SHARE:
        return body + rng.choice([digit for digit in DIGITS if not _id_ok(body + digit)])
    return body + _num(rng, ID_TOO_LONG_TAIL)


def _id_value(rng: random.Random, digits: str) -> str:
    """Return digits as an ID is written: plain, or grouped by hyphen, space or dot."""
    return _group(digits, rng.choice(ID_GROUPS), rng.choice("- ."))


def _il_id(rng: random.Random, near: bool) -> Frame:
    if near and rng.random() < TRIVIAL_SHARE:
        return _pick(rng, ID_FRAMES, _id_value(rng, "0" * ID_LENGTH))
    digits = _nine(rng, rng.choice(ID_HEADS[3:] if near else ID_HEADS), near)
    if not near and digits.startswith("0") and rng.random() < HALF:
        digits = digits[1:]
    return _pick(rng, ID_FRAMES, _id_value(rng, digits))


def _registered(rng: random.Random, near: bool, frames: tuple[str, ...], heads: tuple[str, ...]) -> Frame:
    return _pick(rng, frames, _id_value(rng, _nine(rng, rng.choice(heads), near)))


# IBAN and domestic accounts (build-plan.md Phase 1). Bank codes of the Bank of Israel's list.
IBAN_FRAMES = ("יש להעביר את התשלום לחשבון {}.", "IBAN: {}", "מספר ה-IBAN של החשבון הוא {} ויש לציינו בהעברה.")
BANK_CODES = ("010", "011", "012", "020", "031")
ACCOUNT_FRAMES = ("התשלום יועבר לחשבון מס' {} (בנק-סניף-חשבון).", "פרטי חשבון הבנק: {}.", "החשבון {} רשום על שם החברה.")
# What makes an account near miss fail: three groups of the wrong sizes.
ACCOUNT_MISS_SHAPE = (4, 3, 2)


def _iban_value(rng: random.Random, near: bool) -> Frame:
    bban = rng.choice(BANK_CODES) + _num(rng, IBAN_BBAN - 3)
    iban = _iban(bban)
    if near and rng.random() < CHECKSUM_MISS_SHARE:
        # Check digits run from 02 to 98, so any other pair of them fails mod-97.
        wrong = rng.choice([check for check in range(2, 99) if f"{check:02d}" != iban[2:4]])
        iban = f"IL{wrong:02d}{bban}"
    elif near:
        # One digit more or one less, with check digits that are right for that length.
        iban = _iban(bban + _num(rng, 1) if rng.random() < HALF else bban[:-1])
    spaced = " ".join(iban[at : at + 4] for at in range(0, len(iban), 4))
    return _pick(rng, IBAN_FRAMES, iban if rng.random() < HALF else spaced)


def _account(rng: random.Random, near: bool) -> Frame:
    if near and rng.random() < HALF:
        return "חשבונית מס' {} צורפה לתביעה.", f"{rng.randint(2015, 2025)}/{_num(rng, 6)}"
    if near:
        return _pick(rng, ACCOUNT_FRAMES, "-".join(_num(rng, size, NONZERO) for size in ACCOUNT_MISS_SHAPE))
    bank, branch, account = rng.choice(BANK_CODES)[1:], _num(rng, 3, NONZERO), _num(rng, rng.randint(6, 9))
    if rng.random() < SMALL_SHARE:
        return "התשלום יועבר לבנק {} על שם החברה.", f"{bank} סניף {branch} חשבון {account}"
    return _pick(rng, ACCOUNT_FRAMES, rng.choice("-/").join((bank, branch, account)))


# Credit cards (build-plan.md Phase 1): Visa (13, 16 or 19 digits), Mastercard (51 to 55 and the
# 2-series) and American Express. A near miss fails the Luhn check, or passes it on a number no
# brand issues: no brand starts with 1 at 16 digits, and Visa has no 15.
CARD_FRAMES = ("התשלום בוצע בכרטיס אשראי שמספרו {}.", "מספר כרטיס האשראי: {}.", "החיוב בכרטיס {} בוטל לבקשת הלקוח.")
BRANDS = (
    ("4", 16, (4, 4, 4)), ("4", 13, (4, 3, 3)), ("4", 19, (4, 4, 4, 4)), ("51", 16, (4, 4, 4)), ("53", 16, (4, 4, 4)),
    ("55", 16, (4, 4, 4)), ("25", 16, (4, 4, 4)), ("34", 15, (4, 6)), ("37", 15, (4, 6)),
)  # fmt: skip
NO_BRAND = (("1", 16, (4, 4, 4)), ("4", 15, (4, 4, 4)))


def _card(rng: random.Random, near: bool) -> Frame:
    luhn_fails = near and rng.random() < CHECKSUM_MISS_SHARE
    prefix, length, groups = rng.choice(NO_BRAND if near and not luhn_fails else BRANDS)
    body = prefix + _num(rng, length - len(prefix) - 1)
    right = _luhn_check_digit(body)
    digits = body + (rng.choice([digit for digit in DIGITS if digit != right]) if luhn_fails else right)
    separator = rng.choice((" ", "-", ""))
    return _pick(rng, CARD_FRAMES, _group(digits, groups, separator) if separator else digits)


# Israeli phones (build-plan.md Phase 1): landline 0[23489], mobile 05X, VoIP 07[2-9], +972,
# and *NNNN service numbers. The kind is drawn first, then its area.
PHONE_FRAMES = ("ניתן להשיג את הצד בטלפון {}.", "טל': {}", "נייד: {}", "פקס: {}", "לבירורים ניתן לחייג {} בשעות הפעילות.")
PHONE_KINDS = (("02", "03", "04", "08", "09"), tuple(f"05{digit}" for digit in DIGITS), tuple(f"07{digit}" for digit in "23456789"))
BAD_AREAS = ("06", "01", "070", "071")
PHONE_DIGITS = 7
SERVICE_DIGITS = 4
# What makes a phone near miss fail: a subscriber number of another length, a short service code.
WRONG_PHONE_LENGTHS = (5, 6, 8)
SHORT_SERVICE = 2


def _phone(rng: random.Random, near: bool) -> Frame:
    if rng.random() < SMALL_SHARE:
        return _pick(rng, PHONE_FRAMES, "*" + _num(rng, SHORT_SERVICE if near else SERVICE_DIGITS, NONZERO))
    wrong_area = near and rng.random() < HALF
    area = rng.choice(BAD_AREAS if wrong_area else rng.choice(PHONE_KINDS))
    number = _num(rng, rng.choice(WRONG_PHONE_LENGTHS) if near and not wrong_area else PHONE_DIGITS)
    head, tail = number[:3], number[3:]
    forms = (f"{area}-{number}", f"{area}-{head}-{tail}", area + number, f"{area} {head} {tail}", f"({area}) {number}", f"+972-{area[1:]}-{number}", f"+972 {area[1:]} {head} {tail}")
    return _pick(rng, PHONE_FRAMES, rng.choice(forms))


# Email, URL and IP (build-plan.md Phase 1). Domains of RFC 2606 and RFC 6761 only, never a real one.
EMAIL_FRAMES = ('ניתן לפנות בדוא"ל {} עד סוף השבוע.', 'דוא"ל: {}', "את המסמכים יש לשלוח אל {}.")
LATIN_GIVEN = ("dana", "yossi", "noa", "avi", "michal", "eyal", "tamar", "office", "info", "legal")
LATIN_FAMILY = ("levi", "cohen", "mizrahi", "peretz", "biton", "shapira")
DOMAINS = ("example.com", "example.org", "example.net", "mail.example.com", "law.example", "court.test")
URL_FRAMES = ("המסמכים זמינים בכתובת {}.", "ראו באתר {} את ההנחיות.", "הקישור להורדה: {}")
HOSTS = ("www.example.com", "example.org", "portal.example.net", "files.example.com")
PATHS = ("cases", "docs", "view", "files", "download", "contract", "forms", "archive", "public", "search")
FILE_NAMES = (*PATHS, "נספח", "הסכם", "סריקה", "מכתב", "צילום", "report", "scan", "minutes")
IP_FRAMES = ("הכניסה לחשבון נרשמה מכתובת IP {}.", "השרת בכתובת {} נחסם.", "כתובת ה-IP של המחשב הייתה {} באותו היום.")
# Unicast first octets of classes A to C; an octet past 255 is what makes a near miss fail.
FIRST_OCTET = (1, 223)
OCTET_MAX = 255
BAD_OCTET = (256, 999)


def _email(rng: random.Random, near: bool) -> Frame:
    given, domain = rng.choice(LATIN_GIVEN), rng.choice(DOMAINS)
    local = given if rng.random() < SMALL_SHARE else given + rng.choice("._") + rng.choice(LATIN_FAMILY)
    if near:
        return _pick(rng, EMAIL_FRAMES, rng.choice((f"{local}@", f"{local}@{domain.split('.')[0]}", f"{local}@@{domain}", f"@{domain}")))
    return _pick(rng, EMAIL_FRAMES, f"{local}@{domain}")


def _url(rng: random.Random, near: bool) -> Frame:
    if near:
        return "הקובץ {} צורף להודעה.", f"{rng.choice(FILE_NAMES)}.{rng.choice(('pdf', 'docx', 'xlsx', 'txt'))}"
    host = rng.choice(HOSTS)
    scheme = rng.choice(("https://", "http://", "") if host.startswith("www.") else ("https://", "http://"))
    path = "".join("/" + rng.choice(PATHS) for _ in range(rng.randint(0, 3)))
    query = rng.choice(("", f"?doc={rng.choice(PATHS)}", f"?view={rng.choice(PATHS)}&lang=he"))
    return _pick(rng, URL_FRAMES, scheme + host + path + query)


def _ip(rng: random.Random, near: bool) -> Frame:
    if near and rng.random() < HALF:
        return "כאמור בסעיף {} להסכם, הצדדים מסכימים.", ".".join(str(rng.randint(1, 20)) for _ in range(3))
    octets = [str(rng.randint(*FIRST_OCTET))] + [str(rng.randint(0, OCTET_MAX)) for _ in range(3)]
    if near:
        octets[rng.randrange(4)] = str(rng.randint(*BAD_OCTET))
    return _pick(rng, IP_FRAMES, ".".join(octets))


# License plates (build-plan.md Phase 1): NN-NNN-NN and NNN-NN-NNN, a separator or a trigger.
PLATE_TRIGGERED = ("הרכב, מספר רישוי {}, נגרר מהמקום.", "לוחית הרישוי {} צולמה במצלמת האבטחה.", "רכב מס' {} חנה במקום אסור.")
PLATE_SHAPES = ((7, (2, 3)), (8, (3, 2)))
# What makes a plate near miss fail: a plate's digits with no separator and no trigger, or two
# groups of the wrong sizes.
PLATE_MISS_SHAPE = (4, 3)


def _plate(rng: random.Random, near: bool) -> Frame:
    if near and rng.random() < HALF:
        return "בארכיון נספרו {} פריטים.", _num(rng, rng.choice(PLATE_SHAPES)[0], NONZERO)
    if near:
        return "מספר האסמכתא {} נמסר ללקוח.", "-".join(_num(rng, size, NONZERO) for size in PLATE_MISS_SHAPE)
    length, groups = rng.choice(PLATE_SHAPES)
    digits = _num(rng, length, NONZERO)
    if rng.random() < SMALL_SHARE:
        return "במצלמה נקלט {} ליד השער.", _group(digits, groups, "-")
    return _pick(rng, PLATE_TRIGGERED, _group(digits, groups, rng.choice(("-", "-", ""))))


# Court case numbers (build-plan.md Phase 1): 30 common procedures, two shapes of number. A near
# miss has a month that is none, or is a citation of a law report or of a gazette.
PROCEDURES = (
    'ת"א', 'תא"מ', 'ת"ק', 'ק"פ', 'ע"א', 'רע"א', 'בג"ץ', 'ע"פ', 'רע"פ', 'ת"פ', 'בש"פ', 'בש"א', 'עת"מ', 'עע"מ', 'ה"פ',
    'תמ"ש', 'עמ"ש', 'רמ"ש', 'ע"ע', 'ס"ע', 'ד"מ', 'דנ"א', 'דנ"פ', 'בר"מ', 'ת"צ', 'פש"ר', 'פר"ק', 'ע"מ', 'מ"ח', 'צ"א',
)  # fmt: skip
CASE_FRAMES = ("בתיק {} נקבע דיון הוכחות.", "כפי שנקבע ב{}, אין להתערב בממצאים.", "ההחלטה ב{} ניתנה בהיעדר הצדדים.", "ראו: {}.")
MONTHS = 12
CASE_YEARS = (10, 25)
NO_MONTHS = (0, *range(MONTHS + 1, 20))
GAZETTES = ('ס"ח', 'ק"ת', 'י"פ')


def _case(rng: random.Random, near: bool) -> Frame:
    procedure, year, kind = rng.choice(PROCEDURES), rng.randint(*CASE_YEARS), rng.randrange(4)
    if near and kind == 2:
        return "כפי שנפסק בעבר ({}).", f'פ"ד {_hebrew_number(rng.randint(1, 80))}({rng.randint(1, 5)}) {rng.randint(1, 999)}'
    if near and kind == 3:
        return "הנוסח פורסם ב{}.", f"{rng.choice(GAZETTES)} {rng.randint(100, 9999)}"
    if near or kind < 2:
        month = rng.choice(NO_MONTHS) if near else rng.randint(1, MONTHS)
        return _pick(rng, CASE_FRAMES, f"{procedure} {_num(rng, 5, NONZERO)}-{month:02d}-{year}")
    return _pick(rng, CASE_FRAMES, f"{procedure} {rng.randint(1, 9999)}/{year}")


# Gush and helka (build-plan.md Phase 1). Most near misses carry a cue word and are still no
# parcel; the rest are a part of a text by its number.
PARCEL_FRAMES = ("המקרקעין הידועים כ{} נמכרו לחברה.", "הנכס רשום בפנקסי המקרקעין כ{}.", "הבקשה נוגעת למגרש ב{}.")
REGIONS = ("גוש דן", "גוש עציון")


def _parcel(rng: random.Random, near: bool) -> Frame:
    kind = rng.randrange(4)
    if near and kind == 0:
        return "כאמור ב{} להסכם, הצדדים מסכימים.", f"{rng.choice(('חלק', 'פרק', 'נספח'))} {rng.randint(1, 400)}"
    if near and kind == 1:
        return "הפרויקט ייבנה ב{} בשנים הקרובות.", rng.choice(REGIONS)
    if near and kind == 2:
        return "החברה תקבל את {} ברווחים לפי ההסכם.", "חלקה"
    if near:
        return "ההיתר ניתן ל{} בלבד ולא לשאר המגרש.", f"חלקה {rng.randint(1, 400)}"
    value = f"גוש {rng.randint(1000, 30000)}{rng.choice((' ', ', '))}חלקה {rng.randint(1, 400)}"
    if rng.random() < SMALL_SHARE:
        value += f" {rng.choice(('תת-חלקה', 'תת חלקה'))} {rng.randint(1, 30)}"
    return _pick(rng, PARCEL_FRAMES, value)


# Dates (build-plan.md Phase 1): numeric, Hebrew month names, the Hebrew calendar. A near miss
# has a day past 31, so that it is no date read month first either, or is the year of a law.
DATE_FRAMES = ("ביום {} נחתם ההסכם בין הצדדים.", "תאריך: {}", "המכתב נשלח בתאריך {} בדואר רשום.", "הדיון נקבע ליום {} בשעות הבוקר.")
GREGORIAN = ("ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני", "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר")
HEBREW_MONTHS = ("תשרי", "חשון", "כסלו", "טבת", "שבט", "אדר", "ניסן", "אייר", "סיון", "תמוז", "אב", "אלול")
# Days 1 to 28 exist in every month of both calendars.
SAFE_DAYS = 28
YEARS = (1990, 2025)
NO_DAYS = (32, 39)
ANY_MONTH = (1, 19)


def _date(rng: random.Random, near: bool) -> Frame:
    day, month, year, kind = rng.randint(1, SAFE_DAYS), rng.randint(1, MONTHS), rng.randint(*YEARS), rng.randrange(4)
    hebrew_year = _hebrew_number((year + HEBREW_YEAR_OFFSET) % 1000)
    if near and kind < 2:
        return "לפי חוק הדוגמה, {}, הבקשה נדחית.", f"ה{hebrew_year}-{year}"
    if near:
        return _pick(rng, DATE_FRAMES, f"{rng.randint(*NO_DAYS)}/{rng.randint(*ANY_MONTH):02d}/{year}")
    if kind == 0:
        return _pick(rng, DATE_FRAMES, f"{day} ב{GREGORIAN[month - 1]} {year}")
    if kind == 1:
        return _pick(rng, DATE_FRAMES, f"{_hebrew_number(day)} ב{HEBREW_MONTHS[month - 1]} {hebrew_year}")
    return _pick(rng, DATE_FRAMES, rng.choice((f"{day:02d}/{month:02d}/{year}", f"{day}.{month}.{year}", f"{day:02d}-{month:02d}-{year % 100:02d}")))


# Amounts (build-plan.md Phase 1): ₪, ש"ח, שקל, NIS, $, €, and written-out Hebrew numbers.
AMOUNT_FRAMES = ("החברה תשלם סך של {} בתוך שלושים יום.", "הוסכם על תמורה בסך {} לכל חודש.", "הסכום שנגבה, {}, יוחזר במלואו.")
WRITTEN = ("אלף", "אלפיים", "שלושת אלפים", "חמשת אלפים", "עשרת אלפים", "מאה אלף", "חמש מאות", "שבע מאות וחמישים")
SHEKEL_WORDS = ('ש"ח', "שקלים")
CURRENCY_FORMS = ("{} ₪", "₪{}", "₪ {}", '{} ש"ח', "{} שקלים", "NIS {}", "${}", "€{}", "{} €")
NOT_AMOUNTS = (("שיעור הריבית יעמוד על {}.", "{}%"), ("שיעור ההנחה הוא {} מהמחיר.", "{} אחוזים"), ("יש להגיש {} של כתב הטענות.", "{} עותקים"), ("ההודעה תימסר {} מראש.", "{} ימים"))


def _amount(rng: random.Random, near: bool) -> Frame:
    if near:
        frame, form = rng.choice(NOT_AMOUNTS)
        return frame, form.format(rng.randint(2, 99))
    if rng.random() < SMALL_SHARE:
        return _pick(rng, AMOUNT_FRAMES, f"{rng.choice(WRITTEN)} {rng.choice(SHEKEL_WORDS)}")
    number = rng.randint(10, 2_000_000)
    shown = rng.choice((f"{number:,}", str(number), f"{number:,}.50"))
    return _pick(rng, AMOUNT_FRAMES, rng.choice(CURRENCY_FORMS).format(shown))


# Addresses (build-plan.md Phase 1): a street lexicon, a number, a city lexicon. The first seven
# streets are named after people. A form with no street word is not glued to a proclitic, since
# Hebrew drops a street's ה after one. Most near misses carry a street, a city or a street word;
# the rest are a room by its number.
STREETS = ("הרצל", "ויצמן", "בן גוריון", "רוטשילד", "ז'בוטינסקי", "ביאליק", "סוקולוב", "אלנבי", "הנביאים", "העצמאות", "הרב קוק", "דיזנגוף", "הגפן", "הזית")
CITIES = ("תל אביב-יפו", "ירושלים", "חיפה", "באר שבע", "נתניה", "רמת גן", "פתח תקווה", "ראשון לציון", "חולון", "אשדוד", "רחובות", "כפר סבא")
ADDRESS_FRAMES = ("הצד מתגורר ב{}.", "כתובת הנכס: {}.", "המשרד ממוקם ב{} בקומה השנייה.")
ADDRESS_FORMS = ("רחוב {} {}, {}", "רח' {} {}, {}", "{} {}, {}", "שדרות {} {} {}")
PEOPLE = 7
PLAN_YEARS = (2030, 2050)


def _address(rng: random.Random, near: bool) -> Frame:
    kind = rng.randrange(5)
    if near and kind == 0:
        return "הדיון יתקיים ב{} בבית המשפט.", f"{rng.choice(('אולם', 'חדר', 'קומה'))} {rng.randint(1, 40)}"
    if near and kind == 1:
        return "דמותו של {} נלמדת בבתי הספר.", rng.choice(STREETS[:PEOPLE])
    if near and kind == 2:
        return "הצדדים נפגשו ב{} לפני הדיון.", rng.choice(CITIES)
    if near and kind == 3:
        return "המשרד יעבור ל{} בקרוב.", f"רחוב {rng.choice(STREETS)}"
    if near:
        return "התוכנית {} אושרה בוועדה.", f"{rng.choice(CITIES)} {rng.randint(*PLAN_YEARS)}"
    form = rng.choice(ADDRESS_FORMS)
    value = form.format(rng.choice(STREETS), rng.randint(1, 180), rng.choice(CITIES))
    return _pick(rng, ADDRESS_FRAMES[1:2] if form.startswith("{}") else ADDRESS_FRAMES, value)


# Trigger words and names (build-plan.md Phase 1); a name that stands once (section 7). "@" is
# where the trigger stands. A PERSON near miss is a trigger before a word that is no name; a
# near miss of the untitled group is a name of the plan's list used as the word it is.
TRIGGERS = ("מר", "גב'", 'עו"ד', 'ד"ר', "פרופ'", 'רו"ח', "התובע", "הנתבע", "המבקש", "המשיב", "העד", "כב' השופט", 'ב"כ')
PARTY_TRIGGERS = TRIGGERS[6:11]
PERSON_FRAMES = ("@ {} הצהיר כי הדברים נכונים.", "ההודעה נמסרה ל@ {} ביום הדיון.", "בדיון נכחו הצדדים ו@ {}.", "המסמך נחתם בפני @ {}.")
UNTITLED_FRAMES = ("{} חתם על ההסכם בשם החברה.", "ההסכם נחתם בנוכחות {} ביום הדיון.", "לדברי {}, הסחורה נמסרה במועד.", "המסמך נמסר לידי {} בסוף היום.")
GIVEN = (
    "יעקב", "דנה", "משה", "שרה", "מיכל", "יוסף", "דוד", "דויד", "אבי", "רבקה", "ג'ון", "ז'אק", "צ'רלי", "מֹשֶׁה", "רִבְקָה",
    "אור", "שחר", "רון", "ברק", "יונה", "שרון", "עדן", "טל", "גל", "שקד", "ים", "תום", "עומר", "נועם", "דקל", "חן", "שירה",
)  # fmt: skip
FAMILY = ("כהן", "לוי", "מזרחי", "פרץ", "ביטון", "דהן", "אברהם", "פרידמן", "אגבאריה", "חדד", "גבאי", "שפירא", "ברק", "לביא", "הדר")
# The family names that are no ordinary word, the first twelve: a name of one word standing alone.
LONE_FAMILY = FAMILY[:12]
VERBS = ("טוען", "השיב", "הוסיף", "ציין", "הודה", "ביקש", "הגיש", "העיד", "הכחיש", "סירב", "חזר", "הבהיר", "התנגד", "הסכים", "שתק", "נכח")
NOT_NAMES = (("גורלו של הנכס היה מר {}.", "מאוד"), ("הטעם של המשקה היה מר {} מן הצפוי.", "יותר"))
ORDINARY = (
    ("{} האמור לעיל, הבקשה נדחית.", "לאור"), ("הצדדים יצאו לדרך עם {}.", "שחר"), ("ההצעה מצאה {} בעיני הוועדה.", "חן"),
    ("בבוקר ירד {} כבד על השדה.", "טל"), ("עץ ה{} פרח מוקדם.", "שקד"), ("הבקשה הוגשה ב{} המועד.", "תום"),
    ("הנכס נמצא על שפת ה{}.", "ים"), ("ה{} שבר את החוף.", "גל"), ("הם קצרו את ה{} בשדה.", "עומר"),
    ("ה{} בחצר נכרת בלי היתר.", "דקל"), ("הם שרו {} עד הבוקר.", "שירה"), ("ה{} הלבנה נחה על הגג.", "יונה"),
)  # fmt: skip


def _with_trigger(frame: str, trigger: str) -> str:
    """Return a frame with its trigger; after ל, ב or כ the trigger's ה falls, as Hebrew writes it."""
    if trigger.startswith("ה") and frame[frame.index("@") - 1 : frame.index("@")] in ("ל", "ב", "כ"):
        trigger = trigger[1:]
    return frame.replace("@", trigger)


def _person(rng: random.Random, near: bool) -> Frame:
    if near and rng.random() < SMALL_SHARE:
        return rng.choice(NOT_NAMES)
    if near:
        return _with_trigger("@ {} כי אין לקבל את הבקשה.", rng.choice(PARTY_TRIGGERS)), rng.choice(VERBS)
    given, family = rng.choice(GIVEN), rng.choice(FAMILY)
    name = rng.choice((f"{given} {family}", f"{given} {family}", given, family))
    return _with_trigger(rng.choice(PERSON_FRAMES), rng.choice(TRIGGERS)), name


def _untitled(rng: random.Random, near: bool) -> Frame:
    if near:
        return rng.choice(ORDINARY)
    name = rng.choice(LONE_FAMILY) if rng.random() < SMALL_SHARE else f"{rng.choice(GIVEN)} {rng.choice(FAMILY)}"
    return _pick(rng, UNTITLED_FRAMES, name)


# Placeholders (build-plan.md Phase 1): פלוני, אלמוני, פלונית, initials, a blank line. A near miss
# is an abbreviation of the same shape as initials, or a word that holds a placeholder's letters.
PLACEHOLDER_FRAMES = ("בעניין {} נקבע כי הבקשה מתקבלת.", "שם המצהיר: {}.", "החתום מטה, {}, מאשר את האמור.", "מר {} הופיע לדיון.")
PLACEHOLDER_WORDS = ("פלוני", "אלמוני", "פלונית", "פלוני אלמוני")
INITIAL_LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"
ABBREVIATIONS = ("ת.ז.", "ח.פ.", "ע.ר.", "מ.א.", "ת.ד.", "ד.נ.", "ע.מ.")
ABBREVIATION_FRAMES = ("יש לצרף צילום {} לבקשה.", "יש לציין {} בטופס.")
LOOKALIKES = (("השיחה נקלעה ל{}.", "פלונטר"), ("יש לשמור על {} המתלוננת.", "אלמוניות"))


def _placeholder(rng: random.Random, near: bool) -> Frame:
    kind = rng.randrange(3)
    if near:
        return rng.choice(LOOKALIKES) if rng.random() < SMALL_SHARE else _pick(rng, ABBREVIATION_FRAMES, rng.choice(ABBREVIATIONS))
    if kind == 0:
        return _pick(rng, PLACEHOLDER_FRAMES, rng.choice(PLACEHOLDER_WORDS))
    if kind == 1:
        return _pick(rng, PLACEHOLDER_FRAMES[:3], "_" * rng.randint(3, 8))
    initials = f"{rng.choice(INITIAL_LETTERS)}.{rng.choice(INITIAL_LETTERS)}."
    return _pick(rng, PLACEHOLDER_FRAMES, initials) if initials not in ABBREVIATIONS else _placeholder(rng, near)


# Low-confidence, pattern-only numbers (build-plan.md Phase 1, last item). A near miss is the
# number of something else, as long as a positive, or a number too short beside the same words.
HEALTH_FRAMES = ("מספר החבר בקופת החולים: {}.", 'מס\' חבר בקופ"ח {}.', "הצד מבוטח בקופת החולים, מספר חבר {}.")
MILITARY_FRAMES = ("החייל, מ.א. {}, שוחרר מהשירות.", "מספר אישי: {}.", "בעל מספר אישי {} התייצב בבסיס.")
PASSPORT_FRAMES = ("דרכון מס' {} הוצג בדלפק.", "מספר הדרכון: {}.", "הצד הציג דרכון שמספרו {}.")
PASSPORT_LETTERS = ("AB", "CD", "XY", "PL")
SHORT_PATTERN = (2, 4)


def _pattern_only(rng: random.Random, near: bool, frames: tuple[str, ...], other: str, value: str) -> Frame:
    """Return a frame of a pattern-only kind with its value, or a near miss: other, or too short."""
    if not near:
        return _pick(rng, frames, value)
    return (other, value) if rng.random() < HALF else _pick(rng, frames, _num(rng, rng.randint(*SHORT_PATTERN), NONZERO))


def _health(rng: random.Random, near: bool) -> Frame:
    return _pattern_only(rng, near, HEALTH_FRAMES, "מספר ההפניה {} נשלח לקופת החולים.", _num(rng, rng.randint(6, 9), NONZERO))


def _military(rng: random.Random, near: bool) -> Frame:
    return _pattern_only(rng, near, MILITARY_FRAMES, "מספר הטופס {} צורף לבקשה.", _num(rng, 7, NONZERO))


def _passport(rng: random.Random, near: bool) -> Frame:
    value = _num(rng, 8, NONZERO) if rng.random() < HALF else rng.choice(PASSPORT_LETTERS) + _num(rng, 7)
    return _pattern_only(rng, near, PASSPORT_FRAMES, "מספר האשרה {} נרשם במערכת.", value)


# One maker per line of the scores: a type, or a type and a group after GROUP_MARK.
GROUP_MARK = ":"
UNTITLED = "PERSON:untitled"
MAKERS: dict[str, Maker] = {
    "IL_ID": _il_id,
    "COMPANY_NUMBER": lambda rng, near: _registered(rng, near, COMPANY_FRAMES, COMPANY_HEADS),
    "NONPROFIT_NUMBER": lambda rng, near: _registered(rng, near, NONPROFIT_FRAMES, NONPROFIT_HEADS),
    "IBAN": _iban_value, "BANK_ACCOUNT": _account, "CREDIT_CARD": _card, "PHONE": _phone, "EMAIL": _email, "URL": _url,
    "IP_ADDRESS": _ip, "IL_PLATE": _plate, "CASE_NUMBER": _case, "GUSH_HELKA": _parcel, "DATE": _date,
    "AMOUNT": _amount, "ADDRESS": _address, "PERSON": _person, UNTITLED: _untitled, "PLACEHOLDER": _placeholder,
    "HEALTH_FUND_ID": _health, "MILITARY_ID": _military, "PASSPORT_NUMBER": _passport,
}  # fmt: skip
TYPES = tuple(dict.fromkeys(line.partition(GROUP_MARK)[0] for line in MAKERS))
GROUPS = tuple(line.partition(GROUP_MARK)[2] for line in MAKERS if GROUP_MARK in line)
# What a word of a document is, for "stands once": a run of anything but spaces and punctuation.
WORD = re.compile(r"[^\s.,:;()]+")
ID_FAMILY = ("IL_ID", "COMPANY_NUMBER", "NONPROFIT_NUMBER")
GENRES = (
    ("כתב תביעה", "בכבוד רב,"), ("החלטה", "ניתנה היום בהיעדר הצדדים."), ("הסכם שכירות", "ולראיה באו הצדדים על החתום."),
    ("מכתב התראה", "בכבוד רב,"), ("פרוטוקול דיון", "המזכירות תמציא העתק לצדדים."), ("תצהיר", "הנני מצהיר כי זה שמי, זו חתימתי ותוכן תצהירי אמת."),
)  # fmt: skip
# Plain sentences, with no item: no digit, no trigger word, no name, no place.
FILLERS = (
    "הצדדים מסכימים כי ההסכם ייכנס לתוקף עם חתימתו.", "אין באמור כדי לגרוע מכל זכות אחרת העומדת לצדדים.",
    "בית המשפט שקל את טענות הצדדים בכובד ראש.", "הודעה זו נשלחת לפני נקיטת הליכים משפטיים.",
    "כל שינוי בהסכם ייעשה בכתב בלבד.", "הבקשה נבחנה על פי החומר שהונח לפני בית המשפט.", "אין צו להוצאות.",
    "המסמכים המקוריים יוחזרו למגישם.", "יש לפעול בהתאם להוראות הדין.", "הצדדים ישמרו על סודיות המידע.",
)  # fmt: skip
Planned = tuple[str, bool, str, str]


def _marked(rng: random.Random, frame: str, value: str) -> Frame:
    """Return a frame and its value with the marks ASCII or, one time in two, Hebrew."""
    if rng.random() < HALF:
        return frame.translate(HEBREW_MARK_TABLE), value.translate(HEBREW_MARK_TABLE)
    return frame, value


def _draw(rng: random.Random, line: str, near: bool) -> Frame:
    """Return a frame and value of a line of the scores, its marks ASCII or Hebrew.

    An ID-family near miss with a group of digits that passes the check on its own is drawn again.
    """
    frame, value = MAKERS[line](rng, near)
    while near and line in ID_FAMILY and _part_passes(value):
        frame, value = MAKERS[line](rng, near)
    return _marked(rng, frame, value)


def _alone(rng: random.Random, planned: list[Planned]) -> list[Planned]:
    """Return a document's plan with each untitled name drawn again until each of its words stands once.

    Why: build-plan.md section 7 asks for a name that stands once in its document; a word of it
    found again in another sentence, or twice in the name, would make it no such name.
    """
    planned = list(planned)
    for at, (line, positive, frame, value) in enumerate(planned):
        if line != UNTITLED or not positive:
            continue
        rest = [word for other, (_, _, text, filled) in enumerate(planned) if other != at for word in WORD.findall(text.replace("{}", filled))]
        while any(word in rest for word in value.split()) or len(set(value.split())) < len(value.split()):
            value = _marked(rng, frame, _untitled(rng, False)[1])[1]
        planned[at] = (line, positive, frame, value)
    return planned


def _document(rng: random.Random, index: int, planned: list[Planned]) -> tuple[str, list[Item], list[Item]]:
    """Return one document's text with its key items and near misses, offsets counted as it is joined."""
    title, closing = rng.choice(GENRES)
    parts, length = [title + "\n"], len(title) + 1
    key: list[Item] = []
    near: list[Item] = []
    for line, positive, frame, value in _alone(rng, planned):
        before, after = frame.split("{}")
        kind, _, group = line.partition(GROUP_MARK)
        item = Item(index, length + len(before), length + len(before) + len(value), kind, value, group)
        (key if positive else near).append(item)
        sentence = before + value + after + rng.choice((" ", "\n"))
        if rng.random() < FILLER_SHARE:
            sentence += rng.choice(FILLERS) + rng.choice((" ", "\n"))
        parts.append(sentence)
        length += len(sentence)
    parts.append(closing + "\n")
    return "".join(parts), key, near


def build(seed: int = SEED) -> Batch:
    """Build the held-out batch of a seed in memory.

    Why: the documents are made fresh each run and thrown away (Achia, 2026-11-26, issue 283),
    so this is the only place the batch exists; the seed fixes it.

    Contract: seed, any int; SEED is the batch of the gate. Returns the Batch: PER_SIDE positives
    and PER_SIDE near misses of every line of MAKERS (a type of TYPES, or a group of one),
    shuffled into documents of
    ITEMS_PER_DOCUMENT items each (the last one may hold fewer). The same seed gives the same
    Batch. Raises nothing. Writes nothing to disk and logs nothing.

    Known limits: see the module docstring.
    """
    rng = random.Random(seed)  # noqa: S311 seeded on purpose, so the batch is the same on every run
    planned: list[Planned] = [
        (line, positive, *_draw(rng, line, not positive)) for line in MAKERS for positive in (True, False) for _ in range(PER_SIDE)
    ]
    rng.shuffle(planned)
    documents: list[str] = []
    key: list[Item] = []
    near: list[Item] = []
    for index, start in enumerate(range(0, len(planned), ITEMS_PER_DOCUMENT)):
        text, found, missed = _document(rng, index, planned[start : start + ITEMS_PER_DOCUMENT])
        documents.append(text)
        key += found
        near += missed
    return Batch(tuple(documents), tuple(key), tuple(near))
