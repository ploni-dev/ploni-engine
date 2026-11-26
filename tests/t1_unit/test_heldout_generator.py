"""Unit tests of the held-out batch's generator, eval/heldout/generator.py, on the batch of SEED.

Why: every score of every PR from Phase 1 on is measured against this key (`build-plan.md`
section 7, "The held-out batch"; Achia, 2026-11-26, issue 283). A key that is off by one
character, a positive that fails its own checksum or a near miss that is in truth an item would
make every number built on it wrong, and nobody who writes the detectors may look at the
documents to see it. So the key is checked against oracles written from the plan
(tests/heldout_oracles.py), not from the generator.

Every assertion here is on a bool, a count, a list of indexes or of type names, or a digest: a
failing test prints no document and no planted value, because pytest prints what an assertion
compares, and the session that writes the detectors and the public CI log read that output
(review 1 of the branch, finding 1; tests/t8_privacy/test_heldout_disk.py runs a broken build to
show it). Hebrew words stand at module level, so a traceback that shows a test's source
shows none; a test's body holds single letters and marks only. A parametrized test takes a type
name or text written here by hand, never words that only the generator holds (its frames,
values and lexicons), as pytest prints a failing test's arguments (review 2, finding 24;
review 8, finding 45; review 9, finding 46).

Test matrix:

Equivalence classes (the batch of SEED):
  EC1  every type of TYPES has at least 40 positives and 40 near misses        (21 types)
  EC2  the types of the key are the plan's 21, and every near miss is typed by one of them; the
       one group is the names that stand once, all of them PERSON (review 2, finding 21)
  EC3  every item's span holds exactly its planted text, and start < end
  EC4  every positive of a checksum type passes its check, as build-plan.md Phase 1 writes it,
       and every near miss of that type fails it                               (5 types)
  EC5  each checksum type has at least 20 near misses of its length that fail the checksum only
  EC6  no two planted items overlap, near misses included
  EC7  the same seed gives the same batch (by digest); another seed another; the default is SEED
  EC8  every positive of the 16 other types passes its oracle and every near miss fails it
  EC9  no IL_ID positive starts with 5 (a company's or a non-profit's head); one has 8 digits
  EC10 no trigger that starts with ה keeps it after a glued ל, ב or כ
  EC11 no ID-family near miss that fails the check holds a group of 7 to 9 digits that passes
  EC12 no company or non-profit near miss is a valid registry number of the other kind (review
       2, finding 20)
  EC13 at least a third of the GUSH_HELKA and of the ADDRESS near misses carry a cue word
  EC14 at least a third of the near misses of each pattern-only type have a positive's shape
  EC15 each word of each name of the group stands once in its document, with no trigger before
       the name (review 2, finding 27)
  EC16 plain sentences with no item stand between the items: at least a fifth as many as items
  EC17 no ADDRESS positive that starts with ה is glued to a proclitic
  EC18 the forms of a type are all drawn: phones of each kind and form, cards of 13 and 19
       digits and of the 2-series, an account written with its words; near-miss values of
       PLACEHOLDER, PERSON and URL are varied
  EC19 the batch of SEED has the digest pinned here, so any change of it shows as a change
  EC20 the group has at least 40 positives and 40 near misses, and its positives are not all of
       one word count (review 2, finding 26)

Hebrew and separator axes:
  H1  gershayim as both " (U+0022) and the Hebrew sign (U+05F4) inside CASE_NUMBER positives
  H2  geresh as both ' (U+0027) and the Hebrew sign (U+05F3) in the words before PERSON items
  H3  a proclitic letter directly before a planted item, for CASE_NUMBER, ADDRESS, GUSH_HELKA
  H4  names that are ordinary Hebrew words among the PERSON positives (the plan's list)
  H5  Latin-script items inside Hebrew sentences, RTL and LTR adjacent: EMAIL, URL, IBAN
  H6  niqqud in some PERSON positives
  H7  separator variants on IL_ID positives: hyphen, space, dot, none

Private helpers with logic of their own:
  P1  _hebrew_number: one letter takes a geresh, more take gershayim before the last; 15 and
      16 are written with tet; hundreds compose
  P2  _id_check_digit: for 1,000 bodies made here, the plan's check passes with the digit it
      gives and fails with each of the other nine
  P3  _luhn_check_digit: the same, against a Luhn oracle written here
  P4  _iban: 23 characters, starts IL, mod-97 of the rearranged number is 1
  P5  _part_passes: a failing value with a passing group; a passing whole; no passing group;
      a group of one digit repeated
  P6  _group: groups and the rest; one group as long as the digits; digits shorter than the
      groups; no separator (review 7, finding 43)
  P7  _with_trigger: the trigger first in the frame; after ל, ב and כ a trigger's ה falls;
      after ו it stays; a trigger with no ה after ל
  P8  _alone: a name of the group whose word stands elsewhere in the document is drawn again
      until none does; a near miss of the group and a name of another line are left as they are

Boundaries:
  B1  every document holds at least one item; the first and the last items lie inside their text
  B2  the bound of EC1 is 40, and the smallest count of any type is at least that

Adversarial:
  A1  the repr of an Item and of the Batch shows no planted text

Not applicable: the document-structure axes of the test-matrix skill (runs, headers, tables,
footnotes): the batch is plain text, and Phase 2 brings documents with structure.
"""

