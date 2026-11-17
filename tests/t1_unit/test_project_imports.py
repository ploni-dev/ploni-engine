"""Test matrix for tests/project_imports.py, which reads the imports of a package folder.

The layering test (tests/t0_contract/test_layering.py) and the T8 import tests stand on it.

imported, one source text. Equivalence classes:
  EC1   import a.b                           a.b
  EC2   import a.b as c, d                   every name; the alias is not a module
  EC3   from a.b import c, d as e            a.b, and a.b.c and a.b.d, since c or d may be a module
  EC4   from a import *                      a
  EC5   from . import x      in a module     its package, and its package.x
  EC6   from .x import y     in a module     package.x, and package.x.y
  EC7   from .. import x, from ..x import y  one package up
  EC8   the relative forms in an __init__    counted from the package itself
  EC9   an import under def, async def, class, try, if, with, match    read like any other
  EC10  no import                            nothing
  EC11  line numbers                         the first line of the statement; the result is in line order;
                                             the same import twice is given twice

Boundaries:
  B1  empty source
  B2  a docstring and nothing else
  B3  from . import x in the top package's __init__    the package, and package.x

Error paths:
  E1  source that is not Python                        SyntaxError
  E2  a relative import that leaves the top package    ImportError: one dot too many in an __init__,
      in a module of the top package, and any relative import in a module with no package

Adversarial:
  A1  the word import in a string and in a comment     nothing
  A2  an import made by a call, importlib.import_module("x") or __import__("x"), in every way
      the function can be named: read like an import statement when the name is a string
      literal, relative names against the importer's package; given as UNREADABLE when the
      name is anything else (a variable, an f-string, a sum, no argument). A call of another
      function is nothing. What is still not seen is pinned too: exec of source text
  A3  source bytes with Hebrew text: UTF-8, UTF-8 with a byte order mark, cp1255 with a coding line

project_imports, a folder. Equivalence classes:
  EC12  nested folders        the importer's name comes from the path; __init__.py is its folder
  EC13  what is read          .py and .pyw files under the package folder only, since Python on
                              Windows imports both, with the suffix in any case of letters:
                              not a .txt or .pyi file in it, not a .py file beside it
  EC14  no package folder     nothing, which is today's repository
  EC15  order                 by file path, then by line

Error paths:
  E3  a file that is not Python           SyntaxError that names the file
  E4  a file whose relative import leaves the top package    ImportError that names the file
  E5  a source file that cannot be read (a folder named like one)    OSError

The reader against Python's own import system, on a package that is really imported, is in
tests/t4_integration/test_project_imports.py.

not_allowed, the rule. Equivalence classes:
  EC16  a layer of the table imports a layer its row allows        nothing
  EC17  ... imports itself                                         nothing
  EC18  ... imports a project layer its row does not hold          one line: file:line: A may not import B
  EC19  ... imports a module outside the project                   nothing
  EC20  ... imports the bare top package                           nothing (known limit)
  EC21  an importer whose layer has no row                         nothing
  EC22  the importer is the layer's own __init__                   judged like any module of the layer
  EC23  several imports                                            one line each, in the order given
  EC24  from a.b import c is read as a.b and as a.b.c              one line for the statement, not two

Boundaries:
  B4  no imports
  B5  an empty table

Adversarial:
  A4  a name that only begins like a layer: an importer ploni.adaptersx has no row; a target
      ploni.typesx is not ploni.types and is reported; a target ploni.adaptersx is not the
      importer's own layer and is reported
  A5  the same second name under another top package (eval.write) is outside the project

from_packages, the second rule. Equivalence classes:
  EC25  an import whose top package is one of those given    one line: file:line: imports <top>
  EC26  a module below such a package (http.client)            reported under the top package
  EC27  an import of any other package                         nothing
  EC28  from a import b, read as a and as a.b                  one line for the statement
  EC29  an unreadable import, when UNREADABLE is asked for     one line; nothing when it is not
  EC30  several imports                                        one line each, in the order given

Boundaries:
  B6  no imports; no packages

Adversarial:
  A6  a name that only begins like a package asked for (sockets, httpx when http is asked);
      the package as a lower part of another name (ploni.socket, a relative import of a
      module named socket)

The Hebrew axes of the test-matrix skill apply in one place, A3: a source file may hold Hebrew
literals and must still be read. The document-structure axes do not apply: no document is handled.
"""

import codecs
from pathlib import Path

