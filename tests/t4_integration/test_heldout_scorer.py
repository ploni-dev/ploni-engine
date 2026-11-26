"""Module suite of the held-out batch's scorer: the batch of SEED built and scored end to end.

Why: the unit tests score a batch of three Latin documents written by hand. This suite scores the
real batch, in Hebrew, through the public surface only (`score`, `report`, `main`), so that the
generator and the scorer are shown to agree: the key the one writes is the key the other reads.
No assertion prints a document or a planted value.

Test matrix:
  M1  the empty detector         every type of TYPES: tp 0, fn its count, recall 0.0
  M2  the replay detector        every type: recall 1.0 and precision 1.0; totals 1.0 and 1.0
  M3  a known part: the key's IL_ID items only    IL_ID 1.0 and 1.0, every other type recall
                                 0.0; the total recall is the share of IL_ID in the key
  M4  every key span moved one character right    no tp; every detection is partial
  M5  the near misses replayed as detections      no tp, a fp for each, none partial
  M6  the report on the replay   ASCII only, one line per type and TOTAL, no planted text
  M7  main on a detector named by module and function    exit 0, the TOTAL line last

Not applicable: the Hebrew axes, which the generator's tests carry; the scorer compares spans.
"""

from collections import Counter
from collections.abc import Iterable

import pytest

from eval.heldout import scorer
from eval.heldout.generator import SEED, TYPES, Batch, Item, build
from eval.heldout.scorer import report, score

BATCH = build(SEED)


def replay(batch: Batch, items: Iterable[Item], shift: int = 0) -> scorer.Detector:
    """A detector that returns the spans of the items given, moved by shift characters."""
    listed: dict[str, list[tuple[int, int, str]]] = {}
    for item in items:
        listed.setdefault(batch.documents[item.doc], []).append((item.start + shift, item.end + shift, item.type))
    return lambda text: listed.get(text, [])


def test_m1_the_empty_detector() -> None:
    scores = score(lambda text: [], BATCH)
    sizes = Counter(item.type for item in BATCH.key)
    assert {kind: (row.tp, row.fn, row.recall) for kind, row in scores.per_type.items()} == {kind: (0, sizes[kind], 0.0) for kind in TYPES}
    assert scores.total.recall == 0.0


def test_m2_the_replay_detector() -> None:
    scores = score(replay(BATCH, BATCH.key), BATCH)
    assert sorted(kind for kind, row in scores.per_type.items() if (row.recall, row.precision) != (1.0, 1.0)) == []
    assert (scores.total.recall, scores.total.precision) == (1.0, 1.0)
    assert scores.total.tp == len(BATCH.key)


def test_m3_a_known_part() -> None:
    scores = score(replay(BATCH, [item for item in BATCH.key if item.type == "IL_ID"]), BATCH)
    assert (scores.per_type["IL_ID"].recall, scores.per_type["IL_ID"].precision) == (1.0, 1.0)
    assert sorted(kind for kind, row in scores.per_type.items() if kind != "IL_ID" and row.recall != 0.0) == []
    share = sum(item.type == "IL_ID" for item in BATCH.key) / len(BATCH.key)
    assert scores.total.recall == pytest.approx(share)


def test_m4_spans_moved_by_one_are_partial() -> None:
    inside = [item for item in BATCH.key if item.end < len(BATCH.documents[item.doc])]
    scores = score(replay(BATCH, inside, shift=1), BATCH)
    assert scores.total.tp == 0
    assert scores.total.partial == scores.total.fp == len(inside)


def test_m5_near_misses_replayed() -> None:
    scores = score(replay(BATCH, BATCH.near_misses), BATCH)
    assert scores.total.tp == 0
    assert scores.total.fp == len(BATCH.near_misses)
    assert scores.total.partial == 0


def test_m6_the_report_holds_numbers_and_names_only() -> None:
    lines = report(score(replay(BATCH, BATCH.key), BATCH))
    assert len(lines) == len(TYPES) + 1
    shown = "\n".join(lines)
    assert shown.isascii()
    assert [index for index, item in enumerate(BATCH.key) if len(item.text) >= 4 and item.text in shown] == []


def empty(text: str) -> list[tuple[int, int, str]]:
    """The empty detector, for main to load by name."""
    return []


def test_m7_main_on_a_named_detector(capsys: pytest.CaptureFixture[str]) -> None:
    assert scorer.main([f"{__name__}:empty"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == len(TYPES) + 1
    assert lines[-1].startswith("TOTAL")