import re
from collections import Counter

import pytest

from eval.heldout import generator
from eval.heldout.generator import SEED, TYPES, Batch, Item, build
from tests.heldout_oracles import (
    CHECKSUM_TYPES, ORDINARY_WORD_NAMES, PARTY_TRIGGERS, TRIGGERS, UNTITLED, before, card_brand_ok, checksum_valid, digest,
    luhn_ok, plan_id_ok, stripped, valid,
)  # fmt: skip

BATCH = build(SEED)
ITEMS = BATCH.key + BATCH.near_misses
# The digest of the batch of SEED on Python 3.13; a change of the batch changes it (EC19).
SEED_DIGEST = "62ec2fdca3092f757adc10624f704ea300259e928f56698c162ea8b4dab2273e"
# CLAUDE.md, Tests: detectors 40 positive and 40 negative.
MINIMUM = 40
ID_FAMILY = ("IL_ID", "COMPANY_NUMBER", "NONPROFIT_NUMBER")
OTHER_TYPES = tuple(kind for kind in TYPES if kind not in CHECKSUM_TYPES)
# build-plan.md: the types of Phase 1.
EXPECTED_TYPES = {
    "IL_ID", "COMPANY_NUMBER", "NONPROFIT_NUMBER", "IBAN", "BANK_ACCOUNT", "CREDIT_CARD",
    "PHONE", "EMAIL", "URL", "IP_ADDRESS", "IL_PLATE", "CASE_NUMBER", "GUSH_HELKA", "DATE",
    "AMOUNT", "ADDRESS", "PERSON", "PLACEHOLDER", "HEALTH_FUND_ID", "MILITARY_ID", "PASSPORT_NUMBER",
}  # fmt: skip
CUES = {"GUSH_HELKA": ("גוש", "חלקה"), "ADDRESS": (*generator.STREETS, *generator.CITIES, "רחוב")}
# What a word of a document is, for "stands once": a run of anything but spaces and punctuation.
WORD = re.compile(r"[^\s.,:;()]+")
GERESH_AS_ASCII = str.maketrans({"׳": "'"})
PATTERN_SHAPES = {"HEALTH_FUND_ID": r"\d{6,9}", "MILITARY_ID": r"\d{7}", "PASSPORT_NUMBER": r"\d{8}|[A-Z]{2}\d{7}"}
GLUED_PARTIES = tuple(f"{proclitic}{trigger}" for trigger in PARTY_TRIGGERS for proclitic in "לבכ")
NIQQUD = re.compile("[ְ-ׇ]")
HEBREW_LETTER = re.compile("[א-ת]")
TRIGGER_CASES = [
    ("@ {} הגיע.", "מר", "מר {} הגיע."), ("נמסר ל@ {}.", "התובע", "נמסר לתובע {}."), ("נכח ב@ {}.", "המשיב", "נכח במשיב {}."),
    ("כ@ {}.", "העד", "כעד {}."), ("ו@ {}.", "הנתבע", "והנתבע {}."), ("ל@ {}.", "מר", "למר {}."),
]  # fmt: skip
# P8: a name of the group that shares a word with another sentence of its document.
ALONE_FRAME, ALONE_OTHER, ALONE_TAKEN, ALONE_WORD = "{} חתם על ההסכם.", "מר {} הגיע.", "דנה כהן", "כהן"
HEBREW_NUMBERS = [(1, "א'"), (10, "י'"), (15, 'ט"ו'), (16, 'ט"ז'), (21, 'כ"א'), (30, "ל'"), (786, 'תשפ"ו'), (733, 'תשל"ג'), (400, "ת'")]


