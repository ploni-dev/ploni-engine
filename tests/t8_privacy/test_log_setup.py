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
its level constants, the `warnings` module only for `warn`, `filterwarnings` and `simplefilter`,
and `ploni.safety.logging` only for `Event`, `event` and `install`, with `event` and `install`
only called, each as a statement of its own, so that what they return is never read. Every other name of the three is refused, however it is reached: an attribute
(`logging.getLogger`), a name imported from it, a submodule (`logging.config`), a module
imported by a call (`importlib.import_module("logging")`, by keyword or relative name too), or
the module itself handed on as a value (`getattr(logging, name)`, `x = logging`). So is a dunder
name read past an allowed one (`install.__globals__`, `Event.__init__`), `getattr` with a literal
name that is `logging` or a dunder, and the attribute `logging` of any module a file imports
(`concurrent.futures._base.logging`, also bound by a from-import), but for a module of the
project's own outside ploni/safety/ (`settings.logging`), which cannot import `logging` under
this rule. What that leaves open is under Known limits.

That is narrower than the option's words, and each narrowing is Claude's and only narrows what
product code may do: a plain logging call is refused too (before `install` runs, the logging
module's last-resort handler prints the message of a WARNING or worse); the warnings module is
held to three names (its `catch_warnings` and `showwarning` take warnings around the filter);
only three names of the filter may be used, `event` and `install` only called as statements; a package above
a guarded module may not be used as a value; one of the modules may not be imported by a call;
a name bound to one of the modules and bound again is still judged as that module. Some code to
come is refused by them: `warnings.catch_warnings()` around a model load, `@warnings.deprecated`,
a local name `warnings` in a file that imports the module. Silence a library's warnings with
`warnings.filterwarnings` and its `module` argument; a need beyond that is a helper under
ploni/safety/, not a wider ALLOWED.

Test matrix:

Equivalence classes:
  EC1  each name of each of the three modules (from `dir` of the module itself), in each way to
       reach it: an attribute of the module imported plain, of the module imported under another
       name, a name imported from it; and for `ploni.safety.logging` also from its package, and
       relative. Refused unless the name is allowed (the literal lists below)    659 cases
  EC2  a submodule of `logging`, imported in every form                     a line
  EC3  one of the modules imported by a call, its name given by position, by keyword, or
       relative with a package                                             a line
  EC4  one of the modules, or a package above it, used as a value         a line
  EC5  the scope: every file under ploni/ but those under ploni/safety/
  EC6  the repository                                                      no line
  EC7  the order of the lines `setups` gives                                by line
  EC8  a package's own file (`__init__.py`) with a relative import         resolved from the package

Boundaries:
  B1  the allowed names: a level constant given to `event`, `install` called, a subclass of
      `Event`, `warnings.warn`, `filterwarnings`, `simplefilter`           no line
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
  A4  the ways pass 2 of the review ran: the globals of `install` or `event`, either function
      handed on as a value, a dunder read past `Event`                     refused
  A5  the attribute `logging` of another module (`concurrent.futures._base.logging`)    refused

Not applicable: the Hebrew axes and the document axes of the test-matrix skill, as the input
is Python source and no document is handled.

Known limits:
  - A check over the names in a source text cannot close every route Python has to an object. This
    one refuses the routes that the closing test (#150) and three passes of its review found, and
    each is a case below; a route found later is a new case, or a line here.
  - A warning's text is written as it is until `install` has run: `warnings.warn` is allowed, so
    product code warns only with fixed text, never with text from a document.
  - Names that code reaches some other way are not seen: code given to `exec`, a module found
    through `sys.modules`, a fresh copy of the logging module made by the loader
    (`importlib.util.find_spec("logging")` then `module_from_spec`), a package above
    ploni.safety.logging handed on through a name bound by assignment. An import whose name is
    not a literal is reported by tests/t8_privacy/test_imports.py.
  - Another module's own logger object is not refused: a module that keeps one in an attribute
    under another name (`concurrent.futures._base.LOGGER`) gives a file a logger to set up. So
    is another library's own helper that sets logging up for its caller (a third-party
    `enable_default_handler()`, or `multiprocessing.log_to_stderr()`, which the worker process
    of build-plan.md section 4.6 could reach): only the three modules, and the attribute
    `logging`, are judged.
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
from importlib.util import resolve_name
from pathlib import Path

import pytest

import ploni.safety.logging
# The reader of import calls that tests/t8_privacy/test_imports.py tests: one reading of them for
# every rule about imports, private to the tests.
from tests.project_imports import _called

ROOT = Path(__file__).resolve().parents[2]
# What a file judged may use of each module: the level constants of the logging module (its
# documentation, "Logging Levels", with the aliases WARN and FATAL), `warnings.warn`, and the
# three names of ploni/safety/logging.py that product code calls.
ALLOWED = {
    "logging": ("CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "NOTSET"),
    "warnings": ("warn", "filterwarnings", "simplefilter"),
    "ploni.safety.logging": ("Event", "event", "install"),
}
# The two functions of the filter that a file may only call, as a statement of its own: handed on,
# they carry the filter's globals, and `install` returns the filter's own handler.
CALLED_ONLY = ("ploni.safety.logging.event", "ploni.safety.logging.install")
# The attribute by which a module that imports logging hands it on (`concurrent.futures._base.logging`).
LOGGING_ATTRIBUTE = "logging"
# The project's own modules, whose attribute `logging` is their own (they cannot import the module
# under this rule), and the folder of the filter, which can.
PROJECT = "ploni."
SAFETY = "ploni.safety."
# The function that reads an attribute by a name given as text.
GETATTR = "getattr"


def _package(importer: str, is_package: bool) -> str:
    """Return the package a relative import of a file starts from."""
    return importer if is_package else importer.rpartition(".")[0]


def _base(node: ast.ImportFrom, importer: str, is_package: bool) -> str:
    """Return the absolute name of the module a from-import reads from.

    Raises ImportError for a relative import that climbs above the top package.
    """
    if not node.level:
        return node.module or ""
    return resolve_name("." * node.level + (node.module or ""), _package(importer, is_package))


def _bindings(tree: ast.AST, importer: str, is_package: bool) -> dict[str, str]:
    """Map each name an import binds to the dotted name it stands for."""
    bound: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound[alias.asname or alias.name.split(".")[0]] = alias.name if alias.asname else alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            base = _base(node, importer, is_package)
            for alias in node.names:
                bound[alias.asname or alias.name] = f"{base}.{alias.name}"
    return bound


def _refused(dotted: str) -> str | None:
    """Say what a dotted name uses of a guarded module that ALLOWED does not hold, or None."""
    for module, allowed in ALLOWED.items():
        if dotted.startswith(f"{module}."):
            name = dotted[len(module) + 1 :].split(".")[0]
            if name not in allowed:
                return f"uses {module}.{name}"
    return None


def _guarded_or_above(dotted: str) -> bool:
    """Say whether a dotted name is a guarded module or a package that holds one."""
    return any(module == dotted or module.startswith(f"{dotted}.") for module in ALLOWED)


def _chain(name: ast.Name, parents: dict[ast.AST, ast.AST]) -> tuple[list[str], ast.AST]:
    """Return the attribute names read after a name, and the outermost node of that chain."""
    attributes: list[str] = []
    node: ast.AST = name
    parent = parents.get(node)
    while isinstance(parent, ast.Attribute):
        attributes.append(parent.attr)
        node, parent = parent, parents.get(parent)
    return attributes, node


def _imports(tree: ast.AST, importer: str, is_package: bool) -> list[tuple[int, str]]:
    """Return the lines whose import, import call or getattr with a literal name is refused."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, why) for alias in node.names if (why := _refused(alias.name))]
        elif isinstance(node, ast.ImportFrom):
            base = _base(node, importer, is_package)
            found += [(node.lineno, why) for alias in node.names if (why := _refused(f"{base}.{alias.name}"))]
        elif isinstance(node, ast.Call):
            module = _called(node, _package(importer, is_package))
            if module is not None and (_guarded_or_above(module) or _refused(module)):
                found.append((node.lineno, f"imports {module} by a call"))
            if (name := _getattr_name(node)) and (name == LOGGING_ATTRIBUTE or name.startswith("__")):
                found.append((node.lineno, f"reads {name} by getattr"))
    return found


def _getattr_name(node: ast.Call) -> str | None:
    """Return the name a call of getattr reads, when it is written as a literal, or None."""
    if not (isinstance(node.func, ast.Name) and node.func.id == GETATTR and len(node.args) > 1):
        return None
    name = node.args[1]
    return name.value if isinstance(name, ast.Constant) and isinstance(name.value, str) else None


def _judge(dotted: str, stated: bool) -> str | None:
    """Say what a dotted name that a file reaches through an imported name uses past ALLOWED, or None.

    Why: one judgement for every way a name is reached, apart from how the chain was read.

    Contract: `stated` says whether the chain is the function of a call that stands as a
    statement of its own.
    """
    if why := _refused(dotted):
        return why
    if _guarded_or_above(dotted):
        return f"uses {dotted} as a value"
    module = next((name for name in ALLOWED if dotted.startswith(f"{name}.")), None)
    if module is None:
        own = dotted.startswith(PROJECT) and not dotted.startswith(SAFETY)
        return f"uses {dotted}" if LOGGING_ATTRIBUTE in dotted.split(".")[1:] and not own else None
    if any(part.startswith("__") for part in dotted[len(module) + 1 :].split(".")):
        return f"uses {dotted}"
    if dotted in CALLED_ONLY and not stated:
        return f"uses {dotted} other than as a call statement"
    return None


def _uses(tree: ast.AST, bound: dict[str, str]) -> list[tuple[int, str]]:
    """Return the lines that use a name bound to a guarded module beyond what ALLOWED holds."""
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in bound:
            attributes, outer = _chain(node, parents)
            call = parents.get(outer)
            stated = isinstance(call, ast.Call) and call.func is outer and isinstance(parents.get(call), ast.Expr)
            if why := _judge(".".join([bound[node.id], *attributes]), stated):
                found.append((node.lineno, why))
    return found


def setups(source: str, importer: str = "ploni.mod", is_package: bool = False) -> list[str]:
    """Name each line of a source text that reaches past ALLOWED, as "<line>: <what>", in order.

    Why: the rule of this file, apart from where the source comes from.

    Contract: `importer` is the dotted name of the module and `is_package` says whether the
    file is a package's `__init__.py`, for a relative import. A line that reaches past ALLOWED
    in several ways is named once for each. Raises SyntaxError for a text that is not Python,
    and ImportError for a relative import that climbs above the top package.
    """
    tree = ast.parse(source)
    found = _imports(tree, importer, is_package) + _uses(tree, _bindings(tree, importer, is_package))
    return [f"{line}: {what}" for line, what in sorted(found)]


def judged(root: Path) -> list[Path]:
    """Return the files under ploni/ that the rule judges, in order: all but those under ploni/safety/.

    Why: Achia's option says "outside ploni/safety/", the folder where the filter lives.
    """
    return sorted(
        path for path in (root / "ploni").rglob("*.py") if path.relative_to(root).parts[:2] != ("ploni", "safety")
    )


def lines(source: str, importer: str = "ploni.mod") -> list[int]:
    """Return the line numbers of the lines `setups` names, each once, in order."""
    return sorted({int(line.split(":")[0]) for line in setups(source, importer)})


# The names each module allows, written out here and not taken from ALLOWED, so that a name
# dropped from ALLOWED, or added to it, turns a case red.
LEVELS = ("CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "NOTSET")
EXPECTED_ALLOWED = {
    "logging": LEVELS,
    "warnings": ("warn", "filterwarnings", "simplefilter"),
    "ploni.safety.logging": ("Event", "event", "install"),
}
MODULES = {"logging": logging, "warnings": warnings, "ploni.safety.logging": ploni.safety.logging}
# The two names of the filter that a file may only call, written out here and not taken from CALLED_ONLY.
EXPECTED_CALLED_ONLY = ("event", "install")


def forms(module: str, name: str) -> list[tuple[str, int]]:
    """Return the ways to reach a name of a module, each as (source, the line that reaches it).

    Why: EC1 crosses every name of each module with every way to reach it.

    Contract: the module's dotted name and one of its names; the sources are Python text, read
    with the importer `ploni.detect.fusion`.
    """
    alias = "m"
    # A name the filter allows only in a call is reached by a call; A4 holds the other uses.
    reach = f"{name}()" if module == "ploni.safety.logging" and name in EXPECTED_CALLED_ONLY else name
    found = [
        (f"import {module} as {alias}\n{alias}.{reach}\n", 2),
        (f"import {module}\n{module}.{reach}\n", 2),
        (f"from {module} import {name}\n", 1),
    ]
    if module == "ploni.safety.logging":
        found += [
            (f"from ploni.safety import logging\nlogging.{reach}\n", 2),
            (f"from ..safety import logging as {alias}\n{alias}.{reach}\n", 2),
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
    # CLAUDE.md, Tests: invariants 500 generated cases.
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
        ("import importlib\n\nimportlib.import_module(name='logging')\n", [3]),
        ("__import__(name='logging')\n", [1]),
        ("import importlib\n\nimportlib.import_module('.logging', 'ploni.safety')\n", [3]),
        ("import importlib\n\nimportlib.import_module('.safety.logging', __package__)\n", [3]),
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
    """Return the importer of a file of the repository: its dotted name, and is_package."""
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
        "from ploni.safety import logging\n\nlogging.install(stream)\n",
        "from ploni import errors, types\n",
        "import sys\n\nfrom ploni.safety.logging import install\n\ninstall(sys.stderr)\n",
        "from ploni.safety import logging\n\nlogging.event(logging.Event.DONE)\n",
        "from ploni.safety.logging import Event\n\n\nclass DetectEvent(Event):\n    DONE = 1\n",
        "import warnings\n\nwarnings.filterwarnings('ignore', category=FutureWarning)\n",
        "import warnings\n\nwarnings.simplefilter('ignore')\n",
        "import sys\n\nfrom ploni.safety.logging import install\n\ninstall(sys.stderr)\n",
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
        "from ploni import settings\n\nsettings.logging.level\n",
        "settings = {}\n\ngetattr(settings, 'get')\n",
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


@pytest.mark.parametrize(
    ("source", "found"),
    [
        ("from ploni.safety.logging import install\n\ninstall.__globals__\n", [3]),
        ("from ploni.safety.logging import event\n\ngetattr(event, '__globals__')\n", [3]),
        ("from ploni.safety.logging import install\n\nf = install\n", [3]),
        ("from ploni.safety.logging import event\n\nevent.__globals__['Redacting'].format = str\n", [3]),
        ("from ploni.safety.logging import Event\n\nEvent.__init__.__globals__\n", [3]),
        ("from ploni.safety import logging\n\nlogging.install.__globals__\n", [3]),
        ("from ploni.safety import logging\n\nrun = logging.event\n", [3]),
        ("import sys\n\nfrom ploni.safety.logging import install\n\nhandler = install(sys.stderr)\n", [5]),
        ("import sys\n\nfrom ploni.safety.logging import install\n\ninstall(sys.stderr).formatter\n", [5]),
        ("from ploni.safety.logging import Event, event\n\nx = event(Event.DONE)\n", [3]),
        ("from ploni.safety.logging import event\n\nprint(event)\n", [3]),
        ("from ploni.safety.logging import Event\n\nEvent.__init__\n", [3]),
        ("import logging\n\nlogging.INFO.__class__\n", [3]),
        ("import warnings\n\nwarnings.warn.__self__\n", [3]),
        ("from ploni.safety.logging import Event\n\ngetattr(Event, '__init__')\n", [3]),
    ],
)
def test_a4_the_filter_functions_only_called_and_no_dunder(source: str, found: list[int]) -> None:
    assert lines(source) == found


@pytest.mark.parametrize(
    "source",
    [
        "import concurrent.futures._base as b\n\nb.logging.StreamHandler\n",
        "import concurrent.futures\n\nconcurrent.futures._base.logging\n",
        "from concurrent.futures import _base\n\n_base.logging.getLogger\n",
        "from concurrent.futures._base import logging as lg\n\nlg.getLogger\n",
        "import concurrent.futures\n\ngetattr(concurrent.futures, 'logging')\n",
        "import somepackage.logging as lg\n\nlg.getLogger\n",
        "from ploni.safety import atomic\n\natomic.logging.getLogger\n",
    ],
)
def test_a5_the_logging_attribute_of_another_module(source: str) -> None:
    assert lines(source) == [3]


@pytest.mark.parametrize(
    ("source", "importer"),
    [
        ("from .safety import logging as m\nm.Redacting\n", "ploni"),
        ("from ..safety import logging as m\nm.Redacting\n", "ploni.detect"),
    ],
)
def test_ec8_a_package_own_file(source: str, importer: str) -> None:
    assert setups(source, importer, True) == ["2: uses ploni.safety.logging.Redacting"]


def test_ec8_the_dotted_name_of_a_file() -> None:
    assert _module(ROOT / "ploni" / "detect" / "__init__.py") == ("ploni.detect", True)
    assert _module(ROOT / "ploni" / "errors.py") == ("ploni.errors", False)
