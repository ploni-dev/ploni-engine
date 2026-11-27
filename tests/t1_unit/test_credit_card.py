"""Test matrix for ploni/detect/deterministic/credit_card.py: the credit card detector of issue #35.

Why: build-plan.md Phase 1, "Credit card": "Luhn plus brand prefix sanity." Issue #35: "T1 with
at least 40 positive and 40 negative examples, in Hebrew context, with separator and gershayim
variants ... Gate: recall and precision at or above 0.98 on the fixtures (checksum-backed type)."
The span is the held-out batch's rule for CREDIT_CARD (its span rules, which the detector side
may read by Achia's third answer on #283): "The number
only: first digit to last, separators between included. Not the label." Every number that passes
the Luhn check is made when the tests run (tests/invented_numbers.py, CARDS; Achia, 2026-11-27,
#32, "Make them fresh too (Recommended)"); the numbers written here fail it, or are sixteen zeros.

Test matrix:

luhn_ok:
  C1 a card of each brand                                  True
  C2 the same digits, another check digit                  False
  C3 the empty string; a letter; Arabic-Indic digits; a separator inside    False
  C4 sixteen zeros (trivial: the Luhn check passes it, no brand's prefix does)    True

brand (the issuer ranges and lengths of the module's source):
  BR1 a card of each list of CARDS                          its brand
  BR2 the edges of each range, a number that fails Luhn (brand reads no check digit): 51, 55,
      2221, 2720, 34, 37, 300, 305, 36, 38, 39, 6011, 644, 649, 65, 3528, 3589, 62, 4 in;
      50, 56, 2220, 2721, 35, 306, 6010, 643, 3527, 3590, 63 out (None)
  BR3 a brand's prefix at a length it does not issue: Visa at 12, 14, 15, 17, 18, 20;
      Mastercard at 15, 17; American Express at 14, 16; Diners at 13   None
  BR4 no brand's prefix: 0, 1, 7, 8, 9                      None
  BR5 each brand at every length it issues (Visa 13, 16, 19; Mastercard 16; American Express 15;
      Diners, Discover, JCB, UnionPay 16 to 19, Diners from 14)    its brand
  BR6 the edges of a range at the brand's own length: 33 and 35 at 15 (None), 36 and 38 at 15
      (Diners, not American Express), 299 at 14, 6012, 66 and 61 at 16    None but where named
BR5 and BR6 were added after the code, for 25 mutants that survived Cosmic Ray (the commit that
added them names them).

labelled (a card's label before the number, on its line, within LABEL_WINDOW characters, after
the last digit there):
  LB1 each label: כרטיס, כרטיס אשראי, מספר כרטיס, מס' כרטיס, מס׳ כרטיס, אשראי, ויזה, מאסטרקארד,
      מאסטרקרד, אמריקן אקספרס, אמקס, דיינרס, ישראכרט, לאומי קארד, VISA, Visa, Mastercard,
      MasterCard, Master Card, AMEX, American Express, Diners, card, Credit Card    True
  LB2 a proclitic glued to the label: בכרטיס, ובכרטיס, הכרטיס, מהכרטיס, באשראי, לויזה    True
  LB3 no label; a label's letters inside a longer word (תכרטיס, אשראית, Visas, scard)    False
  LB4 a label further than LABEL_WINDOW before; on the line before; a digit between    False
  LB5 the window's edge: a label that starts LABEL_WINDOW characters before the number counts,
      one a character earlier does not

The detector (`CreditCard`):
  EC1 each written form of a 16-digit Visa: plain; four groups of four with a space, a hyphen,
      a no-break space, a dot, a maqaf (U+05BE), an en dash, the Unicode hyphen (U+2010);
      mixed spaces and hyphens; and American Express 4-6-5, Diners 4-6-4, Visa 13 as 4-3-3-3,
      Visa 19 as 4-4-4-4-3                                 one detection, the span the number only
  EC2 one card of each list of CARDS                       found
  EC3 two cards in one text                                two detections, in order
  EC4 the fields: part the projection's, surface the text of the span, type CREDIT_CARD,
      detector "credit_card", confidence CONFIDENCE_LABELLED (a label), band "high", base_span
      None, needs_review False, detection_id "" (ids are made after detection: Achia,
      2026-11-26, #169)
  EC5 the confidence: CONFIDENCE_LABELLED after a label, CONFIDENCE with none
  EC6 the label glued to the number (כרטיס:), a proclitic on the label, a letter glued to the
      number (ב...)                                         found
  B1  the number alone, at the start and at the end of the text    found
  B2  the empty text; a text with no digit                 nothing
  B3  the shortest and the longest lengths: 13 and 19 found; 12 and 20 digits that pass the
      check with a Visa prefix                             nothing
  A1  a card inside a longer number: a digit after it; "-5" after it; "7-" before it    nothing
  A2  two separators in a row inside it                    nothing
  A3  a near miss (another check digit)                    nothing
  A4  digits that pass the check with no brand's prefix; sixteen zeros    nothing
  A5  a brand's prefix at a length it does not issue, passing the check    nothing
  A6  Arabic-Indic digits                                  nothing
  A7  a nine-digit number after a card label (an ID's length)    nothing
  A8  a card followed by another number after one separator (an expiry, " 12/26"): nothing
      (Known limits: it is read as part of the number); after a comma or a word: found
  A9  CANDIDATE itself: 13 and 19 digits match whole; 12 and 20 do not

The fixture (tests/fixtures/detect/credit_card.json; its numbers are filled in when the tests
run, by tests/invented_numbers.py):
  F1  at least 40 positive and 40 negative texts
  F2  recall and precision at or above 0.98, counted by exact span (build-plan.md Phase 1, Gate);
      the counts and every miss are printed, a miss by its case's place in the fixture, never by
      its text, which holds a number made when the tests run

Hebrew axes: gershayim as " and ״ in the text around the number (ע"י, ע״י); geresh as ' and ׳
in a label (מס' כרטיס, מס׳ כרטיס); a proclitic glued to the label and a letter glued to the
number; niqqud before it; RLM and LRM around it; the maqaf as a separator; Hebrew and Latin
labels. Names that are ordinary words do not apply: the detector reads digits. Document axes: a
number on a line of its own, in a table row; the part is the projection's.

Known limits: those of the module, among them A8.
"""

