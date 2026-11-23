"""Module suite for scripts/check_commit_order.py: the script run as a program on a real git history.

Why: a workflow will see only the exit code of `python -m scripts.check_commit_order <base>
<head>`, run in the checkout. The unit tests judge lists of commits; only a run against git
shows that the commits arrive oldest first, each with what it touched, that a merge of main is
left out, that a deletion and a rename arrive as such, and that a Hebrew name arrives whole.

Matrix:
  M1  the test file in one commit, the module in the next        exit 0, nothing written
  M2  the module first, its test file next                       exit 1, one line
  M3  the module and its test file in one commit                 exit 1, one line
  M4  the branch merges main, which changed a module after the branch was cut    exit 0: the
      merge and main's commits are not the branch's; commits() leaves the merge out
  M5  a module deleted, with no test                             exit 0
  M6  a module renamed, with no test                             exit 1, the new name only
  M7  a Hebrew module with its Hebrew test file first; then one with none    exit 0; exit 1,
      the name whole
  M8  a revision git does not know                               exit not 0, git's "fatal" line;
                                                                 commits() raises
                                                                 CalledProcessError
  M9  commits() gives the commits oldest first, with the status of each path (added, modified,
      deleted)
  M10 documents only                                             exit 0
  M11 main moved on after the branch, with a module and no test, and no merge    exit 0: only
      the branch's commits count (base..head, not base...head)
  M12 the branch merges another branch, cut from the base and not merged into main    exit 1,
      one line naming the merge and that branch's tip; merge_problems() gives the same line
  M13 GitHub's merge of the PR into main: run on HEAD^1 HEAD^2 (the PR's own commits)    exit 0;
      on HEAD^1 HEAD the merge itself brings in the PR, which main does not hold    exit 1
  M14 a test commit that also changes another module, then the module    exit 1: the other
      module's missing test, then the test commit, by module
  M15 git() returns what git wrote (a hash); raises CalledProcessError on a revision git does
      not know

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import check_commit_order as check
from scripts.check_commit_order import Commit

REPOSITORY = Path(__file__).resolve().parents[2]
GIT = ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "core.autocrlf=false"]
MODULE = "ploni/safety/atomic.py"
TEST = "tests/t1_unit/test_safety_atomic.py"


def git(folder: Path, *args: str) -> str:
    """Run one git command in folder and return its output, failing the test when git fails."""
    done = subprocess.run([*GIT, *args], cwd=folder, check=True, capture_output=True, timeout=60)  # noqa: S603 fixed argv, no shell
    return done.stdout.decode("utf-8").strip()


def commit(folder: Path, *paths: str) -> str:
    """Write each path with a new line, commit them all, and return the commit's hash."""
    for path in paths:
        target = folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as file:
            file.write("x\n")
    git(folder, "add", "-A")
    git(folder, "commit", "-q", "-m", "change")
    return git(folder, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Return a git repository on main with one commit holding a module, tagged base."""
    git(tmp_path, "init", "-q")
    commit(tmp_path, "ploni/types.py")
    git(tmp_path, "branch", "-M", "main")
    git(tmp_path, "tag", "base")
    return tmp_path


def run(folder: Path, *revisions: str) -> subprocess.CompletedProcess[str]:
    """Run the script in folder as a workflow would."""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(REPOSITORY)
    # This reader decodes UTF-8, as GitHub's runners write (the script's Known limits).
    environment["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(  # noqa: S603 fixed argv, no shell
        [sys.executable, "-m", "scripts.check_commit_order", *revisions],
        cwd=folder,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )


def no_test(module: str, sha: str) -> str:
    """Return the line of a module with no test file touched before its first commit."""
    return f"{module}: no test file for it is touched before its first commit, {sha[:12]}"


def test_m1_test_first(repo: Path) -> None:
    commit(repo, TEST)
    commit(repo, MODULE)
    done = run(repo, "base", "HEAD")
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_m2_module_first(repo: Path) -> None:
    first = commit(repo, MODULE)
    commit(repo, TEST)
    done = run(repo, "base", "HEAD")
    assert done.returncode == 1 and done.stdout == ""
    assert done.stderr.splitlines() == [no_test(MODULE, first)]


def test_m3_one_commit(repo: Path) -> None:
    sha = commit(repo, MODULE, TEST)
    done = run(repo, "base", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == [no_test(MODULE, sha)]


def test_m4_a_merge_of_main(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "feat")
    first = commit(repo, TEST)
    git(repo, "checkout", "-q", "main")
    commit(repo, "scripts/other.py", "ploni/types.py")
    git(repo, "checkout", "-q", "feat")
    git(repo, "merge", "-q", "--no-ff", "--no-edit", "main")
    second = commit(repo, MODULE)
    done = run(repo, "main", "feat")
    assert (done.returncode, done.stderr) == (0, "")
    assert check.commits("main", "feat", repo) == [Commit(first, {TEST: "A"}), Commit(second, {MODULE: "A"})]


def test_m5_a_deleted_module(repo: Path) -> None:
    (repo / "ploni" / "types.py").unlink()
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "delete")
    done = run(repo, "base", "HEAD")
    assert (done.returncode, done.stderr) == (0, "")


def test_m6_a_renamed_module(repo: Path) -> None:
    git(repo, "mv", "ploni/types.py", "ploni/kinds.py")
    git(repo, "commit", "-q", "-m", "rename")
    sha = git(repo, "rev-parse", "HEAD")
    done = run(repo, "base", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == [no_test("ploni/kinds.py", sha)]


def test_m7_hebrew_names(repo: Path) -> None:
    commit(repo, "tests/t1_unit/test_שם.py")
    commit(repo, "ploni/שם.py")
    assert run(repo, "base", "HEAD").returncode == 0
    sha = commit(repo, "ploni/אחר.py")
    done = run(repo, "base", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == [no_test("ploni/אחר.py", sha)]


def test_m8_an_unknown_revision(repo: Path) -> None:
    done = run(repo, "no-such-revision", "HEAD")
    assert done.returncode != 0
    assert "fatal" in done.stderr
    with pytest.raises(subprocess.CalledProcessError):
        check.commits("no-such-revision", "HEAD", repo)


def test_m9_commits_oldest_first(repo: Path) -> None:
    first = commit(repo, TEST, "docs/a.md")
    second = commit(repo, "docs/a.md")
    (repo / "ploni" / "types.py").unlink()
    third = commit(repo, MODULE)
    assert check.commits("base", "HEAD", repo) == [
        Commit(first, {"docs/a.md": "A", TEST: "A"}),
        Commit(second, {"docs/a.md": "M"}),
        Commit(third, {MODULE: "A", "ploni/types.py": "D"}),
    ]


def test_m10_documents_only(repo: Path) -> None:
    commit(repo, "docs/a.md")
    done = run(repo, "base", "HEAD")
    assert (done.returncode, done.stderr) == (0, "")


def test_m11_main_moved_on_after_the_branch(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "feat")
    commit(repo, TEST)
    commit(repo, MODULE)
    git(repo, "checkout", "-q", "main")
    commit(repo, "scripts/other.py")
    done = run(repo, "main", "feat")
    assert (done.returncode, done.stderr) == (0, "")


def foreign(merge: str, parent: str, base: str) -> str:
    """Return the line of a merge that brings in a commit the base does not hold."""
    return f"{merge[:12]}: merges {parent[:12]}, which {base} does not hold; merge only main into the branch"


def test_m12_a_merge_of_another_branch(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "other")
    tip = commit(repo, "tests/t1_unit/test_other.py")
    git(repo, "checkout", "-q", "main")
    git(repo, "checkout", "-q", "-b", "feat")
    commit(repo, TEST)
    git(repo, "merge", "-q", "--no-ff", "--no-edit", "other")
    merge = git(repo, "rev-parse", "HEAD")
    commit(repo, MODULE)
    done = run(repo, "main", "feat")
    assert done.returncode == 1
    assert done.stderr.splitlines() == [foreign(merge, tip, "main")]
    assert check.merge_problems("main", "feat", repo) == [foreign(merge, tip, "main")]


def test_m13_github_merge_of_the_pr(repo: Path) -> None:
    git(repo, "checkout", "-q", "-b", "feat")
    commit(repo, TEST)
    tip = commit(repo, MODULE)
    git(repo, "checkout", "-q", "main")
    commit(repo, "docs/a.md")
    git(repo, "merge", "-q", "--no-ff", "--no-edit", "feat")
    done = run(repo, "HEAD^1", "HEAD^2")
    assert (done.returncode, done.stderr) == (0, "")
    done = run(repo, "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == [foreign(git(repo, "rev-parse", "HEAD"), tip, "HEAD^1")]


def test_m14_a_test_commit_with_code(repo: Path) -> None:
    first = commit(repo, TEST, "ploni/other.py")
    commit(repo, MODULE)
    done = run(repo, "base", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == [
        no_test("ploni/other.py", first),
        f"{first[:12]}: a test commit of {MODULE} also changes ploni/other.py; "
        "the failing tests are a commit of their own, with no implementation in it",
    ]


def test_m15_git(repo: Path) -> None:
    assert check.git(["rev-parse", "base"], repo).strip() == git(repo, "rev-parse", "base")
    with pytest.raises(subprocess.CalledProcessError):
        check.git(["rev-parse", "--verify", "no-such-revision"], repo)
