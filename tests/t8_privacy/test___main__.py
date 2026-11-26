"""What the command line writes to its error stream carries no document text.

Why: `CLAUDE.md`, Hard constraints: "No document text in logs or temp files." The filter of
`ploni/safety/logging.py` only holds once `install` has run; before it, the logging module's
own handler of last resort prints the message of any WARNING or worse to the error stream, and
a library's warning can quote its input (the filter's docstring names a tokenizer). Finding 1
of the Ponytail pass at the close of Phase 0 found that nothing under ploni/ called `install`
(issue #211). `main` is the one entry point of the command line, so it calls `install` first.
Finding 3 (issue #213): an error that no code catches is printed by Python with its message,
and a message can quote its input (`int()` on text does) or a core object; so `main` catches
it, writes only the command and the error's type, and returns an exit code of its own.

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
       a class of the program's own) -> exit code 4; the error stream is the one line
       "ploni selftest: failed: <type name>"; the canary is on neither stream
  EC5  an error raised while another was handled, and one raised from another -> the same,
       naming the outer error's type only
  EC6  Ctrl+C inside a command, alone and while an error with the canary was being handled
       -> exit code 130 and the one line "ploni selftest: interrupted"; no canary
  EC7  an exit raised inside a command (SystemExit(5)) -> passes through: exit code 5, nothing
       written
  EC8  `error_name`: a plain type name -> the name; a name with a line break, a name in
       Hebrew letters, a name that is a subclass of str -> `<value>`; a metaclass that
       answers any text, or raises, when asked for the name -> the class's own name, not
       what the metaclass answers, and no error
Boundaries:
  B1  the canary given as an argument of the record, not in its format string -> not written
  B2  an error whose own text cannot be made (its `__str__` raises, with the canary) -> the
      same line, its type
  B3  an error of a class whose name holds a line break and the canary -> one line, `<value>`
  B4  an error of a class whose metaclass raises, with the canary, when asked the name, raised
      while an error with the canary is handled -> one line with the class's own name
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
  - An exit raised inside a command passes through, and an exit given a text prints the
    text: no command calls `sys.exit` with a text (`main`'s Known limits). Ctrl+C before the
    arguments are read is not caught.
  - A type name that is a plain identifier is written as it is: a class built at run time
    with a name taken from a document (`Jacob`) would show it, the filter's own limit for
    names of code.

Not applicable: the document-structure axes of the test-matrix skill; no document is read.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

import ploni.__main__ as cli

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


def start(program: str, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    """Run a program text in a fresh interpreter with its arguments; return the finished process, its streams as bytes."""
    return subprocess.run(  # noqa: S603 fixed argv, no shell
        [sys.executable, "-c", program, *arguments], cwd=ROOT, capture_output=True, timeout=60, check=False,
    )  # fmt: skip


def run(when: str, command: str, level: str, message: str, argument: str = "") -> subprocess.CompletedProcess[bytes]:
    """Run PROGRAM in a fresh interpreter; return the finished process, its streams as bytes."""
    return start(PROGRAM, when, command, level, message, argument)


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
    if kind == "odd-name":
        raise type("Line1\\nTraceback " + message, (Exception,), {})()
    if kind == "exit":
        raise SystemExit(5)
    if kind == "interrupt":
        raise KeyboardInterrupt
    if kind == "interrupt-in-error":
        try:
            int(message)
        except ValueError:
            raise KeyboardInterrupt
    if kind == "refusing-name":
        class Refuses(type):
            @property
            def __name__(cls):
                raise ValueError(message)
        try:
            int(message)
        except ValueError:
            raise Refuses("Bad", (Exception,), {})()
    try:
        raise KeyError(message)
    except KeyError as inner:
        if kind == "from":
            raise RuntimeError(message) from inner
        raise RuntimeError(message)

cli.selftest = selftest
raise SystemExit(cli.main(["selftest"]))
"""
# ploni/__main__.py: the exit codes of a command stopped by an error no code caught, and by
# Ctrl+C; 1 is selftest's "not offline" and 2 a stub or a usage error.
FAILED = 4
INTERRUPTED = 130


def crash(kind: str, message: str) -> subprocess.CompletedProcess[bytes]:
    """Run CRASHING in a fresh interpreter; return the finished process, its streams as bytes."""
    return start(CRASHING, kind, message)


def assert_failed(done: subprocess.CompletedProcess[bytes], name: str, canary: str, code: int = FAILED) -> None:
    """Assert the exit code, the one line (the error's type, or interrupted), and no canary on either stream."""
    assert done.returncode == code, done.stderr
    line = f"ploni selftest: failed: {name}" if code == FAILED else "ploni selftest: interrupted"
    assert done.stderr.splitlines() == [line.encode()]
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


def test_b3_an_error_of_a_class_whose_name_holds_a_line_break() -> None:
    assert_failed(crash("odd-name", CANARY), "<value>", CANARY)


@pytest.mark.parametrize("kind", ["interrupt", "interrupt-in-error"])
def test_ec6_ctrl_c_inside_a_command(kind: str) -> None:
    assert_failed(crash(kind, CANARY), "", CANARY, INTERRUPTED)


def test_ec7_an_exit_inside_a_command_passes_through() -> None:
    done = crash("exit", CANARY)
    assert (done.returncode, done.stderr, done.stdout) == (5, b"", b"")


class Answers(type):
    """A metaclass whose classes answer any text when asked for their name."""

    @property
    def __name__(cls) -> str:
        return "CANARY shown by a metaclass"


class Refuses(type):
    """A metaclass whose classes raise when asked for their name, with the canary."""

    @property
    def __name__(cls) -> str:
        raise ValueError(CANARY)


class Sly(str):
    """A text that formats itself as other text."""

    def __format__(self, spec: str) -> str:
        return f"Jacob {CANARY}"


def named_by(name: str) -> BaseException:
    """Return an error of a class whose `__name__` was set to the text given."""
    kind = type("Plain", (Exception,), {})
    kind.__name__ = name
    return kind()


# Each error is made inside its case: an object whose class refuses its name cannot be
# printed, and pytest prints the parameters of a case that fails.
ERRORS = {
    "plain": (lambda: ValueError("x"), "ValueError"),
    "line break": (lambda: type("Line1\nTraceback", (Exception,), {})(), "<value>"),
    "hebrew": (lambda: type("שגיאה", (Exception,), {})(), "<value>"),
    "metaclass answers": (lambda: Answers("Odd", (Exception,), {})(), "Odd"),
    "metaclass raises": (lambda: Refuses("Bad", (Exception,), {})(), "Bad"),
    "str subclass": (lambda: named_by(Sly("Ok")), "<value>"),
}


@pytest.mark.parametrize("case", list(ERRORS))
def test_ec8_error_name(case: str) -> None:
    make, name = ERRORS[case]
    assert cli.error_name(make()) == name


def test_b4_an_error_whose_class_raises_when_asked_its_name() -> None:
    assert_failed(crash("refusing-name", CANARY), "Bad", CANARY)