import pytest

from tests import project_imports as reader
from tests.project_imports import Import

HEBREW = "name = 'יעקב'\nimport json\n"


def test_ec1_plain_import() -> None:
    assert reader.imported("import a.b\n", "pkg.mod") == [(1, "a.b")]


def test_ec2_every_name_of_one_statement_and_no_alias() -> None:
    assert reader.imported("import a.b as c, d\n", "pkg.mod") == [(1, "a.b"), (1, "d")]


def test_ec3_from_import_gives_the_module_and_each_name_under_it() -> None:
    assert reader.imported("from a.b import c, d as e\n", "pkg.mod") == [(1, "a.b"), (1, "a.b.c"), (1, "a.b.d")]


def test_ec4_star_import_gives_the_module_only() -> None:
    assert reader.imported("from a import *\n", "pkg.mod") == [(1, "a")]


def test_ec5_one_dot_in_a_module_is_its_package() -> None:
    assert reader.imported("from . import base\n", "ploni.detect.fusion") == [
        (1, "ploni.detect"),
        (1, "ploni.detect.base"),
    ]


def test_ec6_one_dot_and_a_name_in_a_module() -> None:
    assert reader.imported("from .base import Detector\n", "ploni.detect.fusion") == [
        (1, "ploni.detect.base"),
        (1, "ploni.detect.base.Detector"),
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("from .. import write\n", [(1, "ploni"), (1, "ploni.write")]),
        ("from ..write import edits\n", [(1, "ploni.write"), (1, "ploni.write.edits")]),
    ],
)
def test_ec7_two_dots_are_one_package_up(source: str, expected: list[tuple[int, str]]) -> None:
    assert reader.imported(source, "ploni.detect.fusion") == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("from . import base\n", [(1, "ploni.detect"), (1, "ploni.detect.base")]),
        ("from .base import Detector\n", [(1, "ploni.detect.base"), (1, "ploni.detect.base.Detector")]),
        ("from .. import write\n", [(1, "ploni"), (1, "ploni.write")]),
    ],
)
def test_ec8_in_an_init_file_the_dots_count_from_the_package_itself(
    source: str, expected: list[tuple[int, str]]
) -> None:
    assert reader.imported(source, "ploni.detect", is_package=True) == expected


@pytest.mark.parametrize(
    "source",
    [
        "def late():\n    import socket\n",
        "async def late():\n    import socket\n",
        "class Holder:\n    import socket\n",
        "try:\n    import socket\nexcept ImportError:\n    pass\n",
        "if True:\n    import socket\n",
        "with open('x') as handle:\n    import socket\n",
        "match 1:\n    case 1:\n        import socket\n",
        "def outer():\n    def inner():\n        import socket\n",
    ],
)
def test_ec9_an_import_inside_any_block_is_read(source: str) -> None:
    assert [name for _, name in reader.imported(source, "pkg.mod")] == ["socket"]


def test_ec10_source_without_an_import() -> None:
    assert reader.imported("value = 1\n\n\ndef double(number):\n    return number * 2\n", "pkg.mod") == []


def test_ec11_lines_are_the_first_line_of_each_statement_in_order() -> None:
    source = "import os\n\nfrom a import (\n    b,\n    c,\n)\n\ndef late():\n    import os\n\nimport x, \\\n    y\n"
    assert reader.imported(source, "pkg.mod") == [
        (1, "os"),
        (3, "a"),
        (3, "a.b"),
        (3, "a.c"),
        (9, "os"),
        (11, "x"),
        (11, "y"),
    ]


def test_ec11_the_result_is_sorted_by_line_and_then_by_name() -> None:
    # The walk of the tree meets the import of line 3 before the one inside the function.
    source = "def late():\n    import b\nimport z, a\n"
    assert reader.imported(source, "pkg.mod") == [(2, "b"), (3, "a"), (3, "z")]


@pytest.mark.parametrize("source", ["", '"""Only a docstring."""\n'])
def test_b1_b2_nothing_to_read(source: str) -> None:
    assert reader.imported(source, "pkg.mod") == []


def test_b3_one_dot_in_the_top_package_itself() -> None:
    assert reader.imported("from . import types\n", "ploni", is_package=True) == [(1, "ploni"), (1, "ploni.types")]


def test_e1_source_that_is_not_python() -> None:
    with pytest.raises(SyntaxError):
        reader.imported("def (:\n", "pkg.mod")


