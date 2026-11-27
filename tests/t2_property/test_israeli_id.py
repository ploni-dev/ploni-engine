"""Two invariants of the Israeli ID detector over enumerated texts: what it finds is an ID, and it finds every ID.

Why: build-plan.md Phase 1 asks for a checksum-backed detector at 0.98 recall and precision; the
fixture holds the cases someone wrote. CLAUDE.md, Tests: an invariant is held over 500 generated
cases, 5,000 at phase close. Each invariant here is enumerated, as tests/t2_property/
test_detect_base.py is (hypothesis is not installed; no seeded `random` needs a suppression).

Invariant 1, found means valid: over every sequence of up to four PIECES (11,111 texts; the full
suite runs all, the fast suite every 22nd, 506), each detection's text, its separators taken out,
is nine ASCII digits that pass the checksum (computed here, apart from the module), does not
start with 5, and is not nine equal digits. PIECES mix a valid number, a near miss, a company
number, a trivial number, a landline shape, digits and separators, so that runs of digits join
into longer numbers and split across separators.

Invariant 2, every ID is found: each of NUMBERS (20 invented valid numbers, completed with the
check digit computed here), in each of FORMS (6), after each of LEFT (9 labels, with both
gershayim and both gereshes, a proclitic glued, Latin, nothing) and before each of RIGHT (6):
6,480 texts, all in the full suite, every 12th in the fast one (540). Each gives exactly one
detection, the number's place.

Not applicable: the proclitic and ordinary-word axes of names. A landline written with no
separator is found as an ID (the module's Known limits); none is among the pieces.
"""

import re
from itertools import product

import pytest

from ploni.detect.base import DetectContext
from ploni.detect.deterministic.israeli_id import IsraeliId
from tests.detector_contract import projection
from tests.invented_numbers import ISRAELI_IDS
from tests.sizes import INVARIANT_FULL, full

# CLAUDE.md, Tests: an invariant is held over 500 generated cases, 5,000 at phase close.
FAST = 500
SEPARATORS = re.compile("[-./  ־–]")
CTX = DetectContext()


def checksum(digits: str) -> bool:
    """Say whether nine digits pass the check of build-plan.md Phase 1, written apart from the module."""
    doubled = [int(ch) * (2 if i % 2 else 1) for i, ch in enumerate(digits)]
    return sum(n - 9 if n > 9 else n for n in doubled) % 10 == 0


def complete(eight: str) -> str:
    """Return eight digits with the check digit that makes them valid."""
    return next(eight + c for c in "0123456789" if checksum(eight + c))


# Invented eight-digit stems from a fixed arithmetic sequence, spread over the first digits (0 too);
# those starting with 5 left out, as an ID does not (build-plan.md Phase 1: companies start with 5).
STEMS = (f"{(i * 45678913 + 13579246) % 100000000:08d}" for i in range(30))
NUMBERS = [number for number in map(complete, STEMS) if number[0] != "5"][:20]
FORMS = (
    lambda n: n,
    lambda n: f"{n[:8]}-{n[8]}",
    lambda n: f"{n[:3]}-{n[3:6]}-{n[6:]}",
    lambda n: f"{n[:3]}.{n[3:6]}.{n[6:]}",
    lambda n: f"{n[:3]} {n[3:6]} {n[6:]}",
    lambda n: f"{n[:8]}־{n[8]}",
)
LEFT = ("", "ת.ז. ", "ת\"ז ", "ת״ז ", "מס' זהות ", "מס׳ זהות ", "ות.ז.", "(", "ID ")
RIGHT = ("", ".", ",", ")", " נמסר", "\n")
RECALL_ALL = list(product(NUMBERS, FORMS, LEFT, RIGHT))
RECALL = RECALL_ALL if full() else RECALL_ALL[:: len(RECALL_ALL) // FAST]

VALID = NUMBERS[0]
PIECES = ("7", "-", " ", ".", "ת.ז. ", VALID[:8] + str((int(VALID[8]) + 1) % 10), ISRAELI_IDS.company[0], "000000000", f"{ISRAELI_IDS.landline[0][:2]}-{ISRAELI_IDS.landline[0][2:]}", VALID)
SOUND_ALL = ["".join(pieces) for count in range(5) for pieces in product(PIECES, repeat=count)]
SOUND = SOUND_ALL if full() else SOUND_ALL[:: len(SOUND_ALL) // FAST]


def test_the_samples_are_as_many_as_the_rule_asks() -> None:
    assert len(RECALL_ALL) >= INVARIANT_FULL and len(SOUND_ALL) >= INVARIANT_FULL
    assert min(len(RECALL), len(SOUND)) >= (INVARIANT_FULL if full() else FAST)
    assert all(checksum(n) and n[0] != "5" for n in NUMBERS) and len(set(NUMBERS)) == 20


def test_invariant_1_found_means_valid() -> None:
    bad = []
    for text in SOUND:
        for detection in IsraeliId().detect(projection(text), CTX):
            digits = SEPARATORS.sub("", detection.surface)
            if not (len(digits) == 9 and digits.isascii() and digits.isdigit() and checksum(digits)):
                bad.append((text, detection.surface))
            elif digits[0] == "5" or len(set(digits)) == 1:
                bad.append((text, detection.surface))
    assert bad == []


@pytest.mark.parametrize("chunk", range(4))
def test_invariant_2_every_id_is_found(chunk: int) -> None:
    missed = []
    for number, form, left, right in RECALL[chunk::4]:
        written = form(number)
        text = left + written + right
        got = [(d.span.start, d.span.end) for d in IsraeliId().detect(projection(text), CTX)]
        if got != [(len(left), len(left) + len(written))]:
            missed.append(text)
    assert missed == []
