"""The span property of build-plan.md Phase 1 over generated texts: every span inside, every type declared.

Why: build-plan.md Phase 1, "Tests added": "T2 property: every returned span lies inside the
projection and every returned type is declared." Issue #31. A span that is off by one breaks
the contract only where the match touches an end of the text (T0, A3), which hand-picked
texts reach by luck; generated ones reach it on purpose.

The invariant, for every generated text and every detector of DETECTORS: the check of
tests/detector_contract.py gives no line. That check holds the confidence rule too, so the
property covers it as well.

Generated input: every sequence of 0 to 3 pieces of PIECES, 17 pieces, so 5,220 texts. The
full suite runs all of them (at least the 5,000 of tests/sizes.py); the fast suite runs every
tenth, 522 (at least 500). A piece is one of: a run of digits of one, two or nine
characters; a Hebrew word with final letters, with niqqud, or with gershayim or a geresh in
both forms; a Hebrew abbreviation with dots; a Latin word; a space, a newline, an RLM or LRM
mark; a character outside the BMP. Every piece opens and closes some texts, so a run of digits
does both, and sits next to every other piece.

The property is shown to fail: PastTheEnd, BeforeTheStart and Undeclared each give a line on
some generated text, and the texts include ones that start and ones that end with a digit and
the empty one, the places where the first two break.

Not applicable: the proclitic and ordinary-word axes, as the check judges no word. hypothesis,
which Phase 1 names, is not a dependency of this project (requirements-dev.txt). The texts are
enumerated rather than drawn from `random`, whose seeded use the other T2 tests excuse with a
suppression of ruff's S311 on the line.
"""

from itertools import product

import pytest

from ploni.detect.base import DetectContext, Detector
from tests.detector_contract import BeforeTheStart, Digits, PastTheEnd, Undeclared, breaks, projection
from tests.sizes import INVARIANT_FULL, full

# CLAUDE.md, Tests: an invariant is held over 500 generated cases, 5,000 at phase close.
FAST = 500
MOST_PIECES = 3
PIECES = (
    "7", "42", "123456782", "יעקב", "שָׁלוֹם", "ך ם ן ף ץ", "עו\"ד", "עו״ד", "כב'", "כב׳", "ת.ז.", "Cohen", " ", "\n",
    "‏", "‎", "📄",
)  # fmt: skip
ALL = ["".join(pieces) for count in range(MOST_PIECES + 1) for pieces in product(PIECES, repeat=count)]
TEXTS = ALL if full() else ALL[:: len(ALL) // FAST]

# Each detector of ploni/ is added here as it is written.
DETECTORS: tuple[Detector, ...] = (Digits(),)
CTX = DetectContext()


@pytest.mark.parametrize("detector", DETECTORS, ids=lambda each: each.name)
def test_every_span_is_inside_and_every_type_is_declared(detector: Detector) -> None:
    broken = {index: lines for index, text in enumerate(TEXTS) if (lines := breaks(detector, projection(text), CTX))}
    assert broken == {}


def test_the_texts_are_as_many_as_the_rule_asks() -> None:
    assert len(ALL) >= INVARIANT_FULL
    assert len(TEXTS) >= (INVARIANT_FULL if full() else FAST)


def test_the_texts_reach_both_ends_of_a_run() -> None:
    assert "" in TEXTS
    assert any(text[:1].isdigit() for text in TEXTS)
    assert any(text[-1:].isdigit() for text in TEXTS)


@pytest.mark.parametrize("detector", [PastTheEnd(), BeforeTheStart(), Undeclared()], ids=lambda each: type(each).__name__)
def test_the_property_fails_for_a_detector_that_breaks_it(detector: Detector) -> None:
    assert any(breaks(detector, projection(text), CTX) for text in TEXTS)
