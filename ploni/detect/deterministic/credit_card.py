"""The credit card detector: card numbers that pass the Luhn check and carry a card brand's issuer prefix.

Why: a card number is a key to a person's money and, in a court file, names who paid; build-plan.md
Phase 1, "Credit card": "Luhn plus brand prefix sanity." Recall comes from the wide candidate,
precision from the Luhn check and the issuer ranges, which are never weakened (issue #35).

Contract: `CreditCard` is a Detector (`ploni/detect/base.py`) of type CREDIT_CARD. A detection is
a run of SHORTEST to LONGEST ASCII digits with at most one separator (SEPARATORS of
ploni/detect/deterministic/israeli_id.py) between any two digits; on its left it touches no
digit, nor a digit and one separator, and on its right likewise, but that one plain space and an
expiry (EXPIRY: one or two digits, a slash, two to four digits, no digit after) end the number,
at its right edge and at every step inside it, so that an expiry is never read as more digits of
the card (the review of ec7d0d4, finding 1). Its digits pass `luhn_ok` and
`brand` names a brand whose issuer range holds their prefix and which issues their length. Its
span is the number only, first digit to last, separators included, in code points of the
projection's text (the held-out batch's span rule for CREDIT_CARD); a label before it is read,
never put in the span. Under a card's label (`labelled`) its confidence is CONFIDENCE_LABELLED,
otherwise CONFIDENCE.

The issuer ranges and lengths (BRANDS) are those of ISO/IEC 7812-1 issuer identification numbers
as the card networks publish them for their brands: Visa 4 (13, 16, 19 digits); Mastercard 51-55
and 2221-2720 (16); American Express 34, 37 (15); Diners Club International 300-305, 3095, 36,
38-39 (14 to 19; 3095 added by the review of ec7d0d4, finding 2); Discover 6011, 644-649, 65 (16 to 19); JCB 3528-3589 (16 to 19); UnionPay 62 (16 to
19). They are written from Claude's knowledge of those published tables; no copy of them is in
the repository, and none was downloaded to check them.

Known limits: a card followed by another number after one separator that is no expiry (a security
code after a single space, "... 123"), or by an expiry after a separator other than one plain
space, is read as one longer number and not found; after a comma or a word it is found. An expiry
before the card, one plain space from it, is not an edge: the card is not found. Nor is an expiry
written with spaces around its slash (" 12 / 26") or with a hyphen (" 12-26"): EXPIRY does not
read them, and the card is not found (the review of 2ee56e9 measured 0 of 20 found for each). What the expiry
stop costs, measured by the review of ec7d0d4 on invented texts: random sixteen digits and " 12/26"
give a card 0.023 of the time (the plain Luhn-and-prefix rate), a row of numbers and then a date
0.010 to 0.017, twenty digits in fours and an IBAN-like number 0.000, with the stop and without.
A brand not listed (Maestro, RuPay, Mir, Elo, Verve and others) is not found, nor is a
number outside the listed ranges, also a new range a network opens later. Israeli domestic
Isracard numbers of eight or nine digits are out of scope (#309): they are an ID's length, and the
Israeli ID detector refuses a number under a card's label (its OTHER_LABELS). A number that passes
the check with a brand's prefix is found whatever it is (a reference number). No placeholder
sequence is refused but by the ranges (sixteen zeros has no brand's prefix). A label is read only
as `labelled` reads it. The detection carries no id (detection_id is ""): ids are made just after
detection, with the matter's key, never inside a detector (Achia, 2026-11-26, issue #169, "Use the
secret key (Recommended)").
"""

from __future__ import annotations

import re
from typing import ClassVar

from ploni.detect.base import DetectContext
from ploni.detect.deterministic.israeli_id import _AFTER, _BEFORE, LABEL_WINDOW, SEPARATORS
from ploni.types import Detection, Span, TextProjection

