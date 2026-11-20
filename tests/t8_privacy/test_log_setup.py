"""No module of ploni/ outside ploni/safety/ sets up a log handler or log configuration of its own.

Why: `CLAUDE.md`, Hard constraints: "No document text in logs or temp files." The filter of
`ploni/safety/logging.py` is the one way a log line is written, and its Known limits name the
ways around it: a handler of one's own, a logger that hands nothing up, configuration done
again, the warnings module set back. The closing test of Phase 0 measured one of them (#150):
a module of ploni/ with a handler of its own and `propagate = False`, logging its argument,
passed every check. Achia chose on 2026-11-20 "Build the check first (Recommended)": "A small
test that product code outside ploni/safety/ never sets up its own log handler or log config."
This is that test.

The rule, an allow-list (ALLOWED): a file judged may use the standard `logging` module only for
its level constants, the `warnings` module only for `warn`, and `ploni.safety.logging` only for
`Event`, `event` and `install`. Every other name of the three is refused, however it is reached:
an attribute (`logging.getLogger`), a name imported from it, a submodule (`logging.config`), a
module imported by a call (`importlib.import_module("logging")`), or the module itself handed on
as a value (`getattr(logging, name)`, `x = logging`). Without a logger, a handler class, the
logging module's internals or the filter's own classes, a file has nothing to set up.

That is narrower than the option's words, and each narrowing is Claude's: a plain logging call
is refused too (before `install` runs, the logging module's last-resort handler prints the
message of a WARNING or worse), and the warnings module is held to `warn` (its `catch_warnings`
and `showwarning` take warnings around the filter).

Test matrix:

Equivalence classes:
  EC1  each name of each of the three modules (from `dir` of the module itself), in each way to
       reach it: an attribute of the module imported plain, of the module imported under another
       name, a name imported from it; and for `ploni.safety.logging` also from its package, and
       relative. Refused unless the name is allowed (the literal lists below)    ~600 cases
  EC2  a submodule of `logging`, imported in every form                     a line
  EC3  one of the modules imported by a call with a literal name           a line
  EC4  one of the modules, or a package above it, used as a value         a line
  EC5  the scope: every file under ploni/ but those under ploni/safety/
  EC6  the repository                                                      no line
  EC7  the order of the lines `setups` gives                                by line

Boundaries:
  B1  the allowed names: a level constant given to `event`, `warnings.warn`    no line
  B2  words that only look like logging (`handlers = {...}`, `propagate = True`, a class named
      `MessageHandler`, `ContentHandler` from `xml.sax.handler`, `self.listen()`)    no line
  B3  ploni/safety.py and ploni/detect/safety/x.py are judged: only the folder ploni/safety/ is not

Adversarial:
  A1  bad PR 5b of the closing test (#150), word for word                  refused
  A2  the ways around the filter that the review of c8a6e94 ran, each printing document text
      after `install`: `vars(log).update(...)`, `warnings.catch_warnings`, a patch of
      `Redacting.format`, `logging._handlerList`, a subclass of `logging.Logger`; and
      `logging.Logger.handle`, `logging.Logger.manager`                   refused
  A3  the names inside a function, a class, under `if` and `try`             found

Not applicable: the Hebrew axes and the document axes of the test-matrix skill, as the input
is Python source and no document is handled.

Known limits:
  - Names that code reaches some other way are not seen: code given to `exec`, a module found
    through `sys.modules`, a package above ploni.safety.logging handed on through a name bound
    by assignment. An import whose name is not a literal is reported by
    tests/t8_privacy/test_imports.py.
  - Another library's own helper that sets logging up for its caller (a third-party
    `enable_default_handler()`) is not refused: only the three modules are judged.
  - Writing to the standard streams (`sys.stderr.write`) is not logging and is not refused here;
    `print` is banned under ploni/ by ruff (T201).
  - A name that a file binds to one of the three modules and then binds again to something else
    is judged as the module: refused, the safe side.
  - ploni/safety/ is not judged: it is where the filter lives (Achia's option: "outside
    ploni/safety/").
"""

import ast
import logging
import warnings
from pathlib import Path

import pytest

import ploni.safety.logging
from tests.project_imports import imported

ROOT = Path(__file__).resolve().parents[2]
# The calls and attributes by which logging is set up or taken apart (the logging module's
# own API), and the attribute by which the warnings module prints (ploni/safety/logging.py,
# Known limits). `addHandler` and `removeHandler` are refused by HANDLER_SUFFIX.
SETUP_NAMES = (
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
# The module of the logging package that only sets logging up. Its other one, `logging.handlers`,
# is refused by its name, `handlers`, in SETUP_NAMES.
SETUP_MODULES = ("logging.config",)


def _is_setup(name: str) -> bool:
    """Say whether a name is a setup name or the name of a handler."""
    return name in SETUP_NAMES or name.endswith(HANDLER_SUFFIX)


def _names(node: ast.AST) -> list[str]:
    """Return the names a node holds where code names a thing, and the text of a string."""
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, ast.alias):
        return [node.name.rsplit(".", 1)[-1]]
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    return []


