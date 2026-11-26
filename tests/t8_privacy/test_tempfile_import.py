"""No file under ploni/ but the temp-file helper imports Python's `tempfile` module, or imports or names the helper's copy of it.

Why: a temp file made with `tempfile` outside a `ploni.safety.tempfiles.private_dir` block
lands in the system's temp folder and stays there after a crash, with document text in it
(ADR-0005: going around the helper must take a deliberate act). Achia approved the ban on
2026-11-18 ("Ban plain temp files", `build-plan.md` Phase 0), worded as a linter rule in one
settings file. Ruff cannot do it in that one file without lifting the PyMuPDF ban outside
ploni/: its product-only ban list is the no-network list that `selftest` is held to, and its
other list covers the whole repository. Asked on
2026-11-25 how to build it, and asked again the same night after the first question was found
to hold a false line, he chose "Keep the test (Recommended)": "The privacy test as built: it
reads every product file and fails on any use of tempfile outside the helper, including an
import made by a call. No protected settings file changes. Runs on every PR." (issue #214,
issuecomment-7186453908).

The reading of the files is tests/project_imports.py, as for the no-network test; the ten
ways to write an import are the ones of tests/t8_privacy/test_imports.py.

Test matrix:

Equivalence classes:
  EC1  tempfile in each of the ten ways x 59 places to write it from (PLACES: the 13 packages
       of `build-plan.md` section 4.7, each as a package's own file, a module, a module two
       deep and a package two deep, its six top modules and `__main__`; 10 x 59 = 590
       cases): one line each. The ten ways name the module absolutely, so the place does not
       change their result; EC6 is where it does
  EC6  fourteen relative imports from each of the 59 places, climbing to `ploni` by as many
       dots as the place needs (RELATIVE, 59 x 14 = 826 cases): the helper's bindings, the old
       public name and the private one of #278, each plain, under another name, beside another
       name, and named as a module path (which Python itself refuses at run time), one line
       each (eight forms); the helper's module, a name of the
       helper (`private_dir`), a name it does not have (`tempfiles`), a project module named
       tempfile in two forms, and the helper's binding written with one dot too few, which
       names a module one package below `ploni` (at a top module, an absolute name), not the
       helper, no line (six forms). This class holds the floor of 500 cases, as its result
       depends on the place
  EC2  the helper itself, `ploni/safety/tempfiles.py`, in each of the ten ways: no line
  EC3  the helper's own binding of tempfile imported from it, absolute and relative, plain,
       under another name, and named as a module path (which Python itself refuses at run
       time): one line each, as `tempfile`
  EC4  a tree on disk: the lines, with file and line, of every file under ploni/ but the
       helper
  EC5  the repository: no line
  EC7  the text of a file under ploni/ but the helper holds the helper's private binding
       (`_tempfile`) as a word: the attribute and getattr routes the reader does not see ->
       named; longer names that hold it, in Latin or in Hebrew letters, and a file in cp1255
       (read with the bytes that are not UTF-8 replaced) -> not named; the repository -> none

Boundaries:
  B1  the neighbours of the helper: `ploni/safety/__init__.py`, `ploni/safety/atomic.py`,
      `ploni/safety/tempfiles2.py`, `ploni/safety/tempfiles/__init__.py`, `ploni/tempfiles.py`
      and the helper's path in another case of letters (`ploni/safety/TempFiles.py`) are
      reported. Only the one file is exempt, not the folder, which is narrower than the
      issue's "outside ploni/safety/"
  B2  a repository with no ploni/ folder: no line
  B3  tempfile as the second name of one import line (`import os, tempfile`): reported

Negative cases (no line):
  N1  the helper's own module imported by others (`from ploni.safety import tempfiles`,
      `import ploni.safety.tempfiles`, a relative import of a module named tempfile, a name of
      the helper (`private_dir`), and one it does not have (`tempfiles`))
  N2  look-alikes: `import tempfiles`, `import tempfile_helpers`, `from mytempfile import x`

Adversarial:
  A1  inside a function, inside try/except, by `importlib.import_module` and by `__import__`
      (four of the ten ways of EC1)
  A2  an import whose name cannot be read is refused by
      `test_ec6_every_import_under_ploni_can_be_read` of tests/t8_privacy/test_imports.py, so
      it cannot hide a `tempfile` import here

Known limits:
  - Since #278 the helper binds the module under a private name and lists its public names
    in `__all__`, so a star import of it binds no module (EC26 of
    tests/t1_unit/test_safety_tempfiles.py), and EC7 refuses the word `_tempfile` anywhere in
    a product file, a comment or docstring too: the attribute, getattr and vars routes, which
    the import reader does not see. The private binding reached by a name built when the
    program runs (`getattr(tempfiles, "_" + "tempfile")`, an escape of its first letter, two
    literals side by side, `vars(tempfiles)[name]`) is seen by neither: a deliberate act
    (ADR-0005's bar).
  - `sys.modules["tempfile"]` is no import, so it is not read, and no change to the helper
    closes it: any import of the module, under any name, puts it there. Reaching it is a
    deliberate act (ADR-0005's bar), like code given to exec.
  - A temp file can be made without `tempfile`: `open` on a path under the system's temp
    folder, `os.open`, or a library that calls `tempfile` itself. The temp-file canary covers
    what is written inside a `private_dir` block.
  - Source text handed to exec or eval is not read (tests/project_imports.py).

The Hebrew axis of the test-matrix skill applies to EC7 (names with Hebrew letters, a file in
cp1255); the document-structure axes do not: this code reads import statements and the text
of each product file, and handles no document.
"""