from pathlib import Path

import pytest

from ploni.detect.base import DetectContext
from ploni.detect.deterministic import credit_card
from ploni.detect.deterministic.credit_card import CANDIDATE, CreditCard, brand, labelled, luhn_ok
from ploni.types import Span
from tests import invented_numbers as inv
from tests.detector_contract import projection
from tests.invented_numbers import CARDS, ISRAELI_IDS, read_cases

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "detect" / "credit_card.json"
CTX = DetectContext()
VISA = CARDS.visa[0]
LISTS = ("visa", "visa13", "visa19", "mastercard", "amex", "diners", "discover", "jcb", "unionpay")
BRANDS = {"visa13": "visa", "visa19": "visa"}


def found(text: str) -> list[tuple[int, int]]:
    """Return the places the detector finds in a text."""
    return [(each.span.start, each.span.end) for each in CreditCard().detect(projection(text), CTX)]


def only(text: str, number: str) -> list[tuple[int, int]]:
    """Return the place of the one number in a text, as the detector should find it."""
    start = text.index(number)
    return [(start, start + len(number))]


def groups(number: str, sizes: tuple[int, ...], separator: str = " ") -> str:
    """Write a number in groups of the given sizes, joined by the separator."""
    at, out = 0, []
    for size in sizes:
        out.append(number[at : at + size])
        at += size
    return separator.join(out)


def failing(prefix: str, length: int) -> str:
    """Return the prefix padded with zeros to the length, its last digit one the Luhn check refuses."""
    stem = prefix + "0" * (length - len(prefix) - 1)
    return next(stem + d for d in "0123456789" if not inv.luhn_ok(stem + d))


@pytest.mark.parametrize("field", LISTS)
def test_c1_a_card_of_each_brand(field: str) -> None:
    assert luhn_ok(getattr(CARDS, field)[0])


def test_c2_another_check_digit() -> None:
    assert not any(luhn_ok(n) for n in CARDS.near)


