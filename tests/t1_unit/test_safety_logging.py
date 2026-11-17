"""Test matrix for ploni/safety/logging.py, the only way product code writes a log line.

The canary test, which pushes one string through every way of logging and looks for it in the
output, is tests/t8_privacy/test_log_canary.py. The module run from a program of its own is
tests/t4_integration/test_safety_logging.py.

event. Equivalence classes:
  EC1  a member of an Event class with fields     one line: time, level, file:line of the caller,
                                                  Class.MEMBER, then key=value in the order given
  EC2  a field that is a bool, an int, a float or None    written as Python writes it
  EC3  a field of any other type                  a mark with the name of the type, never its text:
                                                  a string and bytes with their length, a list, a
                                                  dict, a path, an exception, an object whose repr
                                                  is text, a subclass of int whose repr is text
  EC4  the level                                  INFO when none is given; the one given otherwise;
                                                  a line below the installed level is not written
  EC5  no fields                                  the name alone

Error paths:
  E1  the event is no member of an Event class (a string, also one shaped like a name; a member
      of another enum; None)                      TypeError that does not hold the value; no line
  E2  a field key that is no lower-case identifier (only possible through **)
                                                  ValueError that does not hold the key; no line

Records that did not come through event (the standard logging calls of any library):
  EC6  any such record                            time, level, file:line and a fixed mark; nothing of
                                                  the message, its arguments or the logger's name
  EC7  such a record with an exception            the mark and the name of the exception's type
  EC8  a record that carries the fields attribute without an Event as its message    as EC6
  EC9  a record whose message is an Event, sent by a standard call with forged fields
                                                  the event's name; a bad key is written as a mark,
                                                  a value follows EC2 and EC3

install. Equivalence classes:
  EC10  the root logger         its handlers are replaced by the one returned; the level is set
  EC11  named loggers           their own handlers are removed and they hand their records up
  EC12  warnings                written through the handler, as EC6
  EC13  install called twice    one handler, so one line per record

Boundaries:
  B1  a stream that cannot be written to          the call returns, and nothing reaches stderr
  B2  an Event class with no member can be subclassed, and a subclass with members works

Adversarial:
  A1  a message whose formatting fails ("%d" with a string)    the fixed mark, nothing on stderr;
      the standard handler would print the message and its arguments there
  A2  a field named like an argument of the logging call (level, extra, msg, name, exc_info)
  A3  a record built by hand whose level name, file name or line number is text: each is
      written as a fixed word; a file name shaped like a source file and a whole line number
      are written as they are

After the first review (PR #89):

The four small functions, each by itself:
  shown        every kind of value: what is written and what becomes a mark; a whole number
               at and past the largest size; a class that claims to equal `int`
  _is_key      the shapes of a key that pass and that do not; a key that is no string, and
               one of a class of its own
  _is_file     the shapes of a file name; a name of a class of its own
  _code_name   the shapes of a name in code; anything else gives the mark

What a caller's object can do to the line (A4 to A9):
  A4  a string of a class of its own, which shows another text when it is written: as a field
      key, as a record's level name and file name
  A5  what stands in `exc_info`: an exception class with a name of code; one named from data;
      an object that is no class; a tuple of the wrong shape; a class whose metaclass gives
      it another name
  A6  an event made from data: by the enum's functional call, with a name that holds a line
      break, with a `name` property of its own, renamed after it was made
  A7  fields that are a mapping of a class of its own, and a key that is no string
  A8  a record whose time is no number, or no time; a line number past any file
  A9  a whole number too long for Python to write

install and event, more:
  EC14  the level holds for every record: a named logger with a lower level of its own, and
        the logger of `event` with one
  EC15  a logger that stops handing its records up and has no handler: the line is written to
        the stream and not printed on the standard error
  EC16  a named logger with a handler of its own that does hand its records up
  EC17  the time of a record is written as its local time to the second
  E3    a level that is no whole number: TypeError without the value, from `install` before
        anything is changed, and from `event`
  A10   an event sent by a standard call with arguments; a field named `member`

The Hebrew axes of the test-matrix skill apply as input only: text in Hebrew, in Latin letters
and mixed is what must not come out; the canary test carries them. The document-structure axes
do not apply: no document is handled.
"""

