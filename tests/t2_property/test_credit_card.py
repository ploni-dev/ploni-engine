"""Two invariants of the credit card detector over enumerated texts: what it finds is a card, and it finds every card.

Why: build-plan.md Phase 1 asks for a checksum-backed detector at 0.98 recall and precision
(issue #35); the fixture holds the cases someone wrote. CLAUDE.md, Tests: an invariant is held
over 500 generated cases, 5,000 at phase close. Each invariant is enumerated, as
tests/t2_property/test_israeli_id.py is (hypothesis is not installed).

Invariant 1, found means a card: over every sequence of up to four PIECES (10 pieces, 11,111
texts; the full suite runs all, the fast suite every 22nd, 506), each detection's text, its
separators taken out, is 13 to 19 ASCII digits that pass the Luhn check (tests/invented_numbers.py,
apart from the module) and start with a prefix of one of the issuer ranges written there. PIECES
mix a valid card, a near miss, digits that pass the check with no brand's prefix, sixteen zeros,
an ID-length number, digits and separators, so that runs of digits join into longer numbers and
split across separators.

Invariant 2, every card is found: each of NUMBERS (24 invented cards of every list of CARDS), in
each of FORMS (5), after each of LEFT (8: labels, a proclitic glued, a geresh in both forms, a
bracket, nothing) and before each of RIGHT (7, an expiry after one plain space among them, since
the review of ec7d0d4, finding 1): 6,720 texts, all in the full suite, every 13th in the fast one
(517). Each gives exactly one detection, the number's place.

Not applicable: the proclitic and ordinary-word axes of names.
"""

import re
from itertools import product

import pytest

from ploni.detect.base import DetectContext
from ploni.detect.deterministic.credit_card import CreditCard
from tests import invented_numbers as inv
from tests.detector_contract import projection
from tests.invented_numbers import CARDS, ISRAELI_IDS
from tests.sizes import INVARIANT_FULL, full

# CLAUDE.md, Tests: an invariant is held over 500 generated cases, 5,000 at phase close.
FAST = 500
SEPARATORS = re.compile("[-./ \\u00a0\\u05be\\u2013\\u2010\\u2011\\u2012\\u2014\\u2212]")
CTX = DetectContext()
RANGES = (*inv.VISA, *inv.MASTERCARD, *inv.AMEX, *inv.DINERS, *inv.DISCOVER, *inv.JCB, *inv.UNIONPAY)
SHORTEST, LONGEST = 13, 19


def branded(digits: str) -> bool:
    """Say whether digits start with a prefix of one of the issuer ranges of tests/invented_numbers.py."""
    return any(low <= int(digits[: len(str(high))]) <= high for low, high in RANGES)


def by_four(number: str, separator: str) -> str:
    """Write a number in groups of four, the last one shorter, joined by the separator."""
    return separator.join(number[i : i + 4] for i in range(0, len(number), 4))


NUMBERS = [
    *CARDS.visa[:6], *CARDS.visa13, *CARDS.visa19, *CARDS.mastercard[:4], *CARDS.amex[:3], *CARDS.diners[:2],
    *CARDS.discover[:2], *CARDS.jcb[:1], *CARDS.unionpay[:2],
]  # fmt: skip
FORMS = (
    lambda n: n,
    lambda n: by_four(n, " "),
    lambda n: by_four(n, "-"),
    lambda n: by_four(n, " "),
    lambda n: f"{n[:4]} {n[4:10]} {n[10:]}",
)
LEFT = ("", "כרטיס ", "מספר כרטיס האשראי: ", "מס' כרטיס ", "מס׳ כרטיס ", "בכרטיס ויזה ", "(", "VISA ")
RIGHT = ("", ".", ",", ")", " נמסר", "\n", " 12/26")
RECALL_ALL = list(product(NUMBERS, FORMS, LEFT, RIGHT))
RECALL = RECALL_ALL if full() else RECALL_ALL[:: len(RECALL_ALL) // FAST]

VALID = CARDS.visa[0]
PIECES = ("7", "-", " ", "כרטיס ", by_four(VALID, " "), CARDS.near[0], CARDS.nobrand[0], "0000000000000000", ISRAELI_IDS.valid[0], VALID)
SOUND_ALL = ["".join(pieces) for count in range(5) for pieces in product(PIECES, repeat=count)]
SOUND = SOUND_ALL if full() else SOUND_ALL[:: len(SOUND_ALL) // FAST]


def test_the_samples_are_as_many_as_the_rule_asks() -> None:
    assert len(RECALL_ALL) >= INVARIANT_FULL and len(SOUND_ALL) >= INVARIANT_FULL
    assert min(len(RECALL), len(SOUND)) >= (INVARIANT_FULL if full() else FAST)
    assert len(set(NUMBERS)) == 24 and all(inv.luhn_ok(n) and branded(n) for n in NUMBERS)


def test_invariant_1_found_means_a_card() -> None:
    bad = []
    for case, text in enumerate(SOUND):
        for detection in CreditCard().detect(projection(text), CTX):
            digits = SEPARATORS.sub("", detection.surface)
            if not (SHORTEST <= len(digits) <= LONGEST and inv.luhn_ok(digits) and branded(digits)):
                bad.append(case)
    assert bad == []


@pytest.mark.parametrize("chunk", range(4))
def test_invariant_2_every_card_is_found(chunk: int) -> None:
    missed = []
    for case, (number, form, left, right) in enumerate(RECALL[chunk::4]):
        written = form(number)
        text = f"{left}{written}{right}"
        start = len(left)
        got = [(d.span.start, d.span.end) for d in CreditCard().detect(projection(text), CTX)]
        if got != [(start, start + len(written))]:
            missed.append(case)
    assert missed == []
