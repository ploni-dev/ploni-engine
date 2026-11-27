"""The Israeli phone detector: numbers of the prefixes and lengths of build-plan.md Phase 1's phone line.

Why: a phone number reaches one person or one office, and court papers and forms carry them
beside the names (build-plan.md Phase 1, "Israeli phone": "Landline `0[23489]`, mobile `05\\d`,
VoIP `07[2-9]`, `+972` forms, `*NNNN` service numbers"; issue #36). A phone has no check digit,
so this is a pattern-only type: its precision comes from the prefixes and the groupings it is
written in, and from the label of another number, which refuses a number that can be that one.

Contract: `Phone` is a Detector (`ploni/detect/base.py`) of type PHONE, the name of the held-out
batch's span rules. The plan's line gives the prefixes: a 0 and an area code (AREA: 2, 3, 4, 8 or
9 for a landline, 5 and a digit for a mobile, 7 and 2 to 9 for VoIP), and the "+972" forms; the
seven digits after the area code are the Israeli numbering's length (Claude's knowledge; the
ranges were not checked against the Ministry of Communications' tables, none of which is in the
repository). A number is the 0 and the area code, then the seven digits in one group (with no
separator, or one after the area code), or after one separator as three and four, or three, two
and two (SUBSCRIBER); the area code with its 0 may stand in brackets, with or without a
separator after them. From abroad, "+972", "972" or "00972" stands in place of the 0, with an
optional separator after it, and the area code may stand in brackets; or the 0 is kept, as "0"
or "(0)" right before the area code ("+972-03-...", "+972 (0)3 ...": KEPT_ZERO; Achia,
2026-11-27, #36, "Yes, find them (Recommended)": "an optional "(0)" or "0" after 972 and its
separator"). A 1-800 or 1-700 number
is 1, 800 or 700, and six digits, as one group, with a separator after 1 or not, then the six
with or without a separator before them, as six, three and three, or two, two and two (SERVICE).
A short number is a star and four digits. SEPARATORS are those of
ploni/detect/deterministic/israeli_id.py, one at a time. A detection's edges: on its left no
digit, nor a digit and one separator other than a plain space or a slash (EDGE); on its right
likewise, no digit, nor such a separator and a digit; so two phones joined by a space or a slash
are two (the review of b2f3790, finding 3, as the ID detector's _TIGHT, #299). The label before
it is read in israeli_id.window_before (`label_before`): a phone label raises the confidence; an
ID label refuses it when the ID detector takes it as written (`israeli_id.is_israeli_id`), and
otherwise it is found and flagged, so that no span is both; another number's label (a company's,
an account's, a card's, a passport's, ...) refuses it when it has SHARED_LENGTH digits or fewer,
which an ID, a company number or an account can share, and a longer one is found (`refused`;
the review of b2f3790, findings 1 and 2). Its span is the number from its first character to
its last digit, the plus, the star and the brackets of the area code in, separators in, in code
points of the projection's text (the span rule of PHONE); a label before it is read, never put
in the span. Under a phone label its confidence is CONFIDENCE_LABELLED, otherwise CONFIDENCE.
A bare run of digits with no label at all is flagged, needs_review True with REVIEW_REASON,
since nine digits from 0[23489] are an ID's length too; one under an ID label that the ID
detector does not take is flagged with ID_LABEL_REASON (`review_reason`).

Known limits: a phone written with two separators in a row ("05X - XXXXXXX"), in another grouping
(05X-XXXX-XXX, 0X-XXXX-XXX), from abroad with its 0 kept and a separator after the 0
(+972-0-5X-..., +972 (0) 3-...) or the area code in brackets after it (+972 0(3) ...), or
without its 0 and with no country code (5X-XXXXXXX, which is also a company number's grouping:
docs/DEBT.md row 16), is not found; nor is one with another number after a hyphen or another
tight separator ("<phone>-8"), nor a short number of three or five digits, nor a 1-800 or 1-700
number in other groups, nor a prefix the plan's line does not name (1-599, 1-801, 1-900, 070,
071, extensions). A landline with its second line's last digit after a slash ("0X-XXXXXXX/8")
gives the first number's span only; after a plain space ("<phone> 3 ילדים") the phone is found
and the digit is not. A label further than israeli_id.LABEL_WINDOW, on the line before, or not
in the lists is not seen. Under another number's label a landline of nine digits is refused,
also when the label was wrong ("סניף הבנק: 0X-XXXXXXX"); a bank account of more than nine
digits written in a phone's shape under its label is found as a phone. Measured on invented
texts, 3,000 per form, by scratch scripts that are not in the repository (their tables are in
the text of this detector's PR): an Israeli ID written as nine bare digits with no label is
found as PHONE too 0.059 of the time (those that start with 0[23489]: 1.000 of them), every one
flagged for review; an ID under its label, or written 3-3-3 or 8-1, 0.000; a valid ID from
0[23489] under an ID label written 0X-XXX-XXXX or plain, 0.000 (the ID detector takes it), and
written 0X-XXXXXXX, 1.000, flagged (no detector found it before); a company or non-profit
number, plain or 5X-XXXXXXX, under a label or none, 0.000; a card, 0.000; an amount of four to
ten digits in threes with commas, spaces or dots, 0.000, but one of ten digits that reads 1 800
or 1 700 and two groups of three, 1.000 (read as a 1-800 or 1-700 number, not flagged); case
numbers (NNNNN-MM-YY, NNNN/YY), dates (dd.mm.yyyy, dd/mm/yy, yyyy-mm-dd) and IBAN-like strings
(IL and 21 digits, in fours or plain), 0.000. The other detectors' found rates on their own forms
are the same with this detector and without it (it changes none of them; detect_all returns its
detections beside theirs). A mobile under ת.ז., ח.פ., כרטיס ביקור, חשבון, סניף הבנק, בנק or
דרכון, 1.000 (a landline under the six but ת.ז., 0.000); two mobiles joined by a space, a
slash, a comma, ו- or או, 1.000 each; the phone forms of these tables with every phone label and
none, 1.000, but the limits above (0.000). The 0 kept from abroad (+972-0X-XXXXXXX, +972 (0)X
XXXXXXX, +972-05X-XXXXXXX, +972 (0)5X-XXX-XXXX, +972-07X-XXXXXXX): 1.000 each (0.000 before
Achia's answer). Its cost: the number 972 written before a number from 0 by one plain space,
with no plus ("עמוד 972 0X-XXXXXXX", "עמוד 972 <ID from 0[23489]>"), is read as one number from
abroad, the 972 in its span, 1.000, and not flagged.
The detection carries no id (detection_id is ""): ids are made just after detection, with the
matter's key, never inside a detector (Achia, 2026-11-26, issue #169, "Use the secret key
(Recommended)").
"""