import enum
import io
import logging
import decimal
import fractions
import re
import time
import warnings
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from ploni.safety import logging as safe
from tests import logging_state

LINE = r"\d{{4}}-\d\d-\d\dT\d\d:\d\d:\d\d {level} test_safety_logging\.py:\d+ {rest}\n"
TEXT = "יעקב כהן / John Smith"


class Sample(safe.Event):
    """Events of the tests."""

    DONE = enum.auto()
    FAILED = enum.auto()


class Other(enum.Enum):
    """An enum that is no Event class."""

    DONE = enum.auto()


class Chatty:
    """An object whose repr is text."""

    def __repr__(self) -> str:
        return TEXT

    __str__ = __repr__


class ChattyStr(str):
    """A string of a class of its own, which could give itself any length."""

    __slots__ = ()


class ChattyInt(int):
    """A number whose repr is text."""

    def __repr__(self) -> str:
        return TEXT

    __str__ = __repr__


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

    def installed(level: int = logging.INFO) -> io.StringIO:
        stream = io.StringIO()
        safe.install(stream, level=level)
        return stream

    return installed


def matches(out: io.StringIO, rest: str, level: str = "INFO") -> bool:
    """Return whether everything written is one line with the level and the rest given."""
    return re.fullmatch(LINE.format(level=level, rest=re.escape(rest)), out.getvalue()) is not None


def test_ec1_an_event_with_fields_is_one_line_in_the_order_given(start: Callable[..., io.StringIO]) -> None:
    out = start()
    safe.event(Sample.DONE, pages=3, seconds=0.5, cached=False)
    assert matches(out, "Sample.DONE pages=3 seconds=0.5 cached=False"), out.getvalue()


@pytest.mark.parametrize(
    ("value", "shown"),
    [(0, "0"), (-7, "-7"), (2**62, "4611686018427387904"), (1.25, "1.25"), (True, "True"), (False, "False"), (None, "None")],
)
def test_ec2_a_number_a_bool_and_none_are_written_as_python_writes_them(
    start: Callable[..., io.StringIO], value: object, shown: str
) -> None:
    out = start()
    safe.event(Sample.DONE, value=value)
    assert matches(out, f"Sample.DONE value={shown}"), out.getvalue()


@pytest.mark.parametrize(
    ("value", "shown"),
    [
        (TEXT, f"<str:{len(TEXT)}>"),
        ("", "<str:0>"),
        (TEXT.encode("utf-8"), f"<bytes:{len(TEXT.encode('utf-8'))}>"),
        ([TEXT], "<list>"),
        ({TEXT: TEXT}, "<dict>"),
        ((TEXT,), "<tuple>"),
        (Path(TEXT), f"<{type(Path()).__name__}>"),
        (ValueError(TEXT), "<ValueError>"),
        (Chatty(), "<Chatty>"),
        (ChattyInt(5), "<ChattyInt>"),
        (ChattyStr(TEXT), "<ChattyStr>"),
        (Other.DONE, "<Other>"),
    ],
)
def test_ec3_any_other_value_is_a_mark_with_the_name_of_its_type(start: Callable[..., io.StringIO], value: object, shown: str) -> None:
    out = start()
    safe.event(Sample.DONE, value=value)
    assert matches(out, f"Sample.DONE value={shown}"), out.getvalue()
    assert "יעקב" not in out.getvalue()
    assert "John" not in out.getvalue()


def test_ec4_the_level_is_info_unless_one_is_given(start: Callable[..., io.StringIO]) -> None:
    out = start()
    safe.event(Sample.FAILED, level=logging.ERROR, tries=2)
    assert matches(out, "Sample.FAILED tries=2", level="ERROR"), out.getvalue()


