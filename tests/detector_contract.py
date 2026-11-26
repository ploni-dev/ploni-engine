"""The detector conformance check, and the smallest detector that passes it.

Why: build-plan.md section 4.3 and ADR-0004 ask for one conformance suite that every detector
is run through: in-range spans, declared types only, confidence in [0, 1]. The T0 suite, the
T2 property and each detector's own tests call the same check, kept here, so that the three
cannot drift apart.

Contract: `breaks(detector, proj, ctx)` calls `detector.detect(proj, ctx)` once and returns one
line per broken rule per detection, in the order of the detections and, within one, in the
order span, base span, type, confidence; [] when every detection keeps the contract. A span is
in range when 0 <= start <= end <= len(proj.text): offsets are code points of the text, start
inclusive, end exclusive (ploni/types.py). The base span, when it is not None, is held to the
same range. A type is declared when it is a member of the detector's `produces`, compared
exactly. A confidence is in range when 0.0 <= confidence <= 1.0, so NaN is not. A line names
the detector, the index of the detection and the broken rule, with offsets, the type and the
confidence; never the surface, which is document text. What `detect` raises, `breaks` raises.

`projection(text)` builds a TextProjection of one part with one anchor over the whole text.
`Digits` is a detector of runs of ASCII digits, of type NUMBER, that keeps the contract; the
tests that show each rule can fail start from it.

Known limits: an empty span ([n, n)) is in range: the plan's words are "inside the
projection", and an empty place is inside it. Not checked, as section 4.3 does not ask it:
that `part` is the projection's, that `surface` is the text of the span, that `detector` is
the detector's name, that `band` is one of its three words, that `base_span` lies inside
`span`, or that the detector leaves its arguments as they were.
"""

import math
import re
from typing import ClassVar

from ploni.detect.base import DetectContext, Detector
from ploni.types import Anchor, Detection, Span, TextProjection

DIGITS = re.compile(r"[0-9]+")


def projection(text: str, part: str = "body") -> TextProjection:
    """Build the projection of one part whose text is one node."""
    anchors = [Anchor(0, len(text), "node0", 0)] if text else []
    return TextProjection(part, text, anchors, [], [])


def out_of_range(span: Span, length: int) -> bool:
    """Say whether a span is not a place inside a text of `length` code points."""
    return not 0 <= span.start <= span.end <= length


def problems(detection: Detection, length: int, produces: frozenset[str]) -> list[str]:
    """Return the rules of section 4.3 that one detection breaks, one phrase each."""
    found = []
    span, base = detection.span, detection.base_span
    if out_of_range(span, length):
        found.append(f"span [{span.start}, {span.end}) is not inside a text of {length} characters")
    if base is not None and out_of_range(base, length):
        found.append(f"base span [{base.start}, {base.end}) is not inside a text of {length} characters")
    if detection.entity_type not in produces:
        found.append(f"type {detection.entity_type!r} is not in produces {sorted(produces)}")
    if not 0.0 <= detection.confidence <= 1.0:
        found.append(f"confidence {detection.confidence!r} is not in [0, 1]")
    return found


def breaks(detector: Detector, proj: TextProjection, ctx: DetectContext) -> list[str]:
    """Return one line per rule of the Detector contract that one call of a detector breaks."""
    length = len(proj.text)
    return [
        f"{detector.name}: detection {index}: {problem}"
        for index, detection in enumerate(detector.detect(proj, ctx))
        for problem in problems(detection, length, detector.produces)
    ]


class Digits:
    """Find runs of ASCII digits: the smallest detector that keeps the contract."""

    name: ClassVar[str] = "digits"
    produces: ClassVar[frozenset[str]] = frozenset({"NUMBER"})
    requires_morph: ClassVar[bool] = False
    entity_type: ClassVar[str] = "NUMBER"
    confidence: ClassVar[float] = 1.0

    def detect(self, proj: TextProjection, ctx: DetectContext) -> list[Detection]:
        """Return one detection per run of digits."""
        return [self.found(proj, index, match) for index, match in enumerate(DIGITS.finditer(proj.text))]

    def found(self, proj: TextProjection, index: int, match: re.Match[str]) -> Detection:
        """Build the detection of one run."""
        return Detection(
            f"{self.name}-{index}", proj.part, self.span(match), match.group(), self.entity_type, self.confidence,
            "high", self.name, self.base_span(match, len(proj.text)),
        )  # fmt: skip

    def span(self, match: re.Match[str]) -> Span:
        """Return the place of one run."""
        return Span(match.start(), match.end())

    def base_span(self, match: re.Match[str], length: int) -> Span | None:
        """Return no base span: a number carries no proclitic."""
        return None


class PastTheEnd(Digits):
    """Adversarial: one past the end of the run, so out of range only when the run ends the text."""

    def span(self, match: re.Match[str]) -> Span:
        """Return the run and the character after it."""
        return Span(match.start(), match.end() + 1)


class BeforeTheStart(Digits):
    """One before the run, so out of range only when the run starts the text."""

    def span(self, match: re.Match[str]) -> Span:
        """Return the character before the run and the run."""
        return Span(match.start() - 1, match.end())


class Reversed(Digits):
    """Its span ends where the run starts."""

    def span(self, match: re.Match[str]) -> Span:
        """Return the run backwards."""
        return Span(match.end(), match.start())


class BaseOutside(Digits):
    """Its span is right; its base span runs one past the end of the text."""

    def base_span(self, match: re.Match[str], length: int) -> Span | None:
        """Return a base span from the run to past the end."""
        return Span(match.start(), length + 1)


class Undeclared(Digits):
    """Adversarial: a type that differs from the declared one only in case."""

    entity_type: ClassVar[str] = "number"


class AboveOne(Digits):
    """Confidence over 1."""

    confidence: ClassVar[float] = 1.5


class BelowZero(Digits):
    """Confidence under 0."""

    confidence: ClassVar[float] = -0.5


class NotANumber(Digits):
    """Adversarial: NaN, which a check written as `c < 0 or c > 1` lets through."""

    confidence: ClassVar[float] = math.nan
