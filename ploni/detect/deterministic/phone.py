"""The Israeli phone detector: numbers of the prefixes and lengths of the Israeli numbering plan.

Why: a phone number reaches one person or one office, and court papers and forms carry them
beside the names (build-plan.md Phase 1, "Israeli phone": "Landline `0[23489]`, mobile `05\\d`,
VoIP `07[2-9]`, `+972` forms, `*NNNN` service numbers"; issue #36). A phone has no check digit,
so this is a pattern-only type: its precision comes from the prefixes and the groupings it is
written in, and from the label of another number, which refuses it.

Contract: `Phone` is a Detector (`ploni/detect/base.py`) of type PHONE, the name of the held-out
batch's span rules. The numbering plan of the Ministry of Communications, as the plan's line
names it: a 0 and an area code (AREA: 2, 3, 4, 8 or 9 for a landline, 5 and a digit for a
mobile, 7 and 2 to 9 for VoIP), then the seven digits of the line, in one group (with no
separator, or one after the area code), or after one separator as three and four, or three, two
and two (SUBSCRIBER); the area code with its 0 may stand in brackets, with or without a
separator after them. From abroad, "+972", "972" or "00972" stands in place of the 0, with an
optional separator after it, and the area code may stand in brackets. A 1-800 or 1-700 number
is 1, 800 or 700, and six digits, as one group, with a separator after 1 or not, then the six
with or without a separator before them, as six, three and three, or two, two and two (SERVICE).
A short number is a star and four digits. SEPARATORS are those of
ploni/detect/deterministic/israeli_id.py, one at a time. A detection's edges: on its left no
digit, nor a digit and one separator; on its right no digit, nor one separator and a digit. No
label of another number stands before it (`label_before`: israeli_id.LABEL's ID labels and other
numbers' labels, read in israeli_id.window_before), unless a phone label stands there too. Its
span is the number from its first character to its last digit, the plus, the star and the
brackets of the area code in, separators in, in code points of the projection's text (the
span rule of PHONE); a label before it is read, never put in the span. Under a phone label its
confidence is CONFIDENCE_LABELLED, otherwise CONFIDENCE. A bare run of digits with no label at
all is flagged: needs_review True, with REVIEW_REASON (`review_reason`), since nine digits from
0[23489] are an ID's length too.

Known limits: a phone written with two separators in a row ("05X - XXXXXXX"), in another grouping
(05X-XXXX-XXX, 0X-XXXX-XXX), from abroad with its 0 kept (+972-05X-..., +972 (0)5X-...), or
without its 0 and with no country code (5X-XXXXXXX, which is also a company number's grouping:
docs/DEBT.md row 16), is not found; nor is one with another number after one separator ("<phone>
3 ילדים"), nor a short number of three or five digits, nor a 1-800 or 1-700 number in other
groups, nor a prefix the plan's line does not name (1-599, 1-801, 1-900, 070, 071, extensions).
The plan's prefixes are taken as the line writes them; which of 05X and 07X are allocated today
was not checked against the Ministry's tables, none of which is in the repository. A label
further than israeli_id.LABEL_WINDOW, on the line before, or not in the lists is not seen; a
phone under another number's label (ת.ז., ח.פ., חשבון, כרטיס, ...) is refused, also when the
label was wrong. Measured on invented texts, 3,000 per form, by a scratch script that is not in
the repository (its table is in the text of this detector's PR): an Israeli ID written as nine
bare digits with no label is found as PHONE too 0.059 of the time (those that start with
0[23489]: 1.000 of them), every one flagged for review; an ID under its label, or written 3-3-3
or 8-1, 0.000; a company or non-profit number, plain or 5X-XXXXXXX, under a label or none,
0.000; a card, 0.000; an amount of four to ten digits in threes with commas, spaces or dots,
0.000, but one of ten digits that reads 1 800 or 1 700 and two groups of three, 1.000 (read as a
1-800 or 1-700 number, not flagged); case numbers (NNNNN-MM-YY, NNNN/YY), dates (dd.mm.yyyy,
dd/mm/yy, yyyy-mm-dd) and IBAN-like strings (IL and 21 digits, in fours or plain), 0.000. The
other detectors' found rates on their own forms are the same with this detector and without it
(it changes none of them; detect_all returns its detections beside theirs). The phone forms of
that table, a mobile 3-7 and 3-3-4, plain, a landline 2-7 and (0X) 7, a VoIP 3-7, +972-5X-...,
1-800-XXX-XXX and a star number, are found 1.000 of the time.
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
# build-plan.md Phase 1, "Israeli phone": landline `0[23489]`, mobile `05\d`, VoIP `07[2-9]`,
# the area code after the 0.
AREA = "(?:[23489]|5[0-9]|7[2-9])"
# The seven digits of a line after its area code: in one group, or three and four, or three, two
# and two, the forms Israeli forms and letterheads write.
GROUPED = rf"(?:[0-9]{{7}}|[0-9]{{3}}{_SEP}[0-9]{{4}}|[0-9]{{3}}{_SEP}[0-9]{{2}}{_SEP}[0-9]{{2}})"
SUBSCRIBER = rf"(?:[0-9]{{7}}|{_SEP}{GROUPED})"
NATIONAL = rf"0{AREA}{SUBSCRIBER}|\(0{AREA}\){_SEP}?{GROUPED}"
# From abroad the country code, 972, stands in place of the 0 (the plan's "`+972` forms").
ABROAD = rf"(?:\+|00)?972{_SEP}?(?:{AREA}{SUBSCRIBER}|\({AREA}\){_SEP}?{GROUPED})"
# The 1-800 and 1-700 numbers: 1, 800 or 700, and six digits.
SERVICE = rf"1{_SEP}?[78]00(?:[0-9]{{6}}|{_SEP}(?:[0-9]{{6}}|[0-9]{{3}}{_SEP}[0-9]{{3}}|[0-9]{{2}}{_SEP}[0-9]{{2}}{_SEP}[0-9]{{2}}))"
# build-plan.md Phase 1: "`*NNNN` service numbers".
SHORT = r"\*[0-9]{4}"
CANDIDATE = re.compile(rf"(?<![0-9])(?<![0-9]{_SEP})(?:{ABROAD}|{NATIONAL}|{SERVICE}|{SHORT})(?![0-9])(?!{_SEP}[0-9])")
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


def label_before(text: str, start: int) -> str | None:
    """Return the kind of the label that stands before a number: "phone", "other", or None.

    Why: the label is how a form says what a number is; a number in a landline's shape under an
    ID label is an ID, and one under a phone label is a phone with more evidence than its shape.

    Contract: `start` is the number's first character in `text`. Reads the labels in
    `israeli_id.window_before`. "phone" when one of them is of PHONE_LABELS, wherever it stands
    (a combined form label, "טלפון/ת.ז."); else "other" when one is an ID label or another
    number's label of israeli_id.LABEL; else None.

    Known limits: those of `israeli_id.label_before`.
    """
    kinds = {match.lastgroup for match in LABEL.finditer(israeli_id.window_before(text, start))}
    return "phone" if "phone" in kinds else "other" if kinds else None


def review_reason(raw: str, label: str | None) -> str | None:
    """Return why a candidate needs review, or None when it does not.

    Why: nine digits from 0[23489] with no separator are an ID's length and shape too, and ten
    bare digits may be any reference number; a human looks at such a run when no label says
    what it is.

    Contract: `raw`, a match of CANDIDATE; `label`, what `label_before` gives for it.
    REVIEW_REASON when `raw` is digits only (no separator, plus, bracket or star) and no label
    stands before it; None otherwise.

    Known limits: a bare run under another number's label is never asked: the detector refuses it.
    """
    return REVIEW_REASON if raw.isdigit() and label is None else None


class Phone:
    """The detector of Israeli phone numbers, PHONE.

    Why: the fourth deterministic detector of Phase 1 (issue #36), registered in
    eval.detectors.DETECTORS after the credit card detector, so the held-out batch scores it and
    the T0 suite checks it.

    Contract: a Detector; `detect` returns one detection per candidate with no other number's
    label before it, in the order of the text, as the module docstring says.

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
            if label == "other":
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
