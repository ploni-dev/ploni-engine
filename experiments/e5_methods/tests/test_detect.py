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
"""

import hashlib
from pathlib import Path

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
