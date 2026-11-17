"""The only sanctioned way to write a log line: named events and numbers, never text.

Why: the product's promise is that a sensitive document never leaks, and a document surface
in a log line is one of the loudest ways it could (ADR-0005; `CLAUDE.md`, Hard constraints:
"No document text in logs or temp files"). A logger cannot tell document text from any
other string. So this module writes no string that came from a caller at all: a line is the
name of an event, which is a member of an enum and so exists only in code, and fields whose
values are numbers. Everything else is written as a mark.

Contract: `install` puts one handler on the root logger, and from then on every record of
the process goes through it, also the records of libraries that know nothing of this
module. `event` writes one line. A line is

    2026-11-17T09:30:01 INFO fusion.py:88 DetectEvent.WINDOWS_DONE windows=12 seconds=0.41

and a record that did not come through `event` is the same head followed by `<withheld>`.

Known limits:
- A number is written as it is. A number taken from a document and given as a field, an
  identity number as an int, is not told from a count. Fields are for counts and times.
- A library that adds a handler of its own after `install` writes through that handler.
  `install` removes the handlers that exist when it is called.
- What is printed past the logging system, by `print` or by the interpreter for an uncaught
  error, is not seen here. `print` is banned under ploni/ by ruff.
- The log is plain ASCII, so a console in any code page can show it.
"""

import enum
import logging
import re
from typing import TextIO

# The attribute of a log record that carries the fields of an event.
FIELDS = "ploni_fields"

# What a field key may be. A key comes from code, as a keyword of a call; this keeps a key
# that was built from data out of the log.
KEY = re.compile(r"[a-z][a-z0-9_]*")

# The name of the logger that `event` writes to.
LOGGER = "ploni"

TIME = "%Y-%m-%dT%H:%M:%S"

# The level names of the standard logging module. Any other name is written as NO_LEVEL.
LEVELS = frozenset(("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"))

# What the name of a source file looks like: `fusion.py`, or `<string>` for code given to
# the interpreter directly. Any other file name is written as NO_FILE.
FILE = re.compile(r"[A-Za-z0-9_]+\.pyw?|<[a-z]+>")

# What stands in the log for anything that is not written.
WITHHELD = "<withheld>"
BAD_KEY = "<key>"
NO_LEVEL = "LEVEL"
NO_FILE = "<file>"


class Event(enum.Enum):
    """The base class of everything that can be logged: a layer's events are its members.

    Why: a member of an enum is made when its class is defined, in code. A string read from
    a document can never be one, so an event's name is safe to write, whatever it is.

    Contract: subclass it and give the subclass members; the value of a member is not used.
    The log shows `Class.MEMBER`.

    Known limits: none; a class with no member can be subclassed, and this one has none.
    """


def shown(value: object) -> str:
    """Return how one field value is written in a log line.

    Why: the text of a value may be document text, so a value is written only when its type
    cannot hold text. The exact type is asked for, because a subclass can give a number any
    text it likes as its `repr`.

    Contract:
        Args: value, anything.
        Returns: the usual Python form for `None` and for a value whose type is exactly
            `bool`, `int` or `float`; `<str:N>` and `<bytes:N>` with the length for those
            two types; `<TypeName>` for every other value. `str` and `repr` of the value
            are never called.
        Raises: nothing.

    Known limits: the name of the type is written, so a class named after data would show.
    """
    kind = type(value)
    if value is None or kind in (bool, int, float):
        return repr(value)
    if isinstance(value, (str, bytes)) and kind in (str, bytes):
        return f"<{kind.__name__}:{len(value)}>"
    return f"<{kind.__name__}>"