import re
from pathlib import Path

import pytest

from tests.project_imports import SOURCE_SUFFIXES, Import, from_packages, imported, project_imports
from tests.t8_privacy.test_imports import FORMS, LINE

ROOT = Path(__file__).resolve().parents[2]

# The one file that may import tempfile: the helper that owns it (ADR-0005), and its module.
HELPER = "ploni/safety/tempfiles.py"
HELPER_MODULE = "ploni.safety.tempfiles"
BANNED = "tempfile"
# The helper's bindings of the module: the private one of #278, and the old public name, which
# no longer exists and stays refused should it come back.
PRIVATE = f"_{BANNED}"
HELPER_BINDINGS = (f"{HELPER_MODULE}.{BANNED}", f"{HELPER_MODULE}.{PRIVATE}")

# The packages and the top modules of the plan's layout (build-plan.md section 4.7), and the
# command line, `__main__`, which 4.7 does not list.
PACKAGES = (
    "adapters", "detect", "morph", "resolve", "policy", "mapping", "write", "verify", "rehydrate",
    "report", "safety", "worker", "i18n",
)  # fmt: skip
TOP = tuple((f"ploni.{name}", False) for name in ("api", "types", "config", "profiles", "session", "errors", "__main__"))
# Each package as its own file, a module, a module two deep and a package two deep: (importer, is it an __init__ file).
PLACES = TOP + tuple(
    place
    for package in PACKAGES
    for place in (
        (f"ploni.{package}", True),
        (f"ploni.{package}.core", False),
        (f"ploni.{package}.deep.part", False),
        (f"ploni.{package}.deep", True),
    )
)


def as_banned(item: Import) -> Import:
    """Return an import of the helper's binding of tempfile as an import of tempfile; any other as it is."""
    if any(item.module == binding or item.module.startswith(f"{binding}.") for binding in HELPER_BINDINGS):
        return item._replace(module=BANNED)
    return item


def outside_helper(imports: list[Import]) -> list[str]:
    """Return one line for every import of `tempfile` made by a file other than the helper.

    Why: this is the rule of the ban; the tests below judge it on written sources and on the
    repository.

    Contract:
        Args: imports, as `project_imports` returns them.
        Returns: lines of the form `file:line: imports tempfile`, as `from_packages` gives
            them, for every file but HELPER. An import of the helper's own binding of the
            module (`from ploni.safety.tempfiles import _tempfile`, or the old public name)
            counts as one of `tempfile`.
        Raises: nothing.

    Known limits: those of `from_packages`, and the module docstring's.
    """
    return from_packages([as_banned(item) for item in imports if item.file != HELPER], (BANNED,))


def judged(source: str, file: str, importer: str, is_package: bool) -> list[str]:
    """Return the lines reported for one source text written as the file and importer given."""
    found = imported(source, importer, is_package)
    return outside_helper([Import(file, line, importer, module) for line, module in found])


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize(("importer", "is_package"), PLACES)
def test_ec1_a_tempfile_import_is_reported(form: str, importer: str, is_package: bool) -> None:
    source = FORMS[form].format(name=BANNED)
    assert judged(source, "file.py", importer, is_package) == [f"file.py:{LINE.get(form, 1)}: imports tempfile"]


