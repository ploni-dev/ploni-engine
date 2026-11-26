"""What the command line writes to its error stream carries no document text.

Why: `CLAUDE.md`, Hard constraints: "No document text in logs or temp files." The filter of
`ploni/safety/logging.py` only holds once `install` has run; before it, the logging module's
own handler of last resort prints the message of any WARNING or worse to the error stream, and
a library's warning can quote its input (the filter's docstring names a tokenizer). Finding 1
of the Ponytail pass at the close of Phase 0 found that nothing under ploni/ called `install`
(issue #211). `main` is the one entry point of the command line, so it calls `install` first.
Finding 3 (issue #213): an error that no code catches is printed by Python with its message,
and a message can quote its input (`int()` on text does) or a core object; so `main` catches
it and writes only the command, the error's type and an exit code of its own.

The file is named for the module, `test___main__.py`, so that scripts/check_commit_order.py
counts it as the test of ploni/__main__.py (its Known limits: tests/t1_unit/test_cli.py does
not count). Each case runs the program in a fresh interpreter, so the filter is installed in
that process and not in pytest's.

Test matrix:

Equivalence classes:
  EC1  a record logged while `selftest` runs, its message the canary, at each level the
       handler of last resort writes (WARNING, ERROR, CRITICAL)
       -> the error stream holds one line for it, the filter's whole line (time, level,
          place, `<withheld>`); the canary is not on either stream, in UTF-8, in cp1255 or
          as backslash escapes
  EC2  a record logged at INFO while `selftest` runs -> the same: the filter's level, at
       which the handler of last resort writes nothing
  EC3  a record logged after a stub (`scan`) returned and after a usage error stopped `main`
       (SystemExit 2) -> the same: the filter is installed by every command, and before the
       arguments are read
  EC4  an error raised inside a command, its message the canary (ValueError, and an error of
       a class of the program's own) -> exit code 3; the error stream is the one line
       "ploni selftest: failed: <type name>"; the canary is on neither stream
  EC5  an error raised while another was handled, and one raised from another -> the same,
       naming the outer error's type only
Boundaries:
  B1  the canary given as an argument of the record, not in its format string -> not written
  B2  an error whose own text cannot be made (its `__str__` raises, with the canary) -> the
      same line, its type
Adversarial:
  A1  the canary in Hebrew -> not written, in UTF-8 or in the laptop's code page (cp1255)
  A2  the canary in Hebrew in an error's message -> the same as EC4

Known limits:
  - A record logged before `main` is called, by code that runs while ploni/ is imported, is
    outside the filter (the filter's Known limits). No module of ploni/ logs on import today.
  - What `argparse` writes for a usage error is not a log record and is not filtered: it
    repeats an argument it does not know (`main`'s Known limits).
  - The two start-up sweeps that finding 1 also names are not called here: they come with
    the first command that writes a temp file, after issue #212.
  - An interrupt (Ctrl+C) and an exit are not errors (`BaseException`): they are not caught,
    and Python prints an interrupt's traceback, which shows lines of code, not their data.
  - The error's type name is written as it is: a class built at run time with a name taken
    from a document would show it, the filter's own limit for names of code.

Not applicable: the document-structure axes of the test-matrix skill; no document is read.
"""

import re
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


def withheld(stream: bytes, level: str) -> list[bytes]:
    """Return the lines of a stream that are the filter's whole line for a record at a level, its message withheld."""
    shape = re.compile(rb"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d " + level.encode() + rb" <string>:\d+ <withheld>")
    return [line for line in stream.splitlines() if shape.fullmatch(line)]


def assert_withheld(done: subprocess.CompletedProcess[bytes], level: str, *canaries: str) -> None:
    """Assert one filtered line for the record, at its level, and no canary on either stream."""
    assert len(withheld(done.stderr, level)) == 1, done.stderr
    for canary in canaries:
        for form in [canary.encode(encoding) for encoding in ENCODINGS] + [canary.encode("ascii", "backslashreplace")]:
            assert form not in done.stderr + done.stdout


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


# Runs `main(["selftest"])` with selftest replaced by a function that raises: the kind of error
# and its message are given as arguments of the program.
CRASHING = """
import sys
import ploni.__main__ as cli
from ploni.errors import PloniError

kind, message = sys.argv[1:3]

class Unprintable(Exception):
    def __str__(self):
        raise ValueError(message)

def selftest(models, out):
    if kind == "ValueError":
        raise ValueError(message)
    if kind == "PloniError":
        raise PloniError(message)
    if kind == "Unprintable":
        raise Unprintable()
    try:
        raise KeyError(message)
    except KeyError as inner:
        if kind == "from":
            raise RuntimeError(message) from inner
        raise RuntimeError(message)

cli.selftest = selftest
raise SystemExit(cli.main(["selftest"]))
"""
# ploni/__main__.py: the exit code of a command stopped by an error no code caught; 1 is
# selftest's "not offline" and 2 a stub or a usage error.
FAILED = 3


def crash(kind: str, message: str) -> subprocess.CompletedProcess[bytes]:
    """Run CRASHING in a fresh interpreter; return the finished process, its streams as bytes."""
    return subprocess.run(  # noqa: S603 fixed argv, no shell
        [sys.executable, "-c", CRASHING, kind, message], cwd=ROOT, capture_output=True, timeout=60, check=False,
    )  # fmt: skip


def assert_failed(done: subprocess.CompletedProcess[bytes], name: str, canary: str) -> None:
    """Assert the exit code, the one line naming the error's type, and no canary on either stream."""
    assert done.returncode == FAILED, done.stderr
    assert done.stderr.splitlines() == [f"ploni selftest: failed: {name}".encode()]
    assert done.stdout == b""
    for form in [canary.encode(encoding) for encoding in ENCODINGS] + [canary.encode("ascii", "backslashreplace")]:
        assert form not in done.stderr + done.stdout


@pytest.mark.parametrize("kind", ["ValueError", "PloniError"])
def test_ec4_an_error_raised_inside_a_command(kind: str) -> None:
    assert_failed(crash(kind, CANARY), kind, CANARY)


@pytest.mark.parametrize("kind", ["context", "from"])
def test_ec5_an_error_raised_while_another_was_handled(kind: str) -> None:
    assert_failed(crash(kind, CANARY), "RuntimeError", CANARY)


def test_b2_an_error_whose_text_cannot_be_made() -> None:
    assert_failed(crash("Unprintable", CANARY), "Unprintable", CANARY)


def test_a2_a_hebrew_canary_in_an_error() -> None:
    assert_failed(crash("ValueError", HEBREW_CANARY), "ValueError", HEBREW_CANARY)
