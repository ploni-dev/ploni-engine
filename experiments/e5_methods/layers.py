"""Methods that are not a model: they add person spans to what a detector found.

Why: no published system reaches very high recall of names with a tagger alone
(`docs/findings/2026-11-17-e5-methods.md`, "What the research found"). The ones that do add
rules, lists and a second pass over the document. Each function here is one such method, small
enough to be measured by itself and stacked on any detector.

Contract: a span is `(paragraph, start, end)`, characters of that paragraph, end exclusive.
Every function takes the paragraphs of one document and the spans found so far, and returns
the spans it adds. It never removes one.

Known limits: Hebrew only. A word is a run of Hebrew letters with the geresh, gershayim and
maqaf that can stand inside one; no morphology beyond the attached letters ו ה ב ל מ כ ש.
"""

from __future__ import annotations

import re
from collections import Counter

Span = tuple[int, int, int]

# A Hebrew word: letters, with a geresh or gershayim inside or at its end (ג'ון, עו"ד, גב').
WORD = re.compile(r"[א-ת]+(?:[\"'׳״][א-ת]+)*['׳]?")
PREFIX_LETTERS = "והבלמכש"
# The longest run of attached letters the plan lists (build-plan.md Phase 3: לכש, וכש, ושה).
MAX_PREFIX = 3
# Words that stand inside a name and are no name by themselves: propagating them would mark
# every "son of" in a document.
NAME_PARTICLES = frozenset({"בן", "בת", "אבו", "בר", "אל", "דה", "ון"})
# A word after which a family name follows. Only forms that are seldom anything else: `אחים`
# without the article is also "two brothers live there".
GROUP_TRIGGERS = frozenset({"משפחת", "האחים", "האחיות"})
# A title after which a person's name follows. A word that is often an ordinary word is left
# out: `רב` (much), `רשם` (wrote down), `שופט` without the article (a judge of the court).
TITLE_TRIGGERS = frozenset(
    {"מר", "גב'", "גברת", "אדון", 'ד"ר', "דר'", 'עו"ד', 'עוה"ד', "פרופ'", 'רו"ח', "השופט", "השופטת", "הרשם", "הרשמת",
     "האחות", "המהנדס", "המהנדסת", "הרב", "המנוח", "המנוחה"}
)  # fmt: skip
# `מר` behind attached letters, spelled out: `שמר` is "guarded", and a rule that took any
# prefix letter off a word of two letters would mark the word after it.
SHORT_TRIGGERS = frozenset({"למר", "ומר", "ולמר"})
# ל, ב and כ swallow the article of the word they attach to: `לשופט כהן`, `ולאחים לוי`.
ARTICLE_EATERS = ("ל", "ב", "כ", "ול", "וב", "וכ")
# The shortest trigger that is looked for behind attached letters.
MIN_PREFIXED_TRIGGER = 3
# An initial as it is written before a surname: one letter and a geresh (י' כהן).
INITIAL = re.compile(r"[א-ת]['׳]")


def words(paragraph: str) -> list[tuple[int, int, str]]:
    """Return every Hebrew word of a paragraph as (start, end, text)."""
    return [(match.start(), match.end(), match.group()) for match in WORD.finditer(paragraph)]


def strip_prefix(word: str, known: frozenset[str] | set[str]) -> str | None:
    """Return the known word that `word` is, bare or behind attached letters, or None.

    Contract: the word itself when it is in `known`; else the longest remainder in `known`
    after one to MAX_PREFIX leading prefix letters are taken off. A remainder is at least
    two letters long.
    """
    if word in known:
        return word
    for cut in range(1, MAX_PREFIX + 1):
        if len(word) - cut < 2 or word[cut - 1] not in PREFIX_LETTERS:
            return None
        if word[cut:] in known:
            return word[cut:]
    return None


def name_words(paragraphs: list[str], spans: list[Span], strong: bool) -> set[str]:
    """Return the words a document's person spans are made of.

    Why: a name that was found once, in a context that gave it away, is evidence for every
    other place the same word stands in the same document.

    Contract: every word inside a span, without name particles, initials and trigger words:
    a detector that marks `מר` with the name must not make `מר` a name. With `strong` only a
    word that stands in a span of two words or more, or in two spans, is kept: a single
    one-word span is the weakest evidence a tagger gives.
    """
    seen: Counter[str] = Counter()
    in_longer: set[str] = set()
    for paragraph, start, end in spans:
        inside = [text for word_start, word_end, text in words(paragraphs[paragraph]) if word_start < end and word_end > start]
        kept = [text for text in inside if _can_be_a_name(text)]
        seen.update(kept)
        if len(inside) > 1:
            in_longer.update(kept)
    return {word for word, count in seen.items() if not strong or count > 1 or word in in_longer}


