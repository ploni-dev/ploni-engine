"""Methods that are not a model: they add person spans to what a detector found.

Why: the research before E5 found no published system that reaches very high recall of names
with a tagger alone; the ones that come close add rules, lists and a second pass over the
document (PREREGISTRATION.md, "Why this experiment exists"). Each function here is one such
method, small enough to be measured by itself and stacked on any detector.

Contract: a span is `(paragraph, start, end)`, characters of that paragraph, end exclusive.
Every function takes the paragraphs of one document and the spans found so far, and returns
the spans it adds. It never removes one.

Known limits: Hebrew only. A word is a run of Hebrew letters with a geresh or gershayim
inside it or a geresh at its end; a maqaf or a hyphen ends a word, so `בן־גוריון` is two
words. No morphology beyond the attached letters ו ה ב ל מ כ ש. The trigger words are one
closed list, and the generated corpora of E5 use no title outside it: what the trigger steps
gain there is an upper bound (PREREGISTRATION.md, amendment of 2026-11-17).
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
# ל swallows the article of the word it attaches to: `לשופט כהן`, `ולאחים לוי`. Only ל is
# taken: `כשופט` is "as a judge", with no name after it.
ARTICLE_EATERS = ("ל", "ול")
# The triggers whose form without the article, behind ל, is seldom another word. Left out:
# `למנוחה` (to rest), `לרב` (to most), `לאחות` (to mend).
SWALLOWED = frozenset({"השופט", "השופטת", "הרשם", "הרשמת", "המהנדס", "המהנדסת", "האחים", "האחיות"})
# The shortest trigger that is looked for behind attached letters.
MIN_PREFIXED_TRIGGER = 3
# An initial as it is written before a surname: one letter and a geresh (י' כהן).
INITIAL = re.compile(r"[א-ת]['׳]")


def words(paragraph: str) -> list[tuple[int, int, str]]:
    """Return every Hebrew word of a paragraph as (start, end, text).

    Why: every step works on whole words, and all of them must cut a paragraph the same way.
    """
    return [(match.start(), match.end(), match.group()) for match in WORD.finditer(paragraph)]


def strip_prefix(word: str, known: frozenset[str] | set[str]) -> str | None:
    """Return the known word that `word` is, bare or behind attached letters, or None.

    Why: Hebrew writes "to", "and", "that" as letters attached to the next word, so a name
    seldom stands only in its bare form.

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


def is_trigger(word: str, triggers: frozenset[str]) -> bool:
    """Say whether a word is one of the trigger words, as it stands or behind attached letters.

    Why: a title or a group word is written with attached letters as often as without.

    Contract: the word itself, with either form of the geresh and gershayim; or a trigger of
    MIN_PREFIXED_TRIGGER letters or more behind one to MAX_PREFIX prefix letters; or one of
    SWALLOWED that is among the triggers, without its article behind one of ARTICLE_EATERS;
    or, when `מר` is among the triggers, one of SHORT_TRIGGERS.
    """
    plain = word.replace("״", '"').replace("׳", "'")
    if plain in triggers or (plain in SHORT_TRIGGERS and "מר" in triggers):
        return True
    behind = strip_prefix(plain, triggers)
    if behind is not None and len(behind) >= MIN_PREFIXED_TRIGGER:
        return True
    return any(plain == eater + trigger[1:] for trigger in triggers & SWALLOWED for eater in ARTICLE_EATERS)


def _can_be_a_name(word: str) -> bool:
    """Say whether a marked word is taken as a word of a name: no particle, initial or trigger."""
    if word in NAME_PARTICLES or INITIAL.fullmatch(word) or len(word) < 2:
        return False
    return not is_trigger(word, TITLE_TRIGGERS | GROUP_TRIGGERS)


def _next_to(paragraph: str, first: tuple[int, int, str], second: tuple[int, int, str]) -> bool:
    """Say whether nothing but white space lies between two words, the first standing before the second."""
    return not paragraph[first[1] : second[0]].strip()


