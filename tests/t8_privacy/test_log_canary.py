"""The log canary: a string given as document text must never reach a log.

Why: `CLAUDE.md`, Hard constraints: "No document text in logs or temp files." A document
surface in a log line is one of the loudest ways this product could leak (ADR-0005). The
canary is a string that stands for document text. It is pushed through every way of logging
that the handler of `ploni.safety.logging` can meet, and then everything that was written,
to the log and to the standard streams, is searched for it. It is one of the four tests the
merge gate needs in order to work (`PROMOTION.md` section 11).

Test matrix (every case sends the canary, then looks for it):

Through the standard logging calls, as any library or careless product code would:
  W1   the message itself                          W2   an argument of the message
  W3   a mapping given as the arguments            W4   an `extra` attribute
  W5   the name of the logger                      W6   the text of an exception that is logged
  W7   logger.exception inside an except block     W8   stack_info
  W9   an object whose str is the canary           W10  a message whose formatting fails
  W11  a warning                                   W12  a record made by hand and handled, the
                                                        canary as its file name, line number, level
                                                        name and every other part
  W13  the forged fields attribute, with a string message
  W14  an Event message with forged fields: canary as key and as value
  W15  bytes, and a message of several lines
  W16  an exception class named from data          W17  an object where the exception class stands
  W18  an event made from data by the enum's functional call
  W19  an event whose name holds a line break      W20  a field key of a class of its own
  W21  a level name and a file name of a class of their own
  W22  an event sent with arguments                W23  a logger that hands nothing up
  W24  a record at the highest level
  and, with the stream of the log failing on every write, W1 to W24 again: nothing may be
  printed on the standard streams in its place

Through event, the sanctioned call:
  S1   a field value that is the canary, as str, bytes, list, dict, tuple, path, exception,
       an object whose repr is the canary, a subclass of int, of float and of str with that
       repr, a Decimal and a string of its digits, a value whose class claims to be int, and
       a value whose class is named from data
  S2   the canary as the event itself               refused, and the error does not hold it
  S3   the canary as a field key                    refused, and the error does not hold it

The canary: one string with Hebrew letters, Latin letters, digits and a space, so that a
leak of any part is caught: each of its parts is searched for by itself, in the bytes of
what was written, in five encodings, in lower case and as backslash escapes. The standard
streams are read as bytes, so that nothing is lost when they are decoded.

Positive control: an event with number fields is written, with its numbers. Without it a
handler that writes nothing would pass every case above.

Known limits:
  - No pipeline exists yet, so the canary is pushed into the logging calls and not through
    `analyze` and `apply`. Every phase that adds a stage of the pipeline adds a run of that
    stage over a document that holds the canary (`build-plan.md` section 7, T8).
  - A number taken from a document and given as a field (an identity number as an int) is
    written as it is. The handler cannot tell it from a count.
  - What is printed past the logging system, by `print` or by an uncaught error, is not a
    log. `print` is banned under ploni/ by ruff (T201).

The document-structure axes of the test-matrix skill do not apply: no document is handled.
"""

import decimal
import enum
import io
import logging
import warnings
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from ploni.safety import logging as safe
from tests import logging_state

HEBREW, LATIN, DIGITS = "קנרית־יעקב", "Canary-Jacob", "7301946"
CANARY = f"{HEBREW} {LATIN} {DIGITS}"
# The bare word canary is not a part: the name of this file holds it, and a log line names the file.
PARTS = (HEBREW, LATIN, DIGITS, "יעקב", "Jacob")
# cp862 is the code page of a Hebrew Windows console, cp1255 of its other programs.
ENCODINGS = ("utf-8", "utf-16-le", "utf-16-be", "cp1255", "cp862")


class Step(safe.Event):
    """Events of the tests."""

    DONE = enum.auto()


class Loud:
    """An object whose str and repr are the canary."""

    def __repr__(self) -> str:
        return CANARY

    __str__ = __repr__


class LoudInt(int):
    """A whole number whose repr is the canary."""

    __repr__ = __str__ = Loud.__repr__


class LoudFloat(float):
    """A number whose repr is the canary."""

    __repr__ = __str__ = Loud.__repr__


class LoudStr(str):
    """A string that shows the canary when it is written, whatever it holds."""

    __slots__ = ()

    __str__ = __repr__ = Loud.__repr__

    def __format__(self, spec: str) -> str:
        return CANARY


class EqualsAll(type):
    """A metaclass whose classes claim to equal every other class."""

    def __eq__(cls, other: object) -> bool:
        return True

    __hash__ = type.__hash__


class Claims(metaclass=EqualsAll):
    """A value whose class claims to be `int`, and whose repr is the canary."""

    __repr__ = __str__ = Loud.__repr__


def named_by_hand() -> logging.LogRecord:
    """Return a record whose level name and file name are strings of a class of their own."""
    record = logging.LogRecord("library", logging.INFO, "module.py", 1, "plain", None, None)
    record.levelname, record.filename = LoudStr("INFO"), LoudStr("module.py")
    return record


