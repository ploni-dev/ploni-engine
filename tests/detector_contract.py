"""The detector conformance check, and the smallest detector that passes it.

Why: build-plan.md section 4.3 and ADR-0004 ask for one conformance suite that every detector
is run through: in-range spans, declared types only, confidence in [0, 1]. The T0 suite, the
T2 property and each detector's own tests call the same check, kept here, so that the three
cannot drift apart.

Contract: `breaks(detector, proj, ctx)` calls `detector.detect(proj, ctx)` once and returns one
line per broken rule per detection, in the order of the detections and, within one, in the
order of the rules below; [] when every detection keeps the contract. Offsets are code points
of `proj.text`, start inclusive, end exclusive (ploni/types.py). The rules:
  1. the span is inside the text: 0 <= start and end <= len(proj.text) (section 4.3);
  2. the span holds at least one character: start < end, so a reversed span breaks it too;
  3. the surface is `proj.text[start:end]`, judged only when 1 and 2 hold;
  4. a base span, when it is not None, is a non-empty place inside the span:
     span.start <= base.start < base.end <= span.end, so it is inside the text when the span is;
  5. the part is the projection's;
  6. `detection.detector` is the detector's `name`;
  7. the type is a member of the detector's `produces`, compared exactly (section 4.3);
  8. 0.0 <= confidence <= 1.0, so NaN is not (section 4.3).
Rules 1, 7 and 8 are the three of section 4.3. Rules 2 to 6 are Claude's choice, which only
narrows: each refuses more of what a detector could return, and none relaxes the three. A line
names the detector, the index of the detection and the broken rule,
with offsets, the type, the part, the names and the confidence; never the surface or the text,
which are document text. What `detect` raises, `breaks` raises.

`projection(text)` builds a TextProjection of one part with one anchor over the whole text, and
no anchor for the empty text. `Digits` is a detector of runs of ASCII digits, of type NUMBER,
that keeps the contract; the tests that show each rule can fail start from it.

Known limits: the first detector PR may tighten the check further. Not checked, among them:
  - that `band` is one of its three words;
  - that `detection_id` is content-based (build-plan.md section 5);
  - that `prefix` and `suffix` are the letters around the base span;
  - `lemma`, `gender`, `needs_review` and `review_reason`, `at_window_edge`;
  - that `metadata` is a new dict for each detection;
  - overlapping or duplicate detections;
  - that a second call returns the same;
  - that the detector leaves its arguments as they were.
"""

import math
import re
from typing import ClassVar

from ploni.detect.base import DetectContext, Detector
from ploni.types import Anchor, Detection, Span, TextProjection

DIGITS = re.compile(r"[0-9]+")


def projection(text: str, part: str = "body") -> TextProjection:
    """Build the projection of one part whose text is one node; the empty text gets no anchor."""
    anchors = [Anchor(0, len(text), "node0", 0)] if text else []
    return TextProjection(part, text, anchors, [], [])


def place_problems(detection: Detection, text: str) -> list[str]:
    """Return the rules 1 to 4 of the module docstring, on places, that one detection breaks."""
    found = []
    span, base = detection.span, detection.base_span
    inside = 0 <= span.start and span.end <= len(text)
    filled = span.start < span.end
    if not inside:
        found.append(f"span [{span.start}, {span.end}) is not inside a text of {len(text)} characters")
    if not filled:
        found.append(f"span [{span.start}, {span.end}) is empty or reversed")
    if inside and filled and text[span.start : span.end] != detection.surface:
        found.append("surface is not the text of its span")
    if base is not None and not span.start <= base.start < base.end <= span.end:
        found.append(f"base span [{base.start}, {base.end}) is not a non-empty place inside the span [{span.start}, {span.end})")
    return found


def label_problems(detection: Detection, part: str, detector: Detector) -> list[str]:
    """Return the rules 5 to 8 of the module docstring, on what a detection names, that it breaks."""
    found = []
    if detection.part != part:
        found.append(f"part {detection.part!r} is not the projection's {part!r}")
    if detection.detector != detector.name:
        found.append(f"detector {detection.detector!r} is not the detector's name {detector.name!r}")
    if detection.entity_type not in detector.produces:
        found.append(f"type {detection.entity_type!r} is not in produces {sorted(detector.produces)}")
    if not 0.0 <= detection.confidence <= 1.0:
        found.append(f"confidence {detection.confidence!r} is not in [0, 1]")
    return found


def breaks(detector: Detector, proj: TextProjection, ctx: DetectContext) -> list[str]:
    """Return one line per rule of the Detector contract that one call of a detector breaks."""
    return [
        f"{detector.name}: detection {index}: {problem}"
        for index, detection in enumerate(detector.detect(proj, ctx))
        for problem in place_problems(detection, proj.text) + label_problems(detection, proj.part, detector)
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
            f"{self.name}-{index}", self.part_of(proj), self.span(match), match.group(), self.entity_type,
            self.confidence, "high", self.signed(), self.base_span(match, len(proj.text)),
        )  # fmt: skip

    def span(self, match: re.Match[str]) -> Span:
        """Return the place of one run."""
        return Span(match.start(), match.end())

    def base_span(self, match: re.Match[str], length: int) -> Span | None:
        """Return no base span: a number carries no proclitic."""
        return None

    def part_of(self, proj: TextProjection) -> str:
        """Return the part a detection names: the projection's."""
        return proj.part

    def signed(self) -> str:
        """Return the detector a detection names: this one."""
        return self.name


class PastTheEnd(Digits):
    """Adversarial: one past the end of the run: out of range when the run ends the text, else not its surface."""

    def span(self, match: re.Match[str]) -> Span:
        """Return the run and the character after it."""
        return Span(match.start(), match.end() + 1)


class BeforeTheStart(Digits):
    """One before the run: out of range when the run starts the text, else not its surface."""

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


class Shifted(Digits):
    """Adversarial: its span is the run moved one character on, inside the text in mid-text."""

    def span(self, match: re.Match[str]) -> Span:
        """Return the run moved one character on."""
        return Span(match.start() + 1, match.end() + 1)


class Empty(Digits):
    """Its span holds no character: it starts and ends where the run starts."""

    def span(self, match: re.Match[str]) -> Span:
        """Return the empty place at the start of the run."""
        return Span(match.start(), match.start())


class BaseBeyondSpan(Digits):
    """Its base span runs one past its span, inside the text in mid-text."""

    def base_span(self, match: re.Match[str], length: int) -> Span | None:
        """Return the run and the character after it."""
        return Span(match.start(), match.end() + 1)


class WrongPart(Digits):
    """It names a part other than the projection's."""

    def part_of(self, proj: TextProjection) -> str:
        """Return a header, whatever the projection."""
        return "header1"


class Misnamed(Digits):
    """Adversarial: it names a detector one letter short of its own name."""

    def signed(self) -> str:
        """Return a name one letter short."""
        return self.name[:-1]


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