def name_words(paragraphs: list[str], spans: list[Span], strong: bool) -> set[str]:
    """Return the words that a document's marked names are made of.

    Why: a name that was found once, in a context that gave it away, is evidence for every
    other place the same word stands in the same document.

    Contract: every word that a span touches, without name particles, initials and trigger
    words: a detector that marks `מר` with the name must not make `מר` a name. With
    `strong` only a word that is marked in two places, or that stands next to another
    marked word of a name with only white space between, is kept: one word marked once is
    the weakest evidence a tagger gives. Spans may be one per word or one per name.

    Known limits: the whole word is taken. A name found only behind attached letters
    (`לכהן`) gives `לכהן`, and is not carried to its bare form: cutting letters off without
    knowing the name would make `רק` of `ברק`.
    """
    covered = _covered(spans)
    seen: Counter[str] = Counter()
    in_longer: set[str] = set()
    for index, paragraph in enumerate(paragraphs):
        tokens = words(paragraph)
        marked = [_touched(covered.get(index, ()), start, end) for start, end, _ in tokens]
        for position, token in enumerate(tokens):
            if not marked[position] or not _can_be_a_name(token[2]):
                continue
            seen[token[2]] += 1
            before = position > 0 and marked[position - 1] and _next_to(paragraph, tokens[position - 1], token)
            after = position + 1 < len(tokens) and marked[position + 1] and _next_to(paragraph, token, tokens[position + 1])
            neighbours = ([tokens[position - 1][2]] if before else []) + ([tokens[position + 1][2]] if after else [])
            if any(not is_trigger(text, TITLE_TRIGGERS | GROUP_TRIGGERS) for text in neighbours):
                in_longer.add(token[2])
    return {word for word, count in seen.items() if not strong or count > 1 or word in in_longer}


def from_list(paragraphs: list[str], spans: list[Span], names: frozenset[str] | set[str], prefixes: bool = True) -> list[Span]:
    """Mark every word that is in a set of names.

    Why: a list of names finds a name whatever stands around it, which no model promises.
    It also marks every everyday word that is a name too, and the experiment counts those.

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


def propagate(paragraphs: list[str], spans: list[Span], prefixes: bool = True, strong: bool = False) -> list[Span]:
    """Mark every other place where a name word of the document stands.

    Why: the model misses a name where nothing around it gives it away, and finds the same
    name elsewhere in the document. In the product a missed place is a leak.

    Contract: a word is marked when it is one of the document's name words (`name_words`),
    or, with `prefixes`, when it is one behind attached letters. A word already inside a
    span is not returned again.

    Known limits: see `name_words`. An everyday word that is a name in this document is
    marked wherever it stands, also where it is the everyday word.
    """
    return from_list(paragraphs, spans, name_words(paragraphs, spans, strong), prefixes)


def after_triggers(paragraphs: list[str], spans: list[Span], titles: bool = False) -> list[Span]:
    """Mark the name that follows a trigger word.

    Why: the model misses most surnames after `משפחת` and `האחים` (E4: 22 of 55), where the
    word before the name says what it is.

    Contract: the triggers are the group words, and with `titles` the personal titles too.
    The word right after a trigger is marked, and the word after that when the first is a
    name particle or an initial (`בן דוד`, `אבו ראס`, `י' כהן`). "Right after" means that
    nothing but white space lies between: not a full stop, a bracket or a word in other
    letters. A word already inside a span is not returned again.

    Known limits: the word after a trigger is marked whatever it is. `האחות הראשית` marks
    `הראשית`.
    """
    covered = _covered(spans)
    found = []
    for index, paragraph in enumerate(paragraphs):
        tokens = words(paragraph)
        for position, token in enumerate(tokens[:-1]):
            if not is_trigger(token[2], GROUP_TRIGGERS) and not (titles and is_trigger(token[2], TITLE_TRIGGERS)):
                continue
            first = tokens[position + 1]
            if not _next_to(paragraph, token, first):
                continue
            take = [first]
            joins = first[2] in NAME_PARTICLES or INITIAL.fullmatch(first[2])
            if joins and position + 2 < len(tokens) and _next_to(paragraph, first, tokens[position + 2]):
                take.append(tokens[position + 2])
            found += [(index, start, end) for start, end, _ in take if not _inside(covered.get(index, ()), start, end)]
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


def _touched(ranges: list[tuple[int, int]] | tuple[()], start: int, end: int) -> bool:
    """Say whether a word shares at least one character with one of the ranges."""
    return any(low < end and start < high for low, high in ranges)
