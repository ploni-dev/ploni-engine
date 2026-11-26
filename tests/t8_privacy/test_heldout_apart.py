"""The held-out batch is kept apart: no product file and no other test names or imports it.

Why: Achia chose on 2026-11-26 "A separate writer", whose option said: "a test blocks detector
code and its tests from reading it" (issue 283). A detector tuned on the batch's documents, or a
detector test that reads its key, would make the batch a training set, and its score would no
longer say how the detectors do on text they have not seen (`build-plan.md` section 7, "Held
out"). `ploni/` may already not import `eval/` at all (tests/t8_privacy/test_imports.py).

The rules:
  R1  no file under ploni/ or tests/, but the batch's own tests (OWN), holds the name of the
      batch's folder, `heldout`, in any case of letters; nor does any conftest.py anywhere, nor a
      file pytest reads its settings from (pyproject.toml, pytest.ini, setup.cfg, tox.ini)
  R2  no Python file of CODE_FOLDERS or of the repository's root, outside eval/heldout/ and
      OWN, imports a module of eval.heldout, in any way tests/project_imports.py reads (a helper
      under scripts/, or a script at the root, that a detector test imports would hand the
      batch on)
  R3  no Python file under ploni/ or tests/ makes an import whose name cannot be read (a
      computed name, a walk of a package), but the three that do so today on purpose
      (UNREADABLE_ALLOWED), which read imports themselves

Test matrix:
  EC1  the repository                                   no line, for each rule
  EC2  a tree on disk: a file under ploni/ that names it in a comment, a non-Python file under
       ploni/ that holds the name in capitals, a test that imports a module of it, a test that
       imports the package from eval, a test that imports it by a call with a literal name, a
       root conftest.py and a pyproject.toml that name it, a helper under scripts/ and a script
       at the root that import it, a test and a ploni/ file that import a computed name
                                                        one line each, with the file
  EC3  in the same tree: an own test, a file under eval/heldout/, a test that imports eval
       only, a word that only holds part of the name ("held out", "held-out"), a test of
       UNREADABLE_ALLOWED, and a file in a virtual environment or a cache folder under a code
       folder, which R2 does not read (review 3, finding 38)          no line
  EC4  every file of OWN and of UNREADABLE_ALLOWED exists, so that the lists are not stale
  B1   a tree with no ploni/ and no tests/ folder, and a helper under scripts/ that imports the
       batch                                            the import line only

Known limits (what no reading of the source sees, left to the reviewer of a detector PR, who may
read the batch; the author may not, by Claude's reading of issue 283):
  - a name built while the program runs, as "held" + "out", in a path or an import;
  - a glob or a directory walk that reads the generator's source, and runpy with a computed path;
  - a pytest plugin named on the command line, and a path read from a setting;
  - a Python file in a top-level folder other than CODE_FOLDERS.
"""

import os
from pathlib import Path

from tests.project_imports import SOURCE_SUFFIXES, UNREADABLE, Import, imported, project_imports

ROOT = Path(__file__).resolve().parents[2]
NAME = "heldout"
BATCH_MODULE = "eval.heldout"
BATCH_FOLDER = "eval/heldout/"
GUARDED = ("ploni", "tests")
# The folders that hold the repository's Python code. Not models/ or docs/: they hold none, and
# reading models/ took eight minutes on the laptop (review 2, finding 29).
CODE_FOLDERS = ("eval", "experiments", "ploni", "scripts", "tests")
SETTINGS = ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini")
# The batch's own tests, the only files under tests/ that may name it.
OWN = frozenset({
    "tests/heldout_oracles.py",
    "tests/t1_unit/test_heldout_generator.py",
    "tests/t2_property/test_heldout_generator.py",
    "tests/t4_integration/test_heldout_generator.py",
    "tests/t8_privacy/test_heldout_apart.py",
    "tests/t8_privacy/test_heldout_disk.py",
})  # fmt: skip
# The files that read imports themselves, and import by a computed name on purpose.
UNREADABLE_ALLOWED = frozenset({
    "tests/project_imports.py",
    "tests/t0_contract/test_project.py",
    "tests/t4_integration/test_project_imports.py",
})  # fmt: skip
SKIPPED = ("__pycache__", ".pytest_cache", ".git", ".venv", "node_modules")


def _skipped(path: Path) -> bool:
    """Whether a path lies in a cache, a virtual environment or git's own folder."""
    return bool(set(path.parts) & set(SKIPPED))


def _names_it(path: Path) -> bool:
    """Whether a file's bytes hold the batch folder's name, in any case of letters."""
    return NAME.encode() in path.read_bytes().lower()


def by_text(root: Path) -> list[str]:
    """R1: one line per guarded file, conftest or settings file, own tests left out, that names the batch."""
    guarded = [path for folder in GUARDED for path in (root / folder).rglob("*") if path.is_file()]
    conftests = [path for path in root.rglob("conftest.py") if path.is_file()]
    settings = [root / name for name in SETTINGS if (root / name).is_file()]
    found = set()
    for path in [*guarded, *conftests, *settings]:
        relative = path.relative_to(root).as_posix()
        if relative not in OWN and not _skipped(path.relative_to(root)) and _names_it(path):
            found.add(f"{relative}: names {NAME}")
    return sorted(found)


def _sources(root: Path) -> list[Path]:
    """The Python files of CODE_FOLDERS, the folders of SKIPPED left out before they are walked.

    Why: a virtual environment under experiments/ holds thousands of third-party files, and
    parsing them made the scan take minutes in the main checkout (review 3, finding 38).
    """
    found = []
    for folder in CODE_FOLDERS:
        for place, names, files in os.walk(root / folder):
            names[:] = sorted(name for name in names if name not in SKIPPED)
            found += [Path(place) / name for name in sorted(files) if Path(name).suffix.lower() in SOURCE_SUFFIXES]
    return found


