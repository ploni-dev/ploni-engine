"""The Israeli ID detector: nine-digit identity numbers that pass their check digit.

Why: an identity number names one person for life, and leaking it is the damage the product
exists to prevent; its check digit gives a precision a pattern alone cannot (build-plan.md
Phase 1, "Israeli ID": "Nine digits, last is a check digit, Luhn-style ... Separator-tolerant
candidate regex, strip, validate. Reject trivial sequences."). Recall comes from the wide
candidate, precision from the checksum, which is never weakened.

Contract: `IsraeliId` is a Detector (`ploni/detect/base.py`) of type IL_ID. A detection is a run
of nine ASCII digits, or of SHORT_LENGTH to eight right after an ID label (an ID written without
its leading zeros; "right after" as `label_before` reads it: the label within LABEL_WINDOW, 20,
characters before the number, on its line, with no digit between), with at most one separator
(SEPARATORS) between any two digits. Its edges: on its left it touches no digit, nor a digit and
one separator; on its right no run of separators, of any length, and then a digit follows (since
change 3 of issue #32), but for nine digits after an ID label (`label_before` "id"), where a
plain space (U+0020) and then another number may follow: the space ends the ID, as in "ת.ז.
<id> 1.1.2020" (issue #299, narrowed after the independent review of e2bcb86, whose measured
false IDs, an amount or a row of numbers grouped by plain spaces, carry no ID label). The other
separators keep the edges, and so do the short forms. Its digits, padded with zeros to nine,
pass `israeli_id_checksum_ok`, do not start with COMPANY_PREFIX and are not trivial
(`is_trivial`); its written shape is not that of another number (`is_other_shape`); no label of
another number stands before it, unless an ID label stands there too, as in a combined form
label, "ת.ז./דרכון" (`label_before`; issue #299). Its span is the number only, first digit to
last, separators included, in code points of the projection's text (the held-out batch's span
rule for IL_ID); the label before it is read, never put in the span. Under an ID label its
confidence is CONFIDENCE_LABELLED, otherwise CONFIDENCE.

Known limits: a landline written as nine digits with no separator (0X1234567) and no phone label
is found as an ID; written with separators, 0X-XXXXXXX, 0X-XXX-XXXX or 0X XXX XXXX, it is not
(`is_other_shape`, issue #302), nor is an ID written in those groups, but under an ID label,
where 0X-XXX-XXXX and 0X XXX XXXX are read as an ID and 0X-XXXXXXX is refused, as before #302.
The trade, measured on invented texts (3,000 per form): a landline in groups of two, three and
four with no label is found 0.000 of the time (0.095 and 0.096 before #302), and an ID in those
groups under an ID label 1.000 (0.949 when the groups counted under any label); an ID written
0X-XXXXXXX under an ID label 0.949 (0.484 of IDs that start with 0), the same as before #302.
After an ID label, a
longer number grouped by plain spaces gives up its first nine digits, found as an ID when they
pass the checksum (one in ten). With no ID label, an ID with another number after it by a plain
space ("<id> 3 ילדים") is not found; nor is one right after another number and a plain space
("סעיף 3 <id>", the second of two IDs one space apart), under a label or not, since that
number's digits cut the label off. An ID written without its leading zeros is not found with no
ID label before it, nor with a plain space and a digit after it, and never found when six
digits or fewer are left (three leading zeros or more). A valid
number under the label of another number (OTHER_LABELS: a health fund member's, a client's, a
card's, ...) is dropped, not flagged as that number: no other detector on main finds it yet. A
valid number in another context whose label is not one of OTHER_LABELS (a reference number) is
found as an ID. The detection carries no id (detection_id is ""): ids are made just after
detection, with the matter's key, never inside a detector (Achia, 2026-11-26, issue #169, "Use
the secret key (Recommended)").
"""

from __future__ import annotations

import re
from typing import ClassVar

from ploni.detect.base import DetectContext
from ploni.types import Detection, Span, TextProjection

