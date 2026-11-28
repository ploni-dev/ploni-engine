"""Two invariants of the IBAN and bank account detector over enumerated texts: what it finds is an IBAN or a triple, and it finds every one.

Why: build-plan.md Phase 1 asks for a checksum-backed detector at 0.98 recall and precision (the
IBAN), and reports the numbers of the pattern-only triples; the fixture holds the cases someone
wrote. CLAUDE.md, Tests: an invariant is held over 500 generated cases, 5,000 at phase close.
Each invariant here is enumerated, as tests/t2_property/test_israeli_id.py is.

Invariant 1, found means valid: over every sequence of up to four PIECES (11,111 texts; the full
suite runs all, the fast suite every 22nd, 506), each IBAN detection's text, its separators taken
out, is IL (in either case) and 21 ASCII digits whose ISO 7064 MOD 97-10 remainder, computed here
digit by digit apart from the module (tests/invented_numbers.py, iban_remainder), is 1; each BANK_ACCOUNT detection's text starts and ends
with an ASCII digit, touches no digit or Latin letter on its left, and either holds at least
three runs of digits and has a bank word inside it or a bank label in the twenty characters
before it, or (issue #315) ends with an account of 4 to 13 digits in one or two runs that an
account word stands right before, with only the module's glue and מס' between; and no two detections
share a character. PIECES mix an IBAN, a near miss, IL, a grouped triple, an account number,
digits, separators and the bank words, so that runs of digits join and split.

Invariant 2, every one is found: each of the 40 invented IBANs in each of IBAN_FORMS (8, two
spaces between groups and an RLM after IL among them, finding 5 of the review of #34 at
28b6032) after each of IBAN_LEFT (6) before each of RIGHT (4), 7,680 texts; each of the 40 invented triples in
each of WORDED (4) after each of WORDED_LEFT (3) before each of RIGHT, 1,920, in each of
GROUPED (4) after each of LABELLED (6, the possessives among them) before each of RIGHT, 3,840,
and in each of BY_NAME (2, the bank named by its name) after nothing or ו before each of RIGHT,
640; since issue #315, each of the 40 accounts in each of ALONE (4, with no bank's number) after
each of ALONE_LEFT (6) before each of RIGHT, 3,840, and in each of BRANCHED (2, a branch and an
account) after nothing or a bank's name before each of RIGHT, 640: 18,560 in all, all in the
full suite, every 37th in the fast one (502). Each gives exactly one detection, the item's place
and type.

Not applicable: the proclitic and ordinary-word axes of names.
"""

import re
from itertools import product

import pytest

from ploni.detect.base import DetectContext
from ploni.detect.deterministic.iban import Iban
from tests.detector_contract import projection
from tests.invented_numbers import BANK_NUMBERS
from tests.invented_numbers import iban_remainder as remainder
from tests.sizes import INVARIANT_FULL, full

# CLAUDE.md, Tests: an invariant is held over 500 generated cases, 5,000 at phase close.
FAST = 500
# The separators, and the marks of direction an IBAN may carry between its characters (finding 5).
SEPARATORS = re.compile("[-./ \\u00a0\\u05be\\u2013\\u2010\\u2011\\u2012\\u2014\\u2212\\u200e\\u200f]")
BANK_WORDS = re.compile("חשבון|ח[-\\u05be\\u2013]ן|ח(?:[\"\\u05f4]|'')ן|בנק|סניף")
CTX = DetectContext()