def of(items: tuple[Item, ...], kind: str) -> list[Item]:
    """The items of one type."""
    return [item for item in items if item.type == kind]


def test_ec1_every_type_has_40_positives_and_40_near_misses() -> None:
    positives = Counter(item.type for item in BATCH.key)
    near = Counter(item.type for item in BATCH.near_misses)
    assert sorted(kind for kind in TYPES if positives[kind] < MINIMUM or near[kind] < MINIMUM) == []


def test_ec2_the_types_are_the_plans() -> None:
    assert sorted(set(TYPES) ^ EXPECTED_TYPES) == []
    assert len(TYPES) == len(EXPECTED_TYPES)
    assert sorted({item.type for item in BATCH.key} ^ EXPECTED_TYPES) == []
    assert sorted({item.type for item in BATCH.near_misses} - EXPECTED_TYPES) == []
    assert sorted({(item.type, item.group) for item in ITEMS if item.group}) == [("PERSON", UNTITLED)]


def test_ec3_every_span_holds_its_planted_text() -> None:
    assert [index for index, item in enumerate(ITEMS) if BATCH.documents[item.doc][item.start : item.end] != item.text] == []
    assert [index for index, item in enumerate(ITEMS) if not item.start < item.end] == []


@pytest.mark.parametrize("kind", CHECKSUM_TYPES)
def test_ec4_positives_pass_their_check_and_near_misses_fail_it(kind: str) -> None:
    assert [index for index, item in enumerate(of(BATCH.key, kind)) if not checksum_valid(kind, item.text)] == []
    assert [index for index, item in enumerate(of(BATCH.near_misses, kind)) if checksum_valid(kind, item.text)] == []


def checksum_only(kind: str, value: str) -> bool:
    """Whether a near miss has its type's length and fails the checksum alone."""
    digits = stripped(value)
    if kind == "IBAN":
        return len(value.replace(" ", "")) == 23 and not checksum_valid(kind, value)
    if kind == "CREDIT_CARD":
        return digits.isdigit() and card_brand_ok(digits) and not luhn_ok(digits)
    return len(digits) == 9 and digits.isdigit() and not plan_id_ok(digits)


@pytest.mark.parametrize("kind", CHECKSUM_TYPES)
def test_ec5_near_misses_that_fail_the_checksum_only(kind: str) -> None:
    count = sum(checksum_only(kind, item.text) for item in of(BATCH.near_misses, kind))
    assert count >= MINIMUM // 2


def test_ec6_no_two_items_overlap() -> None:
    spans = sorted((item.doc, item.start, item.end) for item in ITEMS)
    assert [index for index in range(1, len(spans)) if spans[index][0] == spans[index - 1][0] and spans[index][1] < spans[index - 1][2]] == []


def test_ec7_the_same_seed_gives_the_same_batch() -> None:
    same = (digest(build(SEED)) == digest(BATCH), digest(build(SEED + 1)) == digest(BATCH), digest(build()) == digest(BATCH))
    assert same == (True, False, True)


@pytest.mark.parametrize("kind", OTHER_TYPES)
def test_ec8_positives_pass_their_oracle_and_near_misses_fail_it(kind: str) -> None:
    assert [index for index, item in enumerate(of(BATCH.key, kind)) if not valid(BATCH, item)] == []
    assert [index for index, item in enumerate(of(BATCH.near_misses, kind)) if valid(BATCH, item)] == []


def test_ec9_il_id_heads_and_lengths() -> None:
    digits = [stripped(item.text) for item in of(BATCH.key, "IL_ID")]
    assert sum(value.startswith("5") for value in digits) == 0
    assert sum(len(value) == 8 for value in digits) >= 1


