"""The type contracts of ploni/types.py and ploni/errors.py: the core types of build-plan.md section 5.

Why: every later phase passes these types between layers. A field renamed, dropped, reordered
or given another default breaks callers that the type checker of one module does not see, and
a frozen type made mutable lets a span change after it was checked. Phase 0 asks for "T0 type
contracts" (build-plan.md Phase 0, "Tests added").

Test matrix:

Equivalence classes:
  EC1  each of the eight types of section 5: its fields, by name and in order, each with the type
       the plan writes (Span, Anchor, TableCell, TextProjection, Detection, Surrogate, Entity,
       ReviewItem). The type is compared as written, a string: the module uses postponed
       annotations
  EC2  the defaults the plan gives (Detection: prefix, suffix, lemma, gender, at_window_edge,
       needs_review, review_reason, metadata; Entity: decision, ambiguous; ReviewItem:
       resolved, resolution); every other field has none
  EC3  frozen: Span and Anchor refuse a new value; the others take one
  EC4  a mutable default is not shared: two Detections get two metadata dicts
  EC5  PartId is a name for str
  EC6  errors: PloniError is an Exception; NotApprovedError is a PloniError

Boundaries:
  B1  a Detection built with only the fields that have no default
  B2  base_span None and a Span; lemma and review_reason None

Error paths:
  E1  a frozen Span given a new start: dataclasses.FrozenInstanceError
  E2  a type built without a field that has no default: TypeError

Adversarial:
  A1  a Span with end before start is built: the type holds places, it does not judge them
      (the detectors and the conformance suite of Phase 1 do)

Known limits: the types are checked by shape, not by the meaning of their values ("band" is
one of three words, "severity" one of two). The plan gives those as comments, and nothing
here enforces them.
"""

import dataclasses

import pytest

from ploni import errors, types

# build-plan.md section 5, field by field, in the order the plan writes them, each with the
# type the plan writes. A bare `dict` in the plan is `dict[Any, Any]`, which is what it means.
TYPED = {
    "Span": [("start", "int"), ("end", "int")],
    "Anchor": [("proj_start", "int"), ("proj_end", "int"), ("node_path", "str"), ("node_offset", "int")],
    "TableCell": [("table_id", "str"), ("row", "int"), ("col", "int"), ("span", "Span")],
    "TextProjection": [
        ("part", "PartId"), ("text", "str"), ("anchors", "list[Anchor]"), ("block_breaks", "list[int]"),
        ("table_cells", "list[TableCell]"),
    ],
    "Detection": [
        ("detection_id", "str"), ("part", "PartId"), ("span", "Span"), ("surface", "str"), ("entity_type", "str"),
        ("confidence", "float"), ("band", "str"), ("detector", "str"), ("base_span", "Span | None"), ("prefix", "str"),
        ("suffix", "str"), ("lemma", "str | None"), ("gender", "str | None"), ("at_window_edge", "bool"),
        ("needs_review", "bool"), ("review_reason", "str | None"), ("metadata", "dict[Any, Any]"),
    ],
    "Surrogate": [
        ("value", "str"), ("given", "str | None"), ("surname", "str | None"), ("gender", "str | None"), ("script", "str"),
        ("forms", "dict[str, str]"), ("translit", "list[str]"),
    ],
    "Entity": [
        ("entity_id", "str"), ("entity_type", "str"), ("canonical", "str"), ("variants", "set[str]"),
        ("detections", "list[Detection]"), ("gender", "str | None"), ("family_group", "str | None"),
        ("surrogate", "Surrogate | None"), ("decision", "str"), ("ambiguous", "bool"),
    ],
    "ReviewItem": [
        ("item_id", "str"), ("kind", "str"), ("severity", "str"), ("message_key", "str"), ("target", "str"),
        ("resolved", "bool"), ("resolution", "str | None"),
    ],
}  # fmt: skip
FIELDS = {name: [field for field, _ in fields] for name, fields in TYPED.items()}
DEFAULTS = {
    "Detection": {
        "prefix": "", "suffix": "", "lemma": None, "gender": None, "at_window_edge": False, "needs_review": False,
        "review_reason": None,
    },
    "Entity": {"decision": "replace", "ambiguous": False},
    "ReviewItem": {"resolved": False, "resolution": None},
}  # fmt: skip
FROZEN = {"Span", "Anchor"}


def detection(**changes: object) -> types.Detection:
    """Build a Detection with every field that has no default."""
    values = {
        "detection_id": "d1", "part": "body", "span": types.Span(0, 3), "surface": "כהן", "entity_type": "PERSON",
        "confidence": 0.9, "band": "high", "detector": "hebrew_ner", "base_span": None,
    }  # fmt: skip
    values.update(changes)
    return types.Detection(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("name", sorted(FIELDS))
def test_ec1_the_fields_of_each_type(name: str) -> None:
    cls = getattr(types, name)
    assert dataclasses.is_dataclass(cls)
    assert [(field.name, field.type) for field in dataclasses.fields(cls)] == TYPED[name]


@pytest.mark.parametrize("name", sorted(FIELDS))
def test_ec2_the_defaults(name: str) -> None:
    fields = {field.name: field for field in dataclasses.fields(getattr(types, name))}
    for field_name, field in fields.items():
        if name in DEFAULTS and field_name in DEFAULTS[name]:
            assert field.default == DEFAULTS[name][field_name], field_name
        elif (name, field_name) == ("Detection", "metadata"):
            assert field.default_factory is dict
        else:
            assert field.default is dataclasses.MISSING and field.default_factory is dataclasses.MISSING, field_name


@pytest.mark.parametrize("name", sorted(FIELDS))
def test_ec3_e1_frozen(name: str) -> None:
    assert getattr(types, name).__dataclass_params__.frozen is (name in FROZEN)
    with pytest.raises(dataclasses.FrozenInstanceError):
        types.Span(0, 1).start = 2  # type: ignore[misc]


def test_ec4_b1_b2_a_detection_and_its_own_metadata() -> None:
    first, second = detection(), detection(base_span=types.Span(1, 3), prefix="ו")
    first.metadata["k"] = "v"
    assert second.metadata == {}
    assert (first.base_span, second.base_span, first.lemma, first.review_reason) == (None, types.Span(1, 3), None, None)


def test_ec5_part_id() -> None:
    assert types.PartId is str


def test_ec6_errors() -> None:
    assert issubclass(errors.PloniError, Exception)
    assert issubclass(errors.NotApprovedError, errors.PloniError)
    with pytest.raises(errors.PloniError):
        raise errors.NotApprovedError("must-resolve items are open")


def test_e2_a_field_with_no_default_is_needed() -> None:
    with pytest.raises(TypeError):
        types.Span(0)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        types.ReviewItem("i", "low_confidence", "advisory", "key")  # type: ignore[call-arg]


def test_a1_a_span_does_not_judge_its_places() -> None:
    assert types.Span(5, 2) == types.Span(5, 2)
