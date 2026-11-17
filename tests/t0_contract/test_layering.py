"""The layering of ploni/: every import inside the project against the table of allowed imports.

Why: `CLAUDE.md`, "Architecture boundaries", names this file as what enforces the layers, and
`PROCESS.md` section 5.2 gives the table. A layer that imports what its row does not hold fails
here with file and line, in the fast suite, and not in a review. It is one of the four tests the
merge gate needs in order to work (`PROMOTION.md` section 11).

The reading of the files and the rule are in tests/project_imports.py; their own matrix is in
tests/t1_unit/test_project_imports.py. This file holds the table and tests it from end to end.

Test matrix:

Equivalence classes:
  EC1  the table                      the one of PROCESS.md section 5.2, read from that file
  EC2  the two lines of CLAUDE.md     adapters may not import detect, resolve, policy, write;
                                      detect may not import write, rehydrate, report
  EC3  what every row allows          types, safety, errors
  EC4  every layer of the table x every package of build-plan.md section 4.7 x seven ways to
       write the import (LAYERS x PACKAGES x FORMS, 5 x 19 x 7 = 665 cases): reported exactly
       when the package is neither the layer itself nor in its row. The other ways to write
       an import (a star, a deeper module, a block other than a function) are in the t1 matrix
  EC5  a tree on disk                 one line per broken import, with file and line; a layer
                                      with no row and a module at the top of ploni/ are not judged
  EC6  the repository                 no line

Boundaries:
  B1  a repository with no ploni/ folder: no line. That is the repository today, so EC6 says
      nothing yet about product code; EC4 and EC5 are what show that the test can fail.

Adversarial:
  A1  an import inside a function, the form a lint rule on top-level imports does not see
      (one of the FORMS of EC4)
  A2  from ploni import write: the forbidden layer is a name, not the module (one of the FORMS)

Known limits:
  - A layer with no row is not judged: morph, mapping, verify, rehydrate, report, safety,
    worker, i18n and the modules at the top of ploni/. The table of section 5.2 has five rows.
  - "Only api.py is public" (`CLAUDE.md`) is not tested here: nothing outside ploni/ exists
    yet that could import past it. Issue #87 owns that test.
  - A layer always may import itself, also a sub-package of it that is named like another
    layer (ploni/adapters/write/).
  - `from ploni import NAME` is judged as the layer ploni.NAME, also when NAME is no module.
  - An import made by a call (importlib.import_module, __import__) is judged like an import
    statement when its name is a string literal. One whose name cannot be read is not judged
    here; tests/t8_privacy/test_imports.py reports it. `import ploni` followed by attribute
    access is not seen.

The Hebrew and document-structure axes of the test-matrix skill do not apply: this code reads
import statements and handles no document. Hebrew text in a source file is in the t1 matrix.
"""

import ast
from pathlib import Path

import pytest

from tests.project_imports import Import, imported, not_allowed, project_imports

ROOT = Path(__file__).resolve().parents[2]

# PROCESS.md section 5.2. A change of this table is a change of that section first.
LAYERS = {
    "ploni.adapters": {"ploni.types", "ploni.safety", "ploni.errors"},
    "ploni.detect": {"ploni.types", "ploni.morph", "ploni.safety", "ploni.errors", "ploni.config"},
    "ploni.resolve": {"ploni.types", "ploni.morph", "ploni.safety", "ploni.errors"},
    "ploni.policy": {"ploni.types", "ploni.morph", "ploni.mapping", "ploni.safety", "ploni.errors"},
    "ploni.write": {"ploni.types", "ploni.adapters", "ploni.safety", "ploni.errors"},
}

# build-plan.md section 4.7: every module and folder at the top of ploni/.
PACKAGES = (
    "api", "types", "config", "profiles", "session", "errors", "adapters", "detect", "morph", "resolve",
    "policy", "mapping", "write", "verify", "rehydrate", "report", "safety", "worker", "i18n",
)  # fmt: skip

# Seven ways to write the import of ploni.<target> from a module two levels down, ploni.<layer>.module.
FORMS = {
    "import": "import ploni.{target}.thing\n",
    "import as": "import ploni.{target}.thing as other\n",
    "from": "from ploni.{target} import thing\n",
    "from the top package": "from ploni import {target}\n",
    "relative": "from ..{target} import thing\n",
    "relative, from the top package": "from .. import {target}\n",
    "inside a function": "def late():\n    import ploni.{target}.thing\n",
}


