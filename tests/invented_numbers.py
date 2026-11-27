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