def silent_logger() -> None:
    """Log through a logger that has no handler and hands nothing up: the last resort of the logging module."""
    logger = logging.getLogger("lonely.library")
    logger.propagate = False
    logger.warning(CANARY)


def raised() -> ValueError:
    """Return an exception whose text is the canary, with a traceback."""
    try:
        raise ValueError(CANARY)
    except ValueError as error:
        return error


def log_exception() -> None:
    """Log from inside an except block, the canary in the error and in the message."""
    try:
        raise KeyError(CANARY)
    except KeyError:
        logging.getLogger("library").exception("failed on %s", CANARY)


def handle_by_hand() -> None:
    """Hand the root logger a record built without a logging call, the canary in every part of it."""
    record = logging.LogRecord(CANARY, logging.ERROR, CANARY, 1, CANARY, (CANARY,), None, func=CANARY, sinfo=CANARY)
    record.levelname = record.filename = record.module = record.threadName = record.processName = CANARY
    record.lineno = record.created = record.exc_text = CANARY
    record.exc_info = (Loud(), ValueError(CANARY), None)
    logging.getLogger().handle(record)


STANDARD: dict[str, Callable[[], object]] = {
    "W1 message": lambda: logging.info(CANARY),
    "W2 argument": lambda: logging.warning("found %s", CANARY),
    "W3 mapping": lambda: logging.info("found %(name)s", {"name": CANARY}),
    "W4 extra": lambda: logging.info("plain", extra={"note": CANARY}),
    "W5 logger name": lambda: logging.getLogger(CANARY).error("plain"),
    "W6 exception text": lambda: logging.error("failed", exc_info=raised()),
    "W7 logger.exception": log_exception,
    "W8 stack_info": lambda: logging.info(CANARY, stack_info=True),
    "W9 object": lambda: logging.info(Loud()),
    "W10 formatting fails": lambda: logging.info("%d pages %s", CANARY),
    "W11 warning": lambda: warnings.warn(CANARY, UserWarning, stacklevel=1),
    "W12 record by hand": handle_by_hand,
    "W13 forged fields": lambda: logging.info(CANARY, extra={"ploni_fields": {"pages": 3}}),
    "W14 forged fields of an event": lambda: logging.info(Step.DONE, extra={"ploni_fields": {CANARY: 1, "note": CANARY}}),
    "W15 bytes": lambda: logging.info(CANARY.encode("utf-8")),
    "W15 several lines": lambda: logging.info(f"first\n{CANARY}\nlast"),
    "W16 exception class named from data": lambda: logging.error("failed", exc_info=(type(CANARY, (Exception,), {}), None, None)),
    "W17 an object in place of the exception class": lambda: logging.error("failed", exc_info=(Loud(), None, None)),
    "W18 event made from data": lambda: logging.info(next(iter(safe.Event(CANARY, {CANARY: 1})))),
    "W19 event name with a line break": lambda: logging.info(next(iter(safe.Event("Fake", {f"x\n{CANARY}": 1})))),
    "W20 key of a class of its own": lambda: logging.info(Step.DONE, extra={"ploni_fields": {LoudStr("pages"): 1}}),
    "W21 level name of a class of its own": lambda: logging.getLogger().handle(named_by_hand()),
    "W22 event with arguments": lambda: logging.info(Step.DONE, CANARY, CANARY),
    "W23 a logger that hands nothing up": silent_logger,
    "W24 critical": lambda: logging.getLogger("library").critical(CANARY),
}

VALUES: dict[str, object] = {
    "str": CANARY,
    "bytes": CANARY.encode("utf-8"),
    "list": [CANARY],
    "dict": {CANARY: CANARY},
    "tuple": (CANARY, 1),
    "path": Path(CANARY),
    "exception": ValueError(CANARY),
    "object": Loud(),
    "int subclass": LoudInt(3),
    "float subclass": LoudFloat(0.5),
    "str subclass": LoudStr("12"),
    "decimal": decimal.Decimal(DIGITS),
    "digits as a string": DIGITS,
    "class that claims to be int": Claims(),
    "class named from data": type(CANARY, (), {})(),
}


@pytest.fixture
def logging_restored() -> Iterator[None]:
    """Put the logging state of the process back when the test is over."""
    with logging_state.restored():
        yield


@pytest.fixture
def start(logging_restored: None) -> Callable[..., io.StringIO]:
    """Return a function that installs the handler on a stream held in memory and returns the stream.

    A test calls it first, in its own body. pytest hangs handlers of its own on the root logger at the start
    of every phase of a test; `install` removes the ones of the phase it is called in.
    """

    def installed(level: int = logging.DEBUG) -> io.StringIO:
        stream = io.StringIO()
        safe.install(stream, level=level)
        return stream

    return installed


