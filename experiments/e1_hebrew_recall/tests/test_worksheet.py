"""Test matrix for worksheet.render_document and worksheet.count_person_highlights.

Equivalence classes:
  EC1  paragraph with no entity              -> text present, no highlight
  EC2  one PER entity                        -> highlight numbered 1
  EC3  PER beside a non-PER entity           -> PER numbered, the other shows its label
  EC4  PER entities in several paragraphs    -> numbering runs through the document
  EC5  entities given out of order           -> numbered in reading order
  EC6  person_span_rows: one row per PER entity with the worksheet's number,
       the paragraph index, the offsets and the text; other labels left out

Boundaries:
  B1  entity at the very start and at the very end of a paragraph
  B2  no paragraphs at all                   -> a page with no highlight

Error paths:
  E1  two entities overlap                   -> ValueError
  E2  entity reaches past the paragraph end  -> ValueError
  E3  entity names a paragraph that does not exist -> ValueError

Adversarial:
  A1  markup characters in the document text are escaped, inside and outside a highlight

Hebrew axes:
  H1  proclitic form and gershayim inside a highlight survive unchanged (ולעו"ד כהן)
"""

from __future__ import annotations

import pytest

from worksheet import Entity, count_person_highlights, person_span_rows, render_document


def test_ec1_no_entity():
    html = render_document("doc01", ["אין כאן שמות"], [])
    assert "אין כאן שמות" in html
    assert "<mark" not in html


def test_ec2_one_person_numbered():
    html = render_document("doc01", ["משה כהן הגיע"], [Entity(0, 0, 7, "PER")])
    assert '<mark class="per"><sup>1</sup>משה כהן</mark> הגיע' in html


def test_ec3_other_label_is_shown_not_numbered():
    paragraphs = ["משה עובד בבנק לאומי"]
    entities = [Entity(0, 0, 3, "PER"), Entity(0, 9, 19, "ORG")]
    html = render_document("doc01", paragraphs, entities)
    assert '<mark class="per"><sup>1</sup>משה</mark>' in html
    assert '<mark class="other"><sup>ORG</sup>בבנק לאומי</mark>' in html


def test_ec4_numbering_runs_across_paragraphs():
    entities = [Entity(0, 0, 3, "PER"), Entity(1, 0, 3, "PER")]
    html = render_document("doc01", ["משה", "דוד"], entities)
    assert "<sup>1</sup>משה" in html
    assert "<sup>2</sup>דוד" in html


def test_ec5_out_of_order_entities_numbered_in_reading_order():
    entities = [Entity(0, 4, 7, "PER"), Entity(0, 0, 3, "PER")]
    html = render_document("doc01", ["משה דוד"], entities)
    assert "<sup>1</sup>משה" in html
    assert "<sup>2</sup>דוד" in html


def test_b1_entity_at_paragraph_edges():
    entities = [Entity(0, 0, 3, "PER"), Entity(0, 8, 11, "PER")]
    html = render_document("doc01", ["משה פגש דוד"], entities)
    assert '<sup>1</sup>משה</mark> פגש <mark class="per"><sup>2</sup>דוד</mark>' in html


def test_b2_no_paragraphs():
    assert "<mark" not in render_document("doc01", [], [])


def test_e1_overlapping_entities_raise():
    with pytest.raises(ValueError):
        render_document("doc01", ["משה כהן"], [Entity(0, 0, 5, "PER"), Entity(0, 4, 7, "PER")])


def test_e2_entity_past_paragraph_end_raises():
    with pytest.raises(ValueError):
        render_document("doc01", ["משה"], [Entity(0, 0, 9, "PER")])


def test_e3_entity_in_missing_paragraph_raises():
    with pytest.raises(ValueError):
        render_document("doc01", ["משה"], [Entity(3, 0, 3, "PER")])


def test_a1_markup_in_text_is_escaped():
    paragraphs = ["<script>x</script> משה <b>"]
    html = render_document("doc01", paragraphs, [Entity(0, 0, 8, "PER")])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;b&gt;" in html


def test_h1_proclitic_and_gershayim_survive():
    text = 'ולעו"ד כהן'
    html = render_document("doc01", [text], [Entity(0, 0, len(text), "PER")])
    assert "ולעו&quot;ד כהן" in html


def test_count_person_highlights_ignores_other_labels():
    entities = [Entity(0, 0, 3, "PER"), Entity(0, 4, 7, "ORG"), Entity(1, 0, 3, "PER")]
    assert count_person_highlights(entities) == 2
    assert count_person_highlights([]) == 0


def test_ec6_span_rows_carry_worksheet_numbers_offsets_and_text():
    paragraphs = ["אתמול הגיע משה כהן", "בנק לאומי ודוד לוי"]
    second = paragraphs[1].index("ודוד לוי")
    entities = [
        Entity(1, second, second + 8, "PER"),
        Entity(1, 0, 9, "ORG"),
        Entity(0, 11, 18, "PER"),
    ]
    assert person_span_rows(paragraphs, entities) == [
        (1, 0, 11, 18, "משה כהן"),
        (2, 1, second, second + 8, "ודוד לוי"),
    ]
    page = render_document("doc01", paragraphs, entities)
    assert "<sup>1</sup>משה כהן" in page and "<sup>2</sup>ודוד לוי" in page
