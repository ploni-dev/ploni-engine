"""Invented numbers that pass a checksum, made from a fixed seed when the tests run.

Why: a number that passes a checksum may be a real person's, and a file that holds it reaches a
public repository. Achia, 2026-11-27, issue #32, "Make them fresh too (Recommended)": "The tests
make their ID numbers from a fixed seed when they run; the files hold only the Hebrew around
them, with a slot for each number. ... Every later detector of a checksum type (cards, bank,
companies) works the same way." Made here, such a number lives only in a test run's memory.

Contract:
- `digits(seed, name)`: an endless stream of decimal digits, the same for the same seed and name
  on every machine and Python version: SHA-256 of "<seed>:<name>:<counter>", counter 0, 1, ...,
  each byte below DIGIT_BYTES taken modulo 10. One stream per name, so a list added later moves
  no other list's numbers.
- `complete(stem, valid)`: the stem with the first check digit, "0" to "9", for which `valid` is
  true. Raises ValueError when no digit is; the message holds no digit of the stem.
- `israeli_id_checksum_ok(digits)`: build-plan.md Phase 1's check, as written there. It is a copy
  apart from ploni/detect/deterministic/israeli_id.py, so that the numbers do not come from the
  code under test.
- `israeli_ids(seed)`: an `IsraeliIds` (its fields say what each list holds). ISRAELI_IDS is
  `israeli_ids(SEED)`, made once when this module is imported.
- `luhn_ok(digits)`: the Luhn check of a card number (issue #35), a copy apart from
  ploni/detect/deterministic/credit_card.py, as `israeli_id_checksum_ok` is.
- `cards(seed)`: a `Cards` (its fields say what each list holds), each list from its own stream
  of the same seed. CARDS is `cards(SEED)`.
- `phones(seed)`: a `Phones` (its fields say what each list holds), Israeli phone numbers of the
  prefixes and lengths of build-plan.md Phase 1, "Israeli phone" (issue #36). A phone has no check
  digit: these are made here too, so that no file holds a phone number (Achia, 2026-11-27, #32).
  PHONES is `phones(SEED)`. A number from abroad holds its "+" or "00" as written, so that a
  slot's span takes it in; the shape's "d" writes it as it is.
- `fill(template, numbers)`: (text, spans). A slot is written as a field of str.format: `{name}`
  or `{name[i]}`, a field of `numbers` (a dataclass), optionally `{name[i]:shape}`. The shape
  writes the number: "d" writes its next digit, "x" skips one, "+" writes the next digit plus one,
  modulo 10; any other character is written as it is; digits the shape does not reach are not
  written. With no shape the number is written whole. spans: each slot's place in the text,
  (start, end) in code points, in the order of the slots. Raises ValueError for a slot with a
  conversion (`!r`) or a shape asking for more digits than the number has; KeyError,
  AttributeError or IndexError for a slot that names no number.
- `read_cases(path, numbers)`: the cases of a fixture file, filled: (positives, negatives), each a
  list of (text, spans). The file is JSON: "positives", each {"text", "found"}, "found" listing
  the slots (by their order in the text, from 0) the detector must find; "negatives", each
  {"text"}, whose spans are [].

Known limits: trivial sequences (nine equal digits, eight running up or down by one, such as
000000000, 123456782, 012345674) pass the checksum and stay written as literals in the tests:
they are what the tests prove refused, and no person holds one. Numbers that fail the checksum
stay written too. A literal brace in a template is doubled ({{, }}), as in str.format.
"""

import dataclasses
import hashlib
import json
import string
from collections.abc import Callable, Iterator, Sequence
from itertools import count, islice
from pathlib import Path