def _can_be_a_name(word: str) -> bool:
    """Say whether a word inside a marked span is taken as a word of the name."""
    if word in NAME_PARTICLES or INITIAL.fullmatch(word) or len(word) < 2:
        return False
    return not is_trigger(word, TITLE_TRIGGERS | GROUP_TRIGGERS)


def propagate(paragraphs: list[str], spans: list[Span], prefixes: bool = True, strong: bool = False) -> list[Span]:
    """Mark every other place where a name word of the document stands.

    Contract: a word is marked when it is one of the document's name words (`name_words`),
    or, with `prefixes`, when it is one behind attached letters. A word already inside a
    span is not returned again.
    """
    known = name_words(paragraphs, spans, strong)
    covered = _covered(spans)
    found = []
    for index, paragraph in enumerate(paragraphs):
        for start, end, text in words(paragraph):
            hit = text in known or (prefixes and strip_prefix(text, known) is not None)
            if hit and not _inside(covered.get(index, ()), start, end):
                found.append((index, start, end))
    return found


def is_trigger(word: str, triggers: frozenset[str]) -> bool:
    """Say whether a word is one of the trigger words, as it stands or behind attached letters.

    Contract: the word itself, with either form of the geresh and gershayim; or a trigger of
    MIN_PREFIXED_TRIGGER letters or more behind one to MAX_PREFIX prefix letters; or a
    trigger that begins with the article, behind one of ARTICLE_EATERS and without it; or,
    when `מר` is among the triggers, one of SHORT_TRIGGERS.
    """
    plain = word.replace("״", '"').replace("׳", "'")
    if plain in triggers or (plain in SHORT_TRIGGERS and "מר" in triggers):
        return True
    behind = strip_prefix(plain, triggers)
    if behind is not None and len(behind) >= MIN_PREFIXED_TRIGGER:
        return True
    return any(plain == eater + trigger[1:] for trigger in triggers if trigger[0] == "ה" for eater in ARTICLE_EATERS)


def after_triggers(paragraphs: list[str], spans: list[Span], titles: bool = False) -> list[Span]:
    """Mark the name that follows a group word, and with `titles` a personal title.

    Why: the model misses most surnames after `משפחת` and `האחים` (E4: 22 of 55), where the
    word before the name says what it is.

    Contract: after a group trigger the next word is marked, and one more when the first is
    a name particle (`בן דוד`, `אבו ראס`). After a title the next word is marked, with the
    word after it when the first is an initial (`י' כהן`). A word already inside a span is
    not returned again.
    """
    covered = _covered(spans)
    found = []
    for index, paragraph in enumerate(paragraphs):
        tokens = words(paragraph)
        for position, (_, _, text) in enumerate(tokens[:-1]):
            if not is_trigger(text, GROUP_TRIGGERS) and not (titles and is_trigger(text, TITLE_TRIGGERS)):
                continue
            take = tokens[position + 1 : position + 2]
            first = take[0][2]
            if (first in NAME_PARTICLES or INITIAL.fullmatch(first)) and position + 2 < len(tokens):
                take = tokens[position + 1 : position + 3]
            found += [(index, start, end) for start, end, _ in take if not _inside(covered.get(index, ()), start, end)]
    return found


def from_list(paragraphs: list[str], spans: list[Span], names: frozenset[str], prefixes: bool = True) -> list[Span]:
    """Mark every word that is in a list of names.

    Contract: `names` are single words. With `prefixes` a word behind attached letters is
    marked too. A word already inside a span is not returned again.
    """
    covered = _covered(spans)
    found = []
    for index, paragraph in enumerate(paragraphs):
        for start, end, text in words(paragraph):
            hit = text in names or (prefixes and strip_prefix(text, names) is not None)
            if hit and not _inside(covered.get(index, ()), start, end):
                found.append((index, start, end))
    return found


def _covered(spans: list[Span]) -> dict[int, list[tuple[int, int]]]:
    """Group spans by paragraph."""
    grouped: dict[int, list[tuple[int, int]]] = {}
    for paragraph, start, end in spans:
        grouped.setdefault(paragraph, []).append((start, end))
    return grouped


def _inside(ranges: list[tuple[int, int]] | tuple[()], start: int, end: int) -> bool:
    """Say whether a word lies wholly inside one of the ranges."""
    return any(low <= start and end <= high for low, high in ranges)