def test_ec10_no_trigger_keeps_its_he_after_a_proclitic() -> None:
    assert sum(document.count(word) for document in BATCH.documents for word in GLUED_PARTIES) == 0


def holds_passing_group(text: str) -> bool:
    """Whether a value that fails the ID check has a separated group of 7 to 9 digits that passes."""
    parts = re.split(r"\D+", text)
    lone = any(7 <= len(part) <= 9 and len(set(part)) > 1 and plan_id_ok(part) for part in parts)
    return lone and not plan_id_ok("".join(parts))


def test_ec11_no_id_family_near_miss_holds_a_passing_group() -> None:
    assert [index for index, item in enumerate(BATCH.near_misses) if item.type in ID_FAMILY and holds_passing_group(item.text)] == []


@pytest.mark.parametrize(("kind", "other"), [("COMPANY_NUMBER", "NONPROFIT_NUMBER"), ("NONPROFIT_NUMBER", "COMPANY_NUMBER")])
def test_ec12_no_near_miss_is_a_valid_registry_number(kind: str, other: str) -> None:
    assert sum(checksum_valid(other, item.text) for item in of(BATCH.near_misses, kind)) == 0


@pytest.mark.parametrize("kind", CUES)
def test_ec13_near_misses_carry_a_cue(kind: str) -> None:
    near = of(BATCH.near_misses, kind)
    carrying = sum(any(cue in item.text.translate(GERESH_AS_ASCII) for cue in CUES[kind]) for item in near)
    assert carrying * 3 >= len(near)


@pytest.mark.parametrize("kind", PATTERN_SHAPES)
def test_ec14_pattern_only_near_misses_with_a_positives_shape(kind: str) -> None:
    near = of(BATCH.near_misses, kind)
    shaped = sum(re.fullmatch(PATTERN_SHAPES[kind], item.text) is not None for item in near)
    assert shaped * 3 >= len(near)


def grouped(items: tuple[Item, ...]) -> list[Item]:
    """The items of the group of names that stand once."""
    return [item for item in items if item.group == UNTITLED]


def test_ec15_a_name_that_stands_once() -> None:
    items = grouped(BATCH.key)
    words = [Counter(WORD.findall(document)) for document in BATCH.documents]
    assert [index for index, item in enumerate(items) if any(words[item.doc][word] != 1 for word in item.text.split())] == []
    assert [index for index, item in enumerate(items) if any(before(BATCH, item, 12).endswith(trigger + " ") for trigger in TRIGGERS)] == []


def test_ec20_the_group_of_names_that_stand_once() -> None:
    sizes = (len(grouped(BATCH.key)), len(grouped(BATCH.near_misses)))
    assert (sizes[0] >= MINIMUM, sizes[1] >= MINIMUM) == (True, True)
    assert len({len(item.text.split()) for item in grouped(BATCH.key)}) >= 2
    assert sum(item.text in ORDINARY_WORD_NAMES for item in grouped(BATCH.near_misses)) >= MINIMUM // 2


def test_ec16_plain_sentences_between_the_items() -> None:
    covered, crossing = 0, 0
    for index, document in enumerate(BATCH.documents):
        spans = [(item.start, item.end) for item in ITEMS if item.doc == index]
        for filler in generator.FILLERS:
            for found in re.finditer(re.escape(filler), document):
                covered += 1
                crossing += any(start < found.end() and found.start() < end for start, end in spans)
    assert crossing == 0
    assert covered * 5 >= len(ITEMS)


def test_ec17_no_address_glued_before_its_he() -> None:
    items = of(BATCH.key, "ADDRESS")
    glued = [index for index, item in enumerate(items) if item.text.startswith("ה") and item.start and HEBREW_LETTER.match(BATCH.documents[item.doc][item.start - 1])]
    assert glued == []


