"""No networking import under ploni/, and nothing under ploni/ imports eval/.

Why: the product's promise is that a document never leaves the machine. `CLAUDE.md`, Hard
constraints: "No networking imports anywhere under ploni/" and "ploni/ must never import
from eval/", which may use the network. The ruff rule in pyproject.toml sees only a plain
import at the top of a module; these tests read every import of every file, wherever it
stands, also one made by a call. The first is one of the four tests the merge gate needs in
order to work (`PROMOTION.md` section 11: "the network test, the two canaries and the
layering test"); the second stands beside it by issue #19.

The reading of the files and the rule are in tests/project_imports.py; their own matrix is
in tests/t1_unit/test_project_imports.py. This file holds the list of networking modules
and tests the three rules from end to end.

Test matrix:

Equivalence classes:
  EC1  the list                     the one ruff bans in pyproject.toml, read from that file
  EC2  every module of the list x ten ways to write the import x four places to write it
       from (NETWORK x FORMS x IMPORTERS, 16 x 10 x 4 = 640 cases): one line each, naming
       the module of the list
  EC3  eval, in the same ten ways and four places (40 cases): one line each
  EC4  an import whose name cannot be read (a call with a variable): one line; no file
       under ploni/ may hold one, since nothing could say what it loads
  EC5  a tree on disk               the lines of the three rules, with file and line
  EC6  the repository               no line, for each of the three rules

Negative cases (no line):
  N1  a module whose name only begins or ends like one of the list (sockety, ysocket),
      for every module of the list                                      32 cases
  N2  a project module with a name of the list (ploni.socket, a relative import of a
      module named socket), for every module of the list                32 cases
  N3  ordinary standard-library modules                                 12 cases
  N4  eval look-alikes: evaluate, ploni.eval, a relative import of a module named eval,
      a call of the built-in eval                                       5 cases

Boundaries:
  B1  a repository with no ploni/ folder: no line. Until ploni/ holds code, EC6 says
      little; EC2 to EC5 are what show that the tests can fail.

Adversarial:
  A1  an import inside a function and one inside try/except ImportError, the forms the
      ruff rule does not see (two of the FORMS)
  A2  an import made by a call, with a literal name (two of the FORMS) and with a name
      that cannot be read (EC4)
  A3  an import function under another name (imported as another name, assigned, fetched
      with getattr): reported as an import that cannot be read, at the line that names it
  A4  a relative name in a call whose package is not the module's own: read against the
      package the call gives

Known limits:
  - The list is the sixteen names of pyproject.toml. A networking package that is not on
    it is not found; a new dependency is read against this list when it is added.
  - Only the first part of a module's name is compared with the list. A networking module
    that another package hands on under its own name is not found:
    `from logging.handlers import socket` binds the real socket module and gives no line.
  - Source text handed to exec or eval is not read, and neither is code that reaches the
    import system some other way (pkgutil, runpy, a loader object).
  - This is a test of imports. That no socket is opened at run time is the socket audit of
    a later phase (`build-plan.md` section 7, T8).

The Hebrew and document-structure axes of the test-matrix skill do not apply: this code
reads import statements and handles no document.
"""

import tomllib
from pathlib import Path

import pytest

from tests.project_imports import UNREADABLE, Import, from_packages, imported, project_imports

ROOT = Path(__file__).resolve().parents[2]

# CLAUDE.md, Hard constraints: no networking imports anywhere under ploni/. The names are
# the ones pyproject.toml gives ruff; test_ec1 fails when the two lists differ.
NETWORK = (
    "aiohttp", "ftplib", "http", "httpx", "imaplib", "poplib", "requests", "smtplib", "socket",
    "socketserver", "ssl", "telnetlib", "urllib", "urllib3", "websockets", "xmlrpc",
)  # fmt: skip

# CLAUDE.md, Hard constraints: eval/ may use the network; ploni/ must never import from eval/.
EVAL = ("eval",)