# Any fixed number: the issue of the first checksum detector, #32.
SEED = 32
# The largest multiple of 10 not above 256: bytes from it up are dropped, so each digit is as likely.
DIGIT_BYTES = 250
# build-plan.md Phase 1: "Nine digits, last is a check digit".
ID_LENGTH = 9
DECIMAL = "0123456789"
# build-plan.md Phase 1: companies start with 5, so a person's ID is made with any other first digit.
PERSON_FIRST = DECIMAL.replace("5", "")
# build-plan.md Phase 1, "Court case numbers": NNNNN-MM-YY. The months, and the years drawn (2015-2025).
MONTHS = 12
YEARS = range(15, 26)

Case = tuple[str, list[tuple[int, int]]]


def digits(seed: int, name: str) -> Iterator[str]:
    """Yield the decimal digits of one named stream, the same on every run."""
    for counter in count():
        block = hashlib.sha256(f"{seed}:{name}:{counter}".encode()).digest()
        yield from (str(byte % 10) for byte in block if byte < DIGIT_BYTES)


def take(stream: Iterator[str], length: int) -> str:
    """Return the next `length` digits of a stream."""
    return "".join(islice(stream, length))


def pick(stream: Iterator[str], choices: Sequence[str]) -> str:
    """Return one of `choices`, by the next two digits of a stream."""
    return choices[int(take(stream, 2)) % len(choices)]


def complete(stem: str, valid: Callable[[str], bool]) -> str:
    """Return the stem with the first check digit that makes it valid."""
    for check in DECIMAL:
        if valid(stem + check):
            return stem + check
    raise ValueError("no check digit makes the stem valid")


def israeli_id_checksum_ok(digits: str) -> bool:
    """Say whether a string of digits passes the Israeli ID check digit (build-plan.md Phase 1, as written)."""
    if len(digits) > 9 or not digits.isdigit():
        return False
    d = digits.zfill(9)
    total = 0
    for i, ch in enumerate(d):
        n = int(ch) * (1 if i % 2 == 0 else 2)
        total += n if n < 10 else n - 9
    return total % 10 == 0


def is_trivial(number: str) -> bool:
    """Say whether nine digits are all one digit, or their first eight run up or down by one."""
    stem = number[: ID_LENGTH - 1]
    steps = {int(b) - int(a) for a, b in zip(stem, stem[1:], strict=False)}
    return len(set(number)) == 1 or steps in ({1}, {-1})


def invent_ids(stream: Iterator[str], how_many: int, firsts: tuple[str, ...], keep: Callable[[str], bool]) -> tuple[str, ...]:
    """Make distinct valid nine-digit numbers: one of `firsts`, digits of the stream to eight, the check digit.

    Contract: each number starts with one of `firsts` (picked by the stream), passes
    `israeli_id_checksum_ok`, is not trivial, and `keep` holds for it; `how_many` of them, in the
    order made.
    """
    made: list[str] = []
    while len(made) < how_many:
        first = pick(stream, firsts)
        number = complete(first + take(stream, ID_LENGTH - 1 - len(first)), israeli_id_checksum_ok)
        if keep(number) and not is_trivial(number) and number not in made:
            made.append(number)
    return tuple(made)


def near_misses(stream: Iterator[str], numbers: tuple[str, ...]) -> tuple[str, ...]:
    """Return each number with another check digit, moved up by one to nine (by the stream)."""
    return tuple(n[:-1] + str((int(n[-1]) + 1 + int(pick(stream, "012345678"))) % 10) for n in numbers)


def case_number(stream: Iterator[str]) -> str:
    """Make a valid nine-digit number in the shape of a case number: five digits, a month, a year."""
    while True:
        stem = pick(stream, PERSON_FIRST) + take(stream, 4) + f"{1 + int(take(stream, 2)) % MONTHS:02d}" + pick(stream, "12")
        number = complete(stem, israeli_id_checksum_ok)
        if int(number[-2:]) in YEARS and not is_trivial(number):
            return number


