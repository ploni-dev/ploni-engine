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
The cases below read the process's file handles 1 and 2 (capfd), where the interpreter's own
streams write:
  O5  a detector that prints every document to the interpreter's original output and error
      streams (sys.__stdout__, sys.__stderr__): no planted text (scorer review 2, finding 4)
  O6  a detector that writes every document to file handles 1 and 2 with os.write: no planted
      text
  O7  a detector that raises an error derived from BaseException alone, with a document's
      text: exit 1, one ASCII line, no planted text (scorer review 2, finding 5)
  O8  a detector that names its type, and the class of its error, by a document's text: no
      planted text
  O9  a detector that turns logging back on and logs every document to the error stream: no
      planted text
The cases below run the command itself, `python -m eval.heldout.scorer`, in a child process:
  O10 a detector that starts a thread which prints a document after main returns: no planted
      text (scorer review 3, finding 7)
  O11 a detector that registers an atexit handler which prints a document: no planted text
      (scorer review 3, finding 7)
  O12 a detector that closes the output stream it kept at import: the command still writes
      something, and no planted text (scorer review 3, finding 8)

Known limits: what a detector writes through a copy of a file handle it made before main ran,
from a process it started that outlives the command, or to a console it opens itself is not
held back (the scorer's Known limits).
"""

import atexit
import logging
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from eval.heldout import scorer
from eval.heldout.generator import GROUPS, SEED, TYPES, build
from eval.heldout.scorer import score
from tests.t8_privacy.test_heldout_disk import no_writes

BATCH = build(SEED)
SHORTEST_LEAK = 4
ROOT = Path(__file__).resolve().parents[2]
# The child command is given this long; it takes a few seconds.
CHILD_TIMEOUT_SECONDS = 300
# The thread of O10 waits this long, so that it prints after main has returned.
LATE_SECONDS = 2
HEBREW_LETTER = re.compile("[א-ת]")
KEPT_OUT = sys.stdout
STARTED: set[str] = set()
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


def original_streams_detector(text: str) -> list[tuple[int, int, str]]:
    """A detector that prints the document to the interpreter's original streams."""
    print(text, file=sys.__stdout__, flush=True)
    print(text, file=sys.__stderr__, flush=True)
    return []


def handle_detector(text: str) -> list[tuple[int, int, str]]:
    """A detector that writes the document to file handles 1 and 2."""
    os.write(1, text.encode("utf-8"))
    os.write(2, text.encode("utf-8"))
    return []


class Outside(BaseException):
    """An error of a class derived from BaseException alone."""


def outside_detector(text: str) -> list[tuple[int, int, str]]:
    """A detector that raises an error outside Exception with the document's start."""
    raise Outside(text[:80])


def naming_detector(text: str) -> list[tuple[int, int, str]]:
    """A detector that raises an error of a class named by the document's first line."""
    raise type(text.splitlines()[0].replace(" ", "_"), (Exception,), {})()


def typing_detector(text: str) -> list[tuple[int, int, str]]:
    """A detector that names the type of its one detection by the document's start."""
    return [(0, 1, text[:40])]


def relogging_detector(text: str) -> list[tuple[int, int, str]]:
    """A detector that turns logging back on and logs the document's start."""
    logging.disable(logging.NOTSET)
    LOGGER.warning("seen: %s", text[:80])
    return []


def _late_print(text: str) -> None:
    """Print a text after main has returned."""
    time.sleep(LATE_SECONDS)
    print(text, flush=True)


def late_thread_detector(text: str) -> list[tuple[int, int, str]]:
    """A detector that starts, once, a thread which prints the document's start later."""
    if "thread" not in STARTED:
        STARTED.add("thread")
        threading.Thread(target=_late_print, args=(text[:80],)).start()
    return []


def at_exit_detector(text: str) -> list[tuple[int, int, str]]:
    """A detector that registers, once, a handler which prints the document's start at exit."""
    if "exit" not in STARTED:
        STARTED.add("exit")
        atexit.register(print, text[:80])
    return []


def closing_detector(text: str) -> list[tuple[int, int, str]]:
    """A detector that closes the output stream it kept at import."""
    KEPT_OUT.close()
    return []


def run_command(detector: str) -> tuple[int, str]:
    """Run `python -m eval.heldout.scorer` on a detector of this module; return its exit code and output."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    env |= {"PYTHONPATH": str(ROOT), "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    command = [sys.executable, "-m", "eval.heldout.scorer", f"tests.t8_privacy.test_heldout_scorer:{detector}"]
    done = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=CHILD_TIMEOUT_SECONDS, check=False)  # noqa: S603 fixed argv, no shell
    return done.returncode, (done.stdout + done.stderr).decode("utf-8", errors="replace")


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


@pytest.mark.parametrize("detector", ["original_streams_detector", "handle_detector"])
def test_o5_o6_main_holds_back_what_reaches_the_file_handles(detector: str, capfd: pytest.CaptureFixture[str]) -> None:
    code = scorer.main([f"{__name__}:{detector}"])
    streams = capfd.readouterr()
    assert (code, streams.err) == (0, "")
    assert leaked(streams.out + streams.err) == []


def test_o7_main_holds_back_an_error_outside_exception(capfd: pytest.CaptureFixture[str]) -> None:
    code = scorer.main([f"{__name__}:outside_detector"])
    streams = capfd.readouterr()
    shown = (code, streams.out, len(streams.err.splitlines()), streams.err.isascii())
    assert shown == (1, "", 1, True)
    assert leaked(streams.out + streams.err) == []


@pytest.mark.parametrize("detector", ["naming_detector", "typing_detector"])
def test_o8_main_prints_no_name_a_detector_makes(detector: str, capfd: pytest.CaptureFixture[str]) -> None:
    scorer.main([f"{__name__}:{detector}"])
    streams = capfd.readouterr()
    shown = (streams.out + streams.err).isascii()
    assert shown
    assert leaked(streams.out + streams.err) == []


def test_o9_main_holds_back_logging_turned_back_on(capfd: pytest.CaptureFixture[str]) -> None:
    handler = logging.StreamHandler(sys.__stderr__)
    LOGGER.addHandler(handler)
    LOGGER.propagate = False
    try:
        code = scorer.main([f"{__name__}:relogging_detector"])
    finally:
        LOGGER.removeHandler(handler)
        logging.disable(logging.NOTSET)
    streams = capfd.readouterr()
    assert code == 0
    assert leaked(streams.out + streams.err) == []


@pytest.mark.parametrize("detector", ["late_thread_detector", "at_exit_detector"])
def test_o10_o11_the_command_ends_before_a_detectors_late_writes(detector: str) -> None:
    code, shown = run_command(detector)
    assert (code, len(HEBREW_LETTER.findall(shown))) == (0, 0)


def test_o12_the_command_writes_when_its_stream_was_closed() -> None:
    _, shown = run_command("closing_detector")
    assert (shown != "", len(HEBREW_LETTER.findall(shown))) == (True, 0)
