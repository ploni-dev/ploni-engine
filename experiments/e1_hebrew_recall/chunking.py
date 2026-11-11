"""Cut one paragraph into pieces the model can read whole.

Why: the model's `predict` tokenizes with `truncation=True`
(`BertForPrefixMarking.py:239` at the pinned commit), so anything past 512
positions is dropped without a word. A name in the dropped tail would be
counted as a model miss when the model never saw it, and E1 would measure this
harness instead of the model.

Known limits: windows do not overlap, so a name can still be cut in two at a
hard cut. Phase 3 windowing (build-plan.md Phase 3: stride 128) is not
implemented here; `Window.hard_cut` exists so the run can report how often a
cut fell somewhere other than a sentence end.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import NamedTuple

# 512 positions (config.json max_position_embeddings at the pinned commit)
# minus [CLS] and [SEP].
MAX_WORDPIECES = 510
SENTENCE_FINAL_MARKS = ".?!"
# Closing quotes and brackets that may follow the mark, in both the ASCII and
# the Hebrew code points (U+05F4 gershayim, U+05F3 geresh).
TRAILING_CLOSERS = "\"'״׳)]"
# One letter and a full stop is an initial (א. כהן), not the end of a sentence.
MIN_SENTENCE_FINAL_WORD_LENGTH = 2
WORD = re.compile(r"\S+")


class Window(NamedTuple):
    """One piece of a paragraph, as character offsets into that paragraph.

    Why: entity offsets come back relative to the piece, and the worksheet needs
    them relative to the paragraph, so the piece carries where it started.

    Contract: `start` inclusive, `end` exclusive, both in characters. `hard_cut`
    is True when the piece ends somewhere other than a sentence end because
    nothing better fit; it is never True for the last piece of a paragraph.
    """

    start: int
    end: int
    hard_cut: bool


def is_sentence_final(word: str) -> bool:
    """Say whether a whitespace-delimited word ends a sentence.

    Why: a cut is harmless after a sentence and harmful inside a name, and the
    commonest full stop inside a Hebrew name is the one after an initial.

    Contract: `word` has no whitespace. True only when it ends in `.`, `?` or
    `!` (closing quotes or brackets after the mark are ignored), has at least
    MIN_SENTENCE_FINAL_WORD_LENGTH characters before the mark, and those
    characters are not all digits.

    Known limits: a two-letter abbreviation written with a full stop is read as
    a sentence end. Hebrew abbreviations normally use gershayim, not a stop.
    """
    core = word.rstrip(TRAILING_CLOSERS)
    if not core or core[-1] not in SENTENCE_FINAL_MARKS:
        return False
    body = core.rstrip(SENTENCE_FINAL_MARKS)
    return len(body) >= MIN_SENTENCE_FINAL_WORD_LENGTH and not body.isdigit()


def _words_that_fit(costs: list[int], first: int, budget: int) -> int:
    """Return the index one past the last word that fits, starting at `first`.

    Why: kept apart from the cut decision so each can be read on its own.

    Contract: always takes at least one word, even one that costs more than the
    whole budget, so the caller always makes progress.
    """
    used = 0
    index = first
    while index < len(costs):
        if index > first and used + costs[index] > budget:
            break
        used += costs[index]
        index += 1
    return index


def _cut_point(sentence_final: list[bool], first: int, limit: int) -> tuple[int, bool]:
    """Choose where a window that cannot hold the rest of the paragraph ends.

    Why: the last sentence end that fits is the least harmful place to cut.

    Contract: `first < limit`. Returns (index one past the window's last word,
    whether the cut is a hard cut). The index is in `first + 1 .. limit`.
    """
    for index in range(limit - 1, first - 1, -1):
        if sentence_final[index]:
            return index + 1, False
    return limit, True


def split_into_windows(
    text: str,
    count_wordpieces: Callable[[str], int],
    budget: int = MAX_WORDPIECES,
) -> list[Window]:
    """Cut `text` into ordered, disjoint windows of at most `budget` wordpieces.

    Why: see the module docstring; silent truncation would corrupt the count.

    Contract: `count_wordpieces` returns the wordpiece count of one
    whitespace-delimited word. Returns windows in reading order that between
    them contain every word of `text` exactly once and no surrounding
    whitespace; an empty or whitespace-only `text` returns an empty list.
    A window never exceeds `budget` unless it is a single word that does so on
    its own, which the caller must reject.

    Known limits: assumes a window's wordpiece count is the sum over its words,
    true for a BERT tokenizer that pre-splits on whitespace. The caller checks
    the encoded length again, so a wrong assumption fails loudly.
    """
    spans = [match.span() for match in WORD.finditer(text)]
    costs = [count_wordpieces(text[start:end]) for start, end in spans]
    sentence_final = [is_sentence_final(text[start:end]) for start, end in spans]

    windows: list[Window] = []
    first = 0
    while first < len(spans):
        limit = _words_that_fit(costs, first, budget)
        if limit == len(spans):
            cut, hard = limit, False
        else:
            cut, hard = _cut_point(sentence_final, first, limit)
        windows.append(Window(spans[first][0], spans[cut - 1][1], hard))
        first = cut
    return windows
