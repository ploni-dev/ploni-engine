"""Test matrix for chunking.split_into_windows and chunking.is_sentence_final.

Cost model in these tests: one wordpiece per whitespace word unless stated.

Equivalence classes:
  EC1  paragraph fits the budget            -> one window, no hard cut
  EC2  too long, a sentence end fits        -> cut after the sentence end
  EC3  too long, no sentence end            -> cut before the overflowing word, hard cut
  EC4  needs several cuts                   -> every window within budget
  EC5  word cost above one (long word)      -> budget counted in wordpieces, not words

Boundaries:
  B1  empty string                          -> no windows
  B2  whitespace only                       -> no windows
  B3  exactly the budget                    -> one window
  B4  budget plus one                       -> two windows
  B5  one word above the budget on its own  -> its own window (the caller's guard rejects it)
  B6  leading and trailing whitespace       -> window spans exclude it

Hebrew axes:
  H1  abbreviations with gershayim, both code points (עו"ד, ד״ר)  -> not a sentence end
  H2  geresh inside a transliterated name, both code points (ג'ון, ג׳ורג׳)
  H3  sentence end followed by a closing quote (אמר "לא.")       -> sentence end

Adversarial:
  A1  initial with a full stop before a surname (א. כהן)  -> never the cut point
  A2  numbered list marker (1.)                           -> never the cut point

Invariant, 500 generated cases:
  P1  windows are ordered and disjoint, together hold every word exactly once,
      and no window of more than one word costs more than the budget.
"""

from __future__ import annotations

import random
import re

from chunking import Window, is_sentence_final, split_into_windows

GENERATED_CASES = 500  # CLAUDE.md Tests: invariants 500 generated cases
SEED = 20261111  # fixed so a failing generated case reproduces


def one_per_word(word: str) -> int:
    return 1


def window_texts(text: str, windows: list[Window]) -> list[str]:
    return [text[w.start : w.end] for w in windows]


def test_ec1_fits_budget():
    text = "משה כהן הגיש תביעה."
    assert split_into_windows(text, one_per_word, 10) == [Window(0, len(text), False)]


def test_ec2_cut_after_sentence_end():
    text = "התובע טען כך. הנתבע השיב אחרת לגמרי"
    windows = split_into_windows(text, one_per_word, 5)
    assert window_texts(text, windows) == ["התובע טען כך.", "הנתבע השיב אחרת לגמרי"]
    assert [w.hard_cut for w in windows] == [False, False]


def test_ec3_hard_cut_without_sentence_end():
    text = "אחת שתיים שלוש ארבע חמש"
    windows = split_into_windows(text, one_per_word, 3)
    assert window_texts(text, windows) == ["אחת שתיים שלוש", "ארבע חמש"]
    assert [w.hard_cut for w in windows] == [True, False]


def test_ec4_several_cuts():
    text = " ".join(f"מילה{i}" for i in range(10))
    windows = split_into_windows(text, one_per_word, 3)
    assert [len(t.split()) for t in window_texts(text, windows)] == [3, 3, 3, 1]


def test_ec5_budget_is_in_wordpieces():
    text = "קצר ארוךמאודמאוד קצר"
    windows = split_into_windows(text, lambda word: 3 if len(word) > 5 else 1, 4)
    assert window_texts(text, windows) == ["קצר ארוךמאודמאוד", "קצר"]


def test_b1_empty_string():
    assert split_into_windows("", one_per_word, 5) == []


def test_b2_whitespace_only():
    assert split_into_windows(" \t\n ", one_per_word, 5) == []


def test_b3_exactly_budget():
    text = "אחת שתיים שלוש"
    assert len(split_into_windows(text, one_per_word, 3)) == 1


def test_b4_budget_plus_one():
    text = "אחת שתיים שלוש ארבע"
    assert len(split_into_windows(text, one_per_word, 3)) == 2


def test_b5_single_word_above_budget_is_its_own_window():
    text = "קצר ענקענקענק קצר"
    windows = split_into_windows(text, lambda word: 9 if len(word) > 5 else 1, 4)
    assert window_texts(text, windows) == ["קצר", "ענקענקענק", "קצר"]


def test_b6_surrounding_whitespace_excluded():
    text = "  משה כהן  "
    assert window_texts(text, split_into_windows(text, one_per_word, 5)) == ["משה כהן"]


def test_h1_abbreviations_are_not_sentence_ends():
    for word in ['עו"ד', "ד״ר", 'רו"ח', "כב'"]:
        assert not is_sentence_final(word)


def test_h2_geresh_names_are_not_sentence_ends():
    for word in ["ג'ון", "ג׳ורג׳", "צ'רלי"]:
        assert not is_sentence_final(word)


def test_h3_sentence_end_before_closing_quote():
    assert is_sentence_final('לא."')
    assert is_sentence_final("הסתיים.")
    assert is_sentence_final("מדוע?")


def test_a1_initial_is_never_the_cut_point():
    assert not is_sentence_final("א.")
    # Two initials before a surname: a cut here would split the name (review finding).
    assert not is_sentence_final("י.ח.")
    assert not is_sentence_final("א.ב.")
    # Initials of a transliterated name carry a geresh, in either code point.
    assert not is_sentence_final("ג'.ק.")
    assert not is_sentence_final("ג׳.ק.")
    # A dotted date or number at the end of a sentence is still a sentence end.
    assert is_sentence_final("1.1.2020.")
    assert is_sentence_final("12.5%.")
    text = "הופיע עו\"ד א. כהן בשם המבקש"
    windows = split_into_windows(text, one_per_word, 3)
    assert window_texts(text, windows)[0] == 'הופיע עו"ד א.'
    assert windows[0].hard_cut  # the stop after the initial did not count as a sentence end


def test_a2_list_marker_is_never_the_cut_point():
    assert not is_sentence_final("1.")
    assert not is_sentence_final("12.")


def random_text(rng: random.Random) -> str:
    alphabet = "אבגדהוזחטיכלמנסעפצקרשת"
    words = []
    for _ in range(rng.randint(0, 60)):
        word = "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 9)))
        words.append(word + rng.choice(["", "", "", ".", "?", ",", '."']))
    return rng.choice(["", " ", "\n"]) + rng.choice([" ", "  ", "\t"]).join(words)


def test_p1_windows_partition_the_words():
    rng = random.Random(SEED)
    for _ in range(GENERATED_CASES):
        text = random_text(rng)
        budget = rng.randint(1, 12)
        cost = rng.choice([one_per_word, lambda word: 1 + len(word) // 4])
        windows = split_into_windows(text, cost, budget)

        assert [w for t in window_texts(text, windows) for w in t.split()] == text.split()
        for previous, current in zip(windows, windows[1:]):
            assert previous.end < current.start
        for window in windows:
            words = re.findall(r"\S+", text[window.start : window.end])
            assert len(words) == 1 or sum(cost(word) for word in words) <= budget
        assert not windows or not windows[-1].hard_cut