def setups(source: str, importer: str = "ploni.mod", is_package: bool = False) -> list[str]:
    """Name each line of a source text that sets up logging, as "<line>: <what>".

    Why: the rule of this file, apart from where the source comes from.

    Contract: `importer` is the dotted name of the module, for a relative import. A line
    holding several setups is named once for each; the lines are in order.
    """
    found = [
        (node.lineno, f"names {name}")
        for node in ast.walk(ast.parse(source))
        for name in _names(node)
        if _is_setup(name)
    ]
    found += [(line, f"imports {module}") for line, module in imported(source, importer) if module in SETUP_MODULES]
    return [f"{line}: {what}" for line, what in sorted(found)]


def judged(root: Path) -> list[Path]:
    """Return the files under ploni/ that the rule judges: all but those under ploni/safety/."""
    return sorted(
        path for path in (root / "ploni").rglob("*.py") if path.relative_to(root).parts[:2] != ("ploni", "safety")
    )


def lines(source: str, importer: str = "ploni.mod") -> list[int]:
    """Return the line numbers of the lines `setups` names, each once, in order."""
    return sorted({int(line.split(":")[0]) for line in setups(source, importer)})


# The names each module allows, written out here and not taken from ALLOWED, so that a name
# dropped from ALLOWED, or added to it, turns a case red.
LEVELS = ("CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "NOTSET")
EXPECTED_ALLOWED = {"logging": LEVELS, "warnings": ("warn",), "ploni.safety.logging": ("Event", "event", "install")}
MODULES = {"logging": logging, "warnings": warnings, "ploni.safety.logging": ploni.safety.logging}


def forms(module: str, name: str) -> list[tuple[str, int]]:
    """Return the ways to reach a name of a module, each as (source, the line that reaches it)."""
    alias = "m"
    found = [
        (f"import {module} as {alias}\n{alias}.{name}\n", 2),
        (f"import {module}\n{module}.{name}\n", 2),
        (f"from {module} import {name}\n", 1),
    ]
    if module == "ploni.safety.logging":
        found += [
            (f"from ploni.safety import logging\nlogging.{name}\n", 2),
            (f"from ..safety import logging as {alias}\n{alias}.{name}\n", 2),
        ]
    return found


CASES = [
    pytest.param(source, line, name in EXPECTED_ALLOWED[module], id=f"{module}.{name}-{index}")
    for module, value in MODULES.items()
    for name in sorted(dir(value))
    for index, (source, line) in enumerate(forms(module, name))
]


@pytest.mark.parametrize(("source", "line", "allowed"), CASES)
def test_ec1_each_name_of_each_module_in_each_form(source: str, line: int, allowed: bool) -> None:
    assert lines(source, "ploni.detect.fusion") == ([] if allowed else [line])


def test_ec1_the_cases_are_many_and_every_allowed_name_exists() -> None:
    assert len(CASES) >= 500
    for module, names in EXPECTED_ALLOWED.items():
        assert set(names) <= set(dir(MODULES[module]))


@pytest.mark.parametrize(
    "source",
    [
        "import logging.config\n",
        "import logging.handlers\n",
        "import logging.config as c\n",
        "from logging import config\n",
        "from logging import handlers as h\n",
        "from logging.config import dictConfig\n",
        "from logging.handlers import RotatingFileHandler\n",
    ],
)
def test_ec2_a_submodule_of_logging(source: str) -> None:
    assert lines(source) == [1]


@pytest.mark.parametrize(
    ("source", "found"),
    [
        ("import importlib\n\nimportlib.import_module('logging')\n", [3]),
        ("__import__('warnings')\n", [1]),
        ("from importlib import import_module\n\nimport_module('ploni.safety.logging')\n", [3]),
        ("from importlib import import_module\n\nimport_module('logging.config')\n", [3]),
        ("from importlib import import_module\n\nimport_module('ploni.safety')\n", [3]),
        ("from importlib import import_module\n\nimport_module('json')\n", []),
    ],
)
def test_ec3_imported_by_a_call(source: str, found: list[int]) -> None:
    assert lines(source) == found


@pytest.mark.parametrize(
    "source",
    [
        "import logging\n\nx = logging\n",
        "import logging\n\ngetattr(logging, 'getLogger')\n",
        "import warnings\n\nvars(warnings)\n",
        "from ploni.safety import logging\n\nhandle = logging\n",
        "import ploni\n\npackage = ploni\n",
        "from ploni import safety\n\nsafety.logging.Redacting\n",
        "import ploni.safety.logging\n\nploni.safety.logging.Quiet\n",
    ],
)
def test_ec4_a_module_or_a_package_above_it_as_a_value(source: str) -> None:
    assert lines(source) == [3]


def test_ec5_the_scope(tmp_path: Path) -> None:
    names = (
        "ploni/a.py",
        "ploni/detect/b.py",
        "ploni/safety.py",
        "ploni/detect/safety/x.py",
        "ploni/safety/logging.py",
        "ploni/safety/c.py",
        "scripts/d.py",
    )
    for name in names:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("", encoding="utf-8")
    assert [path.relative_to(tmp_path).as_posix() for path in judged(tmp_path)] == [
        "ploni/a.py",
        "ploni/detect/b.py",
        "ploni/detect/safety/x.py",
        "ploni/safety.py",
    ]


def _module(path: Path) -> tuple[str, bool]:
    """Return the dotted name of a file of the repository, and whether it is a package's own."""
    parts = path.relative_to(ROOT).with_suffix("").parts
    return (".".join(parts[:-1]), True) if parts[-1] == "__init__" else (".".join(parts), False)


def test_ec6_the_repository() -> None:
    assert judged(ROOT) != []
    found = [
        f"{path.relative_to(ROOT).as_posix()}:{line}"
        for path in judged(ROOT)
        for line in setups(path.read_text(encoding="utf-8"), *_module(path))
    ]
    assert found == []


def test_ec7_the_lines_in_order() -> None:
    source = "import logging\n\nlogging.basicConfig()\nfrom logging import Handler\nx = logging\n"
    assert setups(source) == [
        "3: uses logging.basicConfig",
        "4: uses logging.Handler",
        "5: uses logging as a value",
    ]


@pytest.mark.parametrize(
    "source",
    [
        "import logging\n\nfrom ploni.safety.logging import Event, event\n\nevent(Event.DONE, level=logging.WARNING)\n",
        "from logging import WARNING\n",
        "import warnings\n\nwarnings.warn('a fixed text', UserWarning, stacklevel=2)\n",
        "from ploni.safety import logging\n\nlogging.install\n",
        "from ploni import errors, types\n",
    ],
)
def test_b1_the_allowed_names(source: str) -> None:
    assert setups(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "handlers = {'pdf': 1}\n",
        "table = {'handlers': []}\n",
        "propagate = True\n",
        "class MessageHandler:\n    pass\n",
        "from xml.sax.handler import ContentHandler\n",
        "class Worker:\n    def go(self) -> None:\n        self.listen()\n",
        "def listen() -> None:\n    pass\n",
        '"""This module never calls logging.basicConfig."""\n',
        "import json\n\njson.dumps({})\n",
    ],
)
def test_b2_words_that_only_look_like_logging(source: str) -> None:
    assert setups(source) == []


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


