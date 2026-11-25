"""Tests that each workflow is checked out as git stores it: no attribute rewrites it, none is a link.

Why: the pin tests read a workflow as git checked it out (tests/workflow_lines.py), and GitHub
runs the file as git stores it. A .gitattributes line can make the two differ, and .gitattributes
is no .py file, so the changed-paths check lets it share a PR with a workflow. The review of #240
(finding 1) measured it on the laptop's git: with `working-tree-encoding=ASCII//TRANSLIT` a stored
no-break space before `#|| true` is written as a space on checkout, the reader cuts ` #|| true`
as a comment and the pin passes, while YAML runs the stored line with `|| true`. A workflow
stored as a symbolic link is read through the link, another file than the one GitHub runs (the
same review, finding 2). Issue #239.

Three things are asked of git, for every file it stores under .github/workflows:
- the mode it is stored with: a regular file, not a link and not a submodule;
- the attributes working-tree-encoding, filter and ident, by which git rewrites a file on
  checkout. They are asked twice, of the .gitattributes files on disk and of the stored ones
  (`--cached`): a checkout reads the stored ones, and one more line can rewrite .gitattributes
  itself on checkout so that the copy on disk says nothing (the review of this file, finding 2);
- the stored bytes themselves, compared with the file on disk, line ends apart: whatever
  rewrote the file, by a way known here or not, the two then differ.

Equivalence classes, each on a small repository made in a temporary folder, G1 also on this
repository, G5 only there:
  G1 no attribute set for a workflow, stored as a regular file (100644 or executable, 100755),
     the same bytes on disk, also with CRLF line ends on disk; a repository with no workflow:
     no problem
  G2 working-tree-encoding, filter or ident set for a workflow: by its path, by a pattern that
     takes it in (`*.yml`, `.github/**`), by a macro, in a .gitattributes beside it, or only in
     the stored .gitattributes while the one on disk says nothing: a problem that names the
     file, the attribute and its value
  G3 an attribute that does not rewrite the file on checkout beyond its line ends (text, eol),
     or one of the three explicitly unset (`-filter`), or set for other files: no problem
  G4 a workflow stored as a symbolic link (120000) or as a submodule (160000): one problem, which
     names the file and the mode
  G5 the list is not empty: this repository's pr-checks.yml is among the files read, so that G1
     cannot pass by reading nothing
  G6 a workflow whose bytes on disk are not the stored ones: one problem, which names the file
Hebrew and document axes: do not apply; the input is git's answer about workflow files.
Known limits: G6 compares with the index, so a workflow edited and not yet staged is red until
it is staged; on GitHub the index is the commit under test. git is asked in the checkout the
suite runs in, so its .git/info/attributes and the user's own attributes file count too; a PR
can set neither on GitHub's runner. git-lfs works through `filter`, so it is covered by that
name. This test runs in the fast suite only: the fast-pin job, which reads the PR's fast.yml
outside it, has its own case in tests/t1_unit/test_fast_workflow.py (F2). Whether GitHub's runner
writes a no-break space as a space under that encoding was not measured. A PR that edits this
file holds a .py file, so it is no workflow-only PR.
"""

from pathlib import Path

import pytest

from scripts.check_commit_order import git

REPOSITORY = Path(__file__).resolve().parents[2]
WORKFLOWS = ".github/workflows"
# What git rewrites a file by on checkout, line ends apart: an encoding, a smudge filter
# (git-lfs is one), $Id$.
ATTRIBUTES = ("working-tree-encoding", "filter", "ident")
REGULAR_MODES = ("100644", "100755")
WORKFLOW = "name: x\non:\n  pull_request:\njobs:\n  x:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: true\n"
ADD = ["-c", "core.autocrlf=false", "-c", "core.symlinks=true", "add", "-A"]
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


def _attribute_problems(repository: Path, paths: list[str]) -> list[str]:
    """Return one line for each path and attribute of ATTRIBUTES that git reports with a value.

    Why: git is asked of the attribute files on disk and of the stored ones; a checkout reads
    the stored ones (the module docstring). Contract: "unspecified" and "unset" are no value.
    """
    answers = [git(["check-attr", *where, "-z", *ATTRIBUTES, "--", *paths], repository).split("\0") for where in ([], ["--cached"])]
    triples = [triple for fields in answers for triple in zip(fields[0::3], fields[1::3], fields[2::3], strict=False)]
    return list(dict.fromkeys(f"{path}: {name} is {value}" for path, name, value in triples if value not in ("unspecified", "unset")))


def _byte_problems(repository: Path, paths: list[str]) -> list[str]:
    """Return one line for each path whose bytes on disk are not the stored ones, line ends apart."""
    problems = []
    for path in paths:
        stored = git(["cat-file", "blob", f":{path}"], repository).replace("\r\n", "\n")
        on_disk = (repository / path).read_bytes().decode("utf-8", errors="replace").replace("\r\n", "\n")
        if stored != on_disk:
            problems.append(f"{path}: on disk it is not the file git stores (stage it if you are editing it)")
    return problems