@pytest.mark.parametrize(
    ("source", "importer", "is_package"),
    [
        ("from .. import x\n", "ploni", True),
        ("from .. import x\n", "ploni.api", False),
        ("from ... import x\n", "ploni.detect.fusion", False),
        ("from . import x\n", "solo", False),
    ],
)
def test_e2_a_relative_import_that_leaves_the_top_package(source: str, importer: str, is_package: bool) -> None:
    with pytest.raises(ImportError):
        reader.imported(source, importer, is_package=is_package)


def test_a1_the_word_import_in_a_string_and_in_a_comment() -> None:
    assert reader.imported("text = 'import os'\n# import socket\n", "pkg.mod") == []


@pytest.mark.parametrize(
    ("call", "module"),
    [
        ("importlib.import_module('ploni.write')", "ploni.write"),
        ('importlib.import_module("socket")', "socket"),
        ("il.import_module('http.client')", "http.client"),
        ("import_module('requests')", "requests"),
        ("__import__('socket')", "socket"),
        ("__import__('urllib.request', fromlist=['x'])", "urllib.request"),
        ("importlib.__import__('ssl')", "ssl"),
        ("builtins.__import__('ssl')", "ssl"),
        ("importlib.import_module(name='socket')", "socket"),
        ("value = importlib.import_module('socket').create_connection", "socket"),
        ("importlib.import_module('.base', __package__)", "ploni.detect.base"),
        ("importlib.import_module('..write.edits', package=__package__)", "ploni.write.edits"),
    ],
)
def test_a2_an_import_made_by_a_call_with_a_literal_name_is_read(call: str, module: str) -> None:
    assert reader.imported(f"\n{call}\n", "ploni.detect.fusion") == [(2, module)]


@pytest.mark.parametrize(
    "call",
    [
        "importlib.import_module(name)",
        "importlib.import_module(f'ploni.{name}')",
        "importlib.import_module('ploni.' + name)",
        "importlib.import_module(*parts)",
        "importlib.import_module()",
        "import_module(name)",
        "__import__(name)",
        "__import__(b'socket')",
        "importlib.import_module(name=name)",
    ],
)
def test_a2_an_import_made_by_a_call_with_any_other_name_is_unreadable(call: str) -> None:
    assert reader.imported(f"\n\n{call}\n", "ploni.detect.fusion") == [(3, reader.UNREADABLE)]


@pytest.mark.parametrize(
    "source",
    [
        "load('socket')\n",
        "importlib.reload(module)\n",
        "registry.import_modules('socket')\n",
        "import_module = 3\n",
        "exec('import socket')\n",
    ],
)
def test_a2_a_call_of_another_function_is_nothing(source: str) -> None:
    assert reader.imported(source, "ploni.detect.fusion") == []


def test_a2_a_relative_name_in_a_call_that_leaves_the_top_package() -> None:
    with pytest.raises(ImportError):
        reader.imported("importlib.import_module('...x', __package__)\n", "ploni.api")


@pytest.mark.parametrize(
    ("data", "line"),
    [
        (HEBREW.encode("utf-8"), 2),
        (codecs.BOM_UTF8 + HEBREW.encode("utf-8"), 2),
        (("# coding: cp1255\n" + HEBREW).encode("cp1255"), 3),
    ],
)
def test_a3_source_bytes_with_hebrew_text(data: bytes, line: int) -> None:
    assert reader.imported(data, "pkg.mod") == [(line, "json")]


def write(root: Path, files: dict[str, str]) -> None:
    """Write each file of the tree, with the folders it needs."""
    for name, source in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")


def test_ec12_the_importer_is_named_from_its_path(tmp_path: Path) -> None:
    write(
        tmp_path,
        {
            "ploni/__init__.py": "",
            "ploni/api.py": "import ploni.types\n",
            "ploni/copy.py": "import json\n",
            "ploni/detect/__init__.py": "from . import base\n",
            "ploni/detect/deterministic/iban.py": "\nfrom ...types import Span\n",
        },
    )
    assert reader.project_imports(tmp_path, "ploni") == [
        Import("ploni/api.py", 1, "ploni.api", "ploni.types"),
        # A name that ends in the letters of the suffix: only the suffix is cut off.
        Import("ploni/copy.py", 1, "ploni.copy", "json"),
        Import("ploni/detect/__init__.py", 1, "ploni.detect", "ploni.detect"),
        Import("ploni/detect/__init__.py", 1, "ploni.detect", "ploni.detect.base"),
        Import("ploni/detect/deterministic/iban.py", 2, "ploni.detect.deterministic.iban", "ploni.types"),
        Import("ploni/detect/deterministic/iban.py", 2, "ploni.detect.deterministic.iban", "ploni.types.Span"),
    ]


