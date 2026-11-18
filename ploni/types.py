"""The core types that every layer of the pipeline passes to the next.

Why: a span, a detection or an entity crosses from the adapters to the detectors, the
resolver, the policy and the writer. One definition, in the lowest layer, keeps them the same
everywhere. They are those of build-plan.md section 5.

Contract: plain dataclasses with no behaviour. Places are character offsets, start inclusive
and end exclusive, into the `text` of one `TextProjection` (one `PartId`). `Span` and `Anchor`
are frozen. The words a string field may hold ("high" | "medium" | "low" and so on) are the
plan's and are written beside the field; nothing here checks them.

Known limits: identifiers are content-based (build-plan.md section 5:
`detection_id = sha256(part || type || normalized_surface || ordinal)`,
`entity_id = sha256(canonical || type)`); they are made by the code that makes a detection or
an entity, not here. `TableCell` is not written out in section 5; its fields are those the
comment on `TextProjection.table_cells` names.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PartId = str  # "body" | "header1" | "footnotes" | "comments" | "docProps" | "textbox3"


@dataclass(frozen=True)
class Span:
    """A place in the text of one part: [start, end) in characters."""

    start: int
    end: int


@dataclass(frozen=True)
class Anchor:
    """Run-length entry: projection [proj_start, proj_end) lives in one text node."""

    proj_start: int
    proj_end: int
    node_path: str
    node_offset: int


@dataclass
class TableCell:
    """Where a table cell lies in the projected text: its table, row, column and span."""

    table_id: str
    row: int
    col: int
    span: Span


@dataclass
class TextProjection:
    """The plain text of one part of a document, with the way back to its nodes."""

    part: PartId
    text: str
    anchors: list[Anchor]  # sorted, contiguous, covers all of text
    block_breaks: list[int]  # hard sentence boundaries: paragraph, table cell, list item, footnote
    table_cells: list[TableCell]


@dataclass
class Detection:
    """One thing a detector found: its place, its type, how sure, and its Hebrew form."""

    detection_id: str  # content-based, see the module docstring
    part: PartId
    span: Span
    surface: str
    entity_type: str
    confidence: float  # calibrated
    band: str  # "high" | "medium" | "low"
    detector: str
    base_span: Span | None  # name without Hebrew proclitic
    prefix: str = ""  # the proclitic present, e.g. "ול"
    suffix: str = ""  # possessive or plural suffix
    lemma: str | None = None
    gender: str | None = None
    at_window_edge: bool = False
    needs_review: bool = False
    review_reason: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class Surrogate:
    """The replacement for one entity, with the surface form for each form it was seen in."""

    value: str
    given: str | None
    surname: str | None
    gender: str | None
    script: str  # "hebrew" | "latin" | "arabic"
    forms: dict[str, str]  # observed surface -> replacement surface
    translit: list[str]  # Latin spellings, for rehydration


@dataclass
class Entity:
    """One person, company or other thing, with every detection that names it."""

    entity_id: str  # stable hash of canonical + type
    entity_type: str
    canonical: str
    variants: set[str]
    detections: list[Detection]
    gender: str | None
    family_group: str | None
    surrogate: Surrogate | None
    decision: str = "replace"  # "replace" | "keep"
    ambiguous: bool = False


@dataclass
class ReviewItem:
    """Something the user must see, or may see, before export."""

    item_id: str
    kind: str  # "low_confidence" | "type_conflict" | "ambiguous_entity" | "residual_risk" | "unanalyzed_image"
    # | "empty_result" | "verification_residue" | "numeric_wordform_unresolved"
    severity: str  # "must_resolve" | "advisory"
    message_key: str
    target: str
    resolved: bool = False
    resolution: str | None = None