def broken(layer: str, target: str, form: str) -> list[str]:
    """Return the lines reported for one import of ploni.<target>, written in one form, in a module of the layer."""
    importer = f"{layer}.module"
    lines = imported(FORMS[form].format(target=target), importer)
    return not_allowed([Import("file.py", line, importer, module) for line, module in lines], LAYERS)


def test_ec1_the_table_is_the_one_of_process_md_section_5_2() -> None:
    text = (ROOT / "PROCESS.md").read_text(encoding="utf-8")
    block = text[text.index("LAYERS = {") :]
    assert ast.literal_eval(block[block.index("{") : block.index("```")].strip()) == LAYERS


@pytest.mark.parametrize(
    ("layer", "target"),
    [
        ("ploni.adapters", "detect"),
        ("ploni.adapters", "resolve"),
        ("ploni.adapters", "policy"),
        ("ploni.adapters", "write"),
        ("ploni.detect", "write"),
        ("ploni.detect", "rehydrate"),
        ("ploni.detect", "report"),
    ],
)
@pytest.mark.parametrize("form", FORMS)
def test_ec2_what_claude_md_forbids_is_reported(layer: str, target: str, form: str) -> None:
    assert broken(layer, target, form) != []


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("target", ["types", "safety", "errors"])
@pytest.mark.parametrize("form", FORMS)
def test_ec3_every_layer_may_import_types_safety_and_errors(layer: str, target: str, form: str) -> None:
    assert broken(layer, target, form) == []


@pytest.mark.parametrize("layer", LAYERS)
@pytest.mark.parametrize("target", PACKAGES)
@pytest.mark.parametrize("form", FORMS)
def test_ec4_an_import_is_reported_exactly_when_the_row_does_not_hold_it(layer: str, target: str, form: str) -> None:
    line = 2 if form == "inside a function" else 1
    allowed = f"ploni.{target}" == layer or f"ploni.{target}" in LAYERS[layer]
    expected = [] if allowed else [f"file.py:{line}: {layer} may not import ploni.{target}"]
    assert broken(layer, target, form) == expected


def test_ec4_the_matrix_has_at_least_500_cases() -> None:
    # CLAUDE.md, Tests: an invariant is held over 500 generated cases.
    assert len(LAYERS) * len(PACKAGES) * len(FORMS) >= 500


def test_ec5_a_tree_on_disk_reports_each_broken_import_with_file_and_line(tmp_path: Path) -> None:
    files = {
        "ploni/__init__.py": "",
        "ploni/api.py": "from ploni.write import edits\nfrom ploni.detect import fusion\n",
        "ploni/types.py": "",
        "ploni/adapters/__init__.py": "from ..detect import base\n",
        "ploni/adapters/docx/reader.py": "import json\n\nfrom ploni.types import Span\nfrom ...write import edits\n",
        "ploni/detect/fusion.py": "from . import base\nfrom ploni.morph import prefixes\n",
        "ploni/detect/deterministic/iban.py": "def late():\n    from ploni import report\n",
        "ploni/report/audit.py": "from ploni.write import edits\n",
        "ploni/write/edits.py": "from ploni.adapters import base\nfrom ploni.detect import fusion\n",
    }
    for name, source in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    assert not_allowed(project_imports(tmp_path, "ploni"), LAYERS) == [
        "ploni/adapters/__init__.py:1: ploni.adapters may not import ploni.detect",
        "ploni/adapters/docx/reader.py:4: ploni.adapters may not import ploni.write",
        "ploni/detect/deterministic/iban.py:2: ploni.detect may not import ploni.report",
        "ploni/write/edits.py:2: ploni.write may not import ploni.detect",
    ]


def test_b1_a_repository_with_no_ploni_folder_reports_nothing(tmp_path: Path) -> None:
    assert not_allowed(project_imports(tmp_path, "ploni"), LAYERS) == []


def test_ec6_the_repository_keeps_its_layers() -> None:
    assert not_allowed(project_imports(ROOT, "ploni"), LAYERS) == []