def test_ec4_a_line_below_the_installed_level_is_not_written(logging_restored: None) -> None:
    stream = io.StringIO()
    safe.install(stream, level=logging.WARNING)
    safe.event(Sample.DONE, pages=3)
    safe.event(Sample.FAILED, level=logging.WARNING)
    assert matches(stream, "Sample.FAILED", level="WARNING"), stream.getvalue()


def test_ec5_an_event_with_no_fields_is_its_name_alone(start: Callable[..., io.StringIO]) -> None:
    out = start()
    safe.event(Sample.DONE)
    assert matches(out, "Sample.DONE"), out.getvalue()


@pytest.mark.parametrize("name", [TEXT, "sample.done", "Sample.DONE", Other.DONE, None, 3])
def test_e1_what_is_no_member_of_an_event_class_is_refused_without_its_text(start: Callable[..., io.StringIO], name: object) -> None:
    out = start()
    with pytest.raises(TypeError) as raised:
        safe.event(name)
    assert "יעקב" not in str(raised.value)
    assert "sample.done" not in str(raised.value)
    assert out.getvalue() == ""


@pytest.mark.parametrize("key", [TEXT, "Pages", "two words", "", "1st", "naïve", "שם"])
def test_e2_a_key_that_is_no_lower_case_identifier_is_refused_without_its_text(start: Callable[..., io.StringIO], key: str) -> None:
    out = start()
    with pytest.raises(ValueError, match="key") as raised:
        safe.event(Sample.DONE, **{key: 1})
    assert key == "" or key not in str(raised.value)
    assert out.getvalue() == ""


@pytest.mark.parametrize(
    ("send", "level"),
    [
        (lambda: logging.info(TEXT), "INFO"),
        (lambda: logging.info("%s", TEXT), "INFO"),
        (lambda: logging.getLogger("some.library").warning("found %s in %s", TEXT, "file"), "WARNING"),
        (lambda: logging.getLogger(TEXT).info("plain"), "INFO"),
        (lambda: logging.info("plain", extra={"note": TEXT}), "INFO"),
        (lambda: logging.info("sample.done"), "INFO"),
        (lambda: logging.debug(TEXT), "DEBUG"),
        (lambda: logging.critical(TEXT), "CRITICAL"),
        (lambda: logging.info(Other.DONE), "INFO"),
        (lambda: logging.info(b"bytes of text"), "INFO"),
    ],
)
def test_ec6_a_record_of_a_standard_logging_call_is_a_fixed_mark(
    start: Callable[..., io.StringIO], send: Callable[[], None], level: str
) -> None:
    out = start(logging.DEBUG)
    send()
    assert matches(out, "<withheld>", level=level), out.getvalue()


def test_ec7_a_record_with_an_exception_names_its_type_only(start: Callable[..., io.StringIO]) -> None:
    out = start()
    try:
        raise KeyError(TEXT)
    except KeyError:
        logging.exception("failed on %s", TEXT)
    assert matches(out, "<withheld> raised=KeyError", level="ERROR"), out.getvalue()


def test_ec8_the_fields_attribute_without_an_event_is_still_a_fixed_mark(start: Callable[..., io.StringIO]) -> None:
    out = start()
    logging.info(TEXT, extra={"ploni_fields": {"pages": 3}})
    assert matches(out, "<withheld>"), out.getvalue()


def test_ec9_an_event_sent_by_a_standard_call_with_forged_fields_shows_no_text(start: Callable[..., io.StringIO]) -> None:
    out = start()
    logging.info(Sample.DONE, extra={"ploni_fields": {TEXT: 1, "note": TEXT, "pages": 3}})
    assert matches(out, f"Sample.DONE <key>=1 note=<str:{len(TEXT)}> pages=3"), out.getvalue()


