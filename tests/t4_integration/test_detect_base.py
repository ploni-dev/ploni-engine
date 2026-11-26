"""Module suite for ploni/detect/base.py: two detectors of the protocol run over one projection, as fusion will.

Why: `CLAUDE.md`, Tests: every module gets a suite over its public surface. The T0 suite runs
one detector at a time; this runs two of different types over one projection made as an
adapter makes one (anchors, a block break), and reads them through the protocol alone, as
fusion does (ADR-0004: fusion knows no detector).

Matrix:
  M1  Digits and a placeholder detector over one projection, with one context: each keeps the
      contract of tests/detector_contract.py (surface, part, own name and declared type
      included), and their detections pooled are the three things in the text
  M2  which detectors need the morphology is read from the class, before any is built
"""

import re
from typing import ClassVar

from ploni.detect.base import DetectContext, Detector
from ploni.types import Anchor, Detection, Span, TextProjection
from tests.detector_contract import Digits, breaks

# build-plan.md Phase 1, "Already-anonymized placeholders".
PLACEHOLDER = re.compile("פלונית|פלוני|אלמוני")
TEXT = "התובע פלוני, ת.ז. 123456782.\nהנתבע אלמוני."


class Placeholders:
    """Find the placeholder names of an already-anonymized text."""

    name: ClassVar[str] = "placeholders"
    produces: ClassVar[frozenset[str]] = frozenset({"PLACEHOLDER"})
    requires_morph: ClassVar[bool] = True

    def detect(self, proj: TextProjection, ctx: DetectContext) -> list[Detection]:
        """Return one detection per placeholder."""
        return [
            Detection(f"p{index}", proj.part, Span(match.start(), match.end()), match.group(), "PLACEHOLDER", 0.9, "high", self.name, None)
            for index, match in enumerate(PLACEHOLDER.finditer(proj.text))
        ]


def adapter_projection() -> TextProjection:
    """Build a projection of two paragraphs, each its own node, as an adapter would."""
    cut = TEXT.index("\n") + 1
    anchors = [Anchor(0, cut, "w:p[0]/w:r[0]", 0), Anchor(cut, len(TEXT), "w:p[1]/w:r[0]", 0)]
    return TextProjection("body", TEXT, anchors, [cut], [])


def test_m1_two_detectors_pooled_keep_the_contract() -> None:
    proj, ctx = adapter_projection(), DetectContext()
    detectors: list[Detector] = [Digits(), Placeholders()]
    assert [line for detector in detectors for line in breaks(detector, proj, ctx)] == []
    pooled = [found for detector in detectors for found in detector.detect(proj, ctx)]
    assert sorted((found.detector, found.surface) for found in pooled) == [
        ("digits", "123456782"), ("placeholders", "אלמוני"), ("placeholders", "פלוני"),
    ]  # fmt: skip


def test_m2_the_morphology_need_is_read_from_the_class() -> None:
    classes: list[type[Detector]] = [Digits, Placeholders]
    assert [each.name for each in classes if each.requires_morph] == ["placeholders"]