@dataclasses.dataclass(frozen=True)
class IsraeliIds:
    """Invented nine-digit numbers that pass the Israeli ID checksum, but `near`, which none does.

    Why: the cases of the Israeli ID detector, each kind a list a fixture's slot can name.

    Contract: every number is nine ASCII digits and not trivial. valid: 60 distinct, not starting
    with 5. near: 30, near[i] the eight digits of valid[i] and another check digit. zeros: 3
    starting with one 0 (so their last eight, padded, are the same ID). two_zeros: 1 starting
    with two 0s. cut: 1 whose first eight digits, padded, fail the checksum. nested: 1 whose first
    eight digits, padded, pass it too. company: 30 starting with 51 to 54; nonprofit: 30 starting
    with 58 (build-plan.md Phase 1). landline: 6, a 0, an area code of 0[23489] and seven digits
    (build-plan.md Phase 1, "Israeli phone"). case: one, five digits, a month and a year of
    2015-2025 (NNNNN-MM-YY).

    Known limits: the numbers are invented, not checked against any register.
    """

    valid: tuple[str, ...]
    near: tuple[str, ...]
    zeros: tuple[str, ...]
    two_zeros: tuple[str, ...]
    cut: tuple[str, ...]
    nested: tuple[str, ...]
    company: tuple[str, ...]
    nonprofit: tuple[str, ...]
    landline: tuple[str, ...]
    case: str


def israeli_ids(seed: int) -> IsraeliIds:
    """Make the invented Israeli ID numbers of one seed, each list from its own stream."""
    valid = invent_ids(digits(seed, "valid"), 60, tuple(PERSON_FIRST), lambda _: True)
    return IsraeliIds(
        valid=valid,
        near=near_misses(digits(seed, "near"), valid[:30]),
        zeros=invent_ids(digits(seed, "zeros"), 3, tuple(f"0{d}" for d in "123456789"), lambda _: True),
        two_zeros=invent_ids(digits(seed, "two_zeros"), 1, tuple(f"00{d}" for d in "123456789"), lambda _: True),
        cut=invent_ids(digits(seed, "cut"), 1, tuple(PERSON_FIRST), lambda n: not israeli_id_checksum_ok(n[:-1])),
        nested=invent_ids(digits(seed, "nested"), 1, tuple(PERSON_FIRST), lambda n: israeli_id_checksum_ok(n[:-1])),
        company=invent_ids(digits(seed, "company"), 30, ("51", "52", "53", "54"), lambda _: True),
        nonprofit=invent_ids(digits(seed, "nonprofit"), 30, ("58",), lambda _: True),
        landline=invent_ids(digits(seed, "landline"), 6, tuple(f"0{d}" for d in "23489"), lambda _: True),
        case=case_number(digits(seed, "case")),
    )


ISRAELI_IDS = israeli_ids(SEED)

# The issuer ranges of the card brands, as (low, high) prefixes, written apart from the detector
# (ploni/detect/deterministic/credit_card.py names their source); NO_BRAND starts with no brand's.
VISA = ((4, 4),)
MASTERCARD = ((51, 55), (2221, 2720))
AMEX = ((34, 34), (37, 37))
DINERS = ((36, 36),)
DISCOVER = ((6011, 6011), (644, 649), (65, 65))
JCB = ((3528, 3589),)
UNIONPAY = ((62, 62),)
NO_BRAND = ((1, 1), (7, 9))
# The usual length of a card number; Visa also issues 13 and 19, American Express 15, Diners 14.
CARD_LENGTH = 16


def luhn_ok(digits: str) -> bool:
    """Say whether ASCII digits pass the Luhn check: from the right, every second digit doubled, digits summed, a multiple of 10."""
    if not (digits.isascii() and digits.isdigit()):
        return False
    doubled = [int(ch) * (2 if i % 2 else 1) for i, ch in enumerate(reversed(digits))]
    return sum(n - 9 if n > 9 else n for n in doubled) % 10 == 0


def invent_cards(stream: Iterator[str], how_many: int, ranges: tuple[tuple[int, int], ...], length: int) -> tuple[str, ...]:
    """Make distinct card numbers of `length` digits: a prefix of one of `ranges`, digits of the stream, the Luhn check digit."""
    made: list[str] = []
    while len(made) < how_many:
        low, high = ranges[int(take(stream, 2)) % len(ranges)]
        prefix = str(low + int(take(stream, len(str(high)))) % (high - low + 1))
        number = complete(prefix + take(stream, length - 1 - len(prefix)), luhn_ok)
        if number not in made:
            made.append(number)
    return tuple(made)


