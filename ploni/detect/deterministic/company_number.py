"""The company and non-profit number detector: nine-digit registry numbers that start with 5, by the ID check digit.

Why: build-plan.md Phase 1, "Company and non-profit numbers": "Nine digits, same check digit;
companies (ח.פ.) start with `5`, non-profits (ע.ר.) with `58`. Public-registry facts, so default
is detect and flag, not replace." The Israeli ID detector refuses these numbers (its
COMPANY_PREFIX); this one finds them, with the same candidate, check digit and labels, imported
from `israeli_id.py` (issue #33).

Contract: `CompanyNumber` is a Detector (`ploni/detect/base.py`) of the types COMPANY_NUMBER and
NONPROFIT_NUMBER, the names of the held-out batch's span rules. A detection is a match of
`israeli_id.CANDIDATE` of nine digits, with its edges, that `number_type` gives a type: its
digits pass `israeli_id_checksum_ok` and start with COMPANY_PREFIX; its written shape is not a
case number's (`is_other_shape`), nor, with no company label, a mobile's written without its 0
(two digits and seven, MOBILE_GROUPS); no label of another number stands before it (`label_before`:
a company label, ח.פ. or ע.ר. with any gershayim, wins over one); another number after it by a
plain space (`israeli_id.NUMBER_AFTER`) only under a company label. NONPROFIT_NUMBER when the
digits start with NONPROFIT_PREFIX, else COMPANY_NUMBER. Its span is the number only, first
digit to last, separators included, in code points of the projection's text. Under a company
label its confidence is the ID detector's CONFIDENCE_LABELLED, otherwise CONFIDENCE.
needs_review is False: "detect and flag, not replace" is what policy does with the detection
(a detector reports and does not decide what is replaced), and no policy exists yet.

Known limits: the type is read from the digits, not the label: ע.ר. before a number that starts
with 51 gives COMPANY_NUMBER. Only the plan's two prefixes are told apart: any other number that
starts with 5 and passes the check is a company's. Nine digits that start with 5 and pass the
check under no label of another number are found, whatever they are. Measured on 3,000 invented
texts each, by a scratch script that is not in the repository (its table is in the text of this
detector's PR, issue #33): an unlabelled nine-digit number from 5 is found 0.108
of the time; an amount of nine digits written in threes with spaces ("סך 5XX XXX XXX ש"ח")
0.096 (an amount of ten digits, 5 XXX XXX XXX, 0.000); a mobile written without its 0
(5X-XXXXXXX) 0.000 (0.114 before the two-and-seven refusal), and its usual forms (05X-XXXXXXX,
05X XXX XXXX, +972 5X ...) 0.000. The cost of that refusal: a company number written
5X-XXXXXXX with no company label is not found (0.000, 1.000 before); under a company label it
is. Telling a phone from a company number by more than the grouping is fusion's (PHONE over
COMPANY on 5X-XXXXXXX) once the phone detector exists (docs/DEBT.md). An ID label counts as no
label here. The label limits of `israeli_id.label_before`, and its edges, hold here too. The
detection carries no id (detection_id is ""), as the ID detector's (Achia, 2026-11-26, issue
#169).
"""

from __future__ import annotations

import re
from typing import ClassVar

from ploni.detect.base import DetectContext
from ploni.detect.deterministic import israeli_id
from ploni.detect.deterministic.israeli_id import _AFTER, _BEFORE, _SEP, COMPANY_LABELS, ID_LENGTH
from ploni.types import Detection, Span, TextProjection

COMPANY = "COMPANY_NUMBER"
NONPROFIT = "NONPROFIT_NUMBER"
# build-plan.md Phase 1: "companies (ח.פ.) start with `5`, non-profits (ע.ר.) with `58`".
COMPANY_PREFIX = israeli_id.COMPANY_PREFIX
NONPROFIT_PREFIX = "58"
# A mobile written without its 0 (build-plan.md Phase 1, "Israeli phone": mobile `05\d`), as two
# digits and seven, has a company number's digits: with no company label that grouping is no
# company's (the review of #33 at 4d6e477, finding 2).
MOBILE_GROUPS = [2, 7]
BAND = "high"
# A company label first, so that ח.פ. is read as one where the ID detector reads another number's.
LABEL = re.compile(rf"(?P<company>{_BEFORE}(?:{'|'.join(COMPANY_LABELS)}){_AFTER})|{israeli_id.LABEL.pattern}")


