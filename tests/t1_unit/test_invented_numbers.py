"""Test matrix for tests/invented_numbers.py: invented checksum-valid numbers, made when the tests run.

Why: the numbers of every checksum detector's tests come from this helper (Achia, 2026-11-27,
issue #32, "Make them fresh too (Recommended)"); a wrong number there would make a detector's
tests ask less than they say, and no file holds the numbers to look at.

Test matrix:

digits, take, pick:
  D1 the same seed and name                         the same digits on every call
  D2 another name, another seed                     other digits
  D3 every item                                     one ASCII digit
  D4 take(n)                                        n digits; pick: one of the choices
complete:
  K1 a stem                                         the stem and the first digit that makes it valid
  K2 no digit makes it valid                        ValueError, the stem not in the message
israeli_id_checksum_ok (build-plan.md Phase 1's, copied):
  C1 trivial numbers that pass (000000000, 123456782, eight digits padded to 012345674)    True
  C2 another check digit; ten digits; a letter; the empty string    False
israeli_ids, ISRAELI_IDS:
  I1 each list: its length, nine ASCII digits, the checksum passed (near: failed), none trivial
  I2 valid: distinct, none starting with 5; near[i]: valid[i]'s eight digits, another check digit
  I3 zeros, two_zeros: one and two leading zeros; cut, nested: their first eight digits padded
     fail and pass the checksum
  I4 company 51-54, nonprofit 58, landline 0 and an area code of 0[23489], case a month and a
     year of 2015-2025
  I5 the same seed twice                            equal; another seed: other numbers
fill, shaped:
  F1 no slot; a literal brace doubled               the text as it is, no span
  F2 a slot with no shape                           the number whole, its span
  F3 a shape with separators, "x", "+"; fewer marks than digits    written as the shape says
  F4 two slots                                      both spans, in order, in code points
  F5 a conversion; a shape longer than the number   ValueError
  F6 a name or an index that names no number        KeyError, IndexError
read_cases:
  R1 a fixture file                                 positives with the spans of their "found"
                                                    slots, negatives with none, in file order

Not applicable: Hebrew axes beyond a Hebrew template (the helper writes digits).
"""

import json
from itertools import islice
from pathlib import Path

import pytest

from tests import invented_numbers as inv
from tests.invented_numbers import ISRAELI_IDS, israeli_id_checksum_ok

FIELDS = ("valid", "near", "zeros", "two_zeros", "cut", "nested", "company", "nonprofit", "landline")
LENGTHS = {"valid": 60, "near": 30, "zeros": 3, "two_zeros": 1, "cut": 1, "nested": 1, "company": 6, "nonprofit": 6, "landline": 6}


def first(seed: int, name: str, length: int = 200) -> str:
    """Return the first digits of one stream."""
    return "".join(islice(inv.digits(seed, name), length))


def test_d1_the_same_stream_each_time() -> None:
    assert first(inv.SEED, "valid") == first(inv.SEED, "valid")


def test_d2_another_name_or_seed() -> None:
    assert first(inv.SEED, "valid") != first(inv.SEED, "near")
    assert first(inv.SEED, "valid") != first(inv.SEED + 1, "valid")


def test_d3_every_item_is_one_digit() -> None:
    assert all(len(item) == 1 and item in "0123456789" for item in islice(inv.digits(inv.SEED, "valid"), 5000))


def test_d4_take_and_pick() -> None:
    stream = inv.digits(inv.SEED, "take")
    assert len(inv.take(stream, 7)) == 7
    assert all(inv.pick(stream, ("a", "b", "c")) in ("a", "b", "c") for _ in range(50))


def test_k1_complete() -> None:
    stem = ISRAELI_IDS.valid[0][:8]
    number = inv.complete(stem, israeli_id_checksum_ok)
    assert number == ISRAELI_IDS.valid[0]
    assert not any(israeli_id_checksum_ok(stem + d) for d in "0123456789" if d < number[-1])


def test_k2_no_digit_completes() -> None:
    with pytest.raises(ValueError, match="no check digit") as raised:
        inv.complete("13579", lambda _: False)
    assert "13579" not in str(raised.value)


@pytest.mark.parametrize("digits", ["000000000", "123456782", "12345674"])
def test_c1_trivial_numbers_pass(digits: str) -> None:
    assert israeli_id_checksum_ok(digits)


@pytest.mark.parametrize("digits", ["123456783", "1234567820", "12345678a", ""])
def test_c2_these_fail(digits: str) -> None:
    assert not israeli_id_checksum_ok(digits)


@pytest.mark.parametrize("field", FIELDS)
def test_i1_each_list(field: str) -> None:
    numbers = getattr(ISRAELI_IDS, field)
    assert len(numbers) == LENGTHS[field]
    assert all(len(n) == 9 and n.isascii() and n.isdigit() for n in numbers)
    assert all(israeli_id_checksum_ok(n) is (field != "near") for n in numbers)
    assert not any(inv.is_trivial(n) for n in numbers)


