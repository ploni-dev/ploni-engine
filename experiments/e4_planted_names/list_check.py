"""Measure the readers' cross-check list against the gold: which missed names does it point to?

Why: E1's readers, and the readers of E4's second part, were given a list of places that
may hold a missed name. Every miss they reported in E4 was on it, and 17 of 18 in E1. So
their count leans on the list, and what the list does not hold is left to a reader's
unaided search. Here the answer is known, so the list can be checked with no reader. The
rule is PREREGISTRATION.md, "the third part"; this file adds nothing to it.

Contract: `python -I list_check.py --folder F`, where F holds `docNN_spans.csv` for every
document of the corpus, as `run.py --worksheets-dir F --all-documents` writes them.
Prints, per document and pooled, the rows of the list, the missed mentions and how many
of them are on the list; the verdict against the pre-registered prediction and
threshold; the same by kind of mention; and every missed mention that is off the list.
Names are printed: allowed here because every sentence and every name is generated.
Raises ReaderFileError for a span list that is not of its document, and ValueError when
no mention is missed.

Known limits:
- The list is made by the rule of the throwaway script that made E1's lists, kept as it
  was, oddities included: a title that follows a title is passed over together with the
  word after it, and the row of a word after a title keeps punctuation at its edge.
- Only `PER` highlights are known here, so a missed mention under a highlight of another
  label is an item like any other. The worksheet shows such a highlight in grey, which
  points a reader there without the list; `run.py --list-errors` tells those apart.
- One place can give two rows, as a name word and, with punctuation at its edge, as
  the word after a title. So the rows on missed mentions can outnumber the mentions.
- It says where a reader is pointed, not whether the reader looks.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
# `python -I` drops the script folder.
sys.path[:0] = [str(HERE)]

import generate
import score

# The same reading and the same refusals as the second part. reader_check.py is not
# changed after its run, so its helpers are used under their private names.
from reader_check import SPAN_COLUMNS, _check_spans, _rows, _whole_number

# The letters, the punctuation, the titles and the lengths below are those of the throwaway script.
PREFIX_LETTERS = "והבלמכש"
HEBREW = "א-ת"
EDGE_PUNCTUATION = " \t.,:;()[]{}\"'׳״-–־!?/"
TITLES = (
    "מר", "גב'", "גב׳", "גברת", 'עו"ד', "עו״ד", 'ד"ר', "ד״ר", "פרופ'", "פרופ׳",
    "השופט", "השופטת", "הנשיא", "הנשיאה", "הרשם", "הרשמת", "כב'", "כב׳",
)  # fmt: skip
TITLE_WORDS = frozenset(title.strip(EDGE_PUNCTUATION) for title in TITLES)
# A name word is searched without its own prefix letters only if this many letters are left.
MIN_STRIPPED_LENGTH = 3
MIN_WORD_LENGTH = 2
MAX_PREFIX_BEFORE_NAME = 3
MAX_PREFIX_BEFORE_TITLE = 2
TITLE_PATTERN = re.compile(
    rf"(?<![{HEBREW}])[{PREFIX_LETTERS}]{{0,{MAX_PREFIX_BEFORE_TITLE}}}"
    rf"(?:{'|'.join(re.escape(title) for title in TITLES)})\s+(\S+)"
)
# PREREGISTRATION.md, "the third part": 90 percent or more on the list; below 80 crosses.
PREDICTED_ON_LIST_PERCENT = 90
THRESHOLD_ON_LIST_PERCENT = 80
# As run.ERROR_CONTEXT_CHARACTERS: how much of the paragraph is printed around a mention.
CONTEXT_CHARACTERS = 70
KINDS = ("family", "brothers", "given_ordinary", "rest")


class Span(NamedTuple):
    """One PER highlight of the model, as a span list gives it.

    Contract: `number` as printed on the worksheet; `start` inclusive and `end`
    exclusive in characters of paragraph `paragraph`; `text` without white space at its
    edges. `label` is always the person label, so that `score.outcome` can read it.
    """

    number: int
    paragraph: int
    start: int
    end: int
    text: str
    label: str = score.PERSON_LABEL


class Place(NamedTuple):
    """One row of the cross-check list: `kind` is `name_word` or `after_title`; `end` is exclusive."""

    kind: str
    paragraph: int
    start: int
    end: int


class Coverage(NamedTuple):
    """The list of one document against its missed mentions.

    Contract: `places` are the rows of the list. `rows_on_items` of them share a
    character with a missed mention. `items` are the counted mentions the scorer calls
    missed, in gold order; `off_list` are those of them that no row touches. `found` is
    the number of counted mentions the scorer calls found.
    """

    places: list[Place]
    rows_on_items: int
    items: list[generate.Gold]
    off_list: list[generate.Gold]
    found: int


def name_variants(span_text: str) -> set[str]:
    """Give the words of a highlighted name that the list searches for.

    Why: a name the model found once is the best hint for where it missed the same name.

    Contract: the text is cut at white space and hyphens; punctuation is taken off the
    edges of each word; a word under MIN_WORD_LENGTH letters is left out. A word is also
    given with one, two or three leading prefix letters taken off, if at least
    MIN_STRIPPED_LENGTH letters are left.
    """
    variants = set()
    for raw in re.split(r"[\s־\-]+", span_text):
        word = raw.strip(EDGE_PUNCTUATION)
        if len(word) < MIN_WORD_LENGTH:
            continue
        variants.add(word)
        for cut in range(1, MAX_PREFIX_BEFORE_NAME + 1):
            if all(letter in PREFIX_LETTERS for letter in word[:cut]) and len(word) - cut >= MIN_STRIPPED_LENGTH:
                variants.add(word[cut:])
    return variants


def _name_word_pattern(word: str) -> re.Pattern:
    """Build the search for one name word: up to three prefix letters before it, no Hebrew letter around it."""
    return re.compile(rf"(?<![{HEBREW}])[{PREFIX_LETTERS}]{{0,{MAX_PREFIX_BEFORE_NAME}}}{re.escape(word)}(?![{HEBREW}])")


def _candidates(text: str, name_words: list[re.Pattern]) -> Iterator[tuple[str, int, int]]:
    """Yield every place of one paragraph that the rule looks at, name words first.

    Contract: (kind, start, end), `end` exclusive. A word after a title is given only if
    it is not itself a title, with or without prefix letters.
    """
    for pattern in name_words:
        for match in pattern.finditer(text):
            yield "name_word", match.start(), match.end()
    for match in TITLE_PATTERN.finditer(text):
        word = match.group(1).strip(EDGE_PUNCTUATION)
        if word and word not in TITLE_WORDS and word.lstrip(PREFIX_LETTERS) not in TITLE_WORDS:
            yield "after_title", match.start(1), match.end(1)


def listed_places(paragraphs: list[str], spans: list[Span]) -> list[Place]:
    """Make the cross-check list of one document.

    Why: this is the list E1's readers and the readers of the second part were given.

    Contract: `spans` are the PER highlights of the document. A place is listed if no
    highlight is on any of its characters. A place found both ways is listed once, as a
    name word. Rows are in reading order; rows that begin at one place keep the order
    they were found in, as in the throwaway. The rule is in PREREGISTRATION.md.
    """
    # One search per name word, as the throwaway did: a combined search would pass over
    # a place that begins inside another word's match.
    name_words = [_name_word_pattern(word) for word in sorted({w for span in spans for w in name_variants(span.text)})]
    rows: dict[tuple[int, int, int], str] = {}
    for index, text in enumerate(paragraphs):
        highlighted = [(span.start, span.end) for span in spans if span.paragraph == index]
        for kind, start, end in _candidates(text, name_words):
            if all(end <= s or start >= e for s, e in highlighted):
                rows.setdefault((index, start, end), kind)
    return [Place(kind, *position) for position, kind in sorted(rows.items(), key=lambda row: row[0][:2])]


def read_spans(folder: Path, document: generate.Document) -> list[Span]:
    """Read the span list of one document.

    Contract: reads `docNN_spans.csv` from `folder`. Raises ReaderFileError when the
    file lacks a column, or when a span is not of this document: a paragraph the
    document does not have, or another text at its position.
    """
    spans = []
    for row in _rows(folder / f"{document.doc_id}_spans.csv", SPAN_COLUMNS):
        numbers = (_whole_number(row[name], f"{document.doc_id}: a span's {name}") for name in SPAN_COLUMNS[:4])
        spans.append(Span(*numbers, row["text"]))
    _check_spans(document, spans)
    return spans


def coverage(document: generate.Document, spans: list[Span]) -> Coverage:
    """Set the list of one document against the mentions the model missed in it.

    Why: this is the measurement of the third part.

    Contract: an item is a counted mention that `score.outcome` calls missed. It is on
    the list if a row shares at least one character with the planted name. A partial
    mention is not an item: a highlight sits on it.
    """
    places = listed_places(document.paragraphs, spans)
    outcomes = score.score_document(document, spans)
    items = [item.gold for item in outcomes if item.verdict == "missed"]

    def touching(gold: generate.Gold) -> list[Place]:
        return [p for p in places if p.paragraph == gold.paragraph and p.start < gold.end and gold.start < p.end]

    on_items = {place for gold in items for place in touching(gold)}
    return Coverage(
        places,
        len(on_items),
        items,
        [gold for gold in items if not touching(gold)],
        sum(item.verdict == "found" for item in outcomes),
    )


def kind_of(gold: generate.Gold) -> str:
    """Name the row of the third part's report that a missed mention belongs to.

    Contract: `family` for a surname after `משפחת`, `brothers` for one after `האחים`,
    `given_ordinary` for a given name alone that is an everyday word, else `rest`.
    """
    if gold.form in generate.GROUP_WORDS:
        return gold.form.removeprefix("group_")
    return "given_ordinary" if "given_ordinary" in generate.buckets_of(gold) else "rest"


def list_verdict(on_list: int, items: int) -> str:
    """Compare the share of missed mentions on the list with the prediction and threshold.

    Contract: exact integer arithmetic. `inside_prediction` at PREDICTED_ON_LIST_PERCENT
    or more; `threshold_crossed` below THRESHOLD_ON_LIST_PERCENT; otherwise
    `outside_prediction`. Raises ValueError when no mention is missed.
    """
    if items <= 0:
        raise ValueError("no missed mention to look for on the list")
    if on_list * 100 >= PREDICTED_ON_LIST_PERCENT * items:
        return "inside_prediction"
    if on_list * 100 < THRESHOLD_ON_LIST_PERCENT * items:
        return "threshold_crossed"
    return "outside_prediction"


def _ratio(part: int, whole: int) -> str:
    """Write a fraction with its percentage."""
    return f"{part}/{whole} = {part * 100 / whole:.2f}%"


def _off_list_line(document: generate.Document, gold: generate.Gold) -> str:
    """Write one missed mention that is off the list, with the text around it."""
    text = document.paragraphs[gold.paragraph]
    window = text[max(0, gold.start - CONTEXT_CHARACTERS) : gold.end + CONTEXT_CHARACTERS]
    return f"  {document.doc_id} {document.template} ¶{gold.paragraph} {gold.form} [{gold.prefix}{gold.name}] :: {window}"


def report(documents: list[generate.Document], spans: dict[str, list[Span]]) -> str:
    """Write the report of the third part.

    Contract: `spans` maps a document's id to its PER highlights. One line per
    document, then the pooled lines, the verdict, the kinds that have a missed mention,
    and every missed mention off the list. Raises ValueError when no mention is missed.
    """
    results = {document.doc_id: coverage(document, spans[document.doc_id]) for document in documents}
    lines = [
        f"{doc_id}: list rows {len(r.places)}, on a missed mention {r.rows_on_items}; "
        f"missed mentions {len(r.items)}, on the list {len(r.items) - len(r.off_list)}"
        for doc_id, r in results.items()
    ]
    counted = sum(gold.counted for document in documents for gold in document.gold)
    places = [place for r in results.values() for place in r.places]
    items = [gold for r in results.values() for gold in r.items]
    off_list = [gold for r in results.values() for gold in r.off_list]
    lines.append(f"strict PERSON recall from the span lists: {_ratio(sum(r.found for r in results.values()), counted)}")
    lines.append(
        f"cross-check lists: {len(places)} rows (name_word {sum(p.kind == 'name_word' for p in places)}, "
        f"after_title {sum(p.kind == 'after_title' for p in places)}) in "
        f"{sum(bool(r.places) for r in results.values())} of {len(documents)} documents; "
        f"{sum(r.rows_on_items for r in results.values())} of them on a missed mention"
    )
    lines.append(f"missed mentions on the list, pooled: {_ratio(len(items) - len(off_list), len(items))}")
    lines.append(
        f"verdict: {list_verdict(len(items) - len(off_list), len(items))} (prediction {PREDICTED_ON_LIST_PERCENT} "
        f"percent or more, threshold below {THRESHOLD_ON_LIST_PERCENT} percent)"
    )
    lines.append("by kind:")
    for kind in KINDS:
        missed = sum(kind_of(gold) == kind for gold in items)
        if missed:
            lines.append(f"  {kind}  {_ratio(missed - sum(kind_of(gold) == kind for gold in off_list), missed)}")
    lines.append("missed mentions off the list:")
    lines += [_off_list_line(d, gold) for d in documents for gold in results[d.doc_id].off_list] or ["  none"]
    return "\n".join(lines)


def main(folder: Path) -> None:
    """Print the report of the third part for the span lists of a folder.

    Contract: see the module docstring. The corpus is generated again from the
    committed templates, so the gold is never read from a file.
    """
    documents = generate.corpus(HERE / "templates", HERE / "names.tsv")
    print(report(documents, {document.doc_id: read_spans(folder, document) for document in documents}))


if __name__ == "__main__":
    # `python -I` ignores PYTHONUTF8, and a Windows pipe would get the ANSI code page.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--folder", type=Path, required=True)
    main(parser.parse_args().folder)