@dataclasses.dataclass(frozen=True)
class Cards:
    """Invented card numbers that pass the Luhn check, but `near`, which none does.

    Why: the cases of the credit card detector (issue #35), each kind a list a fixture's slot can name.

    Contract: every number is ASCII digits, distinct within its list. visa: 16, of 16 digits,
    starting with 4; visa13: 2 of 13; visa19: 2 of 19. mastercard: 12 of 16, 51-55 or 2221-2720.
    amex: 8 of 15, 34 or 37. diners: 4 of 14, 36. discover: 4 of 16, 6011, 644-649 or 65. jcb: 3
    of 16, 3528-3589. unionpay: 3 of 16, 62. near: 20 of 16, near[i] the first fifteen digits of
    visa[i] (i < 10) or of mastercard[i - 10], and another check digit. nobrand: 6 of 16, starting
    with 1, 7, 8 or 9. wrong_length: a Visa prefix at 15, 14, 17, 18, 12 and 20 digits, an
    American Express prefix at 16, a Mastercard prefix at 15.

    Known limits: the numbers are invented, not checked against any issuer.
    """

    visa: tuple[str, ...]
    visa13: tuple[str, ...]
    visa19: tuple[str, ...]
    mastercard: tuple[str, ...]
    amex: tuple[str, ...]
    diners: tuple[str, ...]
    discover: tuple[str, ...]
    jcb: tuple[str, ...]
    unionpay: tuple[str, ...]
    near: tuple[str, ...]
    nobrand: tuple[str, ...]
    wrong_length: tuple[str, ...]


def cards(seed: int) -> Cards:
    """Make the invented card numbers of one seed, each list from its own stream."""
    visa = invent_cards(digits(seed, "card_visa"), 16, VISA, CARD_LENGTH)
    mastercard = invent_cards(digits(seed, "card_mastercard"), 12, MASTERCARD, CARD_LENGTH)
    wrong = digits(seed, "card_wrong_length")
    return Cards(
        visa=visa,
        visa13=invent_cards(digits(seed, "card_visa13"), 2, VISA, 13),
        visa19=invent_cards(digits(seed, "card_visa19"), 2, VISA, 19),
        mastercard=mastercard,
        amex=invent_cards(digits(seed, "card_amex"), 8, AMEX, 15),
        diners=invent_cards(digits(seed, "card_diners"), 4, DINERS, 14),
        discover=invent_cards(digits(seed, "card_discover"), 4, DISCOVER, CARD_LENGTH),
        jcb=invent_cards(digits(seed, "card_jcb"), 3, JCB, CARD_LENGTH),
        unionpay=invent_cards(digits(seed, "card_unionpay"), 3, UNIONPAY, CARD_LENGTH),
        near=near_misses(digits(seed, "card_near"), visa[:10] + mastercard[:10]),
        nobrand=invent_cards(digits(seed, "card_nobrand"), 6, NO_BRAND, CARD_LENGTH),
        wrong_length=tuple(
            invent_cards(wrong, 1, ranges, length)[0]
            for ranges, length in ((VISA, 15), (VISA, 14), (VISA, 17), (VISA, 18), (VISA, 12), (VISA, 20), (AMEX, 16), (MASTERCARD, 15))
        ),
    )


CARDS = cards(SEED)