def test_ec10_install_replaces_the_handlers_of_the_root_logger(logging_restored: None) -> None:
    root = logging.getLogger()
    root.addHandler(logging.StreamHandler(io.StringIO()))
    handler = safe.install(io.StringIO(), level=logging.WARNING)
    assert root.handlers == [handler]
    assert root.level == logging.WARNING


def test_ec11_install_takes_the_handlers_of_named_loggers_away(logging_restored: None) -> None:
    leaked = io.StringIO()
    library = logging.getLogger("some.library")
    library.addHandler(logging.StreamHandler(leaked))
    library.propagate = False
    stream = io.StringIO()
    safe.install(stream)
    library.warning(TEXT)
    assert leaked.getvalue() == ""
    assert matches(stream, "<withheld>", level="WARNING"), stream.getvalue()


def test_ec12_a_warning_goes_through_the_handler(start: Callable[..., io.StringIO], capsys: pytest.CaptureFixture[str]) -> None:
    out = start()
    warnings.warn(TEXT, UserWarning, stacklevel=1)
    assert "<withheld>" in out.getvalue()
    assert "יעקב" not in out.getvalue()
    assert capsys.readouterr().err == ""


def test_ec13_install_twice_leaves_one_handler(logging_restored: None) -> None:
    first, second = io.StringIO(), io.StringIO()
    safe.install(first)
    safe.install(second)
    safe.event(Sample.DONE)
    assert first.getvalue() == ""
    assert matches(second, "Sample.DONE"), second.getvalue()


def test_b1_a_stream_that_cannot_be_written_to(logging_restored: None, capsys: pytest.CaptureFixture[str]) -> None:
    stream = io.StringIO()
    safe.install(stream)
    stream.close()
    safe.event(Sample.DONE, pages=3)
    logging.info(TEXT)
    logging.info("%d", TEXT)
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


def test_b2_the_event_class_has_no_member_of_its_own() -> None:
    assert list(safe.Event) == []
    assert isinstance(Sample.DONE, safe.Event)


def test_a1_a_message_whose_formatting_fails(start: Callable[..., io.StringIO], capsys: pytest.CaptureFixture[str]) -> None:
    out = start()
    logging.info("%d pages", TEXT)
    logging.info("%s and %s", TEXT)
    assert out.getvalue().count("<withheld>") == 2
    assert "יעקב" not in out.getvalue()
    assert capsys.readouterr().err == ""


def test_e2_one_bad_key_among_good_ones_is_refused(start: Callable[..., io.StringIO]) -> None:
    out = start()
    with pytest.raises(ValueError, match="key"):
        safe.event(Sample.DONE, **{"pages": 1, TEXT: 2, "seconds": 3})
    assert out.getvalue() == ""


def test_ec4_install_writes_from_info_up_unless_a_level_is_given(logging_restored: None) -> None:
    stream = io.StringIO()
    safe.install(stream)
    safe.event(Sample.DONE, level=logging.DEBUG)
    safe.event(Sample.FAILED)
    assert matches(stream, "Sample.FAILED"), stream.getvalue()


def test_ec7_exc_info_asked_for_where_no_exception_is_being_handled(start: Callable[..., io.StringIO]) -> None:
    out = start()
    logging.error(TEXT, exc_info=True)
    assert matches(out, "<withheld>", level="ERROR"), out.getvalue()


def test_ec9_an_event_sent_by_a_standard_call_without_fields_is_its_name_alone(start: Callable[..., io.StringIO]) -> None:
    out = start()
    logging.info(Sample.DONE)
    logging.info(Sample.FAILED, extra={"ploni_fields": TEXT})
    assert out.getvalue().count("\n") == 2
    assert out.getvalue().splitlines()[0].endswith(" Sample.DONE")
    assert out.getvalue().splitlines()[1].endswith(" Sample.FAILED")


def by_hand(level_name: object, file_name: object, line: object) -> logging.LogRecord:
    """Return a record built without a logging call, with the three parts given."""
    record = logging.LogRecord("library", logging.INFO, "path/module.py", 1, TEXT, None, None)
    record.levelname, record.filename, record.lineno = level_name, file_name, line
    return record


