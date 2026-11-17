"""The only sanctioned way to write a log line: named events and numbers, never text.

Why: the product's promise is that a sensitive document never leaks, and a document surface
in a log line is one of the loudest ways it could (ADR-0005; `CLAUDE.md`, Hard constraints:
"No document text in logs or temp files"). A logger cannot tell document text from any
other string. So this module writes no string of a caller's as it is. A line is made of the
name of an event, which is a member of an enum; of fields whose values are numbers; and of
a few words that stand for everything else. A name is written only when it has the shape of
a name in code.

Contract: `install` puts one handler on the root logger, and from then on every record of
the process goes through it, also the records of libraries that know nothing of this
module. `event` writes one line. A line is

    2026-11-17T09:30:01 INFO fusion.py:88 DetectEvent.WINDOWS_DONE windows=12 seconds=0.41

and a record that did not come through `event` is the same head followed by `<withheld>`.
A line is plain ASCII and holds no line break.

Known limits:
- A number is written as it is. A number taken from a document and given as a field, an
  identity number as an int, is not told from a count. Fields are for counts and times.
- A word with the shape of a name in code is written when it stands where a name of code
  stands: as the name of an event's class or member, of a value's type, of an exception's
  type, or of a source file, and, in lower case, as a field key. Code that builds a class,
  an enum member or a log record from document text could put a word such as `Jacob`
  there, and a call that spreads a mapping made from document text into the fields,
  `event(member, **counts_by_word)`, writes every key that is a lower-case word. No plain
  logging call does either. Field keys are written in the call, never taken from data.
- `install` holds for the process it is called in and from the moment it is called. A
  record logged before it, and a process started later, are outside it; the worker process
  calls `install` for itself.
- Code that sets logging up again after `install` undoes it. Among the ways:
  `logging.basicConfig(force=True)`; `logging.config.dictConfig`; a handler that a library
  adds to its own logger; removing the handler from the root logger; setting
  `logging.lastResort` back, or to `None`, after which the logging module prints the name
  of a logger that has no handler; a caller that gives `warnings.showwarning` a stream of
  its own; and the end of a `warnings.catch_warnings()` block that `install` was called
  inside.
- What is printed past the logging system, by `print` or by the interpreter for an uncaught
  error, is not seen here. `print` is banned under ploni/ by ruff.
- A line that cannot be written leaves no trace: a stream that fails, and a record that
  makes the formatter itself fail, which an object that raises when it is asked for its
  own attributes can do.
- A warning is one line with no category and no place of origin, and an exception shows
  the name of its type and the place of the logging call, not where it was raised.
"""

import enum
import logging
import re
from typing import TextIO

# The attribute of a log record that carries the fields of an event.
FIELDS = "ploni_fields"

# What a field key may be. A key is meant to come from code, as a keyword of a call. The
# shape keeps out a key with a space, a capital, a line break or a letter that is not ASCII;
# it cannot keep out a lower-case word that was taken from data (module docstring).
KEY = re.compile(r"[a-z][a-z0-9_]*")

# What a name written in code looks like: the name of a class or of an enum member.
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# What the name of a source file looks like: `fusion.py`, or `<string>` for code given to
# the interpreter directly.
FILE = re.compile(r"[A-Za-z0-9_]+\.pyw?|<[a-z]+>")

# The level names of the standard logging module.
LEVELS = frozenset(("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"))

# The name of the logger that `event` writes to.
LOGGER = "ploni"

TIME = "%Y-%m-%dT%H:%M:%S"

# A whole number of this size or more is no count and no time, and Python refuses to write
# one of more than 4,300 digits at all. Below 2**63 lies every signed 64-bit number.
LARGEST_NUMBER = 2**63

# `event` hands the record to the logging module from one call deep, so the place written
# in the line is the caller's: logging counts the frames to skip from 1.
CALLER = 2

# What stands in the log for anything that is not written.
WITHHELD = "<withheld>"
BAD_KEY = "<key>"
BAD_NAME = "<name>"
BAD_TYPE = "value"
NO_LEVEL = "LEVEL"
NO_FILE = "<file>"
NO_LINE = 0
NO_TIME = "0000-00-00T00:00:00"


