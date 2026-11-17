"""Test matrix for detect: is_person, _softmax, _rows, file_hashes, peak_memory_mb.

The functions that load a model are not tested here: they need the weights, which are not in
the repository. `run` is exercised by the experiment itself, which prints what it loaded.

is_person (PREREGISTRATION.md, "Which labels are a person")
  EC1  PER, PERSON, private_person, FIRST_NAME, LAST_NAME, bare and with B- or I-   a person
  EC2  O, ORG, GPE, TTL, CITY, private_address, with and without a mark              not one
  A1   a label that only begins like one (PERCENT, PERSONAL_ID)                      not one
  B1   an empty label                                                               not one

_softmax
  EC3  rows of scores                 chances that sum to one per row, the largest score first
  B2   very large scores              no overflow

_rows
  EC4  a token the model labels as a person            written, chosen 1, with its chance
  EC5  a token of another label, chance over the floor written, chosen 0
  EC6  a token of another label, chance under the floor   not written
  EC7  two person labels (FIRST_NAME, LAST_NAME)       their chances are added
  EC8  a mark of the tokenizer, with no characters     not written
  EC9  a window that starts later in the paragraph     places are moved by the shift
  E1   more offsets than rows of chances               ValueError

file_hashes
  EC10 a file that exists and one that does not        only the first, by its name

peak_memory_mb
  EC11 this process                                    a positive number of megabytes

measure (a run made in parts, for a machine that cannot hold a long run)
  EC12 no budget                                       every document, in order; True
  EC13 a budget that ends after two documents          those two; False; a third is not begun
  EC14 a second call on the same state                 the documents already done are not run again
  EC15 the seconds                                     only the time inside the detector is added, over all parts
  B3   a budget smaller than one document              one document is still done in every call

part_state
  EC16 no file of an earlier part                      a fresh state for this model and corpus
  EC17 a file of an earlier part of the same run       that state
  E2   a file of another model or another corpus       ValueError
"""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy
import pytest

import detect


@pytest.mark.parametrize("label", ["PER", "B-PER", "I-PER", "PERSON", "B-private_person", "I-private_person", "B-FIRST_NAME", "I-LAST_NAME", "E-PER", "S-PER"])
def test_ec1_a_person_label(label: str) -> None:
    assert detect.is_person(label)


@pytest.mark.parametrize("label", ["O", "ORG", "B-ORG", "I-GPE", "B-TTL", "B-CITY", "I-private_address", "PERCENT", "B-PERSONAL_ID", "", "B-"])
def test_ec2_a1_b1_a_label_that_is_no_person(label: str) -> None:
    assert not detect.is_person(label)


def test_ec3_b2_softmax() -> None:
    chances = detect._softmax(numpy.array([[1.0, 2.0, 3.0], [1000.0, 0.0, -1000.0]]))
    assert chances.sum(axis=1) == pytest.approx([1.0, 1.0])
    assert chances[0].argmax() == 2
    assert chances[1] == pytest.approx([1.0, 0.0, 0.0])


def test_ec4_to_ec6_rows() -> None:
    # Labels: 0 is O, 1 is a person.
    chances = numpy.array([[0.1, 0.9], [0.8, 0.2], [0.995, 0.005]])
    rows = detect._rows(3, 0, [(0, 4), (5, 8), (9, 12)], chances, [1])
    assert rows == [[3, 0, 4, 0.9, 1], [3, 5, 8, 0.2, 0]]


def test_ec7_two_person_labels_are_added() -> None:
    chances = numpy.array([[0.2, 0.45, 0.35], [0.9, 0.06, 0.04]])
    rows = detect._rows(0, 0, [(0, 4), (5, 8)], chances, [1, 2])
    assert rows == [[0, 0, 4, 0.8, 1], [0, 5, 8, 0.1, 0]]


def test_ec8_ec9_marks_of_the_tokenizer_and_the_shift() -> None:
    chances = numpy.array([[0.0, 1.0], [0.0, 1.0], [0.0, 1.0]])
    rows = detect._rows(0, 100, [(0, 0), (0, 4), (0, 0)], chances, [1])
    assert rows == [[0, 100, 104, 1.0, 1]]


def test_e1_offsets_and_chances_of_different_lengths() -> None:
    with pytest.raises(ValueError, match="zip"):
        detect._rows(0, 0, [(0, 1), (1, 2)], numpy.array([[0.0, 1.0]]), [1])


def test_ec10_file_hashes(tmp_path: Path) -> None:
    (tmp_path / "config.json").write_bytes(b"{}")
    found = detect.file_hashes([tmp_path / "config.json", tmp_path / "missing.bin"])
    assert found == {"config.json": hashlib.sha256(b"{}").hexdigest()}


def test_ec11_peak_memory() -> None:
    assert detect.peak_memory_mb() > 1


DOCUMENTS = [SimpleNamespace(doc_id=f"doc{number:02d}", paragraphs=[f"paragraph {number}"]) for number in range(1, 6)]


class Clock:
    """A clock that moves only when a detector is said to work: ten seconds per document."""

    def __init__(self) -> None:
        self.now = 0.0
        self.ran: list[str] = []

    def __call__(self) -> float:
        return self.now

    def tokens(self, paragraphs: list[str]) -> list[list]:
        self.ran.append(paragraphs[0])
        self.now += 10.0
        return [[0, 0, 1, 1.0, 1]]


def fresh() -> dict:
    """Return the state of a run of which nothing is done yet."""
    return {"model": "m", "dataset": "select", "tokens": {}, "seconds": 0.0, "peak_mb": 0, "parts": 0}


def test_ec12_no_budget_runs_every_document_in_order() -> None:
    clock, state = Clock(), fresh()
    assert detect.measure(clock.tokens, DOCUMENTS, state, None, clock) is True
    assert list(state["tokens"]) == [document.doc_id for document in DOCUMENTS]
    assert clock.ran == [f"paragraph {number}" for number in range(1, 6)]
    assert state["seconds"] == 50.0


def test_ec13_ec14_ec15_a_run_in_parts() -> None:
    clock, state = Clock(), fresh()
    assert detect.measure(clock.tokens, DOCUMENTS, state, 15.0, clock) is False
    assert list(state["tokens"]) == ["doc01", "doc02"]
    clock.now += 1000.0  # the time between two parts, and the loading of the model, are not the detector's
    assert detect.measure(clock.tokens, DOCUMENTS, state, 15.0, clock) is False
    assert list(state["tokens"]) == ["doc01", "doc02", "doc03", "doc04"]
    assert detect.measure(clock.tokens, DOCUMENTS, state, 15.0, clock) is True
    assert clock.ran == [f"paragraph {number}" for number in range(1, 6)]
    assert state["seconds"] == 50.0


def test_b3_a_budget_smaller_than_one_document_still_does_one() -> None:
    clock, state = Clock(), fresh()
    assert detect.measure(clock.tokens, DOCUMENTS, state, 0.001, clock) is False
    assert list(state["tokens"]) == ["doc01"]


def test_ec16_ec17_e2_part_state(tmp_path: Path) -> None:
    part = tmp_path / "golem.select.json.part"
    assert detect.part_state(part, "m", "select") == fresh()
    kept = {**fresh(), "tokens": {"doc01": []}, "seconds": 10.0, "parts": 1}
    part.write_text(json.dumps(kept), encoding="utf-8")
    assert detect.part_state(part, "m", "select") == kept
    with pytest.raises(ValueError, match="another run"):
        detect.part_state(part, "other", "select")
    with pytest.raises(ValueError, match="another run"):
        detect.part_state(part, "m", "heldout")