def test_ec1_the_matrix_has_at_least_500_cases() -> None:
    # CLAUDE.md, Tests: an invariant is held over 500 generated cases, as the no-network test's is.
    # EC1's place does not change its result (the module docstring); EC6's does, so EC6 alone
    # holds the floor too.
    assert len(FORMS) * len(set(PLACES)) >= 500
    assert len(set(PLACES)) * len(RELATIVE) >= 500


def climb(importer: str, is_package: bool) -> str:
    """Return the dots a relative import of a file needs to name the top package `ploni`."""
    package = importer if is_package else importer.rpartition(".")[0]
    return "." * (package.count(".") + 1)


# Fourteen relative imports, written from any place: the source, and whether it must give a line.
# `{short}` is one dot fewer than the place needs, so it names a module one package below
# `ploni` (at a top module, an absolute name), not the helper.
RELATIVE = (
    ("from {short}safety.tempfiles import tempfile\n", False),
    ("from {dots}safety.tempfiles import tempfile\n", True),
    ("from {dots}safety.tempfiles import tempfile as t\n", True),
    ("from {dots}safety.tempfiles import private_dir, tempfile\n", True),
    ("from {dots}safety.tempfiles.tempfile import mkstemp\n", True),
    ("from {dots}safety import tempfiles\n", False),
    ("from {dots}safety.tempfiles import private_dir\n", False),
    ("from {dots}safety.tempfiles import tempfiles\n", False),
    ("from {dots} import tempfile\n", False),
    ("from {dots}tempfile import mkstemp\n", False),
    # The helper's private binding of #278, in the four forms that must give a line.
    ("from {dots}safety.tempfiles import _tempfile\n", True),
    ("from {dots}safety.tempfiles import _tempfile as t\n", True),
    ("from {dots}safety.tempfiles import private_dir, _tempfile\n", True),
    ("from {dots}safety.tempfiles._tempfile import mkstemp\n", True),
)


@pytest.mark.parametrize(("source", "reported"), RELATIVE)
@pytest.mark.parametrize(("importer", "is_package"), PLACES)
def test_ec6_a_relative_import_from_each_place(source: str, reported: bool, importer: str, is_package: bool) -> None:
    dots = climb(importer, is_package)
    text = source.format(dots=dots, short=dots[:-1])
    assert judged(text, "file.py", importer, is_package) == (["file.py:1: imports tempfile"] if reported else [])


@pytest.mark.parametrize("form", FORMS)
def test_ec2_the_helper_may_import_tempfile(form: str) -> None:
    source = FORMS[form].format(name=BANNED)
    assert judged(source, HELPER, HELPER_MODULE, False) == []


@pytest.mark.parametrize(
    ("source", "file", "importer", "is_package"),
    [
        ("from ploni.safety.tempfiles import tempfile\n", "ploni/api.py", "ploni.api", False),
        ("from ploni.safety.tempfiles import _tempfile\n", "ploni/api.py", "ploni.api", False),
        ("from .tempfiles import _tempfile as t\n", "ploni/safety/atomic.py", "ploni.safety.atomic", False),
        ("from ploni.safety.tempfiles import tempfile as tf\n", "ploni/api.py", "ploni.api", False),
        ("import ploni.safety.tempfiles.tempfile\n", "ploni/api.py", "ploni.api", False),
        ("from .tempfiles import tempfile\n", "ploni/safety/atomic.py", "ploni.safety.atomic", False),
        ("from .tempfiles import tempfile\n", "ploni/safety/__init__.py", "ploni.safety", True),
        ("from ..safety.tempfiles import tempfile\n", "ploni/detect/x.py", "ploni.detect.x", False),
    ],
)
def test_ec3_the_helpers_own_binding_imported_from_it(source: str, file: str, importer: str, is_package: bool) -> None:
    assert judged(source, file, importer, is_package) == [f"{file}:1: imports tempfile"]


@pytest.mark.parametrize(
    ("file", "importer", "is_package"),
    [
        ("ploni/safety/__init__.py", "ploni.safety", True),
        ("ploni/safety/atomic.py", "ploni.safety.atomic", False),
        ("ploni/safety/tempfiles2.py", "ploni.safety.tempfiles2", False),
        ("ploni/safety/tempfiles/__init__.py", "ploni.safety.tempfiles", True),
        ("ploni/tempfiles.py", "ploni.tempfiles", False),
        ("ploni/safety/TempFiles.py", "ploni.safety.TempFiles", False),
    ],
)
def test_b1_a_neighbour_of_the_helper_is_reported(file: str, importer: str, is_package: bool) -> None:
    assert judged("import tempfile\n", file, importer, is_package) == [f"{file}:1: imports tempfile"]


