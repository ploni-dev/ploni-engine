"""Tests that each workflow is checked out as git stores it: no attribute rewrites it, none is a link.

Why: the pin tests read a workflow as git checked it out (tests/workflow_lines.py), and GitHub
runs the file as git stores it. A .gitattributes line can make the two differ, and .gitattributes
is no .py file, so the changed-paths check lets it share a PR with a workflow. The review of #240
(finding 1) measured it on the laptop's git: with `working-tree-encoding=ASCII//TRANSLIT` a stored
no-break space before `#|| true` is written as a space on checkout, the reader cuts ` #|| true`
as a comment and the pin passes, while YAML runs the stored line with `|| true`. A workflow
stored as a symbolic link is read through the link, another file than the one GitHub runs (the
same review, finding 2). Issue #239.

Equivalence classes, each on a small repository made in a temporary folder, G1 and G5 also on
this repository:
  G1 no attribute set for a workflow: no problem
  G2 working-tree-encoding, filter or ident set for a workflow: by its path, by a pattern that
     takes it in (`*.yml`, `.github/**`), by a macro, or in a .gitattributes beside it: one
     problem, which names the file, the attribute and its value
  G3 an attribute that does not rewrite the file on checkout beyond its line ends (text, eol),
     or one of the three explicitly unset (`-filter`): no problem
  G4 a workflow stored as a symbolic link (mode 120000): one problem, which names the file
  G5 the list is not empty: this repository's pr-checks.yml is among the files read, so that G1
     cannot pass by reading nothing
Hebrew and document axes: do not apply; the input is git's answer about workflow files.
Known limits: git is asked in the checkout the suite runs in, so its .git/info/attributes and the
user's own attributes file count too; a PR can set neither on GitHub's runner. git-lfs works
through `filter`, so it is covered by that name. Whether GitHub's runner writes a no-break space
as a space under that encoding was not measured; this test refuses the attribute wherever the
suite runs. A PR that edits this file holds a .py file, so it is no workflow-only PR.
"""

from pathlib import Path

import pytest

from scripts.check_commit_order import git

REPOSITORY = Path(__file__).resolve().parents[2]
WORKFLOWS = ".github/workflows"
# What git rewrites a file by on checkout: an encoding, a smudge filter (git-lfs is one), $Id$.
ATTRIBUTES = ("working-tree-encoding", "filter", "ident")
REGULAR_MODES = ("100644", "100755")
WORKFLOW = "name: x\non:\n  pull_request:\njobs:\n  x:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: true\n"
# The names git lists as a repository's own (GIT_DIR and the rest): a test started under a hook
# would otherwise ask the hook's repository (as tests/t4_integration/test_check_reviewed_commit.py).
LOCAL_VARIABLES = git(["rev-parse", "--local-env-vars"], REPOSITORY).split()


@pytest.fixture(autouse=True)
def no_local_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop git's repository-local variables for the test, in this process and in what it starts."""
    for name in LOCAL_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def _stored(repository: Path) -> list[tuple[str, str]]:
    """Return (mode, path) of each file git stores under the workflows folder."""
    entries = [entry.split("\t", 1) for entry in git(["ls-files", "-s", "-z", "--", WORKFLOWS], repository).split("\0") if entry]
    return [(meta.split(" ")[0], path) for meta, path in entries]


def _problems(repository: Path) -> list[str]:
    """Return why a workflow of the repository is not checked out as git stores it.

    Why: a pin reads the checked-out file; what GitHub runs is the stored one (issue #239).
    Contract: repository, a git checkout. Returns one line for each file stored as anything but a
    regular file, and one for each file and attribute of ATTRIBUTES that git reports with a value
    (anything but "unspecified" and "unset"); empty when none. Raises CalledProcessError when git
    fails. Known limits: those of the module docstring.
    """
    stored = _stored(repository)
    problems = [f"{path}: stored with mode {mode}, not as a regular file" for mode, path in stored if mode not in REGULAR_MODES]
    if not stored:
        return problems
    fields = git(["check-attr", "-z", *ATTRIBUTES, "--", *[path for _, path in stored]], repository).split("\0")
    triples = zip(fields[0::3], fields[1::3], fields[2::3], strict=False)
    return problems + [f"{path}: {name} is {value}" for path, name, value in triples if value not in ("unspecified", "unset")]


def repository_with(tmp_path: Path, attributes: str, beside: bool = False) -> Path:
    """Make a repository with one workflow, a.yml, and the given .gitattributes text, all staged."""
    folder = tmp_path / WORKFLOWS
    folder.mkdir(parents=True)
    (folder / "a.yml").write_text(WORKFLOW, encoding="utf-8", newline="\n")
    ((folder if beside else tmp_path) / ".gitattributes").write_text(attributes, encoding="utf-8", newline="\n")
    git(["init", "-q"], tmp_path)
    git(["-c", "core.autocrlf=false", "-c", "core.symlinks=true", "add", "-A"], tmp_path)
    return tmp_path


def test_g1_g5_this_repository() -> None:
    assert f"{WORKFLOWS}/pr-checks.yml" in [path for _, path in _stored(REPOSITORY)]
    assert _problems(REPOSITORY) == []


def test_g1_no_attribute(tmp_path: Path) -> None:
    assert _problems(repository_with(tmp_path, "# nothing set\n")) == []


@pytest.mark.parametrize(
    ("attributes", "beside", "problem"),
    [
        (f"{WORKFLOWS}/a.yml working-tree-encoding=ASCII//TRANSLIT\n", False, "working-tree-encoding is ASCII//TRANSLIT"),
        ("*.yml working-tree-encoding=ISO-8859-1\n", False, "working-tree-encoding is ISO-8859-1"),
        ("*.yml filter=lfs\n", False, "filter is lfs"),
        (".github/** ident\n", False, "ident is set"),
        ("[attr]mine filter=mine\n*.yml mine\n", False, "filter is mine"),
        ("a.yml ident\n", True, "ident is set"),
    ],
    ids=["by-path", "by-extension", "lfs", "ident-by-folder", "macro", "beside-the-workflow"],
)
def test_g2_an_attribute_that_rewrites_the_file(tmp_path: Path, attributes: str, beside: bool, problem: str) -> None:
    assert f"{WORKFLOWS}/a.yml: {problem}" in _problems(repository_with(tmp_path, attributes, beside))


@pytest.mark.parametrize("attributes", ["*.yml text eol=lf\n", "*.yml -filter -ident -working-tree-encoding\n", "*.py filter=x ident\n"], ids=["line-ends", "unset", "other-files"])
def test_g3_an_attribute_that_does_not(tmp_path: Path, attributes: str) -> None:
    assert _problems(repository_with(tmp_path, attributes)) == []


def test_g4_a_workflow_stored_as_a_link(tmp_path: Path) -> None:
    folder = tmp_path / WORKFLOWS
    folder.mkdir(parents=True)
    (folder / "a.yml").write_text(WORKFLOW, encoding="utf-8", newline="\n")
    (folder / "link.yml").symlink_to("a.yml")
    git(["init", "-q"], tmp_path)
    git(["-c", "core.autocrlf=false", "-c", "core.symlinks=true", "add", "-A"], tmp_path)
    assert _problems(tmp_path) == [f"{WORKFLOWS}/link.yml: stored with mode 120000, not as a regular file"]