@pytest.mark.parametrize(
    ("level_name", "file_name", "line", "head"),
    [
        (TEXT, TEXT, TEXT, "LEVEL <file>:0"),
        ("Level 25", "two words.py", 7.5, "LEVEL <file>:0"),
        ("info", "../module.py", True, "LEVEL <file>:0"),
        ("INFO", "module.py and more", 3, "INFO <file>:3"),
        ("WARNING", "tokenization_utils_base.py", 812, "WARNING tokenization_utils_base.py:812"),
        ("CRITICAL", "<stdin>", 3, "CRITICAL <stdin>:3"),
        ("DEBUG", "window.pyw", 0, "DEBUG window.pyw:0"),
        ("ERROR", None, None, "ERROR <file>:0"),
    ],
)
def test_a3_a_record_built_by_hand_shows_only_what_has_the_shape_of_code(
    start: Callable[..., io.StringIO], level_name: object, file_name: object, line: object, head: str
) -> None:
    out = start(logging.DEBUG)
    logging.getLogger().handle(by_hand(level_name, file_name, line))
    assert re.fullmatch(rf"\d{{4}}-\d\d-\d\dT\d\d:\d\d:\d\d {re.escape(head)} <withheld>\n", out.getvalue()), out.getvalue()


@pytest.mark.parametrize("key", ["level", "extra", "msg", "name", "exc_info", "args", "stacklevel"])
def test_a2_a_field_named_like_an_argument_of_the_logging_call(start: Callable[..., io.StringIO], key: str) -> None:
    out = start()
    if key == "level":
        safe.event(Sample.DONE, level=logging.WARNING)
        assert matches(out, "Sample.DONE", level="WARNING"), out.getvalue()
    else:
        safe.event(Sample.DONE, **{key: 4})
        assert matches(out, f"Sample.DONE {key}=4"), out.getvalue()


class LoudStr(str):
    """A string that shows the text of a document when it is written, whatever it holds."""

    __slots__ = ()

    def __str__(self) -> str:
        return TEXT

    __repr__ = __str__

    def __format__(self, spec: str) -> str:
        return TEXT


class EqualsAll(type):
    """A metaclass whose classes claim to equal every other class."""

    def __eq__(cls, other: object) -> bool:
        return True

    __hash__ = type.__hash__


class Claims(metaclass=EqualsAll):
    """A value whose class claims to be `int`, and whose repr is text."""

    def __repr__(self) -> str:
        return TEXT


class Renamed(type):
    """A metaclass that gives its classes the text of a document as their name."""

    @property
    def __name__(cls) -> str:
        return TEXT


@pytest.mark.parametrize(
    ("value", "written"),
    [
        (None, "None"),
        (True, "True"),
        (0, "0"),
        (-12, "-12"),
        (2**63 - 1, "9223372036854775807"),
        (-(2**63) + 1, "-9223372036854775807"),
        (2**63, "<int>"),
        (-(2**63), "<int>"),
        pytest.param(10**5000, "<int>", id="a number of 5001 digits"),
        (0.25, "0.25"),
        (float("inf"), "inf"),
        (float("nan"), "nan"),
        ("12345", "<str:5>"),
        ("a", "<str:1>"),
        ("", "<str:0>"),
        (b"12", "<bytes:2>"),
        (bytearray(b"12"), "<bytearray>"),
        (decimal.Decimal("1.5"), "<Decimal>"),
        (fractions.Fraction(1, 3), "<Fraction>"),
        (1 + 2j, "<complex>"),
        (LoudStr("12"), "<LoudStr>"),
        (Claims(), "<Claims>"),
        (Renamed("Thing", (), {})(), "<Thing>"),
        (type(TEXT, (), {})(), "<value>"),
        (type("two words", (), {})(), "<value>"),
        (type("a\nb", (), {})(), "<value>"),
    ],
)
def test_shown_writes_numbers_and_marks_everything_else(value: object, written: str) -> None:
    assert safe.shown(value) == written