def phone_forms(texts: list[str]) -> dict[str, int]:
    """Count the phones of each kind and form among texts."""
    digits = [re.sub(r"\D", "", text.replace("+972", "0")) for text in texts]
    return {
        "landline": sum(re.match(r"0[23489]", value) is not None for value in digits),
        "mobile": sum(value.startswith("05") for value in digits),
        "voip": sum(re.match(r"07[2-9]", value) is not None for value in digits),
        "international": sum(text.startswith("+972") for text in texts),
        "service": sum(text.startswith("*") for text in texts),
        "bracket": sum("(" in text for text in texts),
        "spaced": sum(" " in text and not text.startswith(("+", "(")) for text in texts),
    }


def test_ec18_the_forms_of_a_type_are_all_drawn() -> None:
    forms = phone_forms([item.text for item in of(BATCH.key, "PHONE")])
    assert sorted(name for name, count in forms.items() if count == 0) == []
    cards = [stripped(item.text) for item in of(BATCH.key, "CREDIT_CARD")]
    drawn = (any(len(card) == 13 for card in cards), any(len(card) == 19 for card in cards), any(card.startswith("2") for card in cards))
    assert drawn == (True, True, True)
    assert sum(HEBREW_LETTER.search(item.text) is not None for item in of(BATCH.key, "BANK_ACCOUNT")) >= 1
    distinct = tuple(len({item.text for item in of(BATCH.near_misses, kind)}) for kind in ("PLACEHOLDER", "PERSON", "URL"))
    assert (distinct[0] >= 8, distinct[1] >= 15, distinct[2] >= 30) == (True, True, True)


def test_ec19_the_batch_of_seed_is_pinned() -> None:
    same = digest(BATCH) == SEED_DIGEST
    assert same


def test_h1_both_gershayim_in_case_numbers() -> None:
    texts = "".join(item.text for item in of(BATCH.key, "CASE_NUMBER"))
    found = ('"' in texts, "״" in texts)
    assert found == (True, True)


def test_h2_both_geresh_before_person_items() -> None:
    text = "".join(BATCH.documents[item.doc][max(0, item.start - 12) : item.start] for item in of(BATCH.key, "PERSON"))
    found = ("'" in text, "׳" in text)
    assert found == (True, True)


@pytest.mark.parametrize("kind", ["CASE_NUMBER", "ADDRESS", "GUSH_HELKA"])
def test_h3_a_proclitic_directly_before_an_item(kind: str) -> None:
    glued = [item for item in of(BATCH.key, kind) if item.start > 0 and HEBREW_LETTER.match(BATCH.documents[item.doc][item.start - 1])]
    assert len(glued) >= 1


def test_h4_ordinary_word_names_among_person_positives() -> None:
    words = {word for item in of(BATCH.key, "PERSON") for word in item.text.split()}
    assert len(words & ORDINARY_WORD_NAMES) >= 5


@pytest.mark.parametrize("kind", ["EMAIL", "URL", "IBAN"])
def test_h5_latin_items_inside_hebrew_sentences(kind: str) -> None:
    items = of(BATCH.key, kind)
    beside_hebrew = [item for item in items if HEBREW_LETTER.search(BATCH.documents[item.doc][max(0, item.start - 20) : item.start])]
    assert len(beside_hebrew) * 2 >= len(items)


def test_h6_niqqud_in_some_person_positives() -> None:
    assert sum(NIQQUD.search(item.text) is not None for item in of(BATCH.key, "PERSON")) >= 1


def test_h7_separator_variants_on_il_id() -> None:
    texts = [item.text for item in of(BATCH.key, "IL_ID")]
    found = (any(text.isdigit() for text in texts), *(any(separator in text for text in texts) for separator in "- ."))
    assert found == (True, True, True, True)


@pytest.mark.parametrize(("number", "letters"), HEBREW_NUMBERS, ids=[str(number) for number, _ in HEBREW_NUMBERS])
def test_p1_hebrew_number(number: int, letters: str) -> None:
    same = generator._hebrew_number(number) == letters
    assert same


def bodies(length: int) -> list[str]:
    """A thousand digit strings of a length, made here from their index."""
    return [str(index * 7919 % 10**length).zfill(length) for index in range(1000)]


def test_p2_id_check_digit() -> None:
    wrong = []
    for index, body in enumerate(bodies(8)):
        digit = generator._id_check_digit(body)
        if not plan_id_ok(body + digit) or any(plan_id_ok(body + other) for other in "0123456789" if other != digit):
            wrong.append(index)
    assert wrong == []