@pytest.mark.parametrize("which", ["empty", "letter", "arabic-indic", "separator"])
def test_c3_not_digits(which: str) -> None:
    digits = {"empty": "", "letter": VISA[:-1] + "a", "arabic-indic": "٠" * 16, "separator": f"{VISA[:8]} {VISA[8:]}"}[which]
    assert not luhn_ok(digits)


def test_c4_sixteen_zeros_pass_the_check() -> None:
    assert luhn_ok("0000000000000000") and brand("0000000000000000") is None


@pytest.mark.parametrize("field", LISTS)
def test_br1_each_list_has_its_brand(field: str) -> None:
    assert {brand(n) for n in getattr(CARDS, field)} == {BRANDS.get(field, field)}


IN_RANGE = {
    "51": ("mastercard", 16), "55": ("mastercard", 16), "2221": ("mastercard", 16), "2720": ("mastercard", 16),
    "34": ("amex", 15), "37": ("amex", 15), "300": ("diners", 14), "305": ("diners", 14), "36": ("diners", 14),
    "38": ("diners", 16), "39": ("diners", 19), "6011": ("discover", 16), "644": ("discover", 16),
    "649": ("discover", 17), "65": ("discover", 19), "3528": ("jcb", 16), "3589": ("jcb", 19),
    "62": ("unionpay", 16), "4": ("visa", 13),
}  # fmt: skip
OUT_OF_RANGE = ("50", "56", "2220", "2721", "35", "306", "6010", "643", "3527", "3590", "63")


@pytest.mark.parametrize("prefix", IN_RANGE)
def test_br2_the_edges_of_a_range_in(prefix: str) -> None:
    name, length = IN_RANGE[prefix]
    assert brand(failing(prefix, length)) == name


@pytest.mark.parametrize("prefix", OUT_OF_RANGE)
def test_br2_the_edges_of_a_range_out(prefix: str) -> None:
    assert brand(failing(prefix, 16)) is None


WRONG = (("4", 12), ("4", 14), ("4", 15), ("4", 17), ("4", 18), ("4", 20), ("51", 15), ("51", 17), ("34", 14), ("34", 16), ("36", 13))


@pytest.mark.parametrize(("prefix", "length"), WRONG, ids=[f"prefix {p} at {n}" for p, n in WRONG])
def test_br3_a_prefix_at_a_wrong_length(prefix: str, length: int) -> None:
    assert brand(failing(prefix, length)) is None


@pytest.mark.parametrize("prefix", ["0", "1", "7", "8", "9"])
def test_br4_no_brand(prefix: str) -> None:
    assert brand(failing(prefix, 16)) is None


EVERY_LENGTH = (
    *(("visa", "4", n) for n in (13, 16, 19)), ("mastercard", "51", 16), ("amex", "34", 15),
    *(("diners", "36", n) for n in range(14, 20)), *(("discover", "65", n) for n in range(16, 20)),
    *(("jcb", "3528", n) for n in range(16, 20)), *(("unionpay", "62", n) for n in range(16, 20)),
)  # fmt: skip


@pytest.mark.parametrize(("name", "prefix", "length"), EVERY_LENGTH, ids=[f"{b} {p} at {n}" for b, p, n in EVERY_LENGTH])
def test_br5_every_length_of_each_brand(name: str, prefix: str, length: int) -> None:
    assert brand(failing(prefix, length)) == name


EDGES = (("33", 15, None), ("35", 15, None), ("36", 15, "diners"), ("38", 15, "diners"), ("299", 14, None), ("6012", 16, None), ("66", 16, None), ("61", 16, None))


@pytest.mark.parametrize(("prefix", "length", "name"), EDGES, ids=[f"{p} at {n}" for p, n, _ in EDGES])
def test_br6_the_edges_at_the_brands_own_length(prefix: str, length: int, name: str | None) -> None:
    assert brand(failing(prefix, length)) == name


LABELS = (
    "כרטיס", "כרטיס אשראי", "מספר כרטיס", "מס' כרטיס", "מס׳ כרטיס", "אשראי", "ויזה", "מאסטרקארד", "מאסטרקרד",
    "אמריקן אקספרס", "אמקס", "דיינרס", "ישראכרט", "לאומי קארד", "VISA", "Visa", "Mastercard", "MasterCard",
    "Master Card", "AMEX", "American Express", "Diners", "card", "Credit Card",
)  # fmt: skip