def test_a1_bad_pr_5b() -> None:
    assert lines(BAD_5B) == [8, 10]


@pytest.mark.parametrize(
    ("source", "found"),
    [
        (
            "import logging\n\nlog = logging.getLogger('x')\nvars(log).update(propagate=False, handlers=[logging._defaultLastResort])\n",
            [3, 4],
        ),
        ("import warnings\n\nwith warnings.catch_warnings():\n    pass\n", [3]),
        ("from ploni.safety.logging import Redacting\n\nRedacting.format = str\n", [1, 3]),
        ("import logging\n\nfor ref in logging._handlerList:\n    pass\n", [3]),
        ("import logging\n\n\nclass Log(logging.Logger):\n    pass\n", [4]),
        ("import logging\n\nlogging.Logger.handle = print\n", [3]),
        ("import logging\n\nlogging.Logger.manager.loggerClass = None\n", [3]),
    ],
)
def test_a2_the_ways_the_review_ran(source: str, found: list[int]) -> None:
    assert lines(source) == found


@pytest.mark.parametrize(
    "source",
    [
        "import logging\n\n\ndef run() -> None:\n    logging.basicConfig()\n",
        "import logging\n\n\nclass Run:\n    def go(self) -> None:\n        logging.basicConfig()\n",
        "import logging\n\nif True:\n    logging.basicConfig()\n",
        "import logging\n\ntry:\n    pass\nexcept Exception:\n    logging.basicConfig()\n",
    ],
)
def test_a3_anywhere_in_the_file(source: str) -> None:
    assert lines(source) == [source.count("\n")]
