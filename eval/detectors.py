"""The detections the held-out batch scores: every detector of ploni/, run over a document's text.

Why: the held-out scorer takes "a callable from a document's text to a list of (start, end,
type)" (its contract, PR #288), and the score check of issue 170 scores main and each PR with
the same callable, `python -m eval.heldout.scorer eval.detectors:detect_all`. It lives in eval/,
which may import ploni/; ploni/ never imports eval/ (CLAUDE.md, Hard constraints).

Contract: `detect_all(text)` runs each detector of DETECTORS, in order, over one projection of
the text (part "body", one anchor over the whole text, none for the empty text) with an empty
context, and returns each detection as (start, end, entity_type), offsets in code points of the
text, in the order the detectors return them. DETECTORS holds the detectors of ploni/, each added
as it is written: the Israeli ID detector first (issue #32), then the company and non-profit
number detector (issue #33), then the credit card detector (issue #35).

Known limits: a document is one part here, so a detector that reads block breaks or table cells
gets none. A detection outside the text is passed on as it is; the scorer refuses it.
"""

from collections.abc import Sequence

from ploni.detect.base import DetectContext, Detector
from ploni.detect.deterministic.company_number import CompanyNumber
from ploni.detect.deterministic.credit_card import CreditCard
from ploni.detect.deterministic.israeli_id import IsraeliId
from ploni.types import Anchor, TextProjection

DETECTORS: tuple[Detector, ...] = (IsraeliId(), CompanyNumber(), CreditCard())


def detect_all(text: str, detectors: Sequence[Detector] = DETECTORS) -> list[tuple[int, int, str]]:
    """Return the places and types every detector finds in one document's text.

    Why: the one function the held-out scorer calls, for main and for the PR alike.

    Contract: `text` is the document's text; `detectors` defaults to DETECTORS. Returns
    (start, end, entity_type) per detection, as the module docstring says. Raises what a
    detector raises.

    Known limits: see the module docstring.
    """
    proj = TextProjection("body", text, [Anchor(0, len(text), "text", 0)] if text else [], [], [])
    ctx = DetectContext()
    return [(found.span.start, found.span.end, found.entity_type) for detector in detectors for found in detector.detect(proj, ctx)]
