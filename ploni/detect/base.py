"""The Detector protocol of build-plan.md section 4.3, and the context a detector is given.

Why: fusion must know no detector, so that adding one is a module and a fixture file, not an
edit of fusion, and a change in the measured numbers has one candidate cause (ADR-0004). This
protocol is all that fusion, the pipeline and the conformance suite may rely on.

Contract: a detector is any class with the four members of `Detector`; it need not inherit
from it. The conformance suite (tests/detector_contract.py, run by tests/t0_contract/) holds
every detector to the rules of section 4.3: each returned span lies inside the projection,
each returned type is one of `produces`, each confidence is in [0, 1].

Known limits: nothing here checks those rules at run time; the suite does. `DetectContext`
holds nothing yet: the plan names it and gives it no field.
"""

from __future__ import annotations

from typing import ClassVar, Protocol

from ploni.types import Detection, TextProjection


class DetectContext:
    """What a detector is given besides the projection: nothing yet.

    Why: section 4.3 passes a context to every call, so that a field added later (for
    example what a detector with `requires_morph` needs) reaches every detector without a
    change of the protocol's signature.

    Contract: built with no argument; holds no field.

    Known limits: empty on purpose: build-plan.md section 4.3 names this class and gives it
    no field, so none is defined here. The first detector that needs one adds it.
    """


class Detector(Protocol):
    """One detector of the pipeline, as fusion sees it.

    Why: the approved abstraction of ADR-0004: roughly 15 implementations in Phase 1 alone,
    and fusion must know none of them. There is no write path: a detector reports, it never
    replaces.

    Contract: `name` names the detector, and every detection it returns carries it in
    `Detection.detector`. `produces` holds every entity type it may return. `requires_morph`
    says whether it needs the morphological analysis of the text. All three are class
    attributes, read before any detector is built.

    Known limits: the words of `produces` are not listed anywhere yet; each detector declares
    its own.
    """

    name: ClassVar[str]
    produces: ClassVar[frozenset[str]]  # entity types
    requires_morph: ClassVar[bool]

    def detect(self, proj: TextProjection, ctx: DetectContext) -> list[Detection]:
        """Find what this detector finds in the text of one projection.

        Why: the one call fusion makes of a detector; it works on one part at a time, as the
        adapters hand the parts over.

        Contract: `proj` is one part of the document; `ctx` is the context of this run.
        Returns the detections in `proj.text`, possibly none. Each span is in code points of
        `proj.text`, start inclusive, end exclusive, with 0 <= start <= end <= len(proj.text);
        each `entity_type` is in `produces`; each `confidence` is in [0, 1]. Raises what the
        detector documents.

        Known limits: one projection per call; a name that runs from one part into another is
        not seen.
        """