# The prefixes of the Israeli numbering plan of the Ministry of Communications, as build-plan.md
# Phase 1, "Israeli phone", names them: "Landline `0[23489]`, mobile `05\d`, VoIP `07[2-9]`, `+972`
# forms, `*NNNN` service numbers"; after the 0 and its area code, SUBSCRIBER digits. The 1-800 and
# 1-700 numbers are 1, 800 or 700, and SERVICE digits. Written apart from ploni/detect/deterministic/phone.py.
LANDLINE_AREAS = tuple(f"0{d}" for d in "23489")
MOBILE_AREAS = tuple(f"05{d}" for d in DECIMAL)
VOIP_AREAS = tuple(f"07{d}" for d in "23456789")
SERVICE_PREFIXES = ("1800", "1700")
SUBSCRIBER = 7
SERVICE = 6
SHORT = 4
# Prefixes no line of the plan above names: 01 and 06, and 05 and 07 as a landline's two digits.
WRONG_AREAS_LONG = tuple(f"0{a}{d}" for a in "16" for d in DECIMAL)
WRONG_AREAS_SHORT = ("01", "05", "06", "07")
# Abroad, the plan's +972 forms write the country code in place of the leading 0.
COUNTRY = "972"


def invent_phones(stream: Iterator[str], how_many: int, prefixes: tuple[str, ...], length: int) -> tuple[str, ...]:
    """Make distinct numbers: one of `prefixes` (picked by the stream), then `length` digits of the stream."""
    made: list[str] = []
    while len(made) < how_many:
        number = pick(stream, prefixes) + take(stream, length)
        if number not in made:
            made.append(number)
    return tuple(made)


def abroad(numbers: tuple[str, ...], lead: str) -> tuple[str, ...]:
    """Write national numbers as from abroad: `lead` and the country code in place of the leading 0."""
    return tuple(lead + COUNTRY + n[1:] for n in numbers)


@dataclasses.dataclass(frozen=True)
class Phones:
    """Invented Israeli phone numbers of the plan's prefixes and lengths, and near misses that are none.

    Why: the cases of the phone detector (issue #36), each kind a list a fixture's slot can name;
    a phone has no check digit, so a number of the right prefix and length is a phone's.

    Contract: each list is distinct. mobile: 12, 05X and seven digits (10). landline: 10, two of
    each area code 0[23489], and seven digits (9). voip: 6, 07[2-9] and seven (10). service: 4,
    1800 or 1700 and six (10). short: 4, a star and four digits. abroad_mobile: 8, "+972" and a
    mobile without its 0; abroad_landline: 5, one per area code; abroad_voip: 2; double_zero: 4,
    "00972" and a mobile without its 0. kept_zero: 4, "+972" and a national number with its 0 kept
    (two landlines, a mobile, a VoIP number; Achia, 2026-11-27, #36: "Yes, find them
    (Recommended)"). wrong_area: 8, 01X or 06X and seven digits (10) and 4,
    01, 05, 06 or 07 and seven (9). short_line: 2 mobiles and 2 landlines a digit short; long_line:
    2 and 2 a digit long.

    Known limits: the numbers are invented, not checked against any operator's list: one may be
    someone's.
    """

    mobile: tuple[str, ...]
    landline: tuple[str, ...]
    voip: tuple[str, ...]
    service: tuple[str, ...]
    short: tuple[str, ...]
    abroad_mobile: tuple[str, ...]
    abroad_landline: tuple[str, ...]
    abroad_voip: tuple[str, ...]
    double_zero: tuple[str, ...]
    kept_zero: tuple[str, ...]
    wrong_area: tuple[str, ...]
    short_line: tuple[str, ...]
    long_line: tuple[str, ...]


