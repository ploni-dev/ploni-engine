"""Render one document as a page for counting missed person names by hand.

Why: build-plan.md section 11 says "count missed person names by hand". A
reader can only do that reliably if the model's output is laid over the text
they are reading, with each `PER` highlight numbered so an exception can be
written down as a number instead of as a name.

Known limits: the page contains the full document text. It is written only to
the private output directory, never into the repository and never to stdout.
"""

from __future__ import annotations

import html
import re
from typing import NamedTuple

PERSON_LABEL = "PER"  # config.json id2label at the pinned commit: B-PER, I-PER
# The word Israeli courts put in place of a name: פלוני or אלמוני, feminine or plural.
_PLACEHOLDER_STEM = "(?:פלוני|אלמוני)[תם]?"
# One unnamed person. Up to four attached prefix letters (ולכש is the longest chain),
# and adjacent stems (פלוני אלמוני) read as one mention.
PLACEHOLDER = re.compile(
    rf"(?<![א-ת])[ושהבלמכ]{{0,4}}{_PLACEHOLDER_STEM}(?:[ \-־]{_PLACEHOLDER_STEM})*(?![א-ת])"
)

PAGE_HEAD = """<!doctype html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>{doc_id}</title>
<style>
body {{ font-family: "David", "Arial", sans-serif; font-size: 18px; line-height: 2;
       max-width: 50em; margin: 2em auto; padding: 0 1em; }}
p {{ margin: 0 0 0.8em; }}
.per {{ background: #ffd54f; }}
.other {{ background: #cfd8dc; }}
sup {{ font-size: 0.6em; font-family: monospace; padding: 0 0.2em; direction: ltr;
      unicode-bidi: isolate; }}
.legend {{ font-size: 0.8em; direction: ltr; text-align: left; }}
</style>
</head>
<body>
<h1 class="legend">{doc_id}</h1>
<p class="legend"><span class="per">yellow</span> = model says PER, numbered.
<span class="other">grey</span> = any other label, shown with its label.
Counting rules: PREREGISTRATION.md.</p>
"""
PAGE_TAIL = "</body>\n</html>\n"
# Header of the per-document span file; the rows come from person_span_rows.
SPAN_COLUMNS = ("highlight", "paragraph", "start", "end", "text")


class Entity(NamedTuple):
    """One span the model labelled, located in the extracted text.

    Why: the model reports offsets inside the window it was given; this is the
    same span after it has been moved back into paragraph coordinates.

    Contract: `paragraph` is a 0-based index into the document's paragraph
    list. `start` inclusive and `end` exclusive, in characters of that
    paragraph. `label` is the model's label without the B-/I- prefix.
    """

    paragraph: int
    start: int
    end: int
    label: str


def count_person_highlights(entities: list[Entity]) -> int:
    """Count the entities labelled as a person.

    Why: this is the `per_highlights` column the tally starts from, and it must
    equal the highest number printed on the page.

    Contract: counts entities whose label is PERSON_LABEL; order irrelevant.
    """
    return sum(entity.label == PERSON_LABEL for entity in entities)


def _checked_paragraph_entities(
    paragraphs: list[str], entities: list[Entity]
) -> list[list[Entity]]:
    """Group entities by paragraph in reading order, rejecting impossible spans.

    Why: a span that overlaps another or runs past its paragraph means the
    offsets were shifted wrongly, and a worksheet drawn from wrong offsets
    would mislead the hand count without looking wrong.

    Contract: returns one start-sorted list per paragraph. Raises ValueError
    for an unknown paragraph index, an empty or out-of-range span, or two
    spans that overlap.
    """
    grouped: list[list[Entity]] = [[] for _ in paragraphs]
    for entity in entities:
        if not 0 <= entity.paragraph < len(paragraphs):
            raise ValueError(f"entity names paragraph {entity.paragraph}, which does not exist")
        if not 0 <= entity.start < entity.end <= len(paragraphs[entity.paragraph]):
            raise ValueError(f"entity span {entity.start}:{entity.end} is outside its paragraph")
        grouped[entity.paragraph].append(entity)
    for group in grouped:
        group.sort(key=lambda entity: entity.start)
        for previous, current in zip(group, group[1:], strict=False):
            if current.start < previous.end:
                raise ValueError(f"entities overlap in paragraph {current.paragraph}")
    return grouped


