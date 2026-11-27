"""Module suite for ploni/detect/deterministic/israeli_id.py: the detector as the pipeline and the batch call it.

Why: `CLAUDE.md`, Tests: every module gets a suite over its public surface. The unit matrix calls
the detector on one text at a time; this runs it as it is registered, through
`eval.detectors.detect_all`, the callable the held-out scorer and the score check use, and
through the conformance check of the T0 suite, over every text of its fixture file.

Matrix:
  M1  every fixture text through detect_all: the places typed IL_ID are the fixture's (since
      issue #33 detect_all runs the company number detector too, whose detections the fixture's
      company and non-profit negatives hold; tests/t4_integration/test_company_number.py judges
      those)
  M2  every fixture text keeps the Detector contract (tests/detector_contract.py), as a header
      part too
  M3  the detector is registered in eval.detectors.DETECTORS, first, before the company number
      detector of issue #33, the credit card detector of issue #35 and the phone detector of
      issue #36, and requires no morphology
  M4  the other detections detect_all gives on the fixture, but PHONE, are exactly its company
      and non-profit slots, each typed as its list says, seven in all (the review of #33 at
      4d6e477, finding 4), so that M1's filter leaves nothing unjudged; since issue #36
      detect_all runs the phone detector too, whose detections the fixture's phone lines hold;
      tests/t4_integration/test_phone.py, M4, judges those
"""

import json
import string
from pathlib import Path

from eval import detectors
from ploni.detect.base import DetectContext
from ploni.detect.deterministic.company_number import CompanyNumber
from ploni.detect.deterministic.credit_card import CreditCard
from ploni.detect.deterministic.israeli_id import IsraeliId
from ploni.detect.deterministic.phone import Phone
from tests.detector_contract import breaks, projection
from tests.invented_numbers import ISRAELI_IDS, fill, read_cases

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "detect" / "il_id.json"
# The slots of the fixture that hold a company's or a non-profit's number, by their list's name.
REGISTRY = {"company": "COMPANY_NUMBER", "nonprofit": "NONPROFIT_NUMBER"}


def texts() -> list[tuple[str, list[tuple[int, int]]]]:
    """Read every fixture text, its numbers filled in, with its expected places."""
    positives, negatives = read_cases(FIXTURE, ISRAELI_IDS)
    return positives + negatives


def test_m1_through_detect_all() -> None:
    for text, spans in texts():
        found = [each for each in detectors.detect_all(text) if each[2] == "IL_ID"]
        assert found == [(start, end, "IL_ID") for start, end in spans]


def test_m2_the_contract_over_the_fixture() -> None:
    for text, _ in texts():
        for part in ("body", "header1"):
            assert breaks(IsraeliId(), projection(text, part), DetectContext()) == []


def test_m3_registered_and_needs_no_morphology() -> None:
    assert [type(each) for each in detectors.DETECTORS] == [IsraeliId, CompanyNumber, CreditCard, Phone]
    assert IsraeliId.requires_morph is False and IsraeliId.produces == frozenset({"IL_ID"})


def registry_slots(template: str) -> list[tuple[int, int, str]]:
    """Return the places of a template's company and non-profit slots, filled, with their types."""
    names = [name for _, name, _, _ in string.Formatter().parse(template) if name is not None]
    _, spans = fill(template, ISRAELI_IDS)
    return [(start, end, REGISTRY[name.split("[")[0]]) for name, (start, end) in zip(names, spans, strict=True) if name.split("[")[0] in REGISTRY]


def test_m4_the_other_detections_are_the_registry_slots() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    templates = [case["text"] for case in data["positives"] + data["negatives"]]
    seen = 0
    for template in templates:
        text, _ = fill(template, ISRAELI_IDS)
        others = [each for each in detectors.detect_all(text) if each[2] not in ("IL_ID", "PHONE")]
        assert others == registry_slots(template)
        seen += len(others)
    assert seen == 7