from __future__ import annotations

import re
from typing import ClassVar

from ploni.detect.base import DetectContext
from ploni.detect.deterministic import israeli_id
from ploni.detect.deterministic.israeli_id import _AFTER, _BEFORE, SEPARATORS
from ploni.types import Detection, Span, TextProjection

ENTITY_TYPE = "PHONE"
_SEP = "[" + re.escape(SEPARATORS) + "]"
# The separators but a plain space and a slash: one of these between two numbers joins them into
# one; a space or a slash between two phones keeps them two (the review of b2f3790, finding 3).
EDGE = "[" + re.escape(SEPARATORS.replace(" ", "").replace("/", "")) + "]"
# build-plan.md Phase 1, "Israeli phone": landline `0[23489]`, mobile `05\d`, VoIP `07[2-9]`,
# the area code after the 0.
AREA = "(?:[23489]|5[0-9]|7[2-9])"
# The seven digits of a line after its area code: in one group, or three and four, or three, two
# and two, the forms Israeli forms and letterheads write.
GROUPED = rf"(?:[0-9]{{7}}|[0-9]{{3}}{_SEP}[0-9]{{4}}|[0-9]{{3}}{_SEP}[0-9]{{2}}{_SEP}[0-9]{{2}})"
SUBSCRIBER = rf"(?:[0-9]{{7}}|{_SEP}{GROUPED})"
NATIONAL = rf"0{AREA}{SUBSCRIBER}|\(0{AREA}\){_SEP}?{GROUPED}"
# From abroad the country code, 972, stands in place of the 0 (the plan's "`+972` forms"), or
# before the 0 kept, glued to the area code (Achia, 2026-11-27, #36, "Yes, find them (Recommended)").
KEPT_ZERO = r"(?:\(0\)|0)?"
ABROAD = rf"(?:\+|00)?972{_SEP}?(?:{KEPT_ZERO}{AREA}{SUBSCRIBER}|\({AREA}\){_SEP}?{GROUPED})"
# The 1-800 and 1-700 numbers: 1, 800 or 700, and six digits.
SERVICE = rf"1{_SEP}?[78]00(?:[0-9]{{6}}|{_SEP}(?:[0-9]{{6}}|[0-9]{{3}}{_SEP}[0-9]{{3}}|[0-9]{{2}}{_SEP}[0-9]{{2}}{_SEP}[0-9]{{2}}))"
# build-plan.md Phase 1: "`*NNNN` service numbers".
SHORT_MARK = "*"
SHORT = re.escape(SHORT_MARK) + "[0-9]{4}"
CANDIDATE = re.compile(rf"(?<![0-9])(?<![0-9]{EDGE})(?:{ABROAD}|{NATIONAL}|{SERVICE}|{SHORT})(?![0-9])(?!{EDGE}[0-9])")
# The most digits a number under another number's label may have and still be that number: an
# ID's, a company number's (israeli_id.ID_LENGTH, nine) or a bank account's; a ten-digit mobile,
# a number from abroad or a 1-800 number cannot be one (the review of b2f3790, finding 1).
SHARED_LENGTH = israeli_id.ID_LENGTH
# shortcut: one fixed confidence per kind until calibration (build-plan.md section 4.7,
# detect/calibration.py) gives a measured one; a phone label before the number is more evidence.
CONFIDENCE = 0.9
CONFIDENCE_LABELLED = 0.99
BAND = "high"
# The labels of a phone in Hebrew forms and papers: telephone, tel. with a geresh or a dot,
# mobile, cellphone, fax; "מס' טלפון" and "נייד:" hold them.
PHONE_LABELS = (r"טלפון", r"טל['׳.]", r"נייד", r"פלאפון", r"פקס")
LABEL = re.compile(rf"(?P<phone>{_BEFORE}(?:{'|'.join(PHONE_LABELS)}){_AFTER})|{israeli_id.LABEL.pattern}")
REVIEW_REASON = "a bare run of digits in a phone's shape, with no label"
ID_LABEL_REASON = "a phone's shape under an ID label"


