"""Module suite for ploni/safety/logging.py: the module used by a program of its own.

Why: the unit tests and the canary test run inside pytest, which holds handlers of its own
on the root logger and takes the standard streams. Only a separate process shows what a
program that uses the module really writes: to a log file on disk, and to its own standard
error, where the standard library prints when a handler fails.

Matrix (one program, started once per case, writing its log to a file in a temp folder):
  M1  the program logs events, and records through the standard logging calls that carry a
      canary, among them one whose formatting fails and a warning
          the file holds one well-formed line per record, in order: the events with their
          numbers, a fixed mark for the others; the canary is nowhere in the file, in the
          standard output or in the standard error; exit code 0
  M2  the same program with the level set to WARNING
          only the lines at WARNING and above are in the file
  M3  the program ends with an error that is not caught, after logging
          the lines logged before it are in the file. The error text on the standard error
          is the interpreter's, not a log, and is not searched (see the canary test's limits)

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANARY = "קנרית־יעקב Canary-Jacob 7301946"
# The program is given with -c, so its own lines are in "<string>"; a warning is logged from warnings.py.
LINE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d (?P<level>[A-Z]+) (?:<string>|warnings\.py):\d+ (?P<rest>.+)")

PROGRAM = '''
import enum, logging, sys, warnings
from ploni.safety import logging as safe

class Run(safe.Event):
    STARTED = enum.auto()
    PAGE = enum.auto()
    FAILED = enum.auto()

canary, level, crash = sys.argv[2], int(sys.argv[3]), sys.argv[4] == "crash"
with open(sys.argv[1], "w", encoding="utf-8") as stream:
    safe.install(stream, level=level)
    safe.event(Run.STARTED, pages=2, check=sum(map(ord, canary)))
    logging.getLogger("library").info("reading %s", canary)
    safe.event(Run.PAGE, number=1, seconds=0.25, title=canary)
    logging.warning("%d pages", canary)
    warnings.warn(canary)
    try:
        raise ValueError(canary)
    except ValueError as error:
        logging.exception(canary)
        safe.event(Run.FAILED, level=logging.ERROR, error=error)
    if crash:
        raise RuntimeError("stopped")
'''


def run(tmp_path: Path, level: int = 20, crash: bool = False) -> tuple[subprocess.CompletedProcess[bytes], list[str]]:
    """Start the program and return how it ended and the lines of its log file."""
    log = tmp_path / "run.log"
    command = [sys.executable, "-c", PROGRAM, str(log), CANARY, str(level), "crash" if crash else "no"]
    ended = subprocess.run(command, cwd=ROOT, capture_output=True, check=False)  # noqa: S603 fixed argv, no shell
    return ended, log.read_text(encoding="utf-8").splitlines()


def shown(lines: list[str]) -> list[tuple[str, str]]:
    """Return (level, rest) of every line; a line of another shape fails the test."""
    matched = [LINE.fullmatch(line) for line in lines]
    assert all(matched), lines
    return [(match["level"], match["rest"]) for match in matched if match]


def test_m1_a_program_writes_events_and_fixed_marks_and_never_the_canary(tmp_path: Path) -> None:
    ended, lines = run(tmp_path)
    assert ended.returncode == 0, ended.stderr
    assert shown(lines) == [
        # The sum of the canary's code points: the canary reached the program whole.
        ("INFO", f"Run.STARTED pages=2 check={sum(map(ord, CANARY))}"),
        ("INFO", "<withheld>"),
        ("INFO", f"Run.PAGE number=1 seconds=0.25 title=<str:{len(CANARY)}>"),
        ("WARNING", "<withheld>"),
        ("WARNING", "<withheld>"),
        ("ERROR", "<withheld> raised=ValueError"),
        ("ERROR", "Run.FAILED error=<ValueError>"),
    ]
    everything = (tmp_path / "run.log").read_bytes() + ended.stdout + ended.stderr
    for part in ("קנרית", "יעקב", "Canary", "Jacob", "7301946"):
        for encoding in ("utf-8", "cp1255", "utf-16-le"):
            assert part.encode(encoding) not in everything, (part, encoding)
    assert ended.stderr == b""


def test_m2_the_level_given_to_install_holds_for_every_record(tmp_path: Path) -> None:
    ended, lines = run(tmp_path, level=30)
    assert ended.returncode == 0, ended.stderr
    assert [level for level, _ in shown(lines)] == ["WARNING", "WARNING", "ERROR", "ERROR"]


def test_m3_what_was_logged_before_an_uncaught_error_is_in_the_file(tmp_path: Path) -> None:
    ended, lines = run(tmp_path, crash=True)
    assert ended.returncode == 1
    assert len(shown(lines)) == 7
    assert b"RuntimeError: stopped" in ended.stderr
