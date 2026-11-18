"""The core types that every layer of the pipeline passes to the next.

Why: a span, a detection or an entity crosses from the adapters to the detectors, the
resolver, the policy and the writer. One definition, in the lowest layer, keeps them the same
everywhere. They are those of build-plan.md section 5.

Contract: plain dataclasses with no behaviour. Places are character offsets, start inclusive
and end exclusive, into the `text` of one `TextProjection` (one `PartId`), except `Anchor.node_offset`,
which counts characters into its own text node. `Span` and `Anchor` are frozen, as the plan
marks them. The words a string field may hold ("high" | "medium" | "low" and so on) are the
plan's and are written beside the field; nothing here checks them.

Known limits: identifiers are content-based (build-plan.md section 5:
`detection_id = sha256(part || type || normalized_surface || ordinal)`,
`entity_id = sha256(canonical || type)`); they are made by the code that makes a detection or
an entity, not here. `TableCell` is not written out in section 5; its fields are those the
comment on `TextProjection.table_cells` names, and its row and column count from 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PartId = str  # "body" | "header1" | "footnotes" | "comments" | "docProps" | "textbox3"


@dataclass(frozen=True)
class Span:
    """A place in the text of one part: [start, end) in characters.

    Why: every detection, base form and table cell is a place, and a place that changed
    after it was checked would point at other text.

    Contract: frozen, so it can be a key of a dict or a member of a set. End exclusive.

    Known limits: it does not check that start <= end or that it lies inside the text; the
    code that makes it does.
    """

    start: int
    end: int


@dataclass(frozen=True)
class Anchor:
    """Run-length entry: projection [proj_start, proj_end) lives in one text node.

    Why: the writer puts a replacement back into the document's own nodes, so every stretch
    of projected text must say which node it came from.

    Contract: frozen. `proj_start` and `proj_end` count characters in the projection's text;
    `node_offset` counts characters into the text node at `node_path`, where `proj_start`
    lies.

    Known limits: the form of `node_path` is the adapter's; nothing here reads it.
    """

    proj_start: int
    proj_end: int
    node_path: str
    node_offset: int


@dataclass
class TableCell:
    """Where one table cell lies in the projected text.

    Why: a cell is a hard boundary for a name (build-plan.md section 5, the comment on
    `TextProjection.block_breaks`).

    Contract: `row` and `col` count from 0; `span` is a place in the projection's text.

    Known limits: not in section 5 as a class; written out from the comment on
    `TextProjection.table_cells` ("table_id, row, col, span"). How a merged cell is written
    is the adapter's, and not settled here.
    """

    table_id: str
    row: int
    col: int
    span: Span


@dataclass
class TextProjection:
    """The plain text of one part of a document, with the way back to its nodes.

    Why: the detectors read plain text, and the writer must put every change back where it
    came from.

    Contract: `anchors` are sorted, contiguous and cover all of `text`; `block_breaks` are
    offsets into `text` where a name cannot run on.

    Known limits: none of the three lists is checked here.
    """

    part: PartId
    text: str
    anchors: list[Anchor]  # sorted, contiguous, covers all of text
    block_breaks: list[int]  # hard sentence boundaries: paragraph, table cell, list item, footnote
    table_cells: list[TableCell]


@dataclass
class Detection:
    """One thing a detector found in one part of a document.

    Why: what every detector returns and what the resolver joins into entities, so that
    detectors of every kind can be compared and fused.

    Contract: `span` is the whole surface, attached letters included; `base_span` is the
    name without its Hebrew proclitic, or None when there is none. `confidence` is
    calibrated, from 0 to 1; `band` is "high", "medium" or "low". `metadata` is the
    detector's own, a new dict for each detection.

    Known limits: the words of `band` and the range of `confidence` are not checked here.
    """

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
    metadata: dict[Any, Any] = field(default_factory=dict)


@dataclass
class Surrogate:
    """The replacement for one entity.

    Why: one entity gets one replacement, used in every surface form it was seen in, and
    the AI's answer is mapped back through it.

    Contract: `forms` maps each observed surface to its replacement surface; `translit`
    holds Latin spellings of the replacement, for rehydration. `script` is "hebrew",
    "latin" or "arabic".

    Known limits: nothing here checks that `forms` covers every variant of the entity.
    """

    value: str
    given: str | None
    surname: str | None
    gender: str | None
    script: str  # "hebrew" | "latin" | "arabic"
    forms: dict[str, str]  # observed surface -> replacement surface
    translit: list[str]  # Latin spellings, for rehydration


@dataclass
class Entity:
    """One person, company or other thing, with every detection that names it.

    Why: the product replaces an entity, not a string: every mention of one person must get
    the same surrogate.

    Contract: `entity_id` is a stable hash of `canonical` and `entity_type`; `decision` is
    "replace" or "keep". `detections` is the list itself, not a copy.

    Known limits: `decision` is not checked here.
    """

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
    """Something the user must see, or may see, before export.

    Why: an export is blocked while a must-resolve item is open (`errors.NotApprovedError`).

    Contract: `severity` is "must_resolve" or "advisory"; `kind` is one of the eight words
    beside it; `message_key` names a text in `ploni/i18n/`. Open until `resolved`.

    Known limits: the words of `kind` and `severity` are not checked here.
    """

    item_id: str
    kind: str  # "low_confidence" | "type_conflict" | "ambiguous_entity" | "residual_risk" | "unanalyzed_image"
    # | "empty_result" | "verification_residue" | "numeric_wordform_unresolved"
    severity: str  # "must_resolve" | "advisory"
    message_key: str
    target: str
    resolved: bool = False
    resolution: str | None = None