ENTITY_TYPE = "CREDIT_CARD"
# (brand, its issuer ranges as (low, high) prefixes, the lengths it issues): the module docstring
# names the source.
BRANDS = (
    ("visa", ((4, 4),), (13, 16, 19)),
    ("mastercard", ((51, 55), (2221, 2720)), (16,)),
    ("amex", ((34, 34), (37, 37)), (15,)),
    ("diners", ((300, 305), (3095, 3095), (36, 36), (38, 39)), (14, 15, 16, 17, 18, 19)),
    ("discover", ((6011, 6011), (644, 649), (65, 65)), (16, 17, 18, 19)),
    ("jcb", ((3528, 3589),), (16, 17, 18, 19)),
    ("unionpay", ((62, 62),), (16, 17, 18, 19)),
)
SHORTEST = min(length for _, _, lengths in BRANDS for length in lengths)
LONGEST = max(length for _, _, lengths in BRANDS for length in lengths)
_SEP = "[" + re.escape(SEPARATORS) + "]"
# A card's expiry after one plain space, MM/YY or MM/YYYY, M/YY: it ends the card (the review of
# ec7d0d4, finding 1, measured 0.000 found before and 1.000 after on 3,000 invented cards per form).
EXPIRY = r" [0-9]{1,2}/[0-9]{2,4}(?![0-9])"
CANDIDATE = re.compile(
    rf"(?<![0-9])(?<![0-9]{_SEP})[0-9](?:(?!{EXPIRY}){_SEP}?[0-9]){{{SHORTEST - 1},{LONGEST - 1}}}"
    rf"(?![0-9])(?!(?!{EXPIRY}){_SEP}[0-9])"
)
# shortcut: one fixed confidence for every match until calibration (build-plan.md section 4.7,
# detect/calibration.py) gives a measured one; a random run of digits passes the check one time in
# ten and few carry a brand's prefix; a card's label before it is more evidence.
CONFIDENCE = 0.95
CONFIDENCE_LABELLED = 0.99
BAND = "high"
# The labels of a card in Hebrew forms and papers, and the brands' names; with up to two proclitic
# letters glued before a Hebrew one, and no letter right after either, as the ID detector reads its labels.
HEBREW_LABELS = (
    r"כרטיס", r"אשראי", r"ויזה", r"מאסטר\s?קא?רד", r"אמריקן\s+אקספרס", r"אמקס", r"דיינרס", r"ישראכרט", r"לאומי\s?קארד",
)  # fmt: skip
LATIN_LABELS = (r"visa", r"master\s?card", r"amex", r"american\s+express", r"diners", r"card")
LABEL = re.compile(
    rf"{_BEFORE}(?:{'|'.join(HEBREW_LABELS)}){_AFTER}|(?<![A-Za-z])(?i:{'|'.join(LATIN_LABELS)})(?![A-Za-z])"
)


def luhn_ok(digits: str) -> bool:
    """Say whether a string of digits passes the Luhn check of card numbers.

    Why: the check that gives this detector its precision (build-plan.md Phase 1, "Credit card":
    "Luhn"), never weakened.

    Contract: `digits`, the number with its separators taken out. True when it is ASCII digits
    only, at least one, that, from the right, weighed 1, 2, 1, 2, ... with the digits of each
    product summed, add up to a multiple of 10. False otherwise, also for "".

    Known limits: it says nothing of the length or the prefix; `brand` does.
    """
    if not (digits.isascii() and digits.isdigit()):
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def brand(digits: str) -> str | None:
    """Return the card brand whose issuer range holds a number's prefix at its length, or None.

    Why: build-plan.md Phase 1's "brand prefix sanity": a number that passes the check but that no
    brand issues is not a card.

    Contract: `digits`, ASCII digits. The first brand of BRANDS whose ranges hold the number's
    first digits (as many as the range's bounds have) and whose lengths hold its length; None
    when none does. The check digit is not read.

    Known limits: the brands and ranges of BRANDS only (the module docstring).
    """
    for name, ranges, lengths in BRANDS:
        if len(digits) in lengths and any(low <= int(digits[: len(str(high))]) <= high for low, high in ranges):
            return name
    return None


def labelled(text: str, start: int) -> bool:
    """Say whether a card's label stands before a number.

    Why: a form says what a number is by its label; a card's label is more evidence than the check.

    Contract: `start` is the number's first character in `text`. Looks at the LABEL_WINDOW
    characters before it, on its line, after the last digit there (str.isdigit), as the ID
    detector does; True when one of HEBREW_LABELS or LATIN_LABELS (in any case) stands there.

    Known limits: a label further away, on the line before, or not listed is not seen.
    """
    line = text.rfind("\n", 0, start) + 1
    window = text[max(line, start - LABEL_WINDOW) : start]
    last_digit = max((i for i, ch in enumerate(window) if ch.isdigit()), default=-1)
    return LABEL.search(window[last_digit + 1 :]) is not None


class CreditCard:
    """The detector of credit card numbers, CREDIT_CARD.

    Why: the second deterministic detector of Phase 1 (issue #35), registered in
    eval.detectors.DETECTORS, so the held-out batch scores it and the T0 suite checks it.

    Contract: a Detector; `detect` returns one detection per candidate whose digits pass
    `luhn_ok` and have a `brand`, in the order of the text, as the module docstring says.

    Known limits: those of the module.
    """

    name: ClassVar[str] = "credit_card"
    produces: ClassVar[frozenset[str]] = frozenset({ENTITY_TYPE})
    requires_morph: ClassVar[bool] = False

    def detect(self, proj: TextProjection, ctx: DetectContext) -> list[Detection]:
        """Find the credit card numbers in the text of one projection.

        Why: the one call fusion makes of this detector.

        Contract: returns a Detection per number, with the part of `proj`, its surface the text
        of its span, CONFIDENCE_LABELLED under a card's label and CONFIDENCE otherwise, BAND, no
        base span, and detection_id "" (the module docstring). Raises nothing.

        Known limits: those of the module.
        """
        found = []
        for match in CANDIDATE.finditer(proj.text):
            digits = re.sub(_SEP, "", match.group())
            if luhn_ok(digits) and brand(digits) is not None:
                confidence = CONFIDENCE_LABELLED if labelled(proj.text, match.start()) else CONFIDENCE
                span = Span(match.start(), match.end())
                found.append(Detection("", proj.part, span, match.group(), ENTITY_TYPE, confidence, BAND, self.name, None))
        return found
