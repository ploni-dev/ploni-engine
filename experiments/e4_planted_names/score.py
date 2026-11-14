"""Score the model's spans against the planted names, with E1's strict rule.

Why: in E1 a reader decided, mention by mention, whether the model had found a name.
Here the generator knows where every name is, so the same rule is applied by a script
and no reading is involved (PREREGISTRATION.md, "How it is scored").

Known limits: the rule is about characters. A span that covers the name and half of
the next word still counts as found, as it did in E1, where a highlight that held more
than the name was not an error.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

from generate import FORM_BUCKETS, KINDS, NAME_CLASSES, Document, Gold, buckets_of

PERSON_LABEL = "PER"  # the model's label for a person, as in e1_hebrew_recall/worksheet.py
# PREREGISTRATION.md, "Prediction and threshold".
PREDICTED_LOW_PERCENT = 90
PREDICTED_HIGH_PERCENT = 96
THRESHOLD_PERCENT = 80
# docs/findings/2026-11-13-e1-hebrew-recall.md: 449 of 470. "More than 10 points under".
E1_FOUND = 449
E1_TOTAL = 470
E1_MARGIN_POINTS = 10


class Outcome(NamedTuple):
    """What happened to one counted mention.

    Contract: `verdict` is `found`, `partial` or `missed`. `other_label` is True only
    for a missed mention that lies wholly inside one span of another label.
    """

    gold: Gold
    verdict: str
    other_label: bool


def outcome(gold: Gold, text: str, spans: Iterable) -> Outcome:
    """Decide whether the model found one planted name.

    Contract: `text` is the paragraph the gold lies in. `spans` are the model's
    entities for the document, each with `paragraph`, `start`, `end` (exclusive) and
    `label`. Found: PER spans of that paragraph cover every character of the name
    that is not white space, so two spans on the two words of a full name count.
    Partial: they cover some. Missed: none.
    """
    here = [span for span in spans if span.paragraph == gold.paragraph]
    letters = [position for position in range(gold.start, gold.end) if not text[position].isspace()]
    covered = sum(
        any(span.start <= position < span.end for span in here if span.label == PERSON_LABEL) for position in letters
    )
    if covered == len(letters):
        return Outcome(gold, "found", False)
    if covered:
        return Outcome(gold, "partial", False)
    inside_other = any(
        span.label != PERSON_LABEL and span.start <= gold.start and gold.end <= span.end for span in here
    )
    return Outcome(gold, "missed", inside_other)


def score_document(document: Document, spans: Iterable) -> list[Outcome]:
    """Score every counted mention of one document, in gold order.

    Contract: a gold item that is not counted (a cited title, a firm, a placeholder)
    gives no outcome. `spans` as in `outcome`.
    """
    spans = list(spans)
    return [outcome(gold, document.paragraphs[gold.paragraph], spans) for gold in document.gold if gold.counted]


def verdict(found: int, total: int) -> str:
    """Compare the pooled strict recall with the pre-registered prediction and threshold.

    Contract: exact integer arithmetic, no rounding. `threshold_crossed` below
    THRESHOLD_PERCENT; `inside_prediction` from PREDICTED_LOW_PERCENT to
    PREDICTED_HIGH_PERCENT inclusive; otherwise `outside_prediction`. Raises
    ValueError when there is nothing to score.
    """
    if total <= 0:
        raise ValueError("no counted mention was scored")
    if found * 100 < THRESHOLD_PERCENT * total:
        return "threshold_crossed"
    if PREDICTED_LOW_PERCENT * total <= found * 100 <= PREDICTED_HIGH_PERCENT * total:
        return "inside_prediction"
    return "outside_prediction"


def against_e1(found: int, total: int) -> str:
    """Say whether the recall is more than ten points under E1's.

    Contract: exact. `more_than_10_points_under_e1` when found/total is below
    E1_FOUND/E1_TOTAL minus E1_MARGIN_POINTS/100, else `within_10_points_of_e1`,
    which also covers a recall above E1's.
    """
    floor_numerator = E1_FOUND * 100 - E1_MARGIN_POINTS * E1_TOTAL
    if found * E1_TOTAL * 100 < floor_numerator * total:
        return "more_than_10_points_under_e1"
    return "within_10_points_of_e1"


def _ratio(found: int, total: int) -> str:
    """Write a count as `found/total = percent`, or `0/0` when there is nothing."""
    return f"{found}/{total} = {found * 100 / total:.2f}%" if total else "0/0"


def _table(title: str, rows: list[tuple[str, list[Outcome]]]) -> list[str]:
    """Format one block of the report: a title, then one `name  found/total` line per row."""
    lines = [title]
    for name, outcomes in rows:
        found = sum(item.verdict == "found" for item in outcomes)
        lines.append(f"  {name}  {_ratio(found, len(outcomes))}")
    return lines


def format_report(documents: list[Document], outcomes: dict[str, list[Outcome]]) -> str:
    """Write the whole E4 report: the pooled number, the verdicts, and every breakdown.

    Why: the findings note pastes this as printed, so every number the
    pre-registration asks for is in it.

    Contract: `outcomes` maps each document's id to what `score_document` returned.
    Breakdowns: form bucket; prefixed, alone, given_ordinary; name class; kind of
    document; template. A mention is listed in every bucket it belongs to.
    """
    everything = [item for document in documents for item in outcomes[document.doc_id]]
    found = sum(item.verdict == "found" for item in everything)
    partial = sum(item.verdict == "partial" for item in everything)
    missed = len(everything) - found - partial
    under_other = sum(item.other_label for item in everything)
    by_bucket: dict[str, list[Outcome]] = {}
    by_class: dict[str, list[Outcome]] = {}
    for item in everything:
        for name in buckets_of(item.gold):
            by_bucket.setdefault(name, []).append(item)
        for name in item.gold.classes or {"no_class"}:
            by_class.setdefault(name, []).append(item)
    by_kind: dict[str, list[Outcome]] = {}
    by_template: dict[str, list[Outcome]] = {}
    for document in documents:
        by_kind.setdefault(document.kind, []).extend(outcomes[document.doc_id])
        by_template.setdefault(document.template, []).extend(outcomes[document.doc_id])
    form_names = list(dict.fromkeys(FORM_BUCKETS.values()))
    lines = [
        f"documents: {len(documents)}",
        f"strict PERSON recall, pooled: {_ratio(found, len(everything))}",
        f"verdict: {verdict(found, len(everything))} (prediction {PREDICTED_LOW_PERCENT} to "
        f"{PREDICTED_HIGH_PERCENT} percent, threshold below {THRESHOLD_PERCENT} percent)",
        f"against E1 ({E1_FOUND}/{E1_TOTAL}): {against_e1(found, len(everything))}",
        f"lenient recall (partial counted as found): {_ratio(found + partial, len(everything))}",
        f"any-label recall: {_ratio(found + under_other, len(everything))}",
        f"errors: {partial + missed} (partial {partial}, missed {missed}, of them under another label {under_other})",
        *_table("by form:", [(name, by_bucket.get(name, [])) for name in form_names]),
        *_table("by trait:", [(name, by_bucket.get(name, [])) for name in ("prefixed", "alone", "given_ordinary")]),
        *_table("by name class:", [(name, by_class.get(name, [])) for name in (*sorted(NAME_CLASSES), "no_class")]),
        *_table("by kind of document:", [(name, by_kind.get(name, [])) for name in KINDS if name in by_kind]),
        *_table("by template:", sorted(by_template.items())),
    ]
    return "\n".join(lines)
