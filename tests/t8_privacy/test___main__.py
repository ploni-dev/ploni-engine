"""The command line switches the log filter on before any command runs.

Why: `CLAUDE.md`, Hard constraints: "No document text in logs or temp files." The filter of
`ploni/safety/logging.py` only holds once `install` has run; before it, the logging module's
own handler of last resort prints the message of any WARNING or worse to the error stream, and
a library's warning can quote its input (the filter's docstring names a tokenizer). Finding 1
of the Ponytail pass at the close of Phase 0 found that nothing under ploni/ called `install`
(issue #211). `main` is the one entry point of the command line, so it calls `install` first.

The file is named for the module, `test___main__.py`, so that scripts/check_commit_order.py
counts it as the test of ploni/__main__.py (its Known limits: tests/t1_unit/test_cli.py does
not count). Each case runs the program in a fresh interpreter, so the filter is installed in
that process and not in pytest's.

Test matrix:

Equivalence classes:
  EC1  a record logged while `selftest` runs, its message the canary, at each level the
       handler of last resort writes (WARNING, ERROR, CRITICAL)
       -> the error stream holds one line for it, the filter's, ending `<withheld>` and
          naming the level; the canary is not on either stream
  EC2  a record logged at INFO while `selftest` runs -> the same: the filter's level, at
       which the handler of last resort writes nothing
  EC3  a record logged after a stub (`scan`) and after a usage error returned -> the same: the
       filter is installed by every command, and before the arguments are read
Boundaries:
  B1  the canary given as an argument of the record, not in its format string -> not written
Adversarial:
  A1  the canary in Hebrew -> not written, in UTF-8 or in the laptop's code page (cp1255)

Known limits:
  - A record logged before `main` is called, by code that runs while ploni/ is imported, is
    outside the filter (the filter's Known limits). No module of ploni/ logs on import today.
  - What `argparse` writes for a usage error is not a log record and is not filtered: it
    repeats an argument it does not know (`main`'s Known limits).
  - The two start-up sweeps that finding 1 also names are not called here: they come with
    the first command that writes a temp file, after issue #212.

Not applicable: the document-structure axes of the test-matrix skill; no document is read.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CANARY = "CANARY-7f3a"
HEBREW_CANARY = "יעקב-כהן-קנרית"
# The encodings the error stream may be written in: Python's default and the laptop's code page.
ENCODINGS = ("utf-8", "cp1255")

# Runs main with the command given. With "inside", selftest is replaced by a function that logs
# the record while the command runs; otherwise the record is logged after main returns or stops.
PROGRAM = """
import logging
import sys
import ploni.__main__ as cli

when, command, level, message, argument = sys.argv[1:6]
arguments = [argument] if argument else []

def record():
    logging.getLogger("a.library").log(getattr(logging, level), message, *arguments)

def selftest(models, out):
    record()
    return 0

if when == "inside":
    cli.selftest = selftest
try:
    code = cli.main(command.split())
except SystemExit as stop:
    code = stop.code
if when != "inside":
    record()
raise SystemExit(code)
"""


def run(when: str, command: str, level: str, message: str, argument: str = "") -> subprocess.CompletedProcess[bytes]:
    """Run PROGRAM in a fresh interpreter; return the finished process, its streams as bytes."""
    return subprocess.run(  # noqa: S603 fixed argv, no shell
        [sys.executable, "-c", PROGRAM, when, command, level, message, argument],
        cwd=ROOT, capture_output=True, timeout=60, check=False,
    )  # fmt: skip


def withheld(stream: bytes) -> list[bytes]:
    """Return the lines of a stream that end with the filter's mark for a record's message."""
    return [line for line in stream.splitlines() if line.endswith(b"<withheld>")]


def assert_withheld(done: subprocess.CompletedProcess[bytes], level: str, *canaries: str) -> None:
    """Assert one filtered line for the record, at its level, and no canary on either stream."""
    lines = withheld(done.stderr)
    assert len(lines) == 1, done.stderr
    assert f" {level} ".encode() in lines[0]
    for canary in canaries:
        for encoding in ENCODINGS:
            assert canary.encode(encoding) not in done.stderr + done.stdout


@pytest.mark.parametrize("level", ["WARNING", "ERROR", "CRITICAL"])
def test_ec1_a_record_logged_while_selftest_runs_is_withheld(level: str) -> None:
    done = run("inside", "selftest", level, CANARY)
    assert done.returncode == 0
    assert_withheld(done, level, CANARY)


def test_ec2_a_record_at_info_is_written_by_the_filter() -> None:
    assert_withheld(run("inside", "selftest", "INFO", CANARY), "INFO", CANARY)


@pytest.mark.parametrize(("command", "code"), [("scan", 2), ("no-such-command", 2), ("", 2)])
def test_ec3_the_filter_is_installed_by_every_command_and_a_usage_error(command: str, code: int) -> None:
    done = run("after", command, "WARNING", CANARY)
    assert done.returncode == code
    assert_withheld(done, "WARNING", CANARY)


def test_b1_the_canary_as_an_argument_of_the_record() -> None:
    assert_withheld(run("inside", "selftest", "WARNING", "found %s", CANARY), "WARNING", CANARY)


def test_a1_a_hebrew_canary() -> None:
    assert_withheld(run("inside", "selftest", "WARNING", "found %s", HEBREW_CANARY), "WARNING", HEBREW_CANARY)
