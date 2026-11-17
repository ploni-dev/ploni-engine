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

Through event, the sanctioned call:
  S1   a field value that is the canary, as str, bytes, list, dict, tuple, path, exception,
       an object whose repr is the canary, and a subclass of int and of float with that repr
  S2   the canary as the event itself               refused, and the error does not hold it
  S3   the canary as a field key                    refused, and the error does not hold it

The canary: one string with Hebrew letters, Latin letters, digits and a space, so that a
leak of any part is caught: each of its parts is searched for by itself, in the text and in
the bytes of every encoding the stream could use.

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

import enum
import io
import logging
import warnings
from collections.abc import Callable
from pathlib import Path

import pytest

from ploni.safety import logging as safe

HEBREW, LATIN, DIGITS = "קנרית־יעקב", "Canary-Jacob", "7301946"
CANARY = f"{HEBREW} {LATIN} {DIGITS}"
# The bare word canary is not a part: the name of this file holds it, and a log line names the file.
PARTS = (HEBREW, LATIN, DIGITS, "יעקב", "Jacob")
ENCODINGS = ("utf-8", "utf-16-le", "cp1255")


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

    __repr__ = __str__ = Loud.__repr__  # type: ignore[assignment]


class LoudFloat(float):
    """A number whose repr is the canary."""

    __repr__ = __str__ = Loud.__repr__  # type: ignore[assignment]


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
    record.lineno = CANARY  # type: ignore[assignment]
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
}


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


def leaks(text: str) -> list[str]:
    """Return every part of the canary that the text holds, as text or in the bytes of an encoding."""
    folded = text.lower()
    as_text = [part for part in (CANARY, *PARTS) if part.lower() in folded]
    # Bytes of another encoding that were read as text show as one character for each byte.
    as_bytes = [
        f"{part} as {encoding} bytes"
        for part in PARTS
        for encoding in ENCODINGS
        if part.encode(encoding).decode("latin-1") in text
    ]
    return as_text + as_bytes


def everything(log: io.StringIO, capfd: pytest.CaptureFixture[str]) -> str:
    """Return all that was written: the log, the standard output and the standard error."""
    captured = capfd.readouterr()
    return log.getvalue() + captured.out + captured.err


@pytest.mark.parametrize("way", STANDARD)
def test_the_canary_does_not_reach_the_log_through_a_standard_logging_call(
    start: Callable[..., io.StringIO], capfd: pytest.CaptureFixture[str], way: str
) -> None:
    log = start()
    STANDARD[way]()
    written = everything(log, capfd)
    assert leaks(written) == []
    assert log.getvalue().count("\n") == 1, "the call wrote one line, so the handler saw it"


@pytest.mark.parametrize("kind", VALUES)
def test_the_canary_does_not_reach_the_log_as_a_field_of_an_event(
    start: Callable[..., io.StringIO], capfd: pytest.CaptureFixture[str], kind: str
) -> None:
    log = start()
    safe.event(Step.DONE, pages=3, value=VALUES[kind])
    written = everything(log, capfd)
    assert leaks(written) == []
    assert "Step.DONE pages=3 value=<" in log.getvalue()


def test_the_canary_as_the_event_itself_is_refused_and_not_repeated(
    start: Callable[..., io.StringIO], capfd: pytest.CaptureFixture[str]
) -> None:
    log = start()
    with pytest.raises(TypeError) as refused:
        safe.event(CANARY)  # type: ignore[arg-type]
    assert leaks(str(refused.value) + everything(log, capfd)) == []
    assert log.getvalue() == ""


def test_the_canary_as_a_field_key_is_refused_and_not_repeated(
    start: Callable[..., io.StringIO], capfd: pytest.CaptureFixture[str]
) -> None:
    log = start()
    with pytest.raises(ValueError, match="key") as refused:
        safe.event(Step.DONE, **{CANARY: 1})
    assert leaks(str(refused.value) + everything(log, capfd)) == []
    assert log.getvalue() == ""


def test_positive_control_an_event_with_numbers_is_written(start: Callable[..., io.StringIO]) -> None:
    log = start()
    safe.event(Step.DONE, pages=3, seconds=0.25)
    assert log.getvalue().endswith(" Step.DONE pages=3 seconds=0.25\n")


def test_the_search_finds_the_canary_when_it_is_there() -> None:
    # The check that the checker works: each way a leak could look is found.
    assert leaks(f"x {CANARY} y") != []
    assert "יעקב" in leaks("only יעקב leaked")
    assert leaks("lower case canary-jacob") != []
    assert leaks(HEBREW.encode("cp1255").decode("latin-1")) == [f"{HEBREW} as cp1255 bytes", "יעקב as cp1255 bytes"]
    assert leaks(DIGITS.encode("utf-16-le").decode("latin-1")) == [f"{DIGITS} as utf-16-le bytes"]
    assert leaks("nothing of it here: Step.DONE pages=3 <withheld>") == []