def _imports(root: Path) -> list[Import]:
    """Every import of the Python files of CODE_FOLDERS and of the root itself."""
    found = []
    for path in [*_sources(root), *sorted(root.glob("*.py"))]:
        parts = path.relative_to(root).with_suffix("").parts
        is_package = parts[-1] == "__init__"
        importer, relative = ".".join(parts[:-1] if is_package else parts), path.relative_to(root).as_posix()
        try:
            lines = imported(path.read_bytes(), importer, is_package)
        except (SyntaxError, ImportError) as error:
            raise type(error)(f"{relative}: {error}") from error
        found += [Import(relative, line, importer, module) for line, module in lines]
    return found


def by_import(root: Path) -> list[str]:
    """R2: one line per import of a module of eval.heldout by a Python file outside it and OWN."""
    found = []
    for item in _imports(root):
        batch = item.module == BATCH_MODULE or item.module.startswith(BATCH_MODULE + ".")
        if batch and item.file not in OWN and not item.file.startswith(BATCH_FOLDER):
            found.append(f"{item.file}:{item.line}: imports {item.module}")
    return list(dict.fromkeys(found))


def by_unreadable(root: Path) -> list[str]:
    """R3: one line per import whose name cannot be read, under ploni/ or tests/, the allowed left out."""
    found = []
    for folder in GUARDED:
        found += [
            f"{item.file}:{item.line}: imports a name that cannot be read"
            for item in project_imports(root, folder)
            if item.module == UNREADABLE and item.file not in UNREADABLE_ALLOWED
        ]
    return list(dict.fromkeys(found))


def test_ec1_the_repository_keeps_the_batch_apart() -> None:
    assert by_text(ROOT) == []
    assert by_import(ROOT) == []
    assert by_unreadable(ROOT) == []


TREE = {
    "ploni/__init__.py": "",
    "ploni/detect/ids.py": "# tuned on eval/heldout, do not\nimport re\n",
    "ploni/detect/table.json": '{"source": "HeldOut"}',
    "ploni/detect/loader.py": "import importlib\nmodule = importlib.import_module(name)\n",
    "tests/t1_unit/test_case.py": "from eval import heldout\n",
    "tests/t1_unit/test_ids.py": "from eval.heldout.generator import build\n",
    "tests/t1_unit/test_phone.py": "import importlib\nbatch = importlib.import_module('eval.heldout.scorer')\n",
    "tests/t1_unit/test_walk.py": "import importlib\nfor name in names:\n    importlib.import_module(name)\n",
    "tests/t1_unit/test_heldout_generator.py": "from eval.heldout.generator import build\n",
    "tests/t1_unit/test_score.py": "import eval\nfrom eval import run_eval\n",
    "tests/t1_unit/test_words.py": "# a held out set, a held-out batch\n",
    "tests/project_imports.py": "import importlib\nvalue = importlib.import_module(name)\n",
    "conftest.py": "pytest_plugins = ['eval.heldout.fixtures']\n",
    "pyproject.toml": "[tool.pytest.ini_options]\naddopts = ['-p', 'eval.HELDOUT.plugin']\n",
    "scripts/helper.py": "from eval.heldout.generator import build\n",
    "run_batch.py": "import eval.heldout.scorer\n",
    "experiments/.venv/Lib/site-packages/tool/run.py": "from eval.heldout.generator import build\n",
    "experiments/e9/__pycache__/run.py": "from eval.heldout.generator import build\n",
    "eval/heldout/generator.py": "SEED = 1\n",
    "eval/heldout/scorer.py": "from eval.heldout.generator import build\n",
}


def make_tree(root: Path, names: tuple[str, ...] = tuple(TREE)) -> None:
    """Write the files of TREE named under root."""
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(TREE[name], encoding="utf-8")


def test_ec2_ec3_a_tree_on_disk(tmp_path: Path) -> None:
    make_tree(tmp_path)
    assert by_text(tmp_path) == [
        "conftest.py: names heldout",
        "ploni/detect/ids.py: names heldout",
        "ploni/detect/table.json: names heldout",
        "pyproject.toml: names heldout",
        "tests/t1_unit/test_case.py: names heldout",
        "tests/t1_unit/test_ids.py: names heldout",
        "tests/t1_unit/test_phone.py: names heldout",
    ]
    assert by_import(tmp_path) == [
        "scripts/helper.py:1: imports eval.heldout.generator",
        "scripts/helper.py:1: imports eval.heldout.generator.build",
        "tests/t1_unit/test_case.py:1: imports eval.heldout",
        "tests/t1_unit/test_ids.py:1: imports eval.heldout.generator",
        "tests/t1_unit/test_ids.py:1: imports eval.heldout.generator.build",
        "tests/t1_unit/test_phone.py:2: imports eval.heldout.scorer",
        "run_batch.py:1: imports eval.heldout.scorer",
    ]
    assert by_unreadable(tmp_path) == [
        "ploni/detect/loader.py:2: imports a name that cannot be read",
        "tests/t1_unit/test_walk.py:3: imports a name that cannot be read",
    ]


def test_ec4_every_listed_file_exists() -> None:
    assert sorted(name for name in OWN | UNREADABLE_ALLOWED if not (ROOT / name).is_file()) == []


def test_b1_a_tree_with_no_guarded_folder(tmp_path: Path) -> None:
    make_tree(tmp_path, ("scripts/helper.py",))
    assert by_text(tmp_path) == []
    assert by_import(tmp_path) == ["scripts/helper.py:1: imports eval.heldout.generator", "scripts/helper.py:1: imports eval.heldout.generator.build"]
    assert by_unreadable(tmp_path) == []