def test_ec13_only_python_files_under_the_package_are_read(tmp_path: Path) -> None:
    write(
        tmp_path,
        {
            "ploni/LOUD.PY": "import socket\n",
            "ploni/real.py": "import json\n",
            "ploni/window.pyw": "import socket\n",
            "ploni/notes.txt": "import socket\n",
            "ploni/stub.pyi": "import socket\n",
            "other/beside.py": "import socket\n",
            "beside.py": "import socket\n",
        },
    )
    assert reader.project_imports(tmp_path, "ploni") == [
        Import("ploni/LOUD.PY", 1, "ploni.LOUD", "socket"),
        Import("ploni/real.py", 1, "ploni.real", "json"),
        Import("ploni/window.pyw", 1, "ploni.window", "socket"),
    ]


def test_ec14_no_package_folder(tmp_path: Path) -> None:
    assert reader.project_imports(tmp_path, "ploni") == []


def test_ec15_order_is_by_file_then_by_line(tmp_path: Path) -> None:
    write(tmp_path, {"ploni/b.py": "import z\nimport a\n", "ploni/a.py": "import y\n"})
    assert [(item.file, item.line, item.module) for item in reader.project_imports(tmp_path, "ploni")] == [
        ("ploni/a.py", 1, "y"),
        ("ploni/b.py", 1, "z"),
        ("ploni/b.py", 2, "a"),
    ]


def test_e3_a_file_that_is_not_python_is_named(tmp_path: Path) -> None:
    write(tmp_path, {"ploni/good.py": "import json\n", "ploni/detect/bad.py": "def (:\n"})
    with pytest.raises(SyntaxError, match="ploni/detect/bad.py: invalid syntax"):
        reader.project_imports(tmp_path, "ploni")


def test_e4_a_file_whose_relative_import_leaves_the_package_is_named(tmp_path: Path) -> None:
    write(tmp_path, {"ploni/api.py": "from .. import outside\n"})
    with pytest.raises(ImportError, match="ploni/api.py: attempted relative import beyond top-level package"):
        reader.project_imports(tmp_path, "ploni")


def test_e5_a_source_file_that_cannot_be_read(tmp_path: Path) -> None:
    (tmp_path / "ploni" / "odd.py").mkdir(parents=True)
    with pytest.raises(OSError, match="odd.py"):
        reader.project_imports(tmp_path, "ploni")


TABLE = {"ploni.adapters": {"ploni.types", "ploni.safety"}}
FILE = "ploni/adapters/docx/reader.py"


def one(module: str, importer: str = "ploni.adapters.docx.reader", line: int = 7) -> Import:
    """Return one import of the adapters layer, of the module given."""
    return Import(FILE, line, importer, module)


@pytest.mark.parametrize("module", ["ploni.types", "ploni.types.Span", "ploni.safety.logging"])
def test_ec16_a_layer_the_row_allows(module: str) -> None:
    assert reader.not_allowed([one(module)], TABLE) == []


@pytest.mark.parametrize("module", ["ploni.adapters", "ploni.adapters.base", "ploni.adapters.docx.anchors"])
def test_ec17_its_own_layer(module: str) -> None:
    assert reader.not_allowed([one(module)], TABLE) == []


@pytest.mark.parametrize(
    ("module", "layer"),
    [("ploni.write", "ploni.write"), ("ploni.write.edits", "ploni.write"), ("ploni.detect.fusion.merge", "ploni.detect")],
)
def test_ec18_a_project_layer_the_row_does_not_hold(module: str, layer: str) -> None:
    assert reader.not_allowed([one(module)], TABLE) == [f"{FILE}:7: ploni.adapters may not import {layer}"]


@pytest.mark.parametrize("module", ["json", "os.path", "docx.shared", "ploniextra.write"])
def test_ec19_a_module_outside_the_project(module: str) -> None:
    assert reader.not_allowed([one(module)], TABLE) == []


def test_ec20_the_bare_top_package() -> None:
    assert reader.not_allowed([one("ploni")], TABLE) == []