def phones(seed: int) -> Phones:
    """Make the invented phone numbers of one seed, each list from its own stream."""
    by_area = digits(seed, "phone_landline")
    return Phones(
        mobile=invent_phones(digits(seed, "phone_mobile"), 12, MOBILE_AREAS, SUBSCRIBER),
        landline=tuple(n for area in LANDLINE_AREAS for n in invent_phones(by_area, 2, (area,), SUBSCRIBER)),
        voip=invent_phones(digits(seed, "phone_voip"), 6, VOIP_AREAS, SUBSCRIBER),
        service=invent_phones(digits(seed, "phone_service"), 4, SERVICE_PREFIXES, SERVICE),
        short=tuple("*" + n for n in invent_phones(digits(seed, "phone_short"), 4, ("",), SHORT)),
        abroad_mobile=abroad(invent_phones(digits(seed, "phone_abroad_mobile"), 8, MOBILE_AREAS, SUBSCRIBER), "+"),
        abroad_landline=abroad(tuple(invent_phones(digits(seed, "phone_abroad_landline"), 1, (a,), SUBSCRIBER)[0] for a in LANDLINE_AREAS), "+"),
        abroad_voip=abroad(invent_phones(digits(seed, "phone_abroad_voip"), 2, VOIP_AREAS, SUBSCRIBER), "+"),
        double_zero=abroad(invent_phones(digits(seed, "phone_double_zero"), 4, MOBILE_AREAS, SUBSCRIBER), "00"),
        kept_zero=tuple(
            "+" + COUNTRY + n
            for n in invent_phones(digits(seed, "phone_kept_zero"), 2, LANDLINE_AREAS, SUBSCRIBER)
            + invent_phones(digits(seed, "phone_kept_zero_mobile"), 1, MOBILE_AREAS, SUBSCRIBER)
            + invent_phones(digits(seed, "phone_kept_zero_voip"), 1, VOIP_AREAS, SUBSCRIBER)
        ),
        wrong_area=invent_phones(digits(seed, "phone_wrong_long"), 8, WRONG_AREAS_LONG, SUBSCRIBER)
        + invent_phones(digits(seed, "phone_wrong_short"), 4, WRONG_AREAS_SHORT, SUBSCRIBER),
        short_line=invent_phones(digits(seed, "phone_short_line"), 2, MOBILE_AREAS, SUBSCRIBER - 1)
        + invent_phones(digits(seed, "phone_short_line_landline"), 2, LANDLINE_AREAS, SUBSCRIBER - 1),
        long_line=invent_phones(digits(seed, "phone_long_line"), 2, MOBILE_AREAS, SUBSCRIBER + 1)
        + invent_phones(digits(seed, "phone_long_line_landline"), 2, LANDLINE_AREAS, SUBSCRIBER + 1),
    )


PHONES = phones(SEED)


def shaped(number: str, shape: str) -> str:
    """Write a number in a slot's shape: "d" a digit, "x" a skipped one, "+" one plus one, others as they are."""
    if not shape:
        return number
    if sum(shape.count(mark) for mark in "dx+") > len(number):
        raise ValueError("the shape asks for more digits than the number has")
    rest = iter(number)
    written = []
    for mark in shape:
        if mark == "x":
            next(rest)
        elif mark in "d+":
            digit = next(rest)
            written.append(digit if mark == "d" else str((int(digit) + 1) % 10))
        else:
            written.append(mark)
    return "".join(written)


def fill(template: str, numbers: object) -> tuple[str, list[tuple[int, int]]]:
    """Write the numbers into a template's slots, keeping each slot's place."""
    formatter = string.Formatter()
    fields = vars(numbers)
    pieces: list[str] = []
    spans: list[tuple[int, int]] = []
    at = 0
    for literal, name, shape, conversion in formatter.parse(template):
        pieces.append(literal)
        at += len(literal)
        if name is None:
            continue
        if conversion:
            raise ValueError("a slot takes no conversion")
        number, _ = formatter.get_field(name, (), fields)
        written = shaped(number, shape or "")
        pieces.append(written)
        spans.append((at, at + len(written)))
        at += len(written)
    return "".join(pieces), spans


def read_cases(path: Path, numbers: object) -> tuple[list[Case], list[Case]]:
    """Read a fixture file's cases, their numbers filled in."""
    data = json.loads(path.read_text(encoding="utf-8"))
    positives: list[Case] = []
    for case in data["positives"]:
        text, spans = fill(case["text"], numbers)
        positives.append((text, [spans[k] for k in case["found"]]))
    negatives: list[Case] = [(fill(case["text"], numbers)[0], []) for case in data["negatives"]]
    return positives, negatives
