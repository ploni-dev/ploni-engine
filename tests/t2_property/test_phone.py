"""Two invariants of the phone detector over enumerated texts: what it finds is a number of the plan, and it finds every one.

Why: build-plan.md Phase 1, "Israeli phone" (issue #36); the fixture holds the cases someone
wrote. CLAUDE.md, Tests: an invariant is held over 500 generated cases, 5,000 at phase close.
Each invariant is enumerated, as tests/t2_property/test_israeli_id.py is (hypothesis is not
installed).

Invariant 1, found means a number of the plan: over every sequence of up to four PIECES (10
pieces, 11,111 texts; the full suite runs all, the fast suite every 22nd, 506), each
detection's text, its separators and brackets taken out, is one of the plan's shapes, written
here apart from the module (OF_THE_PLAN): a 0 and an area code of 0[23489] and seven digits;
05X or 07[2-9] and seven; the same from abroad, "+972", "972" or "00972" in place of the 0;
1800 or 1700 and six; a star and four. PIECES mix a mobile, a landline, a number of an area
code the plan does not name, a mobile a digit short, one from abroad, a digit, separators, a
bracket and a phone label, so that runs of digits join into longer numbers and split across
separators.

Invariant 2, every phone is found: each of NUMBERS (the 28 invented mobiles, landlines and VoIP
numbers of tests/invented_numbers.py), in each of FORMS (8: plain; the area code and the seven
with a hyphen and with a space; three and four after the area code, with hyphens and with
spaces; the area code in brackets; from abroad, "+972" and hyphens; "00972" and spaces), after
each of LEFT (8: phone labels, a proclitic glued to one, a geresh, a letter glued to the number,
a bracket, a phrase, nothing), before each of RIGHT (7): 12,544 texts, all in the full suite,
every 25th in the fast one (502). Each gives exactly one detection, the number's place.

Not applicable: the proclitic and ordinary-word axes of names.
"""

import re
from collections.abc import Callable
from itertools import product

import pytest

from ploni.detect.base import DetectContext
from ploni.detect.deterministic.phone import Phone
from tests.detector_contract import projection
from tests.invented_numbers import PHONES
from tests.sizes import INVARIANT_FULL, full

# CLAUDE.md, Tests: an invariant is held over 500 generated cases, 5,000 at phase close.
FAST = 500
SEPARATORS = re.compile("[-./ ()\\u00a0\\u05be\\u2013\\u2010\\u2011\\u2012\\u2014\\u2212]")
CTX = DetectContext()
# build-plan.md Phase 1, "Israeli phone": "Landline `0[23489]`, mobile `05\d`, VoIP `07[2-9]`,
# `+972` forms, `*NNNN` service numbers"; and the 1-800 and 1-700 numbers.
NATIONAL = r"(?:[23489][0-9]{7}|5[0-9]{8}|7[2-9][0-9]{7})"
OF_THE_PLAN = re.compile(rf"0{NATIONAL}|(?:\+|00)?972{NATIONAL}|1[78]00[0-9]{{6}}|\*[0-9]{{4}}")


def area(number: str) -> int:
    """Return the length of a national number's area code, its 0 in: two for a landline, three for the others."""
    return 2 if len(number) == 9 else 3


Form = Callable[[str], str]
FORMS: tuple[Form, ...] = (
    lambda n: n,
    lambda n: f"{n[: area(n)]}-{n[area(n) :]}",
    lambda n: f"{n[: area(n)]} {n[area(n) :]}",
    lambda n: f"{n[: area(n)]}-{n[area(n) : area(n) + 3]}-{n[area(n) + 3 :]}",
    lambda n: f"{n[: area(n)]} {n[area(n) : area(n) + 3]} {n[area(n) + 3 :]}",
    lambda n: f"({n[: area(n)]}) {n[area(n) :]}",
    lambda n: f"+972-{n[1 : area(n)]}-{n[area(n) :]}",
    lambda n: f"00972 {n[1 : area(n)]} {n[area(n) :]}",
)
NUMBERS = [*PHONES.mobile, *PHONES.landline, *PHONES.voip]
LEFT = ("", "טלפון ", "טל' ", "נייד: ", "בפקס ", "(", "ב", "ניתן להתקשר ")
RIGHT = ("", ".", ",", ")", " נמסר", "\n", " ביום שני")
RECALL_ALL = list(product(NUMBERS, FORMS, LEFT, RIGHT))
RECALL = RECALL_ALL if full() else RECALL_ALL[:: len(RECALL_ALL) // FAST]

MOBILE = PHONES.mobile[0]
PIECES = (
    "7", "-", " ", "(", "טלפון ", f"{MOBILE[:3]}-{MOBILE[3:]}", PHONES.landline[0], PHONES.wrong_area[0],
    PHONES.short_line[0], PHONES.abroad_mobile[0],
)  # fmt: skip
SOUND_ALL = ["".join(pieces) for count in range(5) for pieces in product(PIECES, repeat=count)]
SOUND = SOUND_ALL if full() else SOUND_ALL[:: len(SOUND_ALL) // FAST]


def test_the_samples_are_as_many_as_the_rule_asks() -> None:
    assert len(RECALL_ALL) >= INVARIANT_FULL and len(SOUND_ALL) >= INVARIANT_FULL
    assert min(len(RECALL), len(SOUND)) >= (INVARIANT_FULL if full() else FAST)
    assert len(set(NUMBERS)) == 28 and all(OF_THE_PLAN.fullmatch(n) for n in NUMBERS)


def test_invariant_1_found_means_a_number_of_the_plan() -> None:
    bad = []
    for case, text in enumerate(SOUND):
        for detection in Phone().detect(projection(text), CTX):
            if not OF_THE_PLAN.fullmatch(SEPARATORS.sub("", detection.surface)):
                bad.append(case)
    assert bad == []


@pytest.mark.parametrize("chunk", range(4))
def test_invariant_2_every_phone_is_found(chunk: int) -> None:
    missed = []
    for case, (number, form, left, right) in enumerate(RECALL[chunk::4]):
        written = form(number)
        text = f"{left}{written}{right}"
        start = len(left)
        got = [(d.span.start, d.span.end) for d in Phone().detect(projection(text), CTX)]
        if got != [(start, start + len(written))]:
            missed.append(case)
    assert missed == []