IBAN_FORMS = (
    lambda n: n,
    lambda n: " ".join(n[i : i + 4] for i in range(0, 23, 4)),
    lambda n: " ".join(n[i : i + 4] for i in range(0, 23, 4)),
    lambda n: "-".join(n[i : i + 4] for i in range(0, 23, 4)),
    lambda n: f"{n[:2]} {n[2:]}",
    lambda n: "il" + n[2:],
    lambda n: "  ".join(n[i : i + 4] for i in range(0, 23, 4)),
    lambda n: n[:2] + "\u200f" + " ".join(n[i : i + 4] for i in range(0, 23, 4))[2:],
)
IBAN_LEFT = ("", "IBAN: ", "חשבון ", "ב", "(", "לחשבון מס' ")
RIGHT = ("", ".", ")", " בבנק")
# A triple with words between its numbers: (the text, the place of the item in it).
WORDED = (
    lambda n: f"{n[:2]} סניף {n[2:5]} חשבון {n[5:11]}",
    lambda n: f"{n[:2]}, סניף {n[2:5]}, ח-ן {n[5:12]}",
    lambda n: f"{n[:2]} בסניף מס' {n[2:5]} ובחשבון {n[5:13]}",
    lambda n: f'{n[:2]} סניף: {n[2:5]} ח"ן: {n[5:]}',
)
WORDED_LEFT = ("", "בנק ", "לבנק ")
GROUPED = (
    lambda n: f"{n[:2]}-{n[2:5]}-{n[5:11]}",
    lambda n: f"{n[:2]}/{n[2:5]}/{n[5:12]}",
    lambda n: f"{n[:2]}.{n[2:5]}.{n[5:13]}",
    lambda n: f"{n[:2]} {n[2:5]} {n[5:]}",
)
# The possessive labels, by the review of #34 at 28b6032, finding 3.
LABELLED = ("חשבון ", "ח-ן ", 'ח"ן ', "פרטי חשבון הבנק: ", "בחשבונו ", "לחשבונה ")
# A triple whose bank is named by its name, no number: (the text, its item from the branch on).
BY_NAME = (
    lambda n: (f"בנק לאומי, סניף {n[2:5]}, חשבון {n[5:11]}", f"{n[2:5]}, חשבון {n[5:11]}"),
    lambda n: (f"בבנק הפועלים בסניף {n[2:5]} בחשבונו {n[5:13]}", f"{n[2:5]} בחשבונו {n[5:13]}"),
)
# Issue #315: an account with no bank's number, right after an account word. Nine digits start
# with n[0], never 0, so that none is a landline, which the phone detector takes (#36); four
# digits start with 3 to 9, so that none is a year, which the detector refuses (the review of
# #315 at d6bfbd6, N2).
ALONE = (
    lambda n: n[5:11],
    lambda n: n[0] + n[6:],
    lambda n: str(3 + int(n[0]) % 7) + n[1:4],
    lambda n: f"{n[2:5]}-{n[5:11]}",
)
# The words of an account alone: חשבון, ח-ן and ח"ן with proclitics, no possessive form (the
# review of #315 at d6bfbd6, finding 2).
ALONE_LEFT = ("חשבון ", "ח-ן ", 'ח"ן ', "חשבון מס' ", "בחשבון ", "לחשבון: ")
# A branch and an account, no bank's number: (the text, its item from the branch on).
BRANCHED = (
    lambda n: (f"סניף {n[2:5]} חשבון {n[5:11]}", f"{n[2:5]} חשבון {n[5:11]}"),
    lambda n: (f"בסניף מס' {n[2:5]}, ח-ן {n[5:13]}", f"{n[2:5]}, ח-ן {n[5:13]}"),
)
RECALL_ALL = (
    [(form(n), left, right, "IBAN") for n, form, left, right in product(BANK_NUMBERS.iban, IBAN_FORMS, IBAN_LEFT, RIGHT)]
    + [(form(n), left, right, "BANK_ACCOUNT") for n, form, left, right in product(BANK_NUMBERS.account, WORDED, WORDED_LEFT, RIGHT)]
    + [(form(n), left, right, "BANK_ACCOUNT") for n, form, left, right in product(BANK_NUMBERS.account, GROUPED, LABELLED, RIGHT)]
    + [(form(n), left, right, "BANK_ACCOUNT") for n, form, left, right in product(BANK_NUMBERS.account, BY_NAME, ("", "ו"), RIGHT)]
    + [(form(n), left, right, "BANK_ACCOUNT") for n, form, left, right in product(BANK_NUMBERS.account, ALONE, ALONE_LEFT, RIGHT)]
    + [(form(n), left, right, "BANK_ACCOUNT") for n, form, left, right in product(BANK_NUMBERS.account, BRANCHED, ("", "בנק לאומי "), RIGHT)]
)  # fmt: skip
RECALL = RECALL_ALL if full() else RECALL_ALL[:: len(RECALL_ALL) // FAST]

IBAN = BANK_NUMBERS.iban[0]
ACCOUNT = BANK_NUMBERS.account[0]
PIECES = (
    "7", "-", " ", "חשבון ", " סניף ", " ".join(IBAN[i : i + 4] for i in range(0, 23, 4)), BANK_NUMBERS.iban_near[0], "IL",
    f"{ACCOUNT[:2]}-{ACCOUNT[2:5]}-{ACCOUNT[5:11]}", ACCOUNT[5:11],
)  # fmt: skip
SOUND_ALL = ["".join(pieces) for count in range(5) for pieces in product(PIECES, repeat=count)]
SOUND = SOUND_ALL if full() else SOUND_ALL[:: len(SOUND_ALL) // FAST]


def test_the_samples_are_as_many_as_the_rule_asks() -> None:
    assert len(RECALL_ALL) >= INVARIANT_FULL and len(SOUND_ALL) >= INVARIANT_FULL
    assert min(len(RECALL), len(SOUND)) >= (INVARIANT_FULL if full() else FAST)
    assert all(remainder(n) == 1 for n in BANK_NUMBERS.iban) and len(set(BANK_NUMBERS.account)) == 40


def iban_is_valid(surface: str) -> bool:
    """Say whether an IBAN detection's text is IL and 21 ASCII digits that pass the check, computed here."""
    chars = SEPARATORS.sub("", surface)
    return chars[:2].upper() == "IL" and len(chars) == 23 and chars[2:].isascii() and chars[2:].isdigit() and remainder(chars) == 1


# Issue #315: an account of one or two runs of digits at the end of a detection, and the account
# word right before it, with only the module's glue between (spaces, commas, colons, semicolons,
# dots, brackets, hyphens) and מס'.
ACCOUNT_AT_END = re.compile("[0-9]+(?:[-/][0-9]+)?$")
ACCOUNT_WORD_BEFORE = re.compile("(?:חשבון|ח-ן|ח\"ן)[\\s,:;.()\\-\\u05be\\u2013]*(?:מס' )?$")
# The digits of an account, 4 to 13, written apart from the module's ACCOUNT_SHORTEST and ACCOUNT_LONGEST.
ACCOUNT_DIGITS = range(4, 14)


def account_is_valid(text: str, start: int, surface: str) -> bool:
    """Say whether a BANK_ACCOUNT detection is three runs of digits with bank evidence, or an account after its word, with its edges."""
    runs = re.findall("[0-9]+", surface)
    edges = surface[0] in "0123456789" and surface[-1] in "0123456789"
    left = text[start - 1] if start else ""
    evidence = BANK_WORDS.search(surface) is not None or BANK_WORDS.search(text[max(0, start - 20) : start]) is not None
    tail = ACCOUNT_AT_END.search(surface)
    after_word = (
        tail is not None
        and len(re.sub("[^0-9]", "", tail.group())) in ACCOUNT_DIGITS
        and ACCOUNT_WORD_BEFORE.search(text[: start + tail.start()]) is not None
    )
    return edges and not (left.isascii() and left.isalnum()) and ((len(runs) >= 3 and evidence) or after_word)


def test_invariant_1_found_means_valid() -> None:
    bad = []
    for text in SOUND:
        detections = Iban().detect(projection(text), CTX)
        places = sorted((d.span.start, d.span.end) for d in detections)
        if any(a_end > b_start for (_, a_end), (b_start, _) in zip(places, places[1:], strict=False)):
            bad.append((text, "overlap"))
        for d in detections:
            ok = iban_is_valid(d.surface) if d.entity_type == "IBAN" else account_is_valid(text, d.span.start, d.surface)
            if not ok:
                bad.append((text, d.surface))
    assert bad == []


@pytest.mark.parametrize("chunk", range(4))
def test_invariant_2_every_one_is_found(chunk: int) -> None:
    missed = []
    for written, left, right, kind in RECALL[chunk::4]:
        whole, item = written if isinstance(written, tuple) else (written, written)
        text = left + whole + right
        start = len(left) + whole.index(item)
        got = [(d.span.start, d.span.end, d.entity_type) for d in Iban().detect(projection(text), CTX)]
        if got != [(start, start + len(item), kind)]:
            missed.append(text)
    assert missed == []
