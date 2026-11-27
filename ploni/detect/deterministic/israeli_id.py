"""The Israeli ID detector: nine-digit identity numbers that pass their check digit.

Why: an identity number names one person for life, and leaking it is the damage the product
exists to prevent; its check digit gives a precision a pattern alone cannot (build-plan.md
Phase 1, "Israeli ID": "Nine digits, last is a check digit, Luhn-style ... Separator-tolerant
candidate regex, strip, validate. Reject trivial sequences."). Recall comes from the wide
candidate, precision from the checksum, which is never weakened.

Contract: `IsraeliId` is a Detector (`ploni/detect/base.py`) of type IL_ID. A detection is a run
of nine ASCII digits, with at most one separator (SEPARATORS) between any two, not touching
another digit (or a separator and a digit) on either side, whose digits pass
`israeli_id_checksum_ok`, do not start with COMPANY_PREFIX, are not trivial (`is_trivial`), and
whose written shape is not that of another number (`is_other_shape`). Its span is the number
only, first digit to last, separators included, in code points of the projection's text (the
held-out batch's span rule for IL_ID); a label before it is not read and not in the span.

Known limits: a landline written as nine digits with no separator (0X1234567) is found as an ID;
an ID written with fewer than nine digits (a leading zero dropped) is not found; the label is not
read, so a valid number in another context (a reference number) is found as an ID. The detection
carries no id (detection_id is ""): ids are made just after detection, with the matter's key,
never inside a detector (Achia, 2026-11-26, issue #169, "Use the secret key (Recommended)").
"""

from __future__ import annotations

import re
from typing import ClassVar

from ploni.detect.base import DetectContext
from ploni.types import Detection, Span, TextProjection

ENTITY_TYPE = "IL_ID"
# build-plan.md Phase 1: "Nine digits, last is a check digit".
ID_LENGTH = 9
# build-plan.md Phase 1: "companies (ח.פ.) start with `5`, non-profits (ע.ר.) with `58`": a number
# that starts with 5 is a company's or an association's, not a person's.
COMPANY_PREFIX = "5"
# build-plan.md Phase 1, "Israeli phone": landline area codes `0[23489]`.
AREA_CODES = "23489"
# The digits of a landline after its area code.
LANDLINE_REST = 7
# build-plan.md Phase 1, "Court case numbers": Net HaMishpat style `NNNNN-MM-YY`.
CASE_NUMBER_GROUPS = [5, 2, 2]
# Hyphen, dot, slash, space, no-break space, maqaf (U+05BE) and en dash: the separators the held-out
# batch's span rules name ("hyphen, space, dot, slash"), and the forms of them Hebrew text uses.
SEPARATORS = "-./  ־–"
_SEP = "[" + re.escape(SEPARATORS) + "]"
CANDIDATE = re.compile(rf"(?<![0-9])(?<![0-9]{_SEP})[0-9](?:{_SEP}?[0-9]){{{ID_LENGTH - 1}}}(?!{_SEP}?[0-9])")
# shortcut: one fixed confidence for every checksum match until calibration (build-plan.md
# section 4.7, detect/calibration.py) gives a measured one; a random nine-digit number passes the
# check one time in ten.
CONFIDENCE = 0.95
BAND = "high"


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


def is_other_shape(raw: str) -> bool:
    """Say whether a candidate is written in the shape of another kind of number.

    Why: a landline (0[23489] and seven digits) and a court case number (NNNNN-MM-YY) are nine
    digits too, and one in ten passes the checksum; their written shape tells them apart, where
    the digits alone cannot.

    Contract: `raw`, the candidate as written. True when it is a 0, an area code of AREA_CODES and
    one separator before seven digits, or three groups of five, two and two digits.

    Known limits: the same numbers written with no separator are not told apart.
    """
    groups = [len(group) for group in re.split(_SEP, raw)]
    landline = groups == [2, LANDLINE_REST] and raw[0] == "0" and raw[1] in AREA_CODES
    return landline or groups == CASE_NUMBER_GROUPS


def is_israeli_id(raw: str) -> bool:
    """Say whether a candidate, as written, is an Israeli ID.

    Why: the decision of the detector, apart from the search, so each rule is tested by itself.

    Contract: `raw`, a match of CANDIDATE. True when its digits pass the checksum, do not start
    with COMPANY_PREFIX, are not trivial, and its shape is not another number's.

    Known limits: those of the module.
    """
    digits = re.sub(_SEP, "", raw)
    if not israeli_id_checksum_ok(digits) or digits.startswith(COMPANY_PREFIX):
        return False
    return not is_trivial(digits) and not is_other_shape(raw)


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
        of its span, CONFIDENCE and BAND, no base span, and detection_id "" (the module
        docstring). Raises nothing.

        Known limits: those of the module.
        """
        return [
            Detection("", proj.part, Span(match.start(), match.end()), match.group(), ENTITY_TYPE, CONFIDENCE, BAND, self.name, None)
            for match in CANDIDATE.finditer(proj.text)
            if is_israeli_id(match.group())
        ]