@pytest.mark.parametrize("label", LABELS)
def test_lb1_each_label(label: str) -> None:
    text = f"{label}: {VISA}"
    assert labelled(text, text.index(VISA))


@pytest.mark.parametrize("label", ["בכרטיס", "ובכרטיס", "הכרטיס", "מהכרטיס", "באשראי", "לויזה"])
def test_lb2_a_proclitic_on_the_label(label: str) -> None:
    text = f"שולם {label} {VISA}"
    assert labelled(text, text.index(VISA))


@pytest.mark.parametrize("before", ["שולם סכום ", "תכרטיס ", "אשראית ", "Visas ", "scard "])
def test_lb3_no_label(before: str) -> None:
    text = before + VISA
    assert not labelled(text, text.index(VISA))


@pytest.mark.parametrize("before", ["כרטיס " + "א" * 30 + " ", "כרטיס\n", "כרטיס 3 "], ids=["too far", "line before", "digit between"])
def test_lb4_a_label_not_read(before: str) -> None:
    text = before + VISA
    assert not labelled(text, text.index(VISA))


@pytest.mark.parametrize("lead", ["", "פסקה ארוכה למדי לפני הכרטיס. "], ids=["at the start", "further in"])
def test_lb5_the_windows_edge(lead: str) -> None:
    pad = credit_card.LABEL_WINDOW - len("כרטיס")
    at_edge = f"{lead}כרטיס{'.' * pad}{VISA}"
    past_edge = f"{lead}כרטיס{'.' * (pad + 1)}{VISA}"
    assert labelled(at_edge, at_edge.index(VISA))
    assert not labelled(past_edge, past_edge.index(VISA))


FORMS = {
    "plain": VISA,
    "spaces": groups(VISA, (4, 4, 4, 4)),
    "hyphens": groups(VISA, (4, 4, 4, 4), "-"),
    "no-break spaces": groups(VISA, (4, 4, 4, 4), " "),
    "dots": groups(VISA, (4, 4, 4, 4), "."),
    "maqaf": groups(VISA, (4, 4, 4, 4), "־"),
    "en dash": groups(VISA, (4, 4, 4, 4), "–"),
    "unicode hyphen": groups(VISA, (4, 4, 4, 4), "‐"),
    "mixed": f"{VISA[:4]} {VISA[4:8]}-{VISA[8:12]} {VISA[12:]}",
    "amex 4-6-5": groups(CARDS.amex[0], (4, 6, 5)),
    "diners 4-6-4": groups(CARDS.diners[0], (4, 6, 4)),
    "visa 13": groups(CARDS.visa13[0], (4, 3, 3, 3)),
    "visa 19": groups(CARDS.visa19[0], (4, 4, 4, 4, 3), "-"),
}


@pytest.mark.parametrize("form", FORMS)
def test_ec1_each_written_form(form: str) -> None:
    text = f"מספר כרטיס האשראי: {FORMS[form]}."
    assert found(text) == only(text, FORMS[form])


@pytest.mark.parametrize("field", LISTS)
def test_ec2_one_card_of_each_list(field: str) -> None:
    number = getattr(CARDS, field)[1]
    text = f"שולם בכרטיס {number} ביום ראשון"
    assert found(text) == only(text, number)


def test_ec3_two_cards() -> None:
    first, second = CARDS.visa[1], CARDS.mastercard[1]
    text = f"החיוב בכרטיס {first} ובכרטיס {second} בוטל."
    a, b = text.index(first), text.index(second)
    assert found(text) == [(a, a + 16), (b, b + 16)]


def test_ec4_the_fields() -> None:
    number = CARDS.amex[1]
    proj = projection(f"שָׁלוֹם, כרטיס אמקס ‏{number}‎.", part="header1")
    [detection] = CreditCard().detect(proj, CTX)
    assert detection.span == Span(proj.text.index(number), proj.text.index(number) + 15)
    assert (detection.part, detection.surface, detection.entity_type, detection.detector) == ("header1", number, "CREDIT_CARD", "credit_card")
    assert (detection.confidence, detection.band, detection.base_span) == (credit_card.CONFIDENCE_LABELLED, "high", None)
    assert (detection.detection_id, detection.needs_review, detection.review_reason) == ("", False, None)