@pytest.mark.parametrize("key", ["a", "pages", "a1", "a_b", "seconds_total"])
def test_is_key_takes_a_lower_case_identifier(key: str) -> None:
    assert safe._is_key(key)


@pytest.mark.parametrize("key", ["_x", "aB", "a-b", "a.b", "pages\n", "", "1a", "two words", "שם", 1, None, b"pages", LoudStr("pages")])
def test_is_key_refuses_every_other_shape_and_every_other_type(key: object) -> None:
    assert not safe._is_key(key)


@pytest.mark.parametrize("name", ["fusion.py", "window.pyw", "a_1.py", "<string>", "<stdin>"])
def test_is_file_takes_the_name_of_a_source_file(name: str) -> None:
    assert safe._is_file(name)


@pytest.mark.parametrize(
    "name",
    ["Jacob Cohen.py", "יעקב.py", "<two words>", "<>", "<Stdin>", "x.pyc", "path/x.py", "x.py\n", ".py", "", None, 3, LoudStr("x.py")],
)
def test_is_file_refuses_every_other_shape_and_every_other_type(name: object) -> None:
    assert not safe._is_file(name)


@pytest.mark.parametrize("name", ["Sample", "DONE", "_x", "A1", "a"])
def test_code_name_gives_a_name_of_code_back(name: str) -> None:
    assert safe._code_name(name, "<mark>") == name


@pytest.mark.parametrize("name", ["two words", "יעקב", "a.b", "a\nb", "a-b", "1a", "", None, 3, LoudStr("Sample")])
def test_code_name_gives_the_mark_for_anything_else(name: object) -> None:
    assert safe._code_name(name, "<mark>") == "<mark>"


def test_a4_a_key_of_a_class_of_its_own_is_refused_by_event(start: Callable[..., io.StringIO]) -> None:
    out = start()
    with pytest.raises(ValueError, match="key"):
        safe.event(Sample.DONE, **{LoudStr("pages"): 1})
    assert out.getvalue() == ""


def test_a4_a_key_of_a_class_of_its_own_in_forged_fields_is_a_mark(start: Callable[..., io.StringIO]) -> None:
    out = start()
    logging.info(Sample.DONE, extra={"ploni_fields": {LoudStr("pages"): 1, 7: 2, "seconds": 3}})
    assert matches(out, "Sample.DONE <key>=1 <key>=2 seconds=3"), out.getvalue()


def test_a4_a_level_name_and_a_file_name_of_a_class_of_their_own_are_marks(start: Callable[..., io.StringIO]) -> None:
    out = start()
    logging.getLogger().handle(by_hand(LoudStr("INFO"), LoudStr("module.py"), 3))
    assert out.getvalue().endswith(" LEVEL <file>:3 <withheld>\n"), out.getvalue()
    assert "יעקב" not in out.getvalue()


def with_exc_info(exc_info: object) -> logging.LogRecord:
    """Return a record built by hand that carries the given `exc_info`."""
    record = by_hand("ERROR", "module.py", 5)
    record.exc_info = exc_info
    return record


@pytest.mark.parametrize(
    ("exc_info", "ending"),
    [
        ((KeyError, KeyError("x"), None), " raised=KeyError"),
        ((type(TEXT, (Exception,), {}), None, None), " raised=<name>"),
        ((type("a\nb", (Exception,), {}), None, None), " raised=<name>"),
        ((Renamed("Fine", (Exception,), {}), None, None), " raised=Fine"),
        ((Chatty(), None, None), " raised=<name>"),
        ((1,), " raised=<name>"),
        ((TEXT, None, None), " raised=<name>"),
        ((None, None, None), ""),
        ((), ""),
        (True, ""),
        (None, ""),
    ],
)
def test_a5_what_stands_in_exc_info_is_named_only_when_it_is_a_class_with_a_name_of_code(
    start: Callable[..., io.StringIO], exc_info: object, ending: str
) -> None:
    out = start()
    logging.getLogger().handle(with_exc_info(exc_info))
    assert out.getvalue().endswith(f" ERROR module.py:5 <withheld>{ending}\n"), out.getvalue()
    assert out.getvalue().count("\n") == 1