def test_b3_tempfile_as_the_second_name_of_one_line() -> None:
    assert judged("import os, tempfile\n", "ploni/api.py", "ploni.api", False) == ["ploni/api.py:1: imports tempfile"]


@pytest.mark.parametrize(
    "source",
    [
        "from ploni.safety import tempfiles\n",
        "import ploni.safety.tempfiles\n",
        "from . import tempfile\n",
        "from .safety import tempfiles\n",
        "from ploni.safety.tempfiles import private_dir\n",
        "from ploni.safety.tempfiles import tempfiles\n",
    ],
)
def test_n1_the_helpers_own_module_imported_by_others(source: str) -> None:
    assert judged(source, "ploni/api.py", "ploni.api", False) == []


@pytest.mark.parametrize("source", ["import tempfiles\n", "import tempfile_helpers\n", "from mytempfile import x\n"])
def test_n2_a_module_that_only_looks_like_tempfile(source: str) -> None:
    assert judged(source, "ploni/api.py", "ploni.api", False) == []


def test_ec4_a_tree_on_disk_reports_every_file_but_the_helper(tmp_path: Path) -> None:
    files = {
        "ploni/__init__.py": "",
        HELPER: "import tempfile\n",
        "ploni/safety/atomic.py": "import os\n\n\ndef late():\n    import tempfile\n",
        "ploni/detect/base.py": "from tempfile import mkstemp\n",
        "ploni/write/docx.py": "import importlib\nmodule = importlib.import_module('tempfile')\n",
        "ploni/report/audit.py": "from ploni.safety.tempfiles import tempfile\n",
        "scripts/tool.py": "import tempfile\n",
    }
    for name, source in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    assert outside_helper(project_imports(tmp_path, "ploni")) == [
        "ploni/detect/base.py:1: imports tempfile",
        "ploni/report/audit.py:1: imports tempfile",
        "ploni/safety/atomic.py:5: imports tempfile",
        "ploni/write/docx.py:2: imports tempfile",
    ]


def test_b2_a_repository_with_no_ploni_folder_reports_nothing(tmp_path: Path) -> None:
    assert outside_helper(project_imports(tmp_path, "ploni")) == []


def test_ec5_no_file_under_ploni_but_the_helper_imports_tempfile() -> None:
    assert outside_helper(project_imports(ROOT, "ploni")) == []


def names_private_binding(root: Path) -> list[str]:
    """Return each file under root/ploni but the helper whose text holds the helper's private binding as a word."""
    files = sorted(path for path in (root / "ploni").rglob("*") if path.suffix.lower() in SOURCE_SUFFIXES)
    # Read as text, so that a Hebrew letter beside the name counts as part of a longer name;
    # bytes that are not UTF-8 (a file in cp1255) are replaced, not refused.
    word = re.compile(r"\b" + PRIVATE + r"\b")
    return [
        path.relative_to(root).as_posix()
        for path in files
        if path.relative_to(root).as_posix() != HELPER and word.search(path.read_bytes().decode("utf-8", "replace"))
    ]


def test_ec7_no_file_under_ploni_but_the_helper_names_its_private_binding(tmp_path: Path) -> None:
    # The attribute route the ban's reader does not see (`tempfiles._tempfile.mkstemp()`,
    # `getattr(tempfiles, "_tempfile")`): refused by the name's text (the review of 46a972a,
    # finding 3). A tree on disk first, then the repository.
    for name, source in {
        HELPER: "import tempfile as _tempfile\n",
        "ploni/write/docx.py": "from ploni.safety import tempfiles\n\ntempfiles._tempfile.mkstemp()\n",
        "ploni/report/audit.py": "value = getattr(tempfiles, '_tempfile')\n",
        "ploni/api.py": "import json\n",
        # Longer names that only hold the word, in Latin and in Hebrew letters, and a file in the
        # laptop's code page: no line.
        "ploni/write/names.py": "def write_tempfile(): pass\nis_tempfile = 1\nfrom ploni.safety import tempfiles as _tempfiles\nשם_tempfile = 1\n_tempfileשני = 1\n",
    }.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    (tmp_path / "ploni/write/hebrew.py").write_bytes("# שלום\n".encode("cp1255"))
    assert names_private_binding(tmp_path) == ["ploni/report/audit.py", "ploni/write/docx.py"]
    assert names_private_binding(ROOT) == []