def leaks(data: bytes) -> list[str]:
    """Return every part of the canary that the bytes hold, in any of the forms a leak could take."""
    folded = data.lower()
    # A part that an encoding cannot write is searched with the letter it lacks left out: cp862 has no maqaf.
    found = [
        f"{part} as {encoding}" for part in (CANARY, *PARTS) for encoding in ENCODINGS if part.encode(encoding, "ignore") in data
    ]
    found += [f"{part} in lower case" for part in (LATIN, "Jacob") if part.lower().encode("ascii") in folded]
    found += [f"{part} as escapes" for part in PARTS if part.encode("unicode_escape") in data and not part.isascii()]
    return found


def everything(log: io.StringIO, capfdbinary: pytest.CaptureFixture[bytes]) -> bytes:
    """Return all that was written, as bytes: the log, the standard output and the standard error."""
    captured = capfdbinary.readouterr()
    return log.getvalue().encode("utf-8") + captured.out + captured.err


@pytest.mark.parametrize("way", STANDARD)
def test_the_canary_does_not_reach_the_log_through_a_standard_logging_call(
    start: Callable[..., io.StringIO], capfdbinary: pytest.CaptureFixture[bytes], way: str
) -> None:
    log = start()
    STANDARD[way]()
    written = everything(log, capfdbinary)
    assert leaks(written) == []
    assert log.getvalue().count("\n") == 1, "the call wrote one line, so the handler saw it"


@pytest.mark.parametrize("kind", VALUES)
def test_the_canary_does_not_reach_the_log_as_a_field_of_an_event(
    start: Callable[..., io.StringIO], capfdbinary: pytest.CaptureFixture[bytes], kind: str
) -> None:
    log = start()
    safe.event(Step.DONE, pages=3, value=VALUES[kind])
    written = everything(log, capfdbinary)
    assert leaks(written) == []
    assert "Step.DONE pages=3 value=<" in log.getvalue()


def test_the_canary_as_the_event_itself_is_refused_and_not_repeated(
    start: Callable[..., io.StringIO], capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    log = start()
    with pytest.raises(TypeError) as refused:
        safe.event(CANARY)
    assert leaks(str(refused.value).encode("utf-8") + everything(log, capfdbinary)) == []
    assert log.getvalue() == ""


def test_the_canary_as_a_field_key_is_refused_and_not_repeated(
    start: Callable[..., io.StringIO], capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    log = start()
    with pytest.raises(ValueError, match="key") as refused:
        safe.event(Step.DONE, **{CANARY: 1})
    assert leaks(str(refused.value).encode("utf-8") + everything(log, capfdbinary)) == []
    assert log.getvalue() == ""


def test_positive_control_an_event_with_numbers_is_written(start: Callable[..., io.StringIO]) -> None:
    log = start()
    safe.event(Step.DONE, pages=3, seconds=0.25)
    assert log.getvalue().endswith(" Step.DONE pages=3 seconds=0.25\n")


class Broken(io.StringIO):
    """A stream of the log that fails on every write."""

    def write(self, text: str) -> int:
        raise OSError("the disk is full")


@pytest.mark.parametrize("way", STANDARD)
def test_the_canary_does_not_reach_the_standard_streams_when_the_log_cannot_be_written(
    logging_restored: None, capfdbinary: pytest.CaptureFixture[bytes], way: str
) -> None:
    safe.install(Broken(), level=logging.DEBUG)
    STANDARD[way]()
    captured = capfdbinary.readouterr()
    assert (captured.out, captured.err) == (b"", b"")


def test_the_canary_as_a_field_key_of_a_class_of_its_own_is_refused_and_not_repeated(
    start: Callable[..., io.StringIO], capfdbinary: pytest.CaptureFixture[bytes]
) -> None:
    log = start()
    with pytest.raises(ValueError, match="key") as refused:
        safe.event(Step.DONE, **{LoudStr("pages"): 1})
    assert leaks(str(refused.value).encode("utf-8") + everything(log, capfdbinary)) == []
    assert log.getvalue() == ""


def test_the_search_finds_the_canary_when_it_is_there() -> None:
    # The check that the checker works: each form a leak could take is found, and nothing else is.
    assert leaks(f"x {CANARY} y".encode()) != []
    assert leaks("only יעקב leaked".encode()) == ["יעקב as utf-8"]
    assert leaks(b"lower case canary-jacob") == [f"{LATIN} in lower case", "Jacob in lower case"]
    assert leaks(HEBREW.encode("cp1255")) == [f"{HEBREW} as cp1255", "יעקב as cp1255"]
    assert leaks(DIGITS.encode("utf-16-le")) == [f"{DIGITS} as utf-16-le"]
    assert leaks("יעקב".encode("cp862")) == ["יעקב as cp862"]
    assert leaks("יעקב".encode("utf-16-be")) == ["יעקב as utf-16-be"]
    assert leaks(HEBREW.encode("unicode_escape")) == [f"{HEBREW} as escapes", "יעקב as escapes"]
    assert leaks(b"nothing of it here: Step.DONE pages=3 <withheld> test_log_canary.py:7") == []