def test_a6_an_event_made_from_data_shows_no_name_that_is_not_a_name_of_code(start: Callable[..., io.StringIO]) -> None:
    out = start()
    made = safe.Event(TEXT, {TEXT: 1, "first\nsecond": 2, "FINE": 3})
    for member in made:
        safe.event(member, pages=1)
    assert [line.split(" ", 3)[3] for line in out.getvalue().splitlines()] == [
        "<name>.<name> pages=1",
        "<name>.<name> pages=1",
        "<name>.FINE pages=1",
    ]


def test_a6_an_event_with_a_name_of_its_own_making_shows_the_name_it_was_defined_with(start: Callable[..., io.StringIO]) -> None:
    class Sly(safe.Event):
        """An event class that answers with text when asked for a member's name."""

        DONE = enum.auto()

        @property
        def name(self) -> str:
            return TEXT

    out = start()
    safe.event(Sly.DONE)
    assert matches(out, "Sly.DONE"), out.getvalue()


def test_a6_an_event_that_was_renamed_after_it_was_made_shows_a_mark(start: Callable[..., io.StringIO]) -> None:
    class Later(safe.Event):
        """An event class whose member is given another name at run time."""

        DONE = enum.auto()

    Later.DONE._name_ = TEXT
    out = start()
    safe.event(Later.DONE)
    assert matches(out, "Later.<name>"), out.getvalue()


def test_a7_fields_that_are_a_mapping_of_a_class_of_its_own_are_not_read(start: Callable[..., io.StringIO]) -> None:
    class Talking(dict):
        """A mapping that hands out text when its items are asked for."""

        def items(self):
            return [(TEXT, TEXT)]

    out = start()
    logging.info(Sample.DONE, extra={"ploni_fields": Talking(pages=3)})
    assert matches(out, "Sample.DONE"), out.getvalue()


@pytest.mark.parametrize("created", [TEXT, None, float("nan"), float("inf"), 1e30, -1e30, 3])
def test_a8_a_record_whose_time_is_no_time_is_still_written(start: Callable[..., io.StringIO], created: object) -> None:
    out = start()
    record = by_hand("INFO", "module.py", 3)
    record.created = created
    logging.getLogger().handle(record)
    assert out.getvalue() == "0000-00-00T00:00:00 INFO module.py:3 <withheld>\n"


@pytest.mark.parametrize("line", [-1, 2**63, 10**5000], ids=["negative", "2**63", "a number of 5001 digits"])
def test_a8_a_line_number_that_no_file_has_is_written_as_zero(start: Callable[..., io.StringIO], line: int) -> None:
    out = start()
    logging.getLogger().handle(by_hand("INFO", "module.py", line))
    assert out.getvalue().endswith(" INFO module.py:0 <withheld>\n"), out.getvalue()


def test_a9_a_whole_number_too_long_to_write_is_a_mark_and_the_line_is_kept(start: Callable[..., io.StringIO]) -> None:
    out = start()
    safe.event(Sample.DONE, pages=10**5000, seconds=2)
    assert matches(out, "Sample.DONE pages=<int> seconds=2"), out.getvalue()


def test_ec14_the_level_given_to_install_holds_for_a_logger_with_a_lower_level_of_its_own(logging_restored: None) -> None:
    stream = io.StringIO()
    safe.install(stream, level=logging.WARNING)
    chatty = logging.getLogger("some.chatty.library")
    chatty.setLevel(logging.DEBUG)
    logging.getLogger(safe.LOGGER).setLevel(logging.DEBUG)
    chatty.debug(TEXT)
    chatty.info(TEXT)
    safe.event(Sample.DONE, level=logging.DEBUG)
    safe.event(Sample.FAILED, level=logging.WARNING)
    assert matches(stream, "Sample.FAILED", level="WARNING"), stream.getvalue()