def test_ec21_an_importer_whose_layer_has_no_row() -> None:
    assert reader.not_allowed([one("ploni.write.edits", importer="ploni.report.audit")], TABLE) == []


def test_ec22_the_layers_own_init_file_is_judged_too() -> None:
    assert reader.not_allowed([one("ploni.write", importer="ploni.adapters")], TABLE) == [
        f"{FILE}:7: ploni.adapters may not import ploni.write"
    ]


def test_ec23_one_line_for_each_import_in_the_order_given() -> None:
    imports = [one("ploni.write", line=9), one("ploni.types", line=3), one("ploni.detect.base", line=2)]
    assert reader.not_allowed(imports, TABLE) == [
        f"{FILE}:9: ploni.adapters may not import ploni.write",
        f"{FILE}:2: ploni.adapters may not import ploni.detect",
    ]


def test_ec24_one_statement_read_as_a_module_and_as_a_name_under_it_gives_one_line() -> None:
    imports = [one("ploni.write"), one("ploni.write.edits"), one("ploni.write", line=8)]
    assert reader.not_allowed(imports, TABLE) == [
        f"{FILE}:7: ploni.adapters may not import ploni.write",
        f"{FILE}:8: ploni.adapters may not import ploni.write",
    ]


def test_b4_no_imports() -> None:
    assert reader.not_allowed([], TABLE) == []


def test_b5_an_empty_table_judges_nothing() -> None:
    assert reader.not_allowed([one("ploni.write")], {}) == []


def test_a4_a_name_that_only_begins_like_a_layer() -> None:
    assert reader.not_allowed([one("ploni.write", importer="ploni.adaptersx.thing")], TABLE) == []
    assert reader.not_allowed([one("ploni.typesx")], TABLE) == [f"{FILE}:7: ploni.adapters may not import ploni.typesx"]
    assert reader.not_allowed([one("ploni.adaptersx.thing")], TABLE) == [
        f"{FILE}:7: ploni.adapters may not import ploni.adaptersx"
    ]


def test_a5_the_same_layer_name_under_another_top_package() -> None:
    assert reader.not_allowed([one("eval.write"), one("tests.write.thing")], TABLE) == []


@pytest.mark.parametrize("module", ["socket", "http", "http.client", "urllib.request.urlopen"])
def test_ec25_ec26_a_package_asked_for_is_reported_under_its_top_name(module: str) -> None:
    top = module.split(".")[0]
    assert reader.from_packages([one(module)], {"socket", "http", "urllib"}) == [f"{FILE}:7: imports {top}"]


@pytest.mark.parametrize("module", ["json", "os.path", "ploni.types", "eval"])
def test_ec27_any_other_package(module: str) -> None:
    assert reader.from_packages([one(module)], {"socket", "http"}) == []


def test_ec28_one_statement_read_twice_gives_one_line() -> None:
    imports = [one("http"), one("http.client"), one("http", line=8)]
    assert reader.from_packages(imports, {"http"}) == [f"{FILE}:7: imports http", f"{FILE}:8: imports http"]


def test_ec29_an_unreadable_import_is_reported_only_when_asked_for() -> None:
    imports = [one(reader.UNREADABLE)]
    assert reader.from_packages(imports, {reader.UNREADABLE}) == [f"{FILE}:7: imports {reader.UNREADABLE}"]
    assert reader.from_packages(imports, {"socket"}) == []


def test_ec30_one_line_for_each_import_in_the_order_given() -> None:
    imports = [one("ssl", line=9), one("json", line=3), one("socket.socket", line=2)]
    assert reader.from_packages(imports, {"socket", "ssl"}) == [f"{FILE}:9: imports ssl", f"{FILE}:2: imports socket"]


def test_b6_no_imports_and_no_packages() -> None:
    assert reader.from_packages([], {"socket"}) == []
    assert reader.from_packages([one("socket")], set()) == []


@pytest.mark.parametrize("module", ["sockets", "httpx", "xhttp", "ploni.socket", "ploni.detect.http.client"])
def test_a6_a_name_that_only_looks_like_a_package_asked_for(module: str) -> None:
    assert reader.from_packages([one(module)], {"socket", "http"}) == []


def test_the_unreadable_mark_is_no_module_name() -> None:
    # No import statement can give it, and it has no dot, so no rule takes it for a layer.
    assert not reader.UNREADABLE.isidentifier()
    assert "." not in reader.UNREADABLE
    assert reader.not_allowed([one(reader.UNREADABLE)], TABLE) == []