ENTITY_TYPE = "IL_ID"
# build-plan.md Phase 1: "Nine digits, last is a check digit".
ID_LENGTH = 9
# The fewest digits of an ID written without its leading zeros, read only after an ID label: the
# plan's checksum pads with zeros (`digits.zfill(9)`); that IDs with three leading zeros are not
# issued in practice is Claude's reading, with no source; six digits are too common in other numbers.
SHORT_LENGTH = 7
# build-plan.md Phase 1: "companies (ח.פ.) start with `5`, non-profits (ע.ר.) with `58`": a number
# that starts with 5 is a company's or an association's, not a person's.
COMPANY_PREFIX = "5"
# build-plan.md Phase 1, "Israeli phone": landline area codes `0[23489]`.
AREA_CODES = "23489"
# The groups a landline is written in: a 0 and its area code, then its seven digits in one group
# (0X-XXXXXXX) or in three and four (0X-XXX-XXXX, 0X XXX XXXX; issue #302).
LANDLINE_GROUPS = ([2, 7], [2, 3, 4])
# Under an ID label only the one group is a landline's, as on main: there a number in groups of
# three and four is most likely an ID (the review of 7a99fa8, finding 1, issue #302).
LABELLED_LANDLINE_GROUPS = ([2, 7],)
# build-plan.md Phase 1, "Court case numbers": Net HaMishpat style `NNNNN-MM-YY`.
CASE_NUMBER_GROUPS = [5, 2, 2]
# Hyphen, dot, slash, space, no-break space, maqaf (U+05BE) and en dash: the separators the held-out
# batch's span rules name ("hyphen, space, dot, slash"), and the forms of them Hebrew text uses; and
# the hyphens of word processors and PDF text: the Unicode hyphen (U+2010), the non-breaking hyphen
# Word inserts (U+2011), the figure dash (U+2012), the em dash (U+2014), the minus sign (U+2212).
SEPARATORS = "-./  ־–‐‑‒—−"
_SEP = "[" + re.escape(SEPARATORS) + "]"
# The separators but the plain space: after an ID label, a plain space after nine digits ends the
# number, as Hebrew text writes a date, a count or an age after an ID (issue #299, finding 3).
_TIGHT = "[" + re.escape(SEPARATORS.replace(" ", "")) + "]"
# A number is not followed by a run of separators and a digit: it would be part of a longer one.
# For nine digits, a run that starts with a plain space may be another number's edge; whether it
# is, `is_israeli_id` decides by the label (NUMBER_AFTER). The short forms keep the whole run.
CANDIDATE = re.compile(
    rf"(?<![0-9])(?<![0-9]{_SEP})[0-9](?:{_SEP}?[0-9]){{{ID_LENGTH - 1}}}(?![0-9])(?!{_TIGHT}{_SEP}*[0-9])"
    rf"|(?<![0-9])(?<![0-9]{_SEP})[0-9](?:{_SEP}?[0-9]){{{SHORT_LENGTH - 1},{ID_LENGTH - 2}}}(?!{_SEP}*[0-9])"
)
# Another number right after a candidate: a run of separators and a digit.
NUMBER_AFTER = re.compile(rf"{_SEP}*[0-9]")
# shortcut: one fixed confidence for every checksum match until calibration (build-plan.md
# section 4.7, detect/calibration.py) gives a measured one; a random nine-digit number passes the
# check one time in ten, and an ID label before it is more evidence.
CONFIDENCE = 0.95
CONFIDENCE_LABELLED = 0.99
BAND = "high"
# How far before a number its label is looked for, in characters on the same line: a label and
# the few words forms put between it and the number ("מס'", a colon, "של המבקש").
LABEL_WINDOW = 20
# A label: up to two proclitic letters glued before it (ו, ב, ל, ה, ש, מ, כ), no Hebrew letter
# before those, and none right after the label, so that its letters inside a longer word do not count.
_BEFORE = r"(?<![א-ת])[ובלהשמכ]{0,2}"
_AFTER = r"(?![א-ת])"
# Gershayim: the ASCII quotation mark, the Hebrew sign (U+05F4), or two ASCII apostrophes, as Word
# and typists write them when no gershayim key is at hand (issue #299, finding 7).
_GERSHAYIM = r"(?:[\"״]|'')"
# The labels of an ID in forms and court papers: ת.ז. with or without its dots, ת"ז with any
# gershayim, תעודת זהות, מס' זהות and מספר זהות with either geresh, and the Latin ID.
ID_LABELS = (
    r"ת\.\s?ז\.?", rf"ת{_GERSHAYIM}ז", r"תעודת\s+(?:ה)?זהות", r"מס(?:['׳]|פר)\s*(?:(?:ה)?תעודת\s+)?(?:ה)?זהות",
)  # fmt: skip
# The labels of the numbers that are not an ID and are written the same way: company and
# non-profit (build-plan.md Phase 1), passport, bank account, phone, health fund, military,
# licence and card numbers.
OTHER_LABELS = (
    r"ח\.\s?פ\.?", rf"ח{_GERSHAYIM}פ", r"ע\.\s?ר\.?", rf"ע{_GERSHAYIM}ר", r"דרכון", r"חשבון", r"סניף", r"בנק", r"טלפון",
    r"טל['׳.]", r"פקס", r"נייד", r"פלאפון", r"קופת\s+חולים", rf"קופ{_GERSHAYIM}ח",
    r"מס(?:['׳]|פר)\s*(?:חבר|אישי|רישוי|רכב|לקוח|תיק)", r"מ\.\s?א\.?", rf"מ{_GERSHAYIM}א", r"רישיון", r"רישוי", r"כרטיס",
    r"אשראי",
)  # fmt: skip
LABEL = re.compile(
    rf"(?P<id>{_BEFORE}(?:{'|'.join(ID_LABELS)}){_AFTER}|(?<![A-Za-z])I\.?D\.?(?![A-Za-z]))"
    rf"|(?P<other>{_BEFORE}(?:{'|'.join(OTHER_LABELS)}){_AFTER})"
)