# Ten ways to write the import of one module.
FORMS = {
    "import": "import {name}\n",
    "import a module below it": "import {name}.sub\n",
    "import as": "import {name} as other\n",
    "from": "from {name} import thing\n",
    "from a module below it": "from {name}.sub import thing\n",
    "star": "from {name} import *\n",
    "inside a function": "def late():\n    import {name}\n",
    "inside try": "try:\n    import {name}\nexcept ImportError:\n    {name} = None\n",
    "by a call": "import importlib\nvalue = importlib.import_module('{name}')\n",
    "by the built-in call": "value = __import__('{name}.sub')\n",
}
LINE = {"inside a function": 2, "inside try": 2, "by a call": 2}

# Four places an import can be written from: (importer, is it an __init__ file).
IMPORTERS = (
    ("ploni.api", False),
    ("ploni.detect", True),
    ("ploni.detect.fusion", False),
    ("ploni.detect.deterministic.iban", False),
)

ORDINARY = ("json", "os", "os.path", "pathlib", "re", "hashlib", "logging", "sqlite3", "zipfile", "xml.etree", "io", "ast")


def lines(source: str, importer: str, is_package: bool, packages: tuple[str, ...]) -> list[str]:
    """Return the lines reported for one source text written as the importer given."""
    found = imported(source, importer, is_package)
    return from_packages([Import("file.py", line, importer, module) for line, module in found], packages)


def test_ec1_the_list_is_the_one_ruff_bans_in_pyproject_toml() -> None:
    settings = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    banned = settings["tool"]["ruff"]["lint"]["flake8-tidy-imports"]["banned-module-level-imports"]
    assert sorted(banned) == sorted(NETWORK)
    assert len(set(NETWORK)) == len(NETWORK)


@pytest.mark.parametrize("name", NETWORK)
@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize(("importer", "is_package"), IMPORTERS)
def test_ec2_a_networking_import_is_reported(name: str, form: str, importer: str, is_package: bool) -> None:
    source = FORMS[form].format(name=name)
    assert lines(source, importer, is_package, NETWORK) == [f"file.py:{LINE.get(form, 1)}: imports {name}"]


def test_ec2_the_matrix_has_at_least_500_cases() -> None:
    # CLAUDE.md, Tests: an invariant is held over 500 generated cases.
    assert len(NETWORK) * len(FORMS) * len(IMPORTERS) >= 500


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize(("importer", "is_package"), IMPORTERS)
def test_ec3_an_import_of_eval_is_reported(form: str, importer: str, is_package: bool) -> None:
    source = FORMS[form].format(name="eval")
    assert lines(source, importer, is_package, EVAL) == [f"file.py:{LINE.get(form, 1)}: imports eval"]


@pytest.mark.parametrize(
    "source",
    [
        "import importlib\nvalue = importlib.import_module(name)\n",
        "value = __import__(name)\n",
        "from importlib import import_module\nvalue = import_module(f'ploni.{name}')\n",
    ],
)
def test_ec4_an_import_whose_name_cannot_be_read_is_reported(source: str) -> None:
    line = source.count("\n")
    assert lines(source, "ploni.detect.fusion", False, (UNREADABLE,)) == [f"file.py:{line}: imports {UNREADABLE}"]
    assert lines(source, "ploni.detect.fusion", False, NETWORK + EVAL) == []


@pytest.mark.parametrize(
    ("source", "found"),
    [
        ("from importlib import import_module as load\nvalue = load('socket')\n", 1),
        ("import importlib\nload = importlib.import_module\nvalue = load('socket')\n", 2),
        ("value = getattr(__import__('importlib'), 'import_module')('socket')\n", 1),
    ],
)
def test_a3_an_import_function_under_another_name_is_reported(source: str, found: int) -> None:
    assert lines(source, "ploni.detect.fusion", False, (UNREADABLE,)) == [f"file.py:{found}: imports {UNREADABLE}"]


