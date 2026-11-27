"""Two invariants of the company number detector over enumerated texts: what it finds is a company's or a non-profit's number, and it finds every one.

Why: build-plan.md Phase 1 asks for a checksum-backed detector at 0.98 recall and precision; the
fixture holds the cases someone wrote. CLAUDE.md, Tests: an invariant is held over 500 generated
cases, 5,000 at phase close. Each invariant here is enumerated, as tests/t2_property/
test_israeli_id.py is.

Invariant 1, found means valid: over every sequence of up to four PIECES (11,111 texts; the full
suite runs all, the fast suite every 22nd, 506), each detection's text, its separators taken out,
is nine ASCII digits that pass the checksum (computed here, apart from the module) and start
with 5, and its type is NONPROFIT_NUMBER exactly when they start with 58. PIECES mix a company
number, a non-profit number, a near miss, an ID, digits, separators and a company label, so that
runs of digits join into longer numbers and split across separators.

Invariant 2, every number is found: each of NUMBERS (the 30 invented company and 30 non-profit
numbers of tests/invented_numbers.py), in each of FORMS (5) after each of LABELLED (5: the
company labels with each gershayim, a proclitic), and in each of ANY_LABEL_FORMS (the 4 but two
and seven, a mobile's shape without its 0, which counts only under a company label) with no
label, before each of RIGHT (4): 6,000 and 960 texts, 6,960, all in the full suite, every 13th
in the fast one (536). Each gives exactly one detection, the number's place and type.

Not applicable: the proclitic and ordinary-word axes of names.
"""

import re
from itertools import product

import pytest

from ploni.detect.base import DetectContext
from ploni.detect.deterministic.company_number import CompanyNumber
from tests.detector_contract import projection
from tests.invented_numbers import ISRAELI_IDS
from tests.sizes import INVARIANT_FULL, full

# CLAUDE.md, Tests: an invariant is held over 500 generated cases, 5,000 at phase close.
FAST = 500
SEPARATORS = re.compile("[-./ \\u00a0\\u05be\\u2013\\u2010\\u2011\\u2012\\u2014\\u2212]")
CTX = DetectContext()


def checksum(digits: str) -> bool:
    """Say whether nine digits pass the check of build-plan.md Phase 1, written apart from the module."""
    doubled = [int(ch) * (2 if i % 2 else 1) for i, ch in enumerate(digits)]
    return sum(n - 9 if n > 9 else n for n in doubled) % 10 == 0


NUMBERS = [*ISRAELI_IDS.company, *ISRAELI_IDS.nonprofit]
ANY_LABEL_FORMS = (
    lambda n: n,
    lambda n: f"{n[:2]}-{n[2:8]}-{n[8]}",
    lambda n: f"{n[:3]}-{n[3:6]}-{n[6:]}",
    lambda n: f"{n[:3]} {n[3:6]} {n[6:]}",
)
# Two and seven, a mobile's shape without its 0, is a company's only under a company label.
FORMS = (*ANY_LABEL_FORMS, lambda n: f"{n[:2]}-{n[2:]}")
LABELLED = ("ח.פ. ", "ח\"פ ", "ע״ר ", "ע''ר ", "וח.פ.")
RIGHT = ("", ".", ")", " נרשמה")
RECALL_ALL = list(product(NUMBERS, FORMS, LABELLED, RIGHT)) + list(product(NUMBERS, ANY_LABEL_FORMS, ("",), RIGHT))
RECALL = RECALL_ALL if full() else RECALL_ALL[:: len(RECALL_ALL) // FAST]

COMPANY = ISRAELI_IDS.company[0]
PIECES = (
    "7", "-", " ", "ח.פ. ", COMPANY, ISRAELI_IDS.nonprofit[0], COMPANY[:8] + str((int(COMPANY[8]) + 1) % 10), ISRAELI_IDS.valid[0],
    f"{COMPANY[:2]}-{COMPANY[2:]}", "5",
)  # fmt: skip
SOUND_ALL = ["".join(pieces) for count in range(5) for pieces in product(PIECES, repeat=count)]
SOUND = SOUND_ALL if full() else SOUND_ALL[:: len(SOUND_ALL) // FAST]


def test_the_samples_are_as_many_as_the_rule_asks() -> None:
    assert len(RECALL_ALL) >= INVARIANT_FULL and len(SOUND_ALL) >= INVARIANT_FULL
    assert min(len(RECALL), len(SOUND)) >= (INVARIANT_FULL if full() else FAST)
    assert all(checksum(n) and n[0] == "5" for n in NUMBERS) and len(set(NUMBERS)) == 60


def test_invariant_1_found_means_valid() -> None:
    bad = []
    for text in SOUND:
        for detection in CompanyNumber().detect(projection(text), CTX):
            digits = SEPARATORS.sub("", detection.surface)
            valid = len(digits) == 9 and digits.isascii() and digits.isdigit() and checksum(digits) and digits[0] == "5"
            kind = "NONPROFIT_NUMBER" if digits.startswith("58") else "COMPANY_NUMBER"
            if not valid or detection.entity_type != kind:
                bad.append((text, detection.surface))
    assert bad == []


@pytest.mark.parametrize("chunk", range(4))
def test_invariant_2_every_number_is_found(chunk: int) -> None:
    missed = []
    for number, form, left, right in RECALL[chunk::4]:
        written = form(number)
        text = left + written + right
        kind = "NONPROFIT_NUMBER" if number.startswith("58") else "COMPANY_NUMBER"
        got = [(d.span.start, d.span.end, d.entity_type) for d in CompanyNumber().detect(projection(text), CTX)]
        if got != [(len(left), len(left) + len(written), kind)]:
            missed.append(text)
    assert missed == []