def label_before(text: str, start: int) -> str | None:
    """Return the kind of the label that stands before a number: "phone", "id", "other", or None.

    Why: the label is how a form says what a number is; one in a landline's shape under an ID
    label may be an ID, one under an account's or a company's label may be that number, and one
    under a phone label is a phone with more evidence than its shape. `refused` reads the kind.

    Contract: `start` is the number's first character in `text`. Reads the labels in
    `israeli_id.window_before`. "phone" when one of them is of PHONE_LABELS, wherever it stands
    (a combined form label, "טלפון/ת.ז."); else "id" when one is an ID label of israeli_id.LABEL;
    else "other" when one is another number's label there; else None.

    Known limits: those of `israeli_id.label_before`.
    """
    kinds = {match.lastgroup for match in LABEL.finditer(israeli_id.window_before(text, start))}
    return "phone" if "phone" in kinds else "id" if "id" in kinds else "other" if kinds else None


def refused(raw: str, label: str | None) -> bool:
    """Say whether the label before a candidate makes it another number.

    Why: under an ID label the ID detector may take the same digits, and under another number's
    label a number of an ID's length may be that number; a candidate that cannot be is a phone
    (the review of b2f3790, findings 1 and 2).

    Contract: `raw`, a match of CANDIDATE; `label`, what `label_before` gives for it. True under
    an ID label when `israeli_id.is_israeli_id(raw, "id", False)` is (under an ID label that
    function does not read whether another number follows, so none is looked for); True under
    another number's label when `raw` holds SHARED_LENGTH digits or fewer and is no short number
    (a star and four digits); False otherwise, and under a phone label or none.

    Known limits: the ID detector reads its own candidate; where its candidate and this one differ
    in their edges, `is_israeli_id` on this one's text is what is asked.
    """
    if label == "id":
        return israeli_id.is_israeli_id(raw, label, beside=False)
    digits = sum(ch.isdigit() for ch in raw)
    return label == "other" and digits <= SHARED_LENGTH and not raw.startswith(SHORT_MARK)


def review_reason(raw: str, label: str | None) -> str | None:
    """Return why a candidate needs review, or None when it does not.

    Why: nine digits from 0[23489] with no separator are an ID's length and shape too, and ten
    bare digits may be any reference number; a human looks at such a run when no label says
    what it is, and at a phone's shape that a form labelled as an ID.

    Contract: `raw`, a match of CANDIDATE that `refused` lets through; `label`, what
    `label_before` gives for it. ID_LABEL_REASON under an ID label; REVIEW_REASON when `raw` is
    digits only (no separator, plus, bracket or star) and no label stands before it; None
    otherwise.

    Known limits: one under another number's label that is let through (longer than
    SHARED_LENGTH digits) is not flagged.
    """
    if label == "id":
        return ID_LABEL_REASON
    return REVIEW_REASON if raw.isdigit() and label is None else None


class Phone:
    """The detector of Israeli phone numbers, PHONE.

    Why: the fourth deterministic detector of Phase 1 (issue #36), registered in
    eval.detectors.DETECTORS after the credit card detector, so the held-out batch scores it and
    the T0 suite checks it.

    Contract: a Detector; `detect` returns one detection per candidate that `refused` lets
    through, in the order of the text, as the module docstring says.

    Known limits: those of the module.
    """

    name: ClassVar[str] = "phone"
    produces: ClassVar[frozenset[str]] = frozenset({ENTITY_TYPE})
    requires_morph: ClassVar[bool] = False

    def detect(self, proj: TextProjection, ctx: DetectContext) -> list[Detection]:
        """Find the Israeli phone numbers in the text of one projection.

        Why: the one call fusion makes of this detector.

        Contract: returns a Detection per number, with the part of `proj`, its surface the text
        of its span, CONFIDENCE_LABELLED under a phone label and CONFIDENCE otherwise, BAND, no
        base span, needs_review and review_reason as `review_reason` gives them, and
        detection_id "" (the module docstring). Raises nothing.

        Known limits: those of the module.
        """
        found = []
        for match in CANDIDATE.finditer(proj.text):
            label = label_before(proj.text, match.start())
            if refused(match.group(), label):
                continue
            confidence = CONFIDENCE_LABELLED if label == "phone" else CONFIDENCE
            reason = review_reason(match.group(), label)
            span = Span(match.start(), match.end())
            found.append(
                Detection(
                    "", proj.part, span, match.group(), ENTITY_TYPE, confidence, BAND, self.name, None,
                    needs_review=reason is not None, review_reason=reason,
                )  # fmt: skip
            )
        return found