def _problems(repository: Path) -> list[str]:
    """Return why a workflow of the repository is not checked out as git stores it.

    Why: a pin reads the checked-out file; what GitHub runs is the stored one (issue #239).
    Contract: repository, a git checkout. Returns one line for each file stored as anything but a
    regular file, then the lines of _attribute_problems and of _byte_problems for the regular
    ones; empty when none. Raises CalledProcessError when git fails. Known limits: those of the
    module docstring.
    """
    stored = _stored(repository)
    regular = [path for mode, path in stored if mode in REGULAR_MODES]
    problems = [f"{path}: stored with mode {mode}, not as a regular file" for mode, path in stored if mode not in REGULAR_MODES]
    if not regular:
        return problems
    return problems + _attribute_problems(repository, regular) + _byte_problems(repository, regular)


def repository_with(tmp_path: Path, attributes: str = "", beside: bool = False) -> Path:
    """Make a repository with one workflow, a.yml, staged, and then the given .gitattributes text, staged.

    The workflow is staged first, so that no attribute touches it on the way in: the cases ask
    what git says about it, not what git does with an encoding this machine may not know.
    """
    folder = tmp_path / WORKFLOWS
    folder.mkdir(parents=True)
    (folder / "a.yml").write_text(WORKFLOW, encoding="utf-8", newline="\n")
    git(["init", "-q"], tmp_path)
    git(ADD, tmp_path)
    if attributes:
        ((folder if beside else tmp_path) / ".gitattributes").write_text(attributes, encoding="utf-8", newline="\n")
        git(ADD, tmp_path)
    return tmp_path


def test_g1_g5_this_repository() -> None:
    assert f"{WORKFLOWS}/pr-checks.yml" in [path for _, path in _stored(REPOSITORY)]
    assert _problems(REPOSITORY) == []


def test_g1_no_attribute(tmp_path: Path) -> None:
    assert _problems(repository_with(tmp_path, "# nothing set\n")) == []


def test_g1_executable_and_crlf_on_disk(tmp_path: Path) -> None:
    repository = repository_with(tmp_path)
    git(["update-index", "--chmod=+x", f"{WORKFLOWS}/a.yml"], repository)
    (repository / WORKFLOWS / "a.yml").write_bytes(WORKFLOW.replace("\n", "\r\n").encode("utf-8"))
    assert [mode for mode, _ in _stored(repository)] == ["100755"]
    assert _problems(repository) == []


def test_g1_no_workflow(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("x\n", encoding="utf-8", newline="\n")
    git(["init", "-q"], tmp_path)
    git(ADD, tmp_path)
    assert _stored(tmp_path) == []
    assert _problems(tmp_path) == []


@pytest.mark.parametrize(
    ("attributes", "beside", "problem"),
    [
        (f"{WORKFLOWS}/a.yml working-tree-encoding=ASCII//TRANSLIT\n", False, "working-tree-encoding is ASCII//TRANSLIT"),
        ("*.yml working-tree-encoding=ISO-8859-1\n", False, "working-tree-encoding is ISO-8859-1"),
        ("*.yml filter=rewrite\n", False, "filter is rewrite"),
        (".github/** ident\n", False, "ident is set"),
        ("[attr]mine filter=mine\n*.yml mine\n", False, "filter is mine"),
        ("a.yml ident\n", True, "ident is set"),
    ],
    ids=["by-path", "by-extension", "filter", "ident-by-folder", "macro", "beside-the-workflow"],
)
def test_g2_an_attribute_that_rewrites_the_file(tmp_path: Path, attributes: str, beside: bool, problem: str) -> None:
    assert _problems(repository_with(tmp_path, attributes, beside)) == [f"{WORKFLOWS}/a.yml: {problem}"]


def test_g2_set_in_the_stored_attributes_only(tmp_path: Path) -> None:
    repository = repository_with(tmp_path, "*.yml working-tree-encoding=ASCII//TRANSLIT\n")
    (repository / ".gitattributes").write_text("# nothing set\n", encoding="utf-8", newline="\n")
    assert _problems(repository) == [f"{WORKFLOWS}/a.yml: working-tree-encoding is ASCII//TRANSLIT"]


@pytest.mark.parametrize("attributes", ["*.yml text eol=lf\n", "*.yml -filter -ident -working-tree-encoding\n", "*.py filter=x ident\n"], ids=["line-ends", "unset", "other-files"])
def test_g3_an_attribute_that_does_not(tmp_path: Path, attributes: str) -> None:
    assert _problems(repository_with(tmp_path, attributes)) == []


def test_g4_a_workflow_stored_as_a_link(tmp_path: Path) -> None:
    repository = repository_with(tmp_path)
    (repository / WORKFLOWS / "link.yml").symlink_to("a.yml")
    git(ADD, repository)
    assert _problems(repository) == [f"{WORKFLOWS}/link.yml: stored with mode 120000, not as a regular file"]


def test_g4_a_workflow_stored_as_a_submodule(tmp_path: Path) -> None:
    repository = repository_with(tmp_path)
    git(["update-index", "--add", "--cacheinfo", f"160000,{'1' * 40},{WORKFLOWS}/sub"], repository)
    assert _problems(repository) == [f"{WORKFLOWS}/sub: stored with mode 160000, not as a regular file"]


def test_g6_other_bytes_on_disk_than_stored(tmp_path: Path) -> None:
    repository = repository_with(tmp_path)
    (repository / WORKFLOWS / "a.yml").write_text(WORKFLOW.replace("run: true", "run: true #|| true"), encoding="utf-8", newline="\n")
    assert _problems(repository) == [f"{WORKFLOWS}/a.yml: on disk it is not the file git stores (stage it if you are editing it)"]