class Event(enum.Enum):
    """The base class of everything that can be logged: a layer's events are its members.

    Why: a member of an enum is made in code, when its class is defined. So what a plain
    logging call can pass as a message, a string, is never an event, and a careless call
    cannot log text as one.

    Contract: subclass it and give the subclass members; the value of a member is not used.
    The log shows `Class.MEMBER`, each of the two only when it has the shape of a name in
    code, and `<name>` in its place otherwise.

    Known limits: Python lets code build an enum class from data at run time. A member of
    such a class is an event, and its name is written when it has the shape of a name.
    """


def _is_key(key: object) -> bool:
    """Say whether a field key is exactly a string and a lower-case identifier."""
    return type(key) is str and KEY.fullmatch(key) is not None


def _is_file(name: object) -> bool:
    """Say whether a record's file name is exactly a string with the shape of a source file's name."""
    return type(name) is str and FILE.fullmatch(name) is not None


def _code_name(name: object, otherwise: str) -> str:
    """Return a name when it is exactly a string with the shape of a name in code, else `otherwise`.

    The exact type is asked for: a subclass of `str` can show any text when it is written.
    """
    return name if type(name) is str and NAME.fullmatch(name) is not None else otherwise


def _type_name(kind: type) -> object:
    """Return the name a class was made with, past any name its metaclass shows in its place."""
    return type.__dict__["__name__"].__get__(kind)


def shown(value: object) -> str:
    """Return how one field value is written in a log line.

    Why: the text of a value may be document text, so a value is written only when its type
    cannot hold text. The exact type is asked for, because a subclass can give a number any
    text it likes as its `repr`.

    Contract:
        Args: value, anything.
        Returns: the usual Python form for `None` and for a value whose type is exactly
            `bool`, `int` or `float`, a whole number only below LARGEST_NUMBER in size;
            `<str:N>` and `<bytes:N>` with the length for those two types; `<TypeName>`
            for every other value, or `<value>` when the name of the type has not the
            shape of a name in code. `repr` is called only on `None` and on a value of
            exactly one of the three number types, `str` on none, and the value is never
            asked what class it is: an object can answer that with code of its own.
        Raises: nothing.

    Known limits: the name of a type is written, see the module docstring.
    """
    kind = type(value)
    if value is None or kind is bool or kind is float:
        return repr(value)
    # The real type is asked first, so `isinstance`, which asks the object, runs only for
    # a real number or string; it is there for the type checker.
    if kind is int and isinstance(value, int):
        return repr(value) if -LARGEST_NUMBER < value < LARGEST_NUMBER else "<int>"
    if (kind is str or kind is bytes) and isinstance(value, (str, bytes)):
        return f"<{'str' if kind is str else 'bytes'}:{len(value)}>"
    return f"<{_code_name(_type_name(kind), BAD_TYPE)}>"


class Redacting(logging.Formatter):
    """Formats every record as a line that holds nothing of the record's own text.

    Why: this is the one place where a record becomes text, so it is where the rule is
    kept, for the records of `event` and for those of any other caller alike.

    Contract: `format` returns one line without a line break, in ASCII. It never formats
    the record's message with its arguments, and calls `str` on no value the record
    carries and `repr` only as `shown` does, on exact numbers.

    Known limits: a record built by hand shows its level name, file name and line only
    when they have the shape of code; see the module docstring for what that leaves.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Return the line for one record: an event with its fields, or the fixed mark.

        Why: see the class. Contract: one ASCII line; a part that has not the shape it
        should have is written as its mark. A record that makes it fail is dropped by the
        handler, with nothing written.
        """
        head = f"{self._time(record)} {self._level(record)} {self._place(record)}"
        if not issubclass(type(record.msg), Event):
            body = WITHHELD
        else:
            fields = record.__dict__.get(FIELDS)
            pairs = dict.items(fields) if type(fields) is dict else ()
            written = (f"{key if _is_key(key) else BAD_KEY}={shown(value)}" for key, value in pairs)
            member = record.msg
            name = f"{_code_name(_type_name(type(member)), BAD_NAME)}.{_code_name(vars(member).get('_name_'), BAD_NAME)}"
            body = " ".join([name, *written])
        raised = record.exc_info[0] if type(record.exc_info) is tuple and record.exc_info else None
        if issubclass(type(raised), type) and isinstance(raised, type):
            body += f" raised={_code_name(_type_name(raised), BAD_NAME)}"
        elif record.exc_info and raised is not None:
            body += f" raised={BAD_NAME}"
        return f"{head} {body}"

    def _time(self, record: logging.LogRecord) -> str:
        """Return the time of a record, or NO_TIME when its time is not exactly a float that names a time."""
        try:
            return self.formatTime(record, TIME) if type(record.created) is float else NO_TIME
        except (ValueError, OverflowError, OSError):
            return NO_TIME

    @staticmethod
    def _level(record: logging.LogRecord) -> str:
        """Return the level name of a record when it is one of the standard five, else NO_LEVEL."""
        name = record.levelname
        return name if type(name) is str and name in LEVELS else NO_LEVEL

    @staticmethod
    def _place(record: logging.LogRecord) -> str:
        """Return `file:line` of the logging call, each part only when it has the shape of code."""
        name = record.filename if _is_file(record.filename) else NO_FILE
        line = record.lineno if type(record.lineno) is int and 0 <= record.lineno < LARGEST_NUMBER else NO_LINE
        return f"{name}:{line}"