class Redacting(logging.Formatter):
    """Formats every record as a line that holds nothing of the record's own text.

    Why: this is the one place where a record becomes text, so it is where the rule is
    kept, for the records of `event` and for those of any other caller alike.

    Contract: `format` returns one line without a line break, in ASCII. It never formats
    the record's message with its arguments, and never calls `str` or `repr` on anything
    the record carries, so it cannot fail on a record and cannot run a caller's code.

    Known limits: the file name and line number of the logging call are written; they come
    from the code that logged. In a record built by hand they are written only when the
    file name has the shape of a source file's name and the line is a whole number, and a
    level name that is not one of the standard five is written as `LEVEL`. A hand-built
    record whose file name is text shaped like `word.py` would show it.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Return the line for one record: an event with its fields, or the fixed mark."""
        # A record can be built by hand, with anything in these three; logging itself fills
        # them from the code that logged.
        level = record.levelname if record.levelname in LEVELS else NO_LEVEL
        name = record.filename if _is_file(record.filename) else NO_FILE
        line = record.lineno if type(record.lineno) is int else 0
        head = f"{self.formatTime(record, TIME)} {level} {name}:{line}"
        if not isinstance(record.msg, Event):
            body = WITHHELD
        else:
            fields = record.__dict__.get(FIELDS)
            pairs = fields.items() if isinstance(fields, dict) else ()
            written = (f"{key if _is_key(key) else BAD_KEY}={shown(value)}" for key, value in pairs)
            body = " ".join([f"{type(record.msg).__name__}.{record.msg.name}", *written])
        if record.exc_info and record.exc_info[0] is not None:
            body += f" raised={record.exc_info[0].__name__}"
        return f"{head} {body}"


class Quiet(logging.StreamHandler[TextIO]):
    """A stream handler that says nothing when a line cannot be written.

    Why: when writing fails, the standard handler prints the record's message and its
    arguments to the standard error. That is a way for document text to leave the logging
    system, so the failure is dropped. A lost log line loses no data of the user's.

    Contract: as `logging.StreamHandler`, but `handleError` does nothing.

    Known limits: a log that cannot be written is silent about it.
    """

    def handleError(self, record: logging.LogRecord) -> None:
        """Drop the failure: nothing of the record is printed anywhere."""


def _is_key(key: object) -> bool:
    """Return whether a field key is a lower-case identifier."""
    return isinstance(key, str) and KEY.fullmatch(key) is not None


def _is_file(name: object) -> bool:
    """Return whether a record's file name has the shape of a source file's name."""
    return isinstance(name, str) and FILE.fullmatch(name) is not None


def install(stream: TextIO, level: int = logging.INFO) -> logging.Handler:
    """Make the stream the one place that every log record of the process is written to.

    Why: a rule kept only for the product's own calls would leave the libraries free to
    write document text, a tokenizer warning that quotes its input for one. So the handler
    is put where every record passes, and the handlers that were there are removed.

    Contract:
        Args: stream, an open text stream, which the caller closes; level, the lowest
            level that is written.
        Returns: the handler now on the root logger, the only one there.
        Raises: nothing.
        Effects on the process: the root logger's handlers are replaced and its level is
            set; every named logger that exists loses its own handlers and hands its
            records up; warnings are routed into logging.

    Known limits: a logger made after the call can be given a handler of its own.
    """
    handler = Quiet(stream)
    handler.setFormatter(Redacting())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for logger in logging.root.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.handlers.clear()
            logger.propagate = True
    logging.captureWarnings(True)
    return handler


def event(member: Event, /, *, level: int = logging.INFO, **fields: object) -> None:
    """Write one log line: an event and its fields.

    Why: product code needs to say what it did and how long it took, and must not be able
    to say it with document text by accident. The event is a member of an `Event` class;
    the fields are for counts and times.

    Contract:
        Args: member, the event; level, a level of the standard `logging` module; fields,
            keyword values. A value that is not `None`, a `bool`, an `int` or a `float` is
            written as a mark, see `shown`.
        Returns: nothing. The line goes to the handler that `install` set; without one the
            standard library decides, and its last-resort handler writes warnings and
            errors to the standard error in its own form.
        Raises: TypeError when member is no member of an `Event` class; ValueError when a
            key is not a lower-case identifier, which only a call with `**` can cause.
            Neither error holds the offending value, and nothing is written.

    Known limits: see the module docstring on numbers.
    """
    if not isinstance(member, Event):
        raise TypeError("an event is a member of an Event class")
    if not all(_is_key(key) for key in fields):
        raise ValueError("a field key is a lower-case identifier")
    logging.getLogger(LOGGER).log(level, member, extra={FIELDS: fields}, stacklevel=2)
