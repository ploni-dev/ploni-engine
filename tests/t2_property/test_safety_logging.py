"""The invariant of ploni/safety/logging.py over generated text: what is written does not depend on the text.

Why: the unit tests and the canary try one text. A text with a special shape could behave in
another way: one that looks like a format string, like a level name, like the name of a
source file, like a number, or one that holds a line break. `PROCESS.md` section 4.3 asks for a
test over generated input for any invariant that can be stated over it, and this module has
one.

The invariant: for every way a text can reach the logging system, the line that is written is
the same for every text, once the numbers in it are masked (the time, the line number, the
length of a string). And the text itself is not in the line.

Generated input: TEXTS are 640 texts: 600 from a seeded generator, Hebrew, Latin, digits and
punctuation in runs of 4 to 40 characters, and 40 of special shapes. WAYS are 20 ways a text
can reach the logging system through a call that takes a text; most are ways of the canary
test, which also has ways that take none (a warning, a record built by hand, a logger that
hands nothing up). 640 texts x 20 ways = 12,800 cases, in two tests per way.

Not covered here, and said in the module: a text with the shape of a name of code, where a
name of code stands (the name of an event, of a type, of a source file, a field key). Those are
tested by shape in tests/t1_unit/test_safety_logging.py.
"""

import enum
import io
import logging
import random
import re
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from ploni.safety import logging as safe
from tests import logging_state

HEBREW = "אבגדהוזחטיכלמנסעפצקרשתךםןףץ"
LATIN = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
MARKS = " -_.,:;'\"()[]{}<>%$#@!?/\\|=+*&^~`\n\t־׳״"
SPECIAL = [
    "%s", "%d", "%(name)s", "{}", "{0}", "{name}", "%", "%%", "INFO", "DEBUG", "WARNING", "LEVEL", "<withheld>", "<stdin>",
    "<string>", "module.py", "fusion.py:88", "<key>", "<name>", "pages=3", "Step.DONE", "Step.DONE pages=3", "None", "True",
    "0", "-1", "3.5", "1e5", "nan", "\n", "\r\n", "first\nsecond", "\x00", "\x1b[31m", "a" * 500, "א" * 500, "ploni_fields",
    "__name__", "raised=KeyError", " ",
]  # fmt: skip
# CLAUDE.md, Tests: an invariant is held over 500 generated cases.
GENERATED = 600


def texts() -> list[str]:
    """Return the special shapes and GENERATED texts from a generator with a fixed seed."""
    rng = random.Random("ploni-safety-logging")  # noqa: S311 seeded on purpose, so the cases are the same on every run
    made = []
    for _ in range(GENERATED):
        alphabet = rng.choice([HEBREW, LATIN, "0123456789", HEBREW + LATIN + MARKS, HEBREW + MARKS, LATIN + MARKS])
        made.append("".join(rng.choice(alphabet) for _ in range(rng.randint(4, 40))))
    return SPECIAL + made


TEXTS = texts()


class Step(safe.Event):
    """Events of the tests."""

    DONE = enum.auto()


class Loud:
    """An object whose str and repr are a text."""

    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:
        return self.text

    __str__ = __repr__


def raising(text: str) -> None:
    """Log from inside an except block, the text in the error and in the message."""
    try:
        raise KeyError(text)
    except KeyError:
        logging.getLogger("library").exception("failed on %s", text)


WAYS: dict[str, Callable[[str], object]] = {
    "message": lambda text: logging.info(text),
    "argument": lambda text: logging.warning("found %s", text),
    "two arguments for one place": lambda text: logging.warning("found %s", text, text),
    "mapping": lambda text: logging.info("found %(name)s", {"name": text}),
    "extra": lambda text: logging.info("plain", extra={"note": text}),
    "logger name": lambda text: logging.getLogger(text).error("plain"),
    "exception": raising,
    "stack_info": lambda text: logging.info(text, stack_info=True),
    "object": lambda text: logging.info(Loud(text)),
    "bytes": lambda text: logging.info(text.encode("utf-8", "replace")),
    "forged fields": lambda text: logging.info(text, extra={"ploni_fields": {"pages": 3}}),
    "forged value": lambda text: logging.info(Step.DONE, extra={"ploni_fields": {"note": text}}),
    "event argument": lambda text: logging.info(Step.DONE, text),
    "field str": lambda text: safe.event(Step.DONE, value=text),
    "field bytes": lambda text: safe.event(Step.DONE, value=text.encode("utf-8", "replace")),
    "field list": lambda text: safe.event(Step.DONE, value=[text]),
    "field path": lambda text: safe.event(Step.DONE, value=Path("folder") / "name" if "\x00" in text else Path(text)),
    "field exception": lambda text: safe.event(Step.DONE, value=ValueError(text)),
    "field object": lambda text: safe.event(Step.DONE, value=Loud(text)),
    "exception class named from the text": lambda text: logging.error("x", exc_info=(type(text.replace(chr(0), "?") + " !", (Exception,), {}), None, None)),
}


@pytest.fixture
def logging_restored() -> Iterator[None]:
    """Put the logging state of the process back when the test is over."""
    with logging_state.restored():
        yield


def line(way: Callable[[str], object], text: str, stream: io.StringIO) -> str:
    """Return what one way writes for one text, with every run of digits masked."""
    stream.seek(0)
    stream.truncate()
    way(text)
    return re.sub(r"\d+", "N", stream.getvalue())


@pytest.mark.parametrize("name", WAYS)
def test_what_is_written_is_the_same_for_every_text(logging_restored: None, name: str) -> None:
    stream = io.StringIO()
    safe.install(stream, level=logging.DEBUG)
    way = WAYS[name]
    expected = line(way, "reference text", stream)
    assert expected.count("\n") == 1, expected
    different = [text for text in TEXTS if line(way, text, stream) != expected]
    assert different == []


@pytest.mark.parametrize("name", WAYS)
def test_the_text_is_not_in_what_is_written(logging_restored: None, name: str) -> None:
    stream = io.StringIO()
    safe.install(stream, level=logging.DEBUG)
    WAYS[name]("reference text")
    # What the line holds for any text: its level, the mark, the name of the event.
    fixed = stream.getvalue()
    found = []
    for text in TEXTS:
        stream.seek(0)
        stream.truncate()
        WAYS[name](text)
        # A text of three characters or fewer can stand in a line by chance: a digit, a colon.
        if len(text) > 3 and text in stream.getvalue() and text not in fixed:
            found.append(text)
    assert found == []


def test_the_sample_is_over_the_minimum_for_an_invariant() -> None:
    # CLAUDE.md, Tests: an invariant is held over 500 generated cases.
    assert len(TEXTS) >= 500
    assert len(set(TEXTS)) >= 500
    assert len(TEXTS) * len(WAYS) >= 5000
