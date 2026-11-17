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

peak_memory_mb
  EC11 this process                                    a positive number of megabytes

measure (a run made in parts, for a machine that cannot hold a long run)
  EC12 no budget                                       every document, in order; True
  EC13 a budget that ends after two documents          those two; False; a third is not begun
  EC14 a second call on the same state                 the documents already done are not run again
  EC15 the seconds                                     only the time inside the detector is added, over all parts
  B3   a budget smaller than one document              one document is still done in every call

part_state
  EC16 no file of an earlier part                      a fresh state for this run
  EC17 a file of an earlier part of the same run       that state
  E2   a file of another model, another kind of detector, another weights file, another
       corpus, or the same corpus with another text    ValueError

paragraph_rows (the windows of a long paragraph, with a made-up tokenizer and model)
  EC18 a paragraph of one window                       every character at its own place
  EC19 a paragraph cut into several windows            every character once, at its place in
                                                       the paragraph, not in its window
  E3   a window longer than was counted                ValueError

file_sha256 / checked_hashes / _write
  EC20 a file                                          its SHA-256
  EC21 weights with the expected hash                  the hashes of the folder's files
  E4   weights with another hash, no expected hash, an ONNX file with another hash   ValueError
  EC22 a file written over an older one                the new content, and nothing left beside it
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


IDENTITY = {"detector": "hf", "model": "m", "weights": "model.safetensors", "dataset": "select", "corpus_sha256": "abc"}


def fresh() -> dict:
    """Return the state of a run of which nothing is done yet."""
    return {"identity": dict(IDENTITY), "tokens": {}, "seconds": 0.0, "peak_mb": 0, "parts": 0}


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


def test_ec16_ec17_part_state(tmp_path: Path) -> None:
    part = tmp_path / "golem.select.json.part"
    assert detect.part_state(part, dict(IDENTITY)) == fresh()
    kept = {**fresh(), "tokens": {"doc01": []}, "seconds": 10.0, "parts": 1}
    part.write_text(json.dumps(kept), encoding="utf-8")
    assert detect.part_state(part, dict(IDENTITY)) == kept


@pytest.mark.parametrize(
    ("key", "value"),
    [("model", "other"), ("detector", "onnx"), ("weights", "model_quantized.onnx"), ("dataset", "heldout"), ("corpus_sha256", "def")],
)
def test_e2_a_part_file_of_another_run_is_refused(tmp_path: Path, key: str, value: str) -> None:
    part = tmp_path / "golem.select.json.part"
    part.write_text(json.dumps({**fresh(), "tokens": {"doc01": []}}), encoding="utf-8")
    with pytest.raises(ValueError, match="another run"):
        detect.part_state(part, {**IDENTITY, key: value})


class Pieces:
    """A made-up tokenizer: one piece per character that is no white space, between two marks of its own."""

    def tokenize(self, word: str) -> list[str]:
        return list(word)

    def __call__(self, text: str, return_offsets_mapping: bool, return_tensors: str) -> dict:
        offsets = [(0, 0)] + [(place, place + 1) for place, sign in enumerate(text) if not sign.isspace()] + [(0, 0)]
        return {"input_ids": numpy.zeros((1, len(offsets)), dtype=int), "offset_mapping": numpy.array([offsets])}


def every_piece_a_person(encoded: dict) -> numpy.ndarray:
    """A made-up model with two labels that calls every piece a person."""
    scores = numpy.zeros((encoded["input_ids"].shape[1], 2))
    scores[:, 1] = 9.0
    return scores


def test_ec18_ec19_the_places_of_a_paragraph_cut_into_windows() -> None:
    paragraph = "אב גד. הו זח. טי כל. מנ סע."
    whole = detect.paragraph_rows(3, paragraph, Pieces(), every_piece_a_person, [1])
    cut = detect.paragraph_rows(3, paragraph, Pieces(), every_piece_a_person, [1], budget=6)
    expected = [[3, place, place + 1, 1.0, 1] for place, sign in enumerate(paragraph) if not sign.isspace()]
    assert whole == expected
    assert cut == expected
    # The cut really happened: with a budget of six pieces no window holds the paragraph.
    assert sum(not sign.isspace() for sign in paragraph) > 6


def test_e3_a_window_longer_than_was_counted() -> None:
    class Undercounting(Pieces):
        def tokenize(self, word: str) -> list[str]:
            return [word]

    with pytest.raises(ValueError, match="positions"):
        detect.paragraph_rows(0, "אבגדהו זחטיכל", Undercounting(), every_piece_a_person, [1], budget=2)


def test_ec20_ec21_e4_the_weights_are_checked_before_a_run(tmp_path: Path) -> None:
    (tmp_path / "model.safetensors").write_bytes(b"weights")
    (tmp_path / "config.json").write_bytes(b"{}")
    (tmp_path / "model.onnx").write_bytes(b"other weights")
    right, onnx = hashlib.sha256(b"weights").hexdigest(), hashlib.sha256(b"other weights").hexdigest()
    assert detect.file_sha256(tmp_path / "model.safetensors") == right
    assert detect.checked_hashes("hf", tmp_path, None, right) == {"model.safetensors": right, "config.json": hashlib.sha256(b"{}").hexdigest()}
    assert detect.checked_hashes("onnx", tmp_path, tmp_path / "model.onnx", onnx)["model.onnx"] == onnx
    for expected, onnx_file in ((onnx, None), (None, None), (right, tmp_path / "model.onnx")):
        with pytest.raises(ValueError, match="sha256"):
            detect.checked_hashes("hf" if onnx_file is None else "onnx", tmp_path, onnx_file, expected)
    with pytest.raises(ValueError, match="sha256"):
        detect.checked_hashes("hf", tmp_path / "missing", None, right)


def test_ec22_a_file_is_written_whole(tmp_path: Path) -> None:
    out = tmp_path / "run.json.part"
    detect._write(out, {"parts": 1})
    detect._write(out, {"parts": 2, "name": "יעקב"})
    assert json.loads(out.read_text(encoding="utf-8")) == {"parts": 2, "name": "יעקב"}
    assert [path.name for path in tmp_path.iterdir()] == ["run.json.part"]
