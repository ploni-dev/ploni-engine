"""Test matrix for run_model.document_entities.

No model is loaded: the tokenizer and the model call are stand-ins.

document_entities
  EC1  a paragraph that fits one window -> offsets unchanged, cut_paragraphs 0
  A1   a name in the second window of a long paragraph -> the entity still
       slices to the name in the paragraph (the window start is added back)
  EC2  pieces the tokenizer cannot represent are counted per document

window_entities  (the guard against silent truncation)
  E1   a window one position over the limit -> WindowTooLongError, model untouched
  B1   a window exactly at the limit        -> the model is called
  E6   a tokenizer set to truncate below the limit -> WindowTooLongError, model
       untouched (the model's own predict would cut the window without a sign)

check_private_directories  (no real document text inside a repository)
  EC3  corpus and output folders outside any repository -> accepted
  E2   either folder inside this repository -> ValueError
  E3   an output folder inside another checkout (any git work tree), existing
       or not yet created                   -> ValueError
  E4   an output folder that already holds tally.csv -> FileExistsError
  E7   an output folder under a `.git` file, which is how a second checkout
       (git worktree) is marked           -> ValueError, without asking git
  B2   an output folder whose parents do not exist yet -> accepted, no error

model_file_hashes  (run_meta.json says which weights were run)
  EC4  the SHA-256 of each named file
  E5   a named file is missing              -> FileNotFoundError
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

import run_model


class WordTokenizer:
    """One piece per whitespace word; a word containing `?` is unknown."""

    unk_token = "[UNK]"

    def tokenize(self, text: str) -> list[str]:
        return [self.unk_token if "?" in word else word for word in text.split()]


@pytest.fixture
def find_moshe(monkeypatch):
    def window_entities(model, tokenizer, text):
        start = text.find("משה")
        return [] if start < 0 else [(start, start + 3, "PER")]

    monkeypatch.setattr(run_model, "window_entities", window_entities)


def test_ec1_short_paragraph(find_moshe):
    result = run_model.document_entities(None, WordTokenizer(), ["אתמול הגיע משה למשרד"])
    (entity,) = result.entities
    assert "אתמול הגיע משה למשרד"[entity.start : entity.end] == "משה"
    assert result.cut_paragraphs == 0


def test_a1_name_in_the_second_window(find_moshe):
    paragraph = " ".join(["מילה"] * 600 + ["משה"])
    result = run_model.document_entities(None, WordTokenizer(), ["פתיחה", paragraph])
    (entity,) = result.entities
    assert (entity.paragraph, paragraph[entity.start : entity.end]) == (1, "משה")
    assert (result.windows, result.cut_paragraphs) == (3, 1)


def test_ec2_unknown_pieces_are_counted(find_moshe):
    result = run_model.document_entities(None, WordTokenizer(), ["משה ? כהן", "עוד ?? ?"])
    assert result.unknown_pieces == 3


class FixedLengthTokenizer:
    """Encodes any text to a fixed number of positions."""

    def __init__(self, positions: int, model_max_length: int = run_model.MAX_POSITIONS):
        self.positions = positions
        self.model_max_length = model_max_length

    def __call__(self, text: str) -> dict[str, list[int]]:
        return {"input_ids": [0] * self.positions}


class CountingModel:
    """Stands in for the model with the syntax head off; counts the calls."""

    syntax = None
    calls = 0

    def predict(self, text, tokenizer, **options):
        self.calls += 1
        return {"ner_entities": []}


def test_e1_window_over_the_limit_never_reaches_the_model():
    model = CountingModel()
    with pytest.raises(run_model.WindowTooLongError):
        run_model.window_entities(model, FixedLengthTokenizer(run_model.MAX_POSITIONS + 1), "טקסט")
    assert model.calls == 0


def test_b1_window_at_the_limit_is_run():
    model = CountingModel()
    assert run_model.window_entities(model, FixedLengthTokenizer(run_model.MAX_POSITIONS), "טקסט") == []
    assert model.calls == 1


def test_e6_tokenizer_that_truncates_below_the_limit_never_reaches_the_model():
    model = CountingModel()
    with pytest.raises(run_model.WindowTooLongError):
        run_model.window_entities(model, FixedLengthTokenizer(100, model_max_length=256), "טקסט")
    assert model.calls == 0


def test_e7_folder_inside_a_second_checkout_marked_by_a_git_file(tmp_path: Path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: elsewhere", encoding="utf-8")
    with pytest.raises(ValueError, match="inside"):
        run_model.check_private_directories(tmp_path, worktree / "e1_out")


def test_b2_folder_on_a_path_with_no_existing_parent_is_accepted(tmp_path: Path):
    run_model.check_private_directories(tmp_path, tmp_path / "not" / "created" / "yet")


def test_ec3_folders_outside_any_repository_are_accepted(tmp_path: Path):
    (tmp_path / "corpus").mkdir()
    run_model.check_private_directories(tmp_path / "corpus", tmp_path / "out")


@pytest.mark.parametrize("inside", ["corpus", "out"])
def test_e2_folder_inside_this_repository(tmp_path: Path, inside: str):
    folders = {"corpus": tmp_path / "corpus", "out": tmp_path / "out"}
    folders[inside] = run_model.REPO_ROOT / "experiments" / "not_created"
    with pytest.raises(ValueError, match="inside"):
        run_model.check_private_directories(folders["corpus"], folders["out"])


@pytest.mark.parametrize("out", ["e1_out", "deep/not/created"])
def test_e3_folder_inside_another_checkout(tmp_path: Path, out: str):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(["git", "init", "--quiet", str(checkout)], check=True)
    with pytest.raises(ValueError, match="inside"):
        run_model.check_private_directories(tmp_path, checkout / out)


def test_e4_output_folder_with_a_tally_is_refused(tmp_path: Path):
    (tmp_path / "tally.csv").write_text("annotated by hand", encoding="utf-8")
    with pytest.raises(FileExistsError):
        run_model.check_private_directories(tmp_path, tmp_path)


def test_ec4_model_file_hashes(tmp_path: Path):
    for name in run_model.HASHED_MODEL_FILES:
        (tmp_path / name).write_bytes(name.encode())
    assert run_model.model_file_hashes(tmp_path) == {
        name: hashlib.sha256(name.encode()).hexdigest() for name in run_model.HASHED_MODEL_FILES
    }


def test_e5_model_file_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        run_model.model_file_hashes(tmp_path)