@pytest.mark.parametrize(
    ("source", "name"),
    [
        ("import importlib\nclient = importlib.import_module('.client', 'http')\n", "http"),
        ("import importlib\nscore = importlib.import_module('.run_eval', package='eval')\n", "eval"),
    ],
)
def test_a4_a_relative_name_with_a_package_that_is_not_the_modules_own(source: str, name: str) -> None:
    assert lines(source, "ploni.detect.fusion", False, NETWORK + EVAL) == [f"file.py:2: imports {name}"]


@pytest.mark.parametrize("name", NETWORK)
@pytest.mark.parametrize("source", ["import {name}y\n", "from y{name} import thing\n"])
def test_n1_a_module_that_only_looks_like_one_of_the_list(name: str, source: str) -> None:
    assert lines(source.format(name=name), "ploni.detect.fusion", False, NETWORK) == []


@pytest.mark.parametrize("name", NETWORK)
@pytest.mark.parametrize("source", ["import ploni.{name}\n", "from . import {name}\n"])
def test_n2_a_project_module_with_a_name_of_the_list(name: str, source: str) -> None:
    assert lines(source.format(name=name), "ploni.detect.fusion", False, NETWORK) == []


@pytest.mark.parametrize("name", ORDINARY)
def test_n3_an_ordinary_module(name: str) -> None:
    assert lines(f"import {name}\n", "ploni.detect.fusion", False, NETWORK + EVAL + (UNREADABLE,)) == []


@pytest.mark.parametrize(
    "source",
    [
        "import evaluate\n",
        "import ploni.eval\n",
        "from ploni import eval\n",
        "from . import eval\n",
        "value = eval('1 + 1')\n",
    ],
)
def test_n4_what_only_looks_like_an_import_of_eval(source: str) -> None:
    assert lines(source, "ploni.detect.fusion", False, EVAL) == []


def test_ec5_a_tree_on_disk_reports_each_rule_with_file_and_line(tmp_path: Path) -> None:
    files = {
        "ploni/__init__.py": "",
        "ploni/api.py": "import json\nfrom ploni.types import Span\n",
        "ploni/types.py": "",
        "ploni/adapters/docx/reader.py": "import zipfile\n\n\ndef fetch():\n    from urllib.request import urlopen\n",
        "ploni/detect/__init__.py": "try:\n    import requests\nexcept ImportError:\n    requests = None\n",
        "ploni/detect/hebrew_ner.py": "from eval.run_eval import score\nimport importlib\nmodel = importlib.import_module(name)\n",
        "ploni/report/audit.py": "import importlib\nclient = importlib.import_module('http.client')\n",
        "ploni/window.pyw": "import socket\n",
        "eval/run_eval.py": "import requests\n",
        "scripts/download_models.py": "import urllib.request\n",
    }
    for name, source in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    imports = project_imports(tmp_path, "ploni")
    assert from_packages(imports, NETWORK) == [
        "ploni/adapters/docx/reader.py:5: imports urllib",
        "ploni/detect/__init__.py:2: imports requests",
        "ploni/report/audit.py:2: imports http",
        "ploni/window.pyw:1: imports socket",
    ]
    assert from_packages(imports, EVAL) == ["ploni/detect/hebrew_ner.py:1: imports eval"]
    assert from_packages(imports, (UNREADABLE,)) == [f"ploni/detect/hebrew_ner.py:3: imports {UNREADABLE}"]


def test_b1_a_repository_with_no_ploni_folder_reports_nothing(tmp_path: Path) -> None:
    assert from_packages(project_imports(tmp_path, "ploni"), NETWORK + EVAL + (UNREADABLE,)) == []


def test_ec6_no_networking_import_under_ploni() -> None:
    assert from_packages(project_imports(ROOT, "ploni"), NETWORK) == []


def test_ec6_nothing_under_ploni_imports_eval() -> None:
    assert from_packages(project_imports(ROOT, "ploni"), EVAL) == []


def test_ec6_every_import_under_ploni_can_be_read() -> None:
    assert from_packages(project_imports(ROOT, "ploni"), (UNREADABLE,)) == []