@pytest.mark.parametrize(("before", "confidence"), [("כרטיס אשראי ", "CONFIDENCE_LABELLED"), ("סכום ", "CONFIDENCE"), ("", "CONFIDENCE")])
def test_ec5_the_confidence(before: str, confidence: str) -> None:
    [detection] = CreditCard().detect(projection(before + VISA), CTX)
    assert detection.confidence == getattr(credit_card, confidence)


@pytest.mark.parametrize("text", [f"כרטיס:{VISA}", f"ובכרטיס {VISA}", f"ב{VISA}"], ids=["glued", "proclitic", "letter"])
def test_ec6_the_label_or_a_letter_glued(text: str) -> None:
    assert found(text) == only(text, VISA)


@pytest.mark.parametrize("text", [VISA, f"{VISA} הוא מספר הכרטיס", f"מספר הכרטיס הוא {VISA}"], ids=["alone", "start", "end"])
def test_b1_at_either_end(text: str) -> None:
    assert found(text) == only(text, VISA)


@pytest.mark.parametrize("text", ["", "אין כאן מספר כלל.", "\n"])
def test_b2_nothing_to_find(text: str) -> None:
    assert found(text) == []


def test_b3_the_shortest_and_longest_lengths() -> None:
    for number in (CARDS.visa13[0], CARDS.visa19[0]):
        assert found(f"כרטיס {number}") == only(f"כרטיס {number}", number)
    for number in (CARDS.wrong_length[4], CARDS.wrong_length[5]):
        assert len(number) in (12, 20) and inv.luhn_ok(number)
        assert found(f"כרטיס {number}") == []


@pytest.mark.parametrize("text", [f"{VISA}7", f"מספר {groups(VISA, (4, 4, 4, 4), '-')}-5", f"7-{VISA}"], ids=["a digit after", "-5 after", "7- before"])
def test_a1_inside_a_longer_number(text: str) -> None:
    assert found(text) == []


def test_a2_two_separators_in_a_row() -> None:
    assert found(f"כרטיס {VISA[:4]}--{VISA[4:]}") == []


def test_a3_a_near_miss() -> None:
    for number in CARDS.near:
        assert found(f"כרטיס {groups(number, (4, 4, 4, 4))}") == []


def test_a4_no_brands_prefix() -> None:
    for number in (*CARDS.nobrand, "0000000000000000"):
        assert inv.luhn_ok(number)
        assert found(f"כרטיס {number}") == []


def test_a5_a_prefix_at_a_wrong_length() -> None:
    for number in CARDS.wrong_length:
        assert inv.luhn_ok(number)
        assert found(f"כרטיס אשראי {number}") == []


def test_a6_arabic_indic_digits() -> None:
    assert found("כרטיס " + "".join(chr(0x0660 + int(d)) for d in VISA)) == []


def test_a7_an_id_length_number_after_a_card_label() -> None:
    assert found(f"כרטיס {ISRAELI_IDS.valid[0]}") == []


def test_a8_another_number_after_one_separator() -> None:
    assert found(f"כרטיס {groups(VISA, (4, 4, 4, 4))} 12/26") == []
    for after in (", בתוקף עד 12/26", " בתוקף עד 12/26"):
        text = f"כרטיס {groups(VISA, (4, 4, 4, 4))}{after}"
        assert found(text) == only(text, groups(VISA, (4, 4, 4, 4)))


def test_a9_the_candidate_pattern() -> None:
    for number in (CARDS.visa13[0], CARDS.visa19[0]):
        assert CANDIDATE.fullmatch(number)
    for number in (CARDS.wrong_length[4], CARDS.wrong_length[5]):
        assert CANDIDATE.search(number) is None


def cases() -> tuple[list[tuple[str, set[tuple[int, int]]]], int, int]:
    """Read the fixture, its numbers filled in: each text with its expected places, and the counts of positive and negative texts."""
    positives, negatives = read_cases(FIXTURE, CARDS)
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
