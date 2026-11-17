"""Module suite for tests/project_imports.py: the reader against Python's own import system.

Why: the unit tests say what the reader should give for each form of import. They cannot
say that those names are the ones the interpreter resolves. Here a small package is written
to disk and really imported, with every import statement recorded as Python resolves it, and
the reader has to name the same importers and the same modules from the same files.

Matrix (one package, eleven files, imported once):
  M1  absolute imports: import a.b, import a.b as c, from a import module, from a.b import name
  M2  relative imports: one and two dots in an __init__; one, two and three in a module
  M3  a star import, and an import inside a function that runs
  M4  from a import name where the name is no module: Python resolves the module only; the
      reader also gives a.name, which is no module and is left out of the comparison
  M5  the rule on the same files: with a table that lets the detect layer import types
      only, `not_allowed` names the two imports of other layers, with file and line
  M6  imports made by a call: importlib.import_module with a relative name and __package__,
      and with an absolute name; and the second rule, `from_packages`, on the same files
The comparison is over modules of the package itself. What Python resolved and what the
reader read must be the same set.

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import builtins
import importlib
import sys
import types
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.project_imports import from_packages, not_allowed, project_imports

TOP = "layered_sample"

FILES = {
    "__init__.py": "",
    "types.py": "VALUE = 1\n",
    "errors.py": "from . import types\n",
    "adapters/__init__.py": "from . import base\nfrom .. import types\n",
    "adapters/base.py": f"import {TOP}.errors\nfrom {TOP}.types import VALUE\n",
    "adapters/docx/__init__.py": "",
    "adapters/docx/reader.py": (
        "from ...types import VALUE\n"
        "from .. import base\n"
        "from ..base import VALUE as other\n"
        f"import {TOP}.adapters.docx as own\n"
    ),
    "detect/__init__.py": f"from {TOP} import types, errors\n",
    "detect/fusion.py": (
        "def late():\n"
        "    from . import windows\n"
        "    from ..adapters.docx import reader\n"
        "    return windows, reader\n"
        "\n"
        "\n"
        "late()\n"
    ),
    "detect/windows.py": f"from {TOP}.detect import *\n",
    "detect/lazy.py": (
        "import importlib\n"
        "windows = importlib.import_module('.windows', __package__)\n"
        f"types = importlib.import_module('{TOP}.types')\n"
    ),
}


def inside(module: str) -> bool:
    """Return whether the dotted name is the sample package or lies in it."""
    return module == TOP or module.startswith(TOP + ".")


@pytest.fixture
def package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Write the sample package under a folder that is on the import path, and forget it afterwards."""
    for name, source in FILES.items():
        path = tmp_path / TOP / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(tmp_path)
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    yield tmp_path
    for name in [name for name in sys.modules if inside(name)]:
        del sys.modules[name]


def resolved(monkeypatch: pytest.MonkeyPatch) -> set[tuple[str, str]]:
    """Import every module of the sample and return (importer, module) as Python resolved each import.

    The module of a relative import is taken from the module object that Python hands back,
    not worked out here, so the comparison does not rest on the reader's own arithmetic.
    """
    seen: set[tuple[str, str]] = set()
    real, load = builtins.__import__, importlib.import_module

    def recording(name, scope=None, local=None, fromlist=(), level=0):
        # The signature of __import__; the import statements of the sample call it.
        module = real(name, scope, local, fromlist, level)
        importer = (scope or {}).get("__name__", "")
        if inside(importer):
            seen.add((importer, module.__name__ if fromlist else name))
            for part in fromlist or ():
                value = getattr(module, part, None)
                if isinstance(value, types.ModuleType) and value.__name__ == f"{module.__name__}.{part}":
                    seen.add((importer, value.__name__))
        return module

    def loading(name, package=None):
        # The signature of import_module; a call of it does not pass through __import__.
        module = load(name, package)
        importer = sys._getframe(1).f_globals.get("__name__", "")
        if inside(importer):
            seen.add((importer, module.__name__))
        return module

    monkeypatch.setattr(builtins, "__import__", recording)
    monkeypatch.setattr(importlib, "import_module", loading)
    for name in FILES:
        parts = name.removesuffix(".py").removesuffix("__init__").strip("/").split("/")
        load(".".join([TOP, *filter(None, parts)]))
    monkeypatch.setattr(builtins, "__import__", real)
    monkeypatch.setattr(importlib, "import_module", load)
    return {pair for pair in seen if inside(pair[1])}


def test_the_reader_names_importers_and_modules_as_python_resolves_them(
    package: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    by_python = resolved(monkeypatch)
    read = {
        (item.importer, item.module)
        for item in project_imports(package, TOP)
        if inside(item.module) and item.module in sys.modules
    }
    assert read == by_python
    # Every file but the two empty ones and types.py imports something of the package.
    assert {importer for importer, _ in by_python} == {
        f"{TOP}.errors",
        f"{TOP}.adapters",
        f"{TOP}.adapters.base",
        f"{TOP}.adapters.docx.reader",
        f"{TOP}.detect",
        f"{TOP}.detect.fusion",
        f"{TOP}.detect.lazy",
        f"{TOP}.detect.windows",
    }
    assert (f"{TOP}.adapters.docx.reader", f"{TOP}.types") in by_python
    assert (f"{TOP}.detect.fusion", f"{TOP}.adapters.docx.reader") in by_python


def test_the_rule_reports_the_imports_of_other_layers_in_the_same_package(package: Path) -> None:
    table = {f"{TOP}.detect": {f"{TOP}.types"}}
    assert not_allowed(project_imports(package, TOP), table) == [
        f"{TOP}/detect/__init__.py:1: {TOP}.detect may not import {TOP}.errors",
        f"{TOP}/detect/fusion.py:3: {TOP}.detect may not import {TOP}.adapters",
    ]


def test_an_import_made_by_a_call_is_read_as_python_resolves_it(package: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    by_python = resolved(monkeypatch)
    lazy = f"{TOP}.detect.lazy"
    assert {module for importer, module in by_python if importer == lazy} == {f"{TOP}.detect.windows", f"{TOP}.types"}
    read = {item.module for item in project_imports(package, TOP) if item.importer == lazy and inside(item.module)}
    assert read == {f"{TOP}.detect.windows", f"{TOP}.types"}


def test_the_second_rule_names_the_import_of_a_package_asked_for(package: Path) -> None:
    assert from_packages(project_imports(package, TOP), {"importlib"}) == [
        f"{TOP}/detect/lazy.py:1: imports importlib"
    ]