class Quiet(logging.StreamHandler[TextIO]):
    """A stream handler that says nothing when a line cannot be written.

    Why: when writing fails, the standard handler prints the record's message and its
    arguments to the standard error. That is a way for document text to leave the logging
    system, so the failure is dropped. A lost log line loses no data of the user's.

    Contract: as `logging.StreamHandler`, but `handleError` does nothing.

    Known limits: a log that cannot be written is silent about it. Two things are not
    dropped: a `RecursionError` from the stream goes to the caller, as in the standard
    handler; and when the stream fails to flush at the end of the process with an error
    other than `OSError` or `ValueError`, the logging module prints that error, which holds
    nothing of a record.
    """

    def handleError(self, record: logging.LogRecord) -> None:
        """Drop the failure.

        Why: see the class. Contract: nothing of the record is printed anywhere, and
        nothing is raised.
        """


def _is_level(level: object) -> bool:
    """Say whether a level is exactly a whole number, as the logging module wants one."""
    return type(level) is int


def install(stream: TextIO, level: int = logging.INFO) -> logging.Handler:
    """Make the stream the one place that every log record of the process is written to.

    Why: a rule kept only for the product's own calls would leave the libraries free to
    write document text, a tokenizer warning that quotes its input for one. So the handler
    is put where every record passes, and the handlers that were there are removed.

    Contract:
        Args: stream, an open text stream, which the caller closes; level, the lowest
            level that is written, whatever level a logger has of its own.
        Returns: the handler now on the root logger, the only one there.
        Raises: TypeError when level is not exactly an `int`, before anything is changed.
        Effects on the process: the root logger's handlers are replaced and its level is
            set; every named logger that exists loses its own handlers and hands its
            records up; the handler of last resort, which the logging module uses for a
            record that reaches no handler, is this one too; warnings are routed into
            logging.

    Known limits: see the module docstring: one process, from this call on, until other
    code sets logging up again.
    """
    if not _is_level(level):
        raise TypeError("a level is a whole number of the logging module")
    handler = Quiet(stream)
    handler.setFormatter(Redacting())
    handler.setLevel(level)
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for logger in logging.root.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.handlers.clear()
            logger.propagate = True
    logging.lastResort = handler
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
        Returns: nothing. The line goes to the handler that `install` set. Before
            `install` the logging module decides: its own handler of last resort writes a
            warning or an error to the standard error, in its own form.
        Raises: TypeError when member is no member of an `Event` class, or level is not
            exactly an `int`; ValueError when a key is not a lower-case identifier, which
            only a call with `**` can cause. No error holds the offending value, and
            nothing is written.

    Known limits: see the module docstring on numbers.
    """
    # The real type is asked, not the object: an object can say it is of any class.
    if not issubclass(type(member), Event):
        raise TypeError("an event is a member of an Event class")
    if not _is_level(level):
        raise TypeError("a level is a whole number of the logging module")
    if not all(_is_key(key) for key in fields):
        raise ValueError("a field key is a lower-case identifier")
    logging.getLogger(LOGGER).log(level, member, extra={FIELDS: fields}, stacklevel=CALLER)
