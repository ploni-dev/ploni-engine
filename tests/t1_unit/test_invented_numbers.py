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
luhn_ok (the card check digit, copied apart from ploni/detect/deterministic/credit_card.py; issue #35):
  L1 a number completed by `complete(stem, luhn_ok)`; sixteen zeros (trivial)    True
  L2 another check digit; the empty string; a letter; Arabic-Indic digits    False
  L3 the plan's ID check and Luhn agree on nine digits (the ID check is Luhn on nine)
cards, CARDS (issue #35):
  CD1 each list: its length, its numbers' number of digits, ASCII digits, distinct, Luhn passed
      (near: failed)
  CD2 the brand prefixes: visa 4; mastercard 51-55 and 2221-2720, both kinds; amex 34, 37;
      diners 36; discover 6011, 644-649, 65; jcb 3528-3589; unionpay 62; nobrand 1, 7, 8, 9
  CD3 near[i]: the first fifteen digits of visa[i] (i < 10) or mastercard[i - 10], another
      check digit
  CD4 wrong_length: a visa prefix at 15, 14, 17, 18, 12 and 20 digits, an amex prefix at 16,
      a mastercard prefix at 15
  CD5 the same seed twice                           equal; another seed: other numbers
  CD6 fill writes a card into a slot of a shape     the shape's groups, its span

Not applicable: Hebrew axes beyond a Hebrew template (the helper writes digits).
"""

import json
from itertools import islice
from pathlib import Path

import pytest

from tests import invented_numbers as inv
from tests.invented_numbers import CARDS, ISRAELI_IDS, israeli_id_checksum_ok, luhn_ok

FIELDS = ("valid", "near", "zeros", "two_zeros", "cut", "nested", "company", "nonprofit", "landline")
LENGTHS = {"valid": 60, "near": 30, "zeros": 3, "two_zeros": 1, "cut": 1, "nested": 1, "company": 30, "nonprofit": 30, "landline": 6}


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


CARD_COUNTS = {
    "visa": (16, 16), "visa13": (2, 13), "visa19": (2, 19), "mastercard": (12, 16), "amex": (8, 15), "diners": (4, 14),
    "discover": (4, 16), "jcb": (3, 16), "unionpay": (3, 16), "near": (20, 16), "nobrand": (6, 16),
}  # fmt: skip
WRONG_LENGTHS = (15, 14, 17, 18, 12, 20, 16, 15)


def test_l1_luhn_passes() -> None:
    stem = CARDS.visa[0][:15]
    assert luhn_ok(inv.complete(stem, luhn_ok)) and inv.complete(stem, luhn_ok) == CARDS.visa[0]
    assert luhn_ok("0000000000000000")


@pytest.mark.parametrize("which", ["another check digit", "empty", "letter", "arabic-indic"])
def test_l2_luhn_fails(which: str) -> None:
    card = CARDS.visa[0]
    digits = {
        "another check digit": card[:-1] + str((int(card[-1]) + 1) % 10),
        "empty": "",
        "letter": card[:-1] + "a",
        "arabic-indic": "٠" * 16,
    }[which]
    assert not luhn_ok(digits)


def test_l3_luhn_and_the_id_check_agree_on_nine_digits() -> None:
    for number in ISRAELI_IDS.valid + ISRAELI_IDS.near:
        assert luhn_ok(number) is israeli_id_checksum_ok(number)


@pytest.mark.parametrize("field", CARD_COUNTS)
def test_cd1_each_list_of_cards(field: str) -> None:
    numbers = getattr(CARDS, field)
    how_many, length = CARD_COUNTS[field]
    assert len(numbers) == how_many and len(set(numbers)) == how_many
    assert all(len(n) == length and n.isascii() and n.isdigit() for n in numbers)
    assert all(luhn_ok(n) is (field != "near") for n in numbers)


def test_cd2_the_brand_prefixes() -> None:
    assert all(n[0] == "4" for n in CARDS.visa + CARDS.visa13 + CARDS.visa19)
    assert all(51 <= int(n[:2]) <= 55 or 2221 <= int(n[:4]) <= 2720 for n in CARDS.mastercard)
    assert any(n[0] == "5" for n in CARDS.mastercard) and any(n[0] == "2" for n in CARDS.mastercard)
    assert all(n[:2] in ("34", "37") for n in CARDS.amex)
    assert all(n[:2] == "36" for n in CARDS.diners)
    assert all(n[:4] == "6011" or 644 <= int(n[:3]) <= 649 or n[:2] == "65" for n in CARDS.discover)
    assert all(3528 <= int(n[:4]) <= 3589 for n in CARDS.jcb)
    assert all(n[:2] == "62" for n in CARDS.unionpay)
    assert all(n[0] in "1789" for n in CARDS.nobrand)


def test_cd3_near_misses() -> None:
    sources = CARDS.visa[:10] + CARDS.mastercard[:10]
    assert all(n[:15] == s[:15] and n[15] != s[15] for n, s in zip(CARDS.near, sources, strict=True))


def test_cd4_wrong_lengths() -> None:
    numbers = CARDS.wrong_length
    assert tuple(len(n) for n in numbers) == WRONG_LENGTHS and all(luhn_ok(n) for n in numbers)
    assert all(n[0] == "4" for n in numbers[:6]) and numbers[6][:2] in ("34", "37")
    assert 51 <= int(numbers[7][:2]) <= 55 or 2221 <= int(numbers[7][:4]) <= 2720


def test_cd5_the_seed() -> None:
    assert inv.cards(inv.SEED) == CARDS
    assert set(inv.cards(inv.SEED + 1).visa).isdisjoint(CARDS.visa)


def test_cd6_a_card_in_a_slot() -> None:
    card = CARDS.amex[0]
    text, spans = inv.fill("כרטיס {amex[0]:dddd dddddd ddddd}.", CARDS)
    assert text == f"כרטיס {card[:4]} {card[4:10]} {card[10:]}." and spans == [(6, 23)]
