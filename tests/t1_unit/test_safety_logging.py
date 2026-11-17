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

The Hebrew axes of the test-matrix skill apply as input only: text in Hebrew, in Latin letters
and mixed is what must not come out; the canary test carries them. The document-structure axes
do not apply: no document is handled.
"""

import enum
import io
import logging
import re
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
    [(0, "0"), (-7, "-7"), (10**20, "100000000000000000000"), (1.25, "1.25"), (True, "True"), (False, "False"), (None, "None")],
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
        safe.event(name)  # type: ignore[arg-type]
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
    "send",
    [
        lambda: logging.info(TEXT),
        lambda: logging.info("%s", TEXT),
        lambda: logging.getLogger("some.library").warning("found %s in %s", TEXT, "file"),
        lambda: logging.getLogger(TEXT).info("plain"),
        lambda: logging.info("plain", extra={"note": TEXT}),
        lambda: logging.info("sample.done"),
    ],
)
def test_ec6_a_record_of_a_standard_logging_call_is_a_fixed_mark(start: Callable[..., io.StringIO], send: object) -> None:
    out = start()
    send()  # type: ignore[operator]
    level = "WARNING" if "WARNING" in out.getvalue() else "INFO"
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
    assert capsys.readouterr().err == ""


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
    record.levelname, record.filename, record.lineno = level_name, file_name, line  # type: ignore[assignment]
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