def test_ec15_a_logger_that_hands_nothing_up_and_has_no_handler_writes_to_the_stream(
    start: Callable[..., io.StringIO], capsys: pytest.CaptureFixture[str]
) -> None:
    out = start()
    lonely = logging.getLogger("some.lonely.library")
    lonely.propagate = False
    lonely.warning(TEXT)
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")
    assert matches(out, "<withheld>", level="WARNING"), out.getvalue()


def test_ec16_a_named_logger_that_hands_its_records_up_loses_its_own_handler_too(logging_restored: None) -> None:
    leaked = io.StringIO()
    library = logging.getLogger("some.other.library")
    library.addHandler(logging.StreamHandler(leaked))
    stream = io.StringIO()
    safe.install(stream)
    library.warning(TEXT)
    assert leaked.getvalue() == ""
    assert library.handlers == []
    assert stream.getvalue().count("\n") == 1


def test_ec17_the_time_of_a_record_is_its_local_time_to_the_second(start: Callable[..., io.StringIO]) -> None:
    out = start()
    record = by_hand("INFO", "module.py", 3)
    record.created = 1_700_000_000.75
    logging.getLogger().handle(record)
    expected = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(1_700_000_000.75))
    assert out.getvalue() == f"{expected} INFO module.py:3 <withheld>\n"


@pytest.mark.parametrize("level", ["WARNING", TEXT, 20.0, True, None])
def test_e3_install_refuses_a_level_that_is_no_whole_number_before_it_changes_anything(
    logging_restored: None, level: object
) -> None:
    root = logging.getLogger()
    before = (list(root.handlers), root.level, logging.lastResort)
    with pytest.raises(TypeError) as raised:
        safe.install(io.StringIO(), level=level)
    assert "יעקב" not in str(raised.value)
    assert (list(root.handlers), root.level, logging.lastResort) == before


@pytest.mark.parametrize("level", ["WARNING", TEXT, 20.0, True, None])
def test_e3_event_refuses_a_level_that_is_no_whole_number(start: Callable[..., io.StringIO], level: object) -> None:
    out = start()
    with pytest.raises(TypeError) as raised:
        safe.event(Sample.DONE, level=level)
    assert "יעקב" not in str(raised.value)
    assert out.getvalue() == ""


def test_a10_an_event_sent_by_a_standard_call_with_arguments_shows_none_of_them(start: Callable[..., io.StringIO]) -> None:
    out = start()
    logging.info(Sample.DONE, TEXT, TEXT)
    assert matches(out, "Sample.DONE"), out.getvalue()


def test_a10_a_field_may_be_named_member(start: Callable[..., io.StringIO]) -> None:
    out = start()
    safe.event(Sample.DONE, member=3)
    assert matches(out, "Sample.DONE member=3"), out.getvalue()


def test_install_makes_its_handler_the_one_of_last_resort_and_gives_it_the_level(logging_restored: None) -> None:
    handler = safe.install(io.StringIO(), level=logging.ERROR)
    assert logging.lastResort is handler
    assert handler.level == logging.ERROR


def test_ec11_a_named_logger_hands_its_records_up_again_whatever_the_last_resort_is(logging_restored: None) -> None:
    # Without this a logger that had stopped handing up would depend on the handler of last resort alone.
    library = logging.getLogger("some.closed.library")
    library.propagate = False
    stream, elsewhere = io.StringIO(), io.StringIO()
    safe.install(stream)
    logging.lastResort = logging.StreamHandler(elsewhere)
    library.warning(TEXT)
    assert elsewhere.getvalue() == ""
    assert matches(stream, "<withheld>", level="WARNING"), stream.getvalue()
