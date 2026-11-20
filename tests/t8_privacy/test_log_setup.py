"""No module of ploni/ outside ploni/safety/ sets up a log handler or log configuration of its own.

Why: `CLAUDE.md`, Hard constraints: "No document text in logs or temp files." The filter of
`ploni/safety/logging.py` is the one way a log line is written, and its Known limits name the
ways around it: a handler of one's own, a logger that hands nothing up, configuration done
again. The closing test of Phase 0 measured one of them (#150): a module of ploni/ with a
handler of its own and `propagate = False`, logging its argument, passed every check. Achia
chose on 2026-11-20 "Build the check first (Recommended)": "A small test that product code
outside ploni/safety/ never sets up its own log handler or log config." This is that test.

The rule: a file judged names none of the setup names (SETUP_NAMES), no name ending in
`Handler`, holds no string that is one of them, and imports neither `logging.config` nor
`logging.handlers`. A name is refused wherever it stands, read or written, called or not:
product code has no use for any of them, and the sanctioned call is `event`.

Test matrix:

Equivalence classes:
  EC1  a module that logs through `event`, and one that never logs        no line
  EC2  each setup name, as an attribute (`logging.basicConfig()`, `log.addHandler(h)`), as a
       plain name after `from logging import ...`, and named without a call    one line each
  EC3  a name ending in Handler: a handler made (`logging.StreamHandler()`), a handler class
       subclassed (`class Mine(logging.Handler)`), one imported by name     a line
  EC4  each setup attribute assigned, also by `+=`, by an annotated assignment and inside a
       tuple target (`log.propagate = False`, `logging.lastResort = None`,
       `warnings.showwarning = f`, `log.handlers = []`)                    a line
  EC5  an import of `logging.config` or `logging.handlers`, in every form   a line
  EC6  the scope: every file under ploni/ but those under ploni/safety/
  EC7  the repository                                                       no line

Boundaries:
  B1  a setup name in a comment, or inside a longer string (a docstring that says "addHandler") no line
  B2  a name that only holds the word (`HandlerError`, `handler`, `propagated`)    no line
  B3  a setup attribute only read (`if log.propagate:`)    a line: refused too, see the rule

Adversarial:
  A1  the names inside a function, a class, under `if` and `try`             found
  A2  the name as a string: `getattr(log, "addHandler")`, `setattr(log, "propagate", False)` a line
  A3  bad PR 5b of the closing test (#150), word for word                   lines
  A4  `import logging.config as c`, `from logging import handlers as h`     a line

Not applicable: the Hebrew axes and the document axes of the test-matrix skill, as the input
is Python source and no document is handled.

Known limits:
  - Names only. A name built at run time (`getattr(log, "add" + "Handler")`), code given to
    `exec`, or a module that does the setup for the caller is not seen.
  - A plain logging call is not a setup and is not refused here. Before `install` runs, or in
    a process that never calls it, the logging module's last-resort handler prints the message
    of a WARNING or worse to the standard error stream; `install` is what stops that.
  - `warnings.warn` with document text is not a log setup and is not refused here.
  - ploni/safety/ is not judged: it is where the filter lives (Achia's option: "outside
    ploni/safety/").
"""

import ast
from pathlib import Path

import pytest

from tests.project_imports import imported

ROOT = Path(__file__).resolve().parents[2]
# The calls and attributes by which logging is set up or taken apart (the logging module's
# own API), and the attribute by which the warnings module prints (ploni/safety/logging.py,
# Known limits).
SETUP_NAMES = (
    "addHandler",
    "removeHandler",
    "basicConfig",
    "dictConfig",
    "fileConfig",
    "listen",
    "setLoggerClass",
    "setLogRecordFactory",
    "captureWarnings",
    "setFormatter",
    "propagate",
    "handlers",
    "lastResort",
    "showwarning",
)
HANDLER_SUFFIX = "Handler"
# The two modules of the logging package that only set logging up.
SETUP_MODULES = ("logging.config", "logging.handlers")


def setups(source: str, importer: str = "ploni.mod") -> list[str]:
    """Name each line of a source text that sets up logging, as "<line>: <what>"."""
    return []


def judged(root: Path) -> list[Path]:
    """Return the files under ploni/ that the rule judges: all but those under ploni/safety/."""
    return []


def lines(source: str) -> list[int]:
    """Return the line numbers of the lines `setups` names, each once, in order."""
    return sorted({int(line.split(":")[0]) for line in setups(source)})


@pytest.mark.parametrize(
    "source",
    [
        "from ploni.safety.logging import Event, event\n\n\ndef run() -> None:\n    event(Event.DONE, pages=3)\n",
        "def doubled(number: int) -> int:\n    return number * 2\n",
    ],
)
def test_ec1_no_setup(source: str) -> None:
    assert setups(source) == []


@pytest.mark.parametrize("name", SETUP_NAMES)
def test_ec2_each_setup_name_as_an_attribute(name: str) -> None:
    assert lines(f"import logging\n\nlog = logging.getLogger('x')\nlog.{name}\n") == [4]


