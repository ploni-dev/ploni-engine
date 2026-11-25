"""No file under ploni/ but the temp-file helper imports Python's `tempfile` module.

Why: a temp file made with `tempfile` outside a `ploni.safety.tempfiles.private_dir` block
lands in the system's temp folder and stays there after a crash, with document text in it
(ADR-0005: going around the helper must take a deliberate act). Achia approved the ban on
2026-11-18 ("Ban plain temp files", `build-plan.md` Phase 0). Asked on 2026-11-25 how to build
it, since ruff cannot ban a module under ploni/ alone without the no-network list that
`selftest` reads, he chose "A test instead (Recommended)": "A privacy test reads every product
file and fails if any of them uses tempfile outside the safety helper. It also catches an
import written inside a function, which the linter would miss. No settings file changes. It
runs in the fast suite on every PR." (issue #214).

The reading of the files is tests/project_imports.py, as for the no-network test; the ten
ways to write an import and the four importers are the ones of tests/t8_privacy/test_imports.py.

Test matrix:

Equivalence classes:
  EC1  tempfile in each of the ten ways x four places to write it from (10 x 4 = 40 cases):
       one line each
  EC2  the helper itself, `ploni/safety/tempfiles.py`, in each of the ten ways: no line
  EC3  a tree on disk: the lines, with file and line, of every file but the helper
  EC4  the repository: no line

Boundaries:
  B1  the neighbours of the helper: `ploni/safety/__init__.py`, `ploni/safety/atomic.py`,
      `ploni/safety/tempfiles2.py`, `ploni/safety/tempfiles/__init__.py` and
      `ploni/tempfiles.py` are reported. Only the one file is exempt, not the folder, which is
      narrower than the issue's "outside ploni/safety/" and as the option he chose says.
  B2  a repository with no ploni/ folder: no line

Negative cases (no line):
  N1  the helper's own module imported by others (`from ploni.safety import tempfiles`,
      `import ploni.safety.tempfiles`, a relative import of a module named tempfile)
  N2  look-alikes: `import tempfiles`, `import tempfile_helpers`, `from mytempfile import x`

Adversarial:
  A1  inside a function, inside try/except, by `importlib.import_module` and by `__import__`
      (four of the ten ways of EC1)
  A2  an import whose name cannot be read is refused by the no-network test's EC6 (every
      import under ploni/ can be read), so it cannot hide a `tempfile` import here

Known limits:
  - A temp file can be made without `tempfile`: `open` on a path under the system's temp
    folder, `os.open`, or a library that calls `tempfile` itself. This test reads imports
    only; the temp-file canary covers what is written inside a `private_dir` block.
  - Source text handed to exec or eval is not read (tests/project_imports.py).

The Hebrew and document-structure axes of the test-matrix skill do not apply: this code
reads import statements and handles no document.
"""

from pathlib import Path

import pytest

from tests.project_imports import Import, from_packages, imported, project_imports
from tests.t8_privacy.test_imports import FORMS, IMPORTERS, LINE

ROOT = Path(__file__).resolve().parents[2]

# The one file that may import tempfile: the helper that owns it (ADR-0005).
HELPER = "ploni/safety/tempfiles.py"


def outside_helper(imports: list[Import]) -> list[str]:
    """Return one line for every import of `tempfile` made by a file other than the helper.

    Why: this is the rule of the ban; the tests below judge it on written sources and on the
    repository.

    Contract:
        Args: imports, as `project_imports` returns them.
        Returns: lines of the form `file:line: imports tempfile`, as `from_packages` gives
            them, for every file but HELPER.
        Raises: nothing.

    Known limits: those of `from_packages`.
    """
    return from_packages([item for item in imports if item.file != HELPER], ("tempfile",))


def judged(source: str, file: str, importer: str, is_package: bool) -> list[str]:
    """Return the lines reported for one source text written as the file and importer given."""
    found = imported(source, importer, is_package)
    return outside_helper([Import(file, line, importer, module) for line, module in found])


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize(("importer", "is_package"), IMPORTERS)
def test_ec1_a_tempfile_import_is_reported(form: str, importer: str, is_package: bool) -> None:
    source = FORMS[form].format(name="tempfile")
    assert judged(source, "file.py", importer, is_package) == [f"file.py:{LINE.get(form, 1)}: imports tempfile"]


@pytest.mark.parametrize("form", FORMS)
def test_ec2_the_helper_may_import_tempfile(form: str) -> None:
    source = FORMS[form].format(name="tempfile")
    assert judged(source, HELPER, "ploni.safety.tempfiles", False) == []


@pytest.mark.parametrize(
    ("file", "importer", "is_package"),
    [
        ("ploni/safety/__init__.py", "ploni.safety", True),
        ("ploni/safety/atomic.py", "ploni.safety.atomic", False),
        ("ploni/safety/tempfiles2.py", "ploni.safety.tempfiles2", False),
        ("ploni/safety/tempfiles/__init__.py", "ploni.safety.tempfiles", True),
        ("ploni/tempfiles.py", "ploni.tempfiles", False),
    ],
)
def test_b1_a_neighbour_of_the_helper_is_reported(file: str, importer: str, is_package: bool) -> None:
    assert judged("import tempfile\n", file, importer, is_package) == [f"{file}:1: imports tempfile"]


@pytest.mark.parametrize(
    "source",
    [
        "from ploni.safety import tempfiles\n",
        "import ploni.safety.tempfiles\n",
        "from . import tempfile\n",
        "from .safety import tempfiles\n",
    ],
)
def test_n1_the_helpers_own_module_imported_by_others(source: str) -> None:
    assert judged(source, "ploni/api.py", "ploni.api", False) == []


@pytest.mark.parametrize("source", ["import tempfiles\n", "import tempfile_helpers\n", "from mytempfile import x\n"])
def test_n2_a_module_that_only_looks_like_tempfile(source: str) -> None:
    assert judged(source, "ploni/api.py", "ploni.api", False) == []


def test_ec3_a_tree_on_disk_reports_every_file_but_the_helper(tmp_path: Path) -> None:
    files = {
        "ploni/__init__.py": "",
        HELPER: "import tempfile\n",
        "ploni/safety/atomic.py": "import os\n\n\ndef late():\n    import tempfile\n",
        "ploni/detect/base.py": "from tempfile import mkstemp\n",
        "ploni/write/docx.py": "import importlib\nmodule = importlib.import_module('tempfile')\n",
        "scripts/tool.py": "import tempfile\n",
    }
    for name, source in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    assert outside_helper(project_imports(tmp_path, "ploni")) == [
        "ploni/detect/base.py:1: imports tempfile",
        "ploni/safety/atomic.py:5: imports tempfile",
        "ploni/write/docx.py:2: imports tempfile",
    ]


def test_b2_a_repository_with_no_ploni_folder_reports_nothing(tmp_path: Path) -> None:
    assert outside_helper(project_imports(tmp_path, "ploni")) == []


def test_ec4_no_file_under_ploni_but_the_helper_imports_tempfile() -> None:
    assert outside_helper(project_imports(ROOT, "ploni")) == []