def render_document(doc_id: str, paragraphs: list[str], entities: list[Entity]) -> str:
    """Return the worksheet page for one document as an HTML string.

    Why: see the module docstring.

    Contract: every paragraph appears once, in order, with all document text
    HTML-escaped. `PER` entities are wrapped in `<mark class="per">` and
    numbered from 1 in reading order across the whole document; other entities
    are wrapped in `<mark class="other">` and carry their label. Raises
    ValueError as `_checked_paragraph_entities` does.

    Known limits: no interaction. Exceptions are recorded in the tally file.
    """
    parts = [PAGE_HEAD.format(doc_id=html.escape(doc_id))]
    person_number = 0
    for text, group in zip(paragraphs, _checked_paragraph_entities(paragraphs, entities), strict=True):
        pieces = []
        cursor = 0
        for entity in group:
            if entity.label == PERSON_LABEL:
                person_number += 1
                css_class, tag = "per", str(person_number)
            else:
                css_class, tag = "other", html.escape(entity.label)
            pieces.append(html.escape(text[cursor : entity.start]))
            pieces.append(
                f'<mark class="{css_class}"><sup>{tag}</sup>'
                f"{html.escape(text[entity.start : entity.end])}</mark>"
            )
            cursor = entity.end
        pieces.append(html.escape(text[cursor:]))
        parts.append(f"<p>{''.join(pieces)}</p>\n")
    parts.append(PAGE_TAIL)
    return "".join(parts)


def person_span_rows(paragraphs: list[str], entities: list[Entity]) -> list[tuple[int, int, int, int, str]]:
    """List every PERSON span the model found, as rows a person can check.

    Why: the worksheet shows where each highlight is; this gives the same
    highlights as a list with offsets, to compare against the original
    document one by one.

    Contract: one row per `PER` entity, in the columns of SPAN_COLUMNS:
    the number printed on the worksheet, the paragraph index from 0, the start
    and end offsets in characters of that paragraph with the end exclusive,
    and the text of the span. Raises ValueError as
    `_checked_paragraph_entities` does.
    """
    rows = []
    for index, group in enumerate(_checked_paragraph_entities(paragraphs, entities)):
        for entity in group:
            if entity.label == PERSON_LABEL:
                rows.append((len(rows) + 1, index, entity.start, entity.end, paragraphs[index][entity.start : entity.end]))
    return rows


def count_placeholders(paragraphs: list[str]) -> int:
    """Count the mentions of an unnamed person written as `פלוני` or `אלמוני`.

    Why: a published decision often has a party's name already replaced. Such
    a word is not a person name the model could miss, and the findings note
    reports how many there were (issue #4; build-plan.md Phase 5 warns that
    published decisions are part-anonymized).

    Contract: returns the number of matches of PLACEHOLDER over all paragraphs.

    Known limits: bare initials (`א.ב.`) and blanks (`___`) are not counted;
    they stay with the hand count. A real person surnamed אלמוני, or
    `החייל האלמוני`, is counted here as a placeholder.
    """
    return sum(len(PLACEHOLDER.findall(paragraph)) for paragraph in paragraphs)


def placeholder_highlights(paragraphs: list[str], entities: list[Entity]) -> list[int]:
    """List the numbers of the `PER` highlights that hold only a placeholder.

    Why: these highlights are not person names, so the tally starts with them
    already listed in `not_person_ids` instead of leaving dozens of identical
    exceptions to be typed by hand.

    Contract: returns worksheet numbers in reading order. A highlight is
    listed when it holds a placeholder and no other letter or digit. Raises
    ValueError as `person_span_rows` does.
    """
    return [
        number
        for number, _, _, _, text in person_span_rows(paragraphs, entities)
        if PLACEHOLDER.search(text) and not re.search(r"\w", PLACEHOLDER.sub("", text))
    ]