def israeli_id_checksum_ok(digits: str) -> bool:
    """Say whether a string of digits passes the Israeli ID check digit.

    Why: the check that gives this detector its precision; it is build-plan.md Phase 1's
    function, as written there, and never weakened.

    Contract: `digits`, the number with its separators taken out. True when it is at most nine
    characters, all digits (str.isdigit), that, padded with leading zeros to nine and weighed
    1, 2, 1, 2, ... with the digits of each product summed, add up to a multiple of 10. False
    otherwise, also for "".

    Known limits: str.isdigit() takes other scripts' digits too; the candidate pattern lets only
    ASCII digits through.
    """
    if len(digits) > 9 or not digits.isdigit():
        return False
    d = digits.zfill(9)
    total = 0
    for i, ch in enumerate(d):
        n = int(ch) * (1 if i % 2 == 0 else 2)
        total += n if n < 10 else n - 9
    return total % 10 == 0


def is_trivial(digits: str) -> bool:
    """Say whether nine digits are a placeholder sequence rather than a person's number.

    Why: build-plan.md Phase 1: "Reject trivial sequences". 000000000, 123456782 and 012345674
    pass the checksum and are written in forms and examples, not issued to anyone.

    Contract: `digits`, nine digits. True when all nine are the same digit, or the first eight
    run up or down by one (01234567, 12345678, ..., 87654321).

    Known limits: other well-known example numbers are not listed.
    """
    stem = [int(ch) for ch in digits[: ID_LENGTH - 1]]
    steps = {b - a for a, b in zip(stem, stem[1:], strict=False)}
    return len(set(digits)) == 1 or steps in ({1}, {-1})


def is_other_shape(raw: str, label: str | None = None) -> bool:
    """Say whether a candidate is written in the shape of another kind of number.

    Why: a landline (0[23489] and seven digits) and a court case number (NNNNN-MM-YY) are nine
    digits too, and one in ten passes the checksum; their written shape tells them apart, where
    the digits alone cannot.

    Contract: `raw`, the candidate as written; `label`, what `label_before` gives for it (None
    when not known). True when it is a 0 and an area code of AREA_CODES, then seven digits in one
    of LANDLINE_GROUPS (seven, or three and four, after a separator; issue #302), under an ID
    label only in LABELLED_LANDLINE_GROUPS (seven); or three groups of five, two and two digits.

    Known limits: the same numbers written with no separator are not told apart. With no ID label,
    an ID that starts with 0 and an area code, written in groups of two, three and four, is taken
    for a landline; under an ID label it is found, and so is a landline written so right after an
    ID label. 0X-XXXXXXX is refused under any label, as before issue #302.
    """
    groups = [len(group) for group in re.split(_SEP, raw)]
    shapes = LABELLED_LANDLINE_GROUPS if label == "id" else LANDLINE_GROUPS
    landline = groups in shapes and raw[0] == "0" and raw[1] in AREA_CODES
    return landline or groups == CASE_NUMBER_GROUPS


