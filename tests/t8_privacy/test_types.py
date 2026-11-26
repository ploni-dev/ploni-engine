"""The core types never show document text when they are printed.

Why: `CLAUDE.md`, Hard constraints: "No document text in logs or temp files." A dataclass's
automatic text form lists every field, and an error message built with one
(`f"overlap: {a} and {b}"`), a debug line or a test failure then carries the text of a
document. Finding 3 of the Ponytail pass at the close of Phase 0 (issue #213). Achia chose on
2026-11-25 "Hide them (Recommended)" for TextProjection.text, Detection.surface,
Entity.canonical and variants, and Surrogate's text fields (issuecomment-7177675350), and on
2026-11-26 "Hide all three too (Recommended)" for Detection.lemma, Detection.metadata and
Surrogate.forms (issuecomment-7187153495).

The name is the module's, `test_types.py`, so that scripts/check_commit_order.py counts it as
a test of ploni/types.py.

Test matrix:

Equivalence classes:
  EC1  the hidden fields, by class (HIDDEN): exactly these have `repr=False`, and no other
       field of the eight types does
  EC2  each of the four classes with text, every hidden field holding the canary, printed in
       each way Python prints an object (repr, str, an f-string, `%s` and `%r`, `format`, a
       list holding it) -> the canary is not in the text; each field that is not hidden is
       (its value still printed)
  EC3  an Entity holding Detections and a Surrogate, the canary in every hidden field of
       each -> not in the text
  EC4  hidden is not gone: the fields read back as given, and two objects that differ only
       in a hidden field are not equal

Boundaries:
  B1  a hidden field left at its default (lemma None, metadata empty): printed the same way
  B2  the canary in the dict keys of Surrogate.forms and of Detection.metadata, and in a set
      (Entity.variants): not in the text

Adversarial:
  A1  the canary in Hebrew, and as a string a field that is not hidden does not hold
  A2  an error raised with an object in its message, `str(error)` and its traceback text:
      no canary

Known limits:
  - A field that is not hidden is printed as it is: an id, a type name, places, a
    confidence, a gender, the proclitic letters (`prefix`, `suffix`), the detector's name.
    They hold no name by the plan; a caller that puts document text into one of them is not
    seen here.
  - `dataclasses.asdict`, `vars()` and a field read by name still give the text: hiding is
    about printing, not about access.

The document-structure axes of the test-matrix skill do not apply: no document is read.
"""

import dataclasses
import traceback
from typing import Any

import pytest

from ploni import types

CANARY = "CANARY-5b21"
HEBREW_CANARY = "יעקב-כהן-קנרית"

# The fields Achia chose to hide, by class (the module docstring), written out here and not
# read from ploni/types.py, so that a field dropped from the list, or added to it, turns EC1 red.
HIDDEN = {
    "TextProjection": {"text"},
    "Detection": {"surface", "lemma", "metadata"},
    "Entity": {"canonical", "variants"},
    "Surrogate": {"value", "given", "surname", "forms", "translit"},
}
CLASSES = ("Span", "Anchor", "TableCell", "TextProjection", "Detection", "Surrogate", "Entity", "ReviewItem")


def projection(canary: str) -> types.TextProjection:
    """Return a TextProjection whose text is the canary."""
    return types.TextProjection(part="body", text=canary, anchors=[], block_breaks=[], table_cells=[])


def detection(canary: str) -> types.Detection:
    """Return a Detection whose hidden fields each hold the canary."""
    return types.Detection(
        detection_id="d1", part="body", span=types.Span(0, 4), surface=canary, entity_type="PERSON",
        confidence=0.9, band="high", detector="trigger", base_span=None, lemma=canary,
        metadata={canary: canary, "local_part": canary},
    )  # fmt: skip


def surrogate(canary: str) -> types.Surrogate:
    """Return a Surrogate whose hidden fields each hold the canary."""
    return types.Surrogate(
        value=canary, given=canary, surname=canary, gender="m", script="hebrew",
        forms={canary: canary}, translit=[canary],
    )  # fmt: skip


def entity(canary: str) -> types.Entity:
    """Return an Entity whose hidden fields, and those of its Detection and Surrogate, hold the canary."""
    return types.Entity(
        entity_id="e1", entity_type="PERSON", canonical=canary, variants={canary}, detections=[detection(canary)],
        gender="m", family_group=None, surrogate=surrogate(canary),
    )  # fmt: skip


MAKERS = {"TextProjection": projection, "Detection": detection, "Surrogate": surrogate, "Entity": entity}


def printed(value: object) -> list[str]:
    """Return the object printed in each way Python prints one."""
    return [repr(value), str(value), f"{value}", f"{value!r}", "%s" % (value,), "%r" % (value,), format(value), str([value])]


def test_ec1_exactly_the_chosen_fields_are_hidden() -> None:
    for name in CLASSES:
        hidden = {item.name for item in dataclasses.fields(getattr(types, name)) if not item.repr}
        assert hidden == HIDDEN.get(name, set()), name


@pytest.mark.parametrize("canary", [CANARY, HEBREW_CANARY])
@pytest.mark.parametrize("name", list(MAKERS))
def test_ec2_a_printed_object_shows_no_hidden_text(name: str, canary: str) -> None:
    value: Any = MAKERS[name](canary)
    for text in printed(value):
        assert canary not in text
    shown = [item.name for item in dataclasses.fields(value) if item.repr]
    for text in printed(value):
        for field in shown:
            assert f"{field}=" in text


@pytest.mark.parametrize("canary", [CANARY, HEBREW_CANARY])
def test_ec3_an_entity_with_its_detections_and_surrogate(canary: str) -> None:
    value = entity(canary)
    assert "Detection(" in repr(value)
    assert "Surrogate(" in repr(value)
    for text in printed(value):
        assert canary not in text


def test_ec4_hidden_is_not_gone() -> None:
    value = detection(CANARY)
    assert value.surface == CANARY
    assert value.lemma == CANARY
    assert value.metadata["local_part"] == CANARY
    assert entity(CANARY).canonical == CANARY
    assert dataclasses.replace(value, surface="other") != value
    assert dataclasses.replace(projection(CANARY), text="other") != projection(CANARY)


def test_b1_a_hidden_field_at_its_default() -> None:
    value = dataclasses.replace(detection(CANARY), lemma=None, metadata={})
    assert "lemma" not in repr(value)
    assert "metadata" not in repr(value)
    assert CANARY not in repr(value)


def test_b2_the_canary_in_keys_and_in_a_set() -> None:
    shown = repr(surrogate(CANARY)) + repr(detection(CANARY)) + repr(entity(CANARY))
    assert CANARY not in shown


def test_a1_a_canary_in_a_field_that_is_not_hidden_is_printed() -> None:
    # The positive control: printing does show what a field that is not hidden holds, so the
    # cases above cannot pass by printing nothing.
    assert CANARY in repr(dataclasses.replace(detection("x"), detector=CANARY))


@pytest.mark.parametrize("name", list(MAKERS))
def test_a2_an_error_raised_with_an_object_in_its_message(name: str) -> None:
    value = MAKERS[name](CANARY)
    try:
        raise ValueError(f"overlap: {value} and {value!r}")
    except ValueError as error:
        assert CANARY not in str(error)
        assert CANARY not in "".join(traceback.format_exception(error))