def label_before(text: str, start: int) -> str | None:
    """Return the kind of the label that stands before a number: "company", "other", or None.

    Why: the label is how a form says what a number is; a valid number that starts with 5 under
    a phone's or a bank account's label is that number, not a company's.

    Contract: `start` is the number's first character in `text`. Reads the labels in
    `israeli_id.window_before`. "company" when one of them is of COMPANY_LABELS, wherever it
    stands (a combined form label, "ת.ז./ח.פ."); else "other" when one is of the ID detector's
    other labels; else None, also under an ID label.

    Known limits: those of `israeli_id.label_before`.
    """
    kinds = {match.lastgroup for match in LABEL.finditer(israeli_id.window_before(text, start))}
    return "company" if "company" in kinds else "other" if "other" in kinds else None


def number_type(raw: str, label: str | None, beside: bool) -> str | None:
    """Return the type a candidate gets in its context: COMPANY_NUMBER, NONPROFIT_NUMBER, or None.

    Why: the decision of the detector, apart from the search, so each rule is tested by itself.

    Contract: `raw`, a match of `israeli_id.CANDIDATE`; `label`, what `label_before` gives for
    it; `beside`, whether another number follows it (NUMBER_AFTER matches right after it). None
    under another number's label, or beside another number with no company label; None unless
    its digits are nine, start with COMPANY_PREFIX and pass the check digit, and its shape is
    not a case number's, nor, with no company label, a mobile's without its 0 (MOBILE_GROUPS,
    two digits and seven). Else NONPROFIT_NUMBER for NONPROFIT_PREFIX, COMPANY_NUMBER otherwise.

    Known limits: the check of trivial sequences is not asked: no nine digits that start with 5
    are trivial in `israeli_id.is_trivial`'s sense (eight running up or down by one cannot start
    at 5, and 555555555 fails the check digit).
    """
    if label == "other" or (beside and label != "company"):
        return None
    digits = re.sub(_SEP, "", raw)
    if len(digits) != ID_LENGTH or not digits.startswith(COMPANY_PREFIX) or not israeli_id.israeli_id_checksum_ok(digits):
        return None
    groups = [len(group) for group in re.split(_SEP, raw)]
    if israeli_id.is_other_shape(raw) or (groups == MOBILE_GROUPS and label != "company"):
        return None
    return NONPROFIT if digits.startswith(NONPROFIT_PREFIX) else COMPANY


class CompanyNumber:
    """The detector of company and non-profit numbers, COMPANY_NUMBER and NONPROFIT_NUMBER.

    Why: the second deterministic detector of Phase 1 (issue #33), registered in
    eval.detectors.DETECTORS after the Israeli ID detector, so the held-out batch scores it and
    the T0 suite checks it.

    Contract: a Detector; `detect` returns one detection per candidate that `number_type` types,
    in the order of the text, as the module docstring says.

    Known limits: those of the module.
    """

    name: ClassVar[str] = "company_number"
    produces: ClassVar[frozenset[str]] = frozenset({COMPANY, NONPROFIT})
    requires_morph: ClassVar[bool] = False

    def detect(self, proj: TextProjection, ctx: DetectContext) -> list[Detection]:
        """Find the company and non-profit numbers in the text of one projection.

        Why: the one call fusion makes of this detector.

        Contract: returns a Detection per number, with the part of `proj`, its surface the text
        of its span, its type, CONFIDENCE_LABELLED under a company label and CONFIDENCE
        otherwise, BAND, no base span, and detection_id "" (the module docstring). Raises
        nothing.

        Known limits: those of the module.
        """
        found = []
        for match in israeli_id.CANDIDATE.finditer(proj.text):
            label = label_before(proj.text, match.start())
            beside = israeli_id.NUMBER_AFTER.match(proj.text, match.end()) is not None
            kind = number_type(match.group(), label, beside)
            if kind is not None:
                confidence = israeli_id.CONFIDENCE_LABELLED if label == "company" else israeli_id.CONFIDENCE
                span = Span(match.start(), match.end())
                found.append(Detection("", proj.part, span, match.group(), kind, confidence, BAND, self.name, None))
        return found