def label_before(text: str, start: int) -> str | None:
    """Return the kind of the label that stands before a number: "id", "other", or None.

    Why: the label is how a form says what a number is; a valid number under a passport's or a
    phone's label is that number, and one under ת.ז. is an ID with more evidence than its checksum.

    Contract: `start` is the number's first character in `text`. Looks at the LABEL_WINDOW
    characters before it, on its line, after the last digit there (str.isdigit). "id" when a
    label there is one of ID_LABELS or the Latin ID, wherever it stands (a combined form label,
    "ת.ז./דרכון", asks for an ID; issue #299); else "other" when one is of OTHER_LABELS; else None.

    Known limits: a label further away, on the line before, or not in the two lists is not seen.
    An ID label beside another number's in the window wins over it, also when the form meant the
    other number ("ת.ז. של בעל חשבון").
    """
    line = text.rfind("\n", 0, start) + 1
    window = text[max(line, start - LABEL_WINDOW) : start]
    last_digit = max((i for i, ch in enumerate(window) if ch.isdigit()), default=-1)
    kinds = {match.lastgroup for match in LABEL.finditer(window[last_digit + 1 :])}
    return "id" if "id" in kinds else "other" if kinds else None


def is_israeli_id(raw: str, label: str | None, beside: bool) -> bool:
    """Say whether a candidate, as written, under its label and beside what follows, is an Israeli ID.

    Why: the decision of the detector, apart from the search, so each rule is tested by itself.

    Contract: `raw`, a match of CANDIDATE; `label`, what `label_before` gives for it; `beside`,
    whether another number follows it (NUMBER_AFTER matches right after it). True when no label
    of another number stands before it; under no ID label, it has nine digits and no number
    beside it, under an ID label at least SHORT_LENGTH digits; and its digits, padded with zeros
    to nine, pass the checksum, do not start with COMPANY_PREFIX, are not trivial, and its shape
    is not another number's.

    Known limits: those of the module.
    """
    written = re.sub(_SEP, "", raw)
    if label == "other" or (label != "id" and (beside or len(written) < ID_LENGTH)):
        return False
    digits = written.zfill(ID_LENGTH)
    if not israeli_id_checksum_ok(digits) or digits.startswith(COMPANY_PREFIX):
        return False
    return not is_trivial(digits) and not is_other_shape(raw, label)


class IsraeliId:
    """The detector of Israeli ID numbers, IL_ID.

    Why: the first deterministic detector of Phase 1 (issue #32), registered in
    eval.detectors.DETECTORS, so the held-out batch scores it and the T0 suite checks it.

    Contract: a Detector; `detect` returns one detection per candidate that `is_israeli_id`
    accepts, in the order of the text, as the module docstring says.

    Known limits: those of the module.
    """

    name: ClassVar[str] = "israeli_id"
    produces: ClassVar[frozenset[str]] = frozenset({ENTITY_TYPE})
    requires_morph: ClassVar[bool] = False

    def detect(self, proj: TextProjection, ctx: DetectContext) -> list[Detection]:
        """Find the Israeli ID numbers in the text of one projection.

        Why: the one call fusion makes of this detector.

        Contract: returns a Detection per number, with the part of `proj`, its surface the text
        of its span, CONFIDENCE_LABELLED under an ID label and CONFIDENCE otherwise, BAND, no base
        span, and detection_id "" (the module docstring). Raises nothing.

        Known limits: those of the module.
        """
        found = []
        for match in CANDIDATE.finditer(proj.text):
            label = label_before(proj.text, match.start())
            beside = NUMBER_AFTER.match(proj.text, match.end()) is not None
            if is_israeli_id(match.group(), label, beside):
                confidence = CONFIDENCE_LABELLED if label == "id" else CONFIDENCE
                span = Span(match.start(), match.end())
                found.append(Detection("", proj.part, span, match.group(), ENTITY_TYPE, confidence, BAND, self.name, None))
        return found