@pytest.mark.parametrize("length", [12, 14, 15])
def test_p3_luhn_check_digit(length: int) -> None:
    wrong = []
    for index, body in enumerate(bodies(length)):
        digit = generator._luhn_check_digit(body)
        if not luhn_ok(body + digit) or any(luhn_ok(body + other) for other in "0123456789" if other != digit):
            wrong.append(index)
    assert wrong == []


def test_p4_iban() -> None:
    made = [generator._iban(body[:3] + body + body[:2]) for body in bodies(14)]
    assert [index for index, value in enumerate(made) if not checksum_valid("IBAN", value)] == []


def test_p5_part_passes() -> None:
    body = "1" + bodies(8)[1][1:]
    passing = body + generator._id_check_digit(body)
    cases = (
        generator._part_passes(f"{passing}-7"),
        generator._part_passes(f"{passing[:3]}-{passing[3:]}"),
        generator._part_passes(f"{passing[:4]}-{passing[4:]}7"),
        generator._part_passes("000000000-7"),
    )
    assert cases == (True, False, False, False)


@pytest.mark.parametrize(
    ("digits", "sizes", "separator", "grouped"),
    [("123456789", (3, 3), "-", "123-456-789"), ("123456789", (9,), "-", "123456789"), ("12345", (3, 3), "-", "123-45"), ("1234567", (2, 3), "", "1234567")],
    ids=["groups and the rest", "one whole group", "shorter than the groups", "no separator"],
)
def test_p6_group(digits: str, sizes: tuple[int, ...], separator: str, grouped: str) -> None:
    same = generator._group(digits, sizes, separator) == grouped
    assert same


@pytest.mark.parametrize(("frame", "trigger", "filled"), TRIGGER_CASES, ids=["first", "after lamed", "after bet", "after kaf", "after vav", "no he"])
def test_p7_with_trigger(frame: str, trigger: str, filled: str) -> None:
    same = generator._with_trigger(frame, trigger) == filled
    assert same


class TurnRandom:
    """A stand-in for random.Random that takes each choice in turn and draws 0.9, the same on every run."""

    def __init__(self) -> None:
        """Start at the first choice."""
        self.turn = 0

    def random(self) -> float:
        """Draw a share above every share the generator compares with."""
        return 0.9

    def choice(self, options: tuple[str, ...]) -> str:
        """Take the next option in turn."""
        self.turn += 1
        return options[self.turn % len(options)]


def test_p8_alone() -> None:
    planned = [(generator.UNTITLED, True, ALONE_FRAME, ALONE_TAKEN), ("PERSON", True, ALONE_OTHER, ALONE_WORD), (generator.UNTITLED, False, ALONE_FRAME, ALONE_WORD)]
    result = generator._alone(TurnRandom(), planned)
    others = {word for _, _, frame, value in result[1:] for word in generator.WORD.findall(frame.replace("{}", value))}
    drawn = result[0][3]
    shown = (drawn != ALONE_TAKEN, any(word in others for word in drawn.split()), result[1:] == planned[1:])
    assert shown == (True, False, True)


def test_b1_every_document_holds_an_item_and_the_ends_lie_inside() -> None:
    assert sorted(set(range(len(BATCH.documents))) - {item.doc for item in ITEMS}) == []
    last = max(BATCH.key, key=lambda item: (item.doc, item.end))
    inside = last.end <= len(BATCH.documents[last.doc]) and min(item.start for item in ITEMS) >= 0
    assert inside


def test_b2_the_bound_is_40() -> None:
    assert MINIMUM == 40
    assert min(Counter(item.type for item in BATCH.key).values()) >= MINIMUM
    assert min(Counter(item.type for item in BATCH.near_misses).values()) >= MINIMUM


def test_a1_repr_shows_no_planted_text() -> None:
    shown = (BATCH.key[0].text in repr(BATCH.key[0]), "secret-text" in repr(Item(0, 0, 4, "X", "secret-text")))
    assert shown == (False, False)
    hidden = "secret-document" not in repr(Batch(("secret-document",), (), ()))
    assert hidden
