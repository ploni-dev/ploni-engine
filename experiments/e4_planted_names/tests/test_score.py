"""Test matrix for score: outcome, score_document, verdict, against_e1, format_report.

One gold mention, `יעקב כהן` at 4..12 of paragraph 0, unless a case says otherwise.

outcome (E1's strict rule, applied by a script)
  EC1  one PER span covers the name exactly            -> found
  EC2  one PER span covers the name and more (a title, a prefix letter) -> found
  EC3  two PER spans cover the two tokens, the space between them bare  -> found
  EC4  PER covers one token of the two                  -> partial
  EC5  PER covers part of a token                       -> partial
  EC6  no PER span touches the name                     -> missed, not under another label
  EC7  the whole name inside one span of another label  -> missed, under another label
  EC8  another label on one token only, nothing else    -> missed, not under another label
  EC9  a PER span in another paragraph                  -> missed
  B1   a PER span that ends where the name starts, or starts where it ends -> missed
  B2   a name of one character                          -> found when covered

score_document
  EC10 a gold item that is not counted                  -> no outcome
  EC11 several mentions                                 -> one outcome each, in gold order

verdict (PREREGISTRATION.md, decision rule; exact fractions, no rounding)
  B3   799 of 1000 -> threshold_crossed;  800 of 1000 -> outside_prediction
  B4   899 of 1000 -> outside_prediction; 900 of 1000 -> inside_prediction
  B5   960 of 1000 -> inside_prediction;  961 of 1000 -> outside_prediction
  E1   no mentions -> ValueError

against_e1 (more than 10 points under E1's 449 of 470)
  B6   85.53 percent is not under; one mention less is

format_report
  EC12 the pooled line, the verdict, each bucket with its fraction, any-label recall
"""

from __future__ import annotations

from typing import NamedTuple

import pytest

from generate import Document, Gold
from score import against_e1, format_report, outcome, score_document, verdict


class Span(NamedTuple):
    paragraph: int
    start: int
    end: int
    label: str


TEXT = "מר  יעקב כהן העיד"
NAME = Gold(paragraph=0, start=4, end=12, name="יעקב כהן", person="A", form="full", prefix="", alone=False,
            classes=frozenset(), counted=True)


def test_the_fixture_is_what_it_says():
    assert TEXT[NAME.start : NAME.end] == NAME.name


@pytest.mark.parametrize(
    ("spans", "expected"),
    [
        ([Span(0, 4, 12, "PER")], ("found", False)),
        ([Span(0, 0, 12, "PER")], ("found", False)),
        ([Span(0, 4, 8, "PER"), Span(0, 9, 12, "PER")], ("found", False)),
        ([Span(0, 4, 8, "PER")], ("partial", False)),
        ([Span(0, 4, 6, "PER")], ("partial", False)),
        ([], ("missed", False)),
        ([Span(0, 3, 13, "ORG")], ("missed", True)),
        ([Span(0, 4, 8, "ORG")], ("missed", False)),
        ([Span(1, 4, 12, "PER")], ("missed", False)),
        ([Span(0, 0, 4, "PER"), Span(0, 12, 16, "PER")], ("missed", False)),
    ],
    ids=["ec1", "ec2", "ec3", "ec4", "ec5", "ec6", "ec7", "ec8", "ec9", "b1"],
)
def test_outcome(spans, expected):
    result = outcome(NAME, TEXT, spans)
    assert (result.verdict, result.other_label) == expected


def test_b2_one_character_name():
    gold = NAME._replace(start=4, end=5, name="י")
    assert outcome(gold, TEXT, [Span(0, 4, 5, "PER")]).verdict == "found"


def document(gold: list[Gold]) -> Document:
    return Document(doc_id="doc01", template="t", kind="letter", filling=1, paragraphs=[TEXT, TEXT], gold=gold)


def test_ec10_ec11_score_document():
    second = NAME._replace(paragraph=1)
    skipped = NAME._replace(counted=False)
    outcomes = score_document(document([NAME, skipped, second]), [Span(0, 4, 12, "PER")])
    assert [(item.gold.paragraph, item.verdict) for item in outcomes] == [(0, "found"), (1, "missed")]


@pytest.mark.parametrize(
    ("found", "expected"),
    [(799, "threshold_crossed"), (800, "outside_prediction"), (899, "outside_prediction"),
     (900, "inside_prediction"), (960, "inside_prediction"), (961, "outside_prediction")],
)
def test_b3_b4_b5_verdict_boundaries(found: int, expected: str):
    assert verdict(found, 1000) == expected


def test_e1_verdict_needs_mentions():
    with pytest.raises(ValueError):
        verdict(0, 0)


def test_b6_ten_points_under_e1():
    # E1: 449 of 470. Ten points under is 449/470 - 1/10 = 402/470.
    assert against_e1(402, 470) == "within_10_points_of_e1"
    assert against_e1(401, 470) == "more_than_10_points_under_e1"
    assert against_e1(470, 470) == "within_10_points_of_e1"


def test_ec12_report_lines():
    documents = [document([NAME, NAME._replace(paragraph=1, form="surname", prefix="ל")])]
    outcomes = {"doc01": score_document(documents[0], [Span(0, 4, 12, "PER"), Span(1, 3, 13, "ORG")])}
    report = format_report(documents, outcomes)
    assert "strict PERSON recall, pooled: 1/2 = 50.00%" in report
    assert "verdict: threshold_crossed" in report
    assert "any-label recall: 2/2 = 100.00%" in report
    assert "full  1/1 = 100.00%" in report and "surname  0/1 = 0.00%" in report
    assert "prefixed  0/1 = 0.00%" in report
    assert "letter  1/2 = 50.00%" in report