@pytest.mark.parametrize(
    "source",
    [
        "import logging\n\nlogging.basicConfig(level=logging.INFO)\n",
        "import logging\n\nlog = logging.getLogger('x')\nlog.addHandler(object())\n",
        "from logging import basicConfig\n\nbasicConfig()\n",
        "import logging\n\nsetup = logging.basicConfig\n",
    ],
)
def test_ec2_called_imported_or_named(source: str) -> None:
    assert lines(source)[-1] == source.count("\n")


@pytest.mark.parametrize(
    "source",
    [
        "import logging\n\nhandler = logging.StreamHandler()\n",
        "import logging\n\n\nclass Mine(logging.Handler):\n    pass\n",
        "from logging import FileHandler\n",
    ],
)
def test_ec3_a_handler(source: str) -> None:
    assert lines(source) != []


@pytest.mark.parametrize(
    "statement",
    [
        "log.propagate = False",
        "logging.lastResort = None",
        "warnings.showwarning = print",
        "log.handlers = []",
        "log.handlers += []",
        "log.propagate: bool = False",
        "log.propagate, other = False, 1",
    ],
)
def test_ec4_a_setup_attribute_assigned(statement: str) -> None:
    assert lines(f"import logging\nimport warnings\n\nlog = logging.getLogger('x')\n{statement}\n") == [5]


@pytest.mark.parametrize(
    "statement",
    [
        "import logging.config",
        "import logging.handlers",
        "from logging import config",
        "from logging import handlers",
        "from logging.config import dictConfig",
        "from logging.handlers import RotatingFileHandler",
        "import logging.config as c",
        "from logging import handlers as h",
    ],
)
def test_ec5_and_a4_a_setup_module_imported(statement: str) -> None:
    assert lines(f"{statement}\n") == [1]


def test_ec6_the_scope(tmp_path: Path) -> None:
    for name in ("ploni/a.py", "ploni/detect/b.py", "ploni/safety/logging.py", "ploni/safety/c.py", "scripts/d.py"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("", encoding="utf-8")
    assert sorted(path.relative_to(tmp_path).as_posix() for path in judged(tmp_path)) == [
        "ploni/a.py",
        "ploni/detect/b.py",
    ]


def test_ec7_the_repository() -> None:
    assert judged(ROOT) != []
    found = [
        f"{path.relative_to(ROOT).as_posix()}:{line}"
        for path in judged(ROOT)
        for line in setups(path.read_text(encoding="utf-8"), ".".join(path.relative_to(ROOT).with_suffix("").parts))
    ]
    assert found == []


@pytest.mark.parametrize(
    "source",
    [
        "import logging\n\n# log.addHandler(h) is not done here\n",
        '"""This module never calls addHandler or basicConfig."""\n',
        "message = 'set propagate to False'\n",
    ],
)
def test_b1_a_comment_or_a_longer_string(source: str) -> None:
    assert setups(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "class HandlerError(Exception):\n    pass\n",
        "handler = None\n",
        "propagated = True\n",
        "def handle(record: object) -> None:\n    pass\n",
    ],
)
def test_b2_a_name_that_only_holds_the_word(source: str) -> None:
    assert setups(source) == []


def test_b3_a_setup_attribute_only_read() -> None:
    assert lines("import logging\n\nif logging.getLogger('x').propagate:\n    pass\n") == [3]


@pytest.mark.parametrize(
    "source",
    [
        "import logging\n\n\ndef run() -> None:\n    logging.basicConfig()\n",
        "import logging\n\n\nclass Run:\n    def go(self) -> None:\n        logging.basicConfig()\n",
        "import logging\n\nif True:\n    logging.basicConfig()\n",
        "import logging\n\ntry:\n    pass\nexcept Exception:\n    logging.basicConfig()\n",
    ],
)
def test_a1_anywhere_in_the_file(source: str) -> None:
    assert lines(source) == [source.count("\n")]


@pytest.mark.parametrize(
    "statement",
    ['getattr(log, "addHandler")', 'setattr(log, "propagate", False)', 'vars(log)["handlers"]'],
)
def test_a2_the_name_as_a_string(statement: str) -> None:
    assert lines(f"import logging\n\nlog = logging.getLogger('x')\n{statement}\n") == [4]


# Bad PR 5b of the closing test (#150), as it went green on every check.
BAD_5B = '''"""Bad PR 5b of the Phase 0 closing test: a product line that logs past the filter.

Why: issue #30, finding 2 of the review of 47780be. This file must never merge.
"""

import logging

_LOG = logging.getLogger("ploni.bad_log_leak")
_LOG.propagate = False
_LOG.addHandler(logging.StreamHandler())


def leak(text: str) -> None:
    """Write a text to the log through a handler of its own, past the filter.

    Why: the shape bad PR 5b tests. Contract: any text in, nothing returned.
    """
    _LOG.warning("document text: %s", text)
'''


def test_a3_bad_pr_5b() -> None:
    assert lines(BAD_5B) == [9, 10]
