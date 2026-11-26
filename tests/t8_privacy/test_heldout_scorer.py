"""Scoring the held-out batch writes nothing and prints names and numbers only.

Why: the session that writes the detectors reads only what the scorer prints (Achia,
2026-11-26, issue 283, "I see only the scores, never the documents"), and the batch is "Made
fresh each run": nothing of it may reach a file. A detector's own error message or debug print
quotes the text it was given, so `main` must hold both back (review 1 of the branch, finding 2).

Test matrix (each case on the batch of SEED):
  W1  scoring the replay detector inside the guard of tests/t8_privacy/test_heldout_disk.py,
      which makes every write raise: scored whole, nothing written
  O1  main on the replay detector: ASCII only, one line per type, per group and TOTAL, no
      planted text of 4 code points or more
  O2  main on a detector that prints every document on both streams and then raises with a
      document's text: exit 1, one ASCII line on the error stream, no planted text anywhere
  O3  main on a detector that logs every document through a handler made before main runs,
      which keeps the real error stream: no planted text anywhere (scorer review 1, finding 1)
  O4  main on a detector that exits with a document's text as its message: exit 1, one ASCII
      line on the error stream, no planted text anywhere (scorer review 1, finding 1)

Known limits: a detector that writes to the process's own file handles, not through sys.stdout,
sys.stderr or logging, is not held back (the scorer's Known limits).
"""

import logging
import sys

import pytest

from eval.heldout import scorer
from eval.heldout.generator import GROUPS, SEED, TYPES, build
from eval.heldout.scorer import score
from tests.t8_privacy.test_heldout_disk import no_writes

BATCH = build(SEED)
SHORTEST_LEAK = 4
LISTED: dict[str, list[tuple[int, int, str]]] = {}
for _item in BATCH.key:
    LISTED.setdefault(BATCH.documents[_item.doc], []).append((_item.start, _item.end, _item.type))


def replay_detector(text: str) -> list[tuple[int, int, str]]:
    """The replay detector of the batch of SEED, for main to load by name."""
    return LISTED.get(text, [])


def loud_detector(text: str) -> list[tuple[int, int, str]]:
    """A detector that prints the document on both streams, then raises with its text."""
    print(text)
    sys.stderr.write(text)
    raise KeyError(text[:80])


LOGGER = logging.getLogger("heldout_scorer_test_detector")


def logging_detector(text: str) -> list[tuple[int, int, str]]:
    """A detector that logs the start of each document and finds nothing."""
    LOGGER.warning("seen: %s", text[:80])
    return []


def exiting_detector(text: str) -> list[tuple[int, int, str]]:
    """A detector that exits with the start of the document as its message."""
    sys.exit(text[:80])


def leaked(shown: str) -> list[int]:
    """The indexes of the planted items whose text, 4 code points or more, appears in shown."""
    items = BATCH.key + BATCH.near_misses
    return [index for index, item in enumerate(items) if len(item.text) >= SHORTEST_LEAK and item.text.strip("_") and item.text in shown]


def test_w1_scoring_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    with no_writes(monkeypatch):
        scores = score(replay_detector, BATCH)
    assert (scores.total.tp, scores.total.fp, scores.total.fn) == (len(BATCH.key), 0, 0)


def test_o1_main_prints_numbers_and_names_only(capsys: pytest.CaptureFixture[str]) -> None:
    assert scorer.main([f"{__name__}:replay_detector"]) == 0
    streams = capsys.readouterr()
    shown = (len(streams.out.splitlines()), streams.out.isascii(), streams.err)
    assert shown == (len(TYPES) + len(GROUPS) + 1, True, "")
    assert leaked(streams.out) == []


def test_o2_main_holds_back_a_loud_detector(capsys: pytest.CaptureFixture[str]) -> None:
    code = scorer.main([f"{__name__}:loud_detector"])
    streams = capsys.readouterr()
    shown = (code, streams.out, len(streams.err.splitlines()), streams.err.isascii())
    assert shown == (1, "", 1, True)
    assert leaked(streams.out + streams.err) == []


def test_o3_main_holds_back_a_detectors_log(capsys: pytest.CaptureFixture[str]) -> None:
    # The handler takes the error stream as it is now, before main replaces it, as one made
    # when a detector's module is imported would.
    handler = logging.StreamHandler(sys.stderr)
    LOGGER.addHandler(handler)
    LOGGER.propagate = False
    try:
        code = scorer.main([f"{__name__}:logging_detector"])
    finally:
        LOGGER.removeHandler(handler)
    streams = capsys.readouterr()
    assert (code, streams.err) == (0, "")
    assert leaked(streams.out + streams.err) == []


def test_o4_main_holds_back_a_detectors_exit_message(capsys: pytest.CaptureFixture[str]) -> None:
    code = scorer.main([f"{__name__}:exiting_detector"])
    streams = capsys.readouterr()
    shown = (code, streams.out, len(streams.err.splitlines()), streams.err.isascii())
    assert shown == (1, "", 1, True)
    assert leaked(streams.out + streams.err) == []
