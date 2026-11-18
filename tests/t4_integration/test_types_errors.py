"""Module suite for ploni/types.py and ploni/errors.py: the types put together as the pipeline will.

Why: `CLAUDE.md`, Tests: every module gets a suite over its public surface. The T0 contracts
check each type alone; this checks that they compose: a projection with its anchors and
table cells, detections inside an entity with its surrogate, and a review item that blocks
an export with the error the plan names.

Matrix:
  M1  a projection of one table cell, two detections of one person in it, an entity that holds
      both and a surrogate with a form for each surface: every place points into the text
  M2  two entities built from the same detections list: they share it (a list is not copied)
  M3  an open must-resolve item: NotApprovedError raised, caught as PloniError, its message
      holds the item id and no text of the document
"""

import pytest

from ploni import errors, types

TEXT = "ישראל ישראלי ולישראלי"


def build() -> tuple[types.TextProjection, types.Entity]:
    """Build a projection with one table cell and an entity named twice in it."""
    cell = types.TableCell("t1", 0, 0, types.Span(0, len(TEXT)))
    projection = types.TextProjection("body", TEXT, [types.Anchor(0, len(TEXT), "w:body/w:tbl[0]/w:tc[0]/w:r[0]", 0)], [len(TEXT)], [cell])
    first = types.Detection("d1", "body", types.Span(0, 12), "ישראל ישראלי", "PERSON", 0.95, "high", "hebrew_ner", None)
    second = types.Detection("d2", "body", types.Span(13, 21), "ולישראלי", "PERSON", 0.7, "medium", "carry", types.Span(15, 21), prefix="ול")
    surrogate = types.Surrogate("דוד לוי", "דוד", "לוי", "m", "hebrew", {"ישראל ישראלי": "דוד לוי", "ולישראלי": "וללוי"}, ["David Levi"])
    entity = types.Entity("e1", "PERSON", "ישראל ישראלי", {"ישראל ישראלי", "ישראלי"}, [first, second], "m", None, surrogate)
    return projection, entity


def test_m1_the_types_compose() -> None:
    projection, entity = build()
    for detection in entity.detections:
        assert projection.text[detection.span.start : detection.span.end] == detection.surface
        assert entity.surrogate is not None and detection.surface in entity.surrogate.forms
    second = entity.detections[1]
    assert second.base_span is not None
    assert second.prefix + projection.text[second.base_span.start : second.base_span.end] == second.surface
    assert projection.anchors[0].proj_end == len(projection.text) == projection.table_cells[0].span.end
    assert entity.decision == "replace" and not entity.ambiguous


def test_m2_a_list_is_shared_not_copied() -> None:
    _, entity = build()
    other = types.Entity("e2", "PERSON", "x", set(), entity.detections, None, None, None)
    other.detections.append(entity.detections[0])
    assert len(entity.detections) == 3


def test_m3_an_open_item_blocks_an_export() -> None:
    item = types.ReviewItem("r1", "low_confidence", "must_resolve", "review.low_confidence", "e1")

    def export(items: list[types.ReviewItem]) -> None:
        open_items = [each.item_id for each in items if each.severity == "must_resolve" and not each.resolved]
        if open_items:
            raise errors.NotApprovedError(f"open must-resolve items: {', '.join(open_items)}")

    with pytest.raises(errors.PloniError, match="r1") as caught:
        export([item])
    assert isinstance(caught.value, errors.NotApprovedError) and TEXT not in str(caught.value)
    item.resolved, item.resolution = True, "kept"
    export([item])