def test_i2_valid_and_near() -> None:
    assert len(set(ISRAELI_IDS.valid)) == 60 and not any(n.startswith("5") for n in ISRAELI_IDS.valid)
    assert all(n[:8] == v[:8] and n[8] != v[8] for n, v in zip(ISRAELI_IDS.near, ISRAELI_IDS.valid, strict=False))


def test_i3_zeros_cut_and_nested() -> None:
    assert all(n[0] == "0" and n[1] != "0" for n in ISRAELI_IDS.zeros)
    assert all(n[:2] == "00" and n[2] != "0" for n in ISRAELI_IDS.two_zeros)
    assert not israeli_id_checksum_ok(ISRAELI_IDS.cut[0][:8])
    assert israeli_id_checksum_ok(ISRAELI_IDS.nested[0][:8])


def test_i4_the_other_numbers() -> None:
    assert all(n[:2] in ("51", "52", "53", "54") for n in ISRAELI_IDS.company)
    assert all(n[:2] == "58" for n in ISRAELI_IDS.nonprofit)
    assert all(n[0] == "0" and n[1] in "23489" for n in ISRAELI_IDS.landline)
    case = ISRAELI_IDS.case
    assert israeli_id_checksum_ok(case) and not inv.is_trivial(case) and case[0] != "5"
    assert 1 <= int(case[5:7]) <= 12 and 15 <= int(case[7:]) <= 25


def test_i5_the_seed() -> None:
    assert inv.israeli_ids(inv.SEED) == ISRAELI_IDS
    assert set(inv.israeli_ids(inv.SEED + 1).valid).isdisjoint(ISRAELI_IDS.valid[:5])


def test_f1_no_slot() -> None:
    assert inv.fill("אין כאן מספר {{x}}", ISRAELI_IDS) == ("אין כאן מספר {x}", [])


def test_f2_a_slot_whole() -> None:
    text, spans = inv.fill("ת.ז. {valid[0]}", ISRAELI_IDS)
    assert text == "ת.ז. " + ISRAELI_IDS.valid[0] and spans == [(5, 14)]


def test_f3_shapes() -> None:
    v, z = ISRAELI_IDS.valid[1], ISRAELI_IDS.zeros[0]
    assert inv.shaped(v, "ddd-ddd‑ddd") == f"{v[:3]}-{v[3:6]}‑{v[6:]}"
    assert inv.shaped(z, "xdddddddd") == z[1:]
    assert inv.shaped(z, "xddddddd+") == z[1:8] + str((int(z[8]) + 1) % 10)
    assert inv.shaped(v, "dddddddd") == v[:8]
    assert inv.fill("{case:ddddd-dd-dd}", ISRAELI_IDS)[0] == f"{ISRAELI_IDS.case[:5]}-{ISRAELI_IDS.case[5:7]}-{ISRAELI_IDS.case[7:]}"


def test_f4_two_slots() -> None:
    text, spans = inv.fill("שָׁלוֹם {valid[2]:ddd ddd ddd} ו-{near[0]}.", ISRAELI_IDS)
    assert [text[start:end] for start, end in spans] == [" ".join([ISRAELI_IDS.valid[2][i : i + 3] for i in (0, 3, 6)]), ISRAELI_IDS.near[0]]
    assert spans[0][0] == len("שָׁלוֹם ")


@pytest.mark.parametrize("template", ["{valid[0]!r}", "{valid[0]:dddddddddd}"])
def test_f5_a_slot_refused(template: str) -> None:
    with pytest.raises(ValueError):
        inv.fill(template, ISRAELI_IDS)


@pytest.mark.parametrize(("template", "error"), [("{passport[0]}", KeyError), ("{zeros[3]}", IndexError)])
def test_f6_no_such_number(template: str, error: type[Exception]) -> None:
    with pytest.raises(error):
        inv.fill(template, ISRAELI_IDS)


def test_r1_read_cases(tmp_path: Path) -> None:
    path = tmp_path / "cases.json"
    data = {
        "positives": [{"text": "ת.ז. {valid[0]}, {zeros[0]:xdddddddd}", "found": [0]}, {"text": "{near[1]} ו-{valid[1]}", "found": [1]}],
        "negatives": [{"text": "דרכון {valid[2]}"}, {"text": "אין מספר"}],
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    positives, negatives = inv.read_cases(path, ISRAELI_IDS)
    assert positives == [
        (f"ת.ז. {ISRAELI_IDS.valid[0]}, {ISRAELI_IDS.zeros[0][1:]}", [(5, 14)]),
        (f"{ISRAELI_IDS.near[1]} ו-{ISRAELI_IDS.valid[1]}", [(12, 21)]),
    ]
    assert negatives == [(f"דרכון {ISRAELI_IDS.valid[2]}", []), ("אין מספר", [])]
