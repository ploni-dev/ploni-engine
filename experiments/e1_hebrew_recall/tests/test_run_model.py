"""Test matrix for run_model.document_entities.

No model is loaded: the tokenizer and the model call are stand-ins.

document_entities
  EC1  a paragraph that fits one window -> offsets unchanged, cut_paragraphs 0
  A1   a name in the second window of a long paragraph -> the entity still
       slices to the name in the paragraph (the window start is added back)
  EC2  pieces the tokenizer cannot represent are counted per document
"""

from __future__ import annotations

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
