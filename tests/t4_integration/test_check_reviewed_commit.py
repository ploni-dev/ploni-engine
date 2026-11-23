"""Module suite for scripts/check_reviewed_commit.py: the script run as a program on a real git history.

Why: a workflow will see only the exit code of `python -m scripts.check_reviewed_commit <base>
<head>`, run in the checkout with the PR body in PR_BODY. The unit tests read bodies; only a
run against git shows that the named commit is looked for in the PR, that a commit after it
is judged by its parents, and that the branch's own diff is compared as git stores it.

Matrix:
  M1  the reviewed commit is the head                                  exit 0, nothing written
  M2  an ordinary commit after the reviewed one                        exit 1, one line naming it
  M3  one merge of main after it, main changed another path; and two such merges    exit 0
  M4  a merge of main whose resolution changes a line of the branch's file    exit 1, the diff
      line
  M5  a merge of main whose resolution adds a file                     exit 1, the diff line
  M6  a merge of main after it, where main changed another line of a file the branch changes,
      merged clean                                                     exit 1, the diff line:
      the old content of that file differs (Known limits: it only narrows)
  M7  a merge of another branch, cut from main and not in it, after the reviewed commit    exit 1,
      a line naming that branch's commit, the oldest after the reviewed one
  M8  the named commit is not in the PR: the base itself, a commit of another branch, a hash
      the store does not hold, a commit main made after the branch was cut, and the base and
      head the same                                                    exit 1, one line
  M9  a merge of main, then an ordinary commit                         exit 1, a line naming
      the ordinary commit
  M10 main merged the wrong way: a commit on main's side merges the branch, and the branch is
      moved to it (its later parent is the branch)                     exit 1, a line naming it
  M11 a revision git does not know                                     exit not 0, git's
      "fatal" line
  M12 the reviewed commit is itself a merge of main, and the head      exit 0
  M13 merges of main before the reviewed commit, which is the head     exit 0
  M14 own_diff() gives git's raw diff, with full object names and the path; the same for the
      reviewed commit and for the merge of main of M3; history_problem() gives "" there
  M15 GitHub's merge of the PR into main: on HEAD^1 HEAD^2, the PR's own commits    exit 0;
      on HEAD^1 HEAD                                                   exit 1, the merge named
  M16 main moved on after the branch, with no merge                    exit 0
  M17 a Hebrew path changed by the branch, then a merge of main        exit 0
  M18 a merge of a newer main than the base passed (main~1 given as base)    exit 1, main's
      commit the base does not hold named first: the base must hold what was merged
  M19 the resolution changes only white space in the branch's file     exit 1, the diff line
      (git patch-id would not see it: why the trees are compared)
  M20 a body that names no commit, on a real history                   exit 1, the body's line,
      and no git line

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import check_reviewed_commit as check
from scripts import pre_commit

REPOSITORY = Path(__file__).resolve().parents[2]
GIT = [pre_commit.GIT, "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "core.autocrlf=false"]
# The names git lists as a repository's own (GIT_DIR and the rest): a test started under a hook
# would otherwise write into this repository (the review of #183, finding 3).
LOCAL_VARIABLES = pre_commit._local_variables(REPOSITORY)


@pytest.fixture(autouse=True)
def no_local_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop git's repository-local variables for the test, in this process and in what it starts."""
    for name in LOCAL_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def git(folder: Path, *args: str) -> str:
    """Run one git command in folder and return its output, failing the test when git fails."""
    done = pre_commit._run([*GIT, *args], folder, stdout=subprocess.PIPE)
    done.check_returncode()
    return done.stdout.decode("utf-8").strip()


def commit(folder: Path, path: str, text: str = "x\n") -> str:
    """Append text to a file, commit it, and return the commit's hash."""
    target = folder / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="") as file:
        file.write(text)
    git(folder, "add", "-A")
    git(folder, "commit", "-q", "-m", "change")
    return git(folder, "rev-parse", "HEAD")


def merge(folder: Path, branch: str) -> str:
    """Merge a branch into the checked-out one with a merge commit; return its hash."""
    git(folder, "merge", "-q", "--no-ff", "--no-edit", branch)
    return git(folder, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Return a git repository with one commit on main and the branch feat checked out from it."""
    git(tmp_path, "init", "-q")
    commit(tmp_path, "a.txt", "1\n2\n3\n4\n5\n")
    git(tmp_path, "branch", "-M", "main")
    git(tmp_path, "checkout", "-q", "-b", "feat")
    return tmp_path


def body(sha: str) -> str:
    """Return a PR body whose review names the commit."""
    return f"## Orientation\nGoal: x\n\n## Ponytail review\nCommit reviewed: `{sha}`, the head: Ship.\n\n## Who merges\nx\n"


def run(folder: Path, base: str, head: str, text: str) -> subprocess.CompletedProcess[str]:
    """Run the script in folder as a workflow would, with text as the PR body."""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(REPOSITORY)
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PR_BODY"] = text
    return subprocess.run(  # noqa: S603 fixed argv, no shell
        [sys.executable, "-m", "scripts.check_reviewed_commit", base, head],
        cwd=folder,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )


def outside(sha: str, base: str, head: str) -> str:
    """Return the line of a named commit that is not in the PR."""
    return f"{sha[:12]}: the commit the review names is not one of {base}..{head}"


def later(commit_sha: str, sha: str, base: str) -> str:
    """Return the line of a commit after the reviewed one that is not a merge of main."""
    return f"{commit_sha[:12]}: comes after the reviewed commit {sha[:12]} and is not a merge of {base}; review the last commit"


def differs(head: str, sha: str) -> str:
    """Return the line of a head whose own diff is not the reviewed commit's."""
    return f"the branch's own diff at {head} is not the one of the reviewed commit {sha[:12]}; review the last commit"


def main_moves(folder: Path, path: str = "c.txt", text: str = "x\n") -> str:
    """Commit on main, check feat out again, and return main's new commit."""
    git(folder, "checkout", "-q", "main")
    sha = commit(folder, path, text)
    git(folder, "checkout", "-q", "feat")
    return sha


def test_m1_the_head_is_reviewed(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    done = run(repo, "main", "feat", body(sha))
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_m2_an_ordinary_commit_after(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    after = commit(repo, "b.txt")
    done = run(repo, "main", "feat", body(sha))
    assert (done.returncode, done.stdout) == (1, "")
    assert done.stderr.splitlines() == [later(after, sha, "main")]


def test_m3_merges_of_main_after(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    main_moves(repo)
    merge(repo, "main")
    assert run(repo, "main", "feat", body(sha)).returncode == 0
    main_moves(repo, "d.txt")
    merge(repo, "main")
    done = run(repo, "main", "feat", body(sha))
    assert (done.returncode, done.stderr) == (0, "")


def test_m4_the_resolution_changes_a_line(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    main_moves(repo)
    git(repo, "merge", "-q", "--no-ff", "--no-commit", "main")
    commit(repo, "b.txt", "y\n")
    done = run(repo, "main", "feat", body(sha))
    assert done.returncode == 1
    assert done.stderr.splitlines() == [differs("feat", sha)]


def test_m5_the_resolution_adds_a_file(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    main_moves(repo)
    git(repo, "merge", "-q", "--no-ff", "--no-commit", "main")
    commit(repo, "new.txt")
    done = run(repo, "main", "feat", body(sha))
    assert done.returncode == 1
    assert done.stderr.splitlines() == [differs("feat", sha)]


def test_m6_main_changed_another_line_of_the_branch_file(repo: Path) -> None:
    (repo / "a.txt").write_text("one\n2\n3\n4\n5\n", encoding="utf-8", newline="")
    git(repo, "commit", "-q", "-am", "the first line")
    sha = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "main")
    (repo / "a.txt").write_text("1\n2\n3\n4\nfive\n", encoding="utf-8", newline="")
    git(repo, "commit", "-q", "-am", "the last line")
    git(repo, "checkout", "-q", "feat")
    merge(repo, "main")
    assert (repo / "a.txt").read_text(encoding="utf-8") == "one\n2\n3\n4\nfive\n"
    done = run(repo, "main", "feat", body(sha))
    assert done.returncode == 1
    assert done.stderr.splitlines() == [differs("feat", sha)]


def test_m7_a_merge_of_another_branch(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    git(repo, "checkout", "-q", "-b", "other", "main")
    brought = commit(repo, "d.txt")
    git(repo, "checkout", "-q", "feat")
    merge(repo, "other")
    done = run(repo, "main", "feat", body(sha))
    assert done.returncode == 1
    assert done.stderr.splitlines() == [later(brought, sha, "main")]


def test_m8_the_named_commit_is_not_in_the_pr(repo: Path) -> None:
    base = git(repo, "rev-parse", "main")
    commit(repo, "b.txt")
    git(repo, "checkout", "-q", "-b", "other", "main")
    elsewhere = commit(repo, "d.txt")
    git(repo, "checkout", "-q", "feat")
    unknown = "0123456789abcdef0123456789abcdef01234567"
    newer = main_moves(repo)
    for sha in (base, elsewhere, unknown, newer):
        done = run(repo, "main", "feat", body(sha))
        assert done.returncode == 1
        assert done.stderr.splitlines() == [outside(sha, "main", "feat")]
    done = run(repo, "feat", "feat", body(git(repo, "rev-parse", "feat")))
    assert done.stderr.splitlines() == [outside(git(repo, "rev-parse", "feat"), "feat", "feat")]


def test_m9_a_merge_then_an_ordinary_commit(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    main_moves(repo)
    merge(repo, "main")
    after = commit(repo, "b.txt")
    done = run(repo, "main", "feat", body(sha))
    assert done.returncode == 1
    assert done.stderr.splitlines() == [later(after, sha, "main")]


def test_m10_merged_the_wrong_way(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    main_moves(repo)
    git(repo, "checkout", "-q", "-b", "turned", "main")
    turned = merge(repo, "feat")
    git(repo, "branch", "-f", "feat", "turned")
    done = run(repo, "main", "feat", body(sha))
    assert done.returncode == 1
    assert done.stderr.splitlines() == [later(turned, sha, "main")]


def test_m11_an_unknown_revision(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    done = run(repo, "no-such-revision", "feat", body(sha))
    assert done.returncode != 0
    assert "fatal" in done.stderr


def test_m12_the_reviewed_commit_is_a_merge_of_main(repo: Path) -> None:
    commit(repo, "b.txt")
    main_moves(repo)
    sha = merge(repo, "main")
    done = run(repo, "main", "feat", body(sha))
    assert (done.returncode, done.stderr) == (0, "")


def test_m13_merges_before_the_reviewed_commit(repo: Path) -> None:
    commit(repo, "b.txt")
    main_moves(repo)
    merge(repo, "main")
    sha = commit(repo, "b.txt")
    done = run(repo, "main", "feat", body(sha))
    assert (done.returncode, done.stderr) == (0, "")


def test_m14_own_diff(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    blob = git(repo, "rev-parse", f"{sha}:b.txt")
    expected = f":000000 100644 {'0' * 40} {blob} A\0b.txt\0"
    assert check.own_diff(sha, "main", repo) == expected
    main_moves(repo)
    head = merge(repo, "main")
    assert check.own_diff(head, "main", repo) == expected
    assert check.history_problem(sha, "main", "feat", repo) == ""


def test_m15_githubs_merge_of_the_pr(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    main_moves(repo)
    git(repo, "checkout", "-q", "--detach", "main")
    merged = merge(repo, "feat")
    done = run(repo, "HEAD^1", "HEAD^2", body(sha))
    assert (done.returncode, done.stderr) == (0, "")
    done = run(repo, "HEAD^1", "HEAD", body(sha))
    assert done.returncode == 1
    assert done.stderr.splitlines() == [later(merged, sha, "HEAD^1")]


def test_m16_main_moved_on_without_a_merge(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    main_moves(repo)
    done = run(repo, "main", "feat", body(sha))
    assert (done.returncode, done.stderr) == (0, "")


def test_m17_a_hebrew_path(repo: Path) -> None:
    sha = commit(repo, "docs/שם.md", "שלום\n")
    main_moves(repo, "docs/אחר.md")
    merge(repo, "main")
    done = run(repo, "main", "feat", body(sha))
    assert (done.returncode, done.stderr) == (0, "")


def test_m18_a_newer_main_than_the_base(repo: Path) -> None:
    sha = commit(repo, "b.txt")
    main_moves(repo)
    newer = main_moves(repo, "d.txt")
    merge(repo, "main")
    done = run(repo, "main~1", "feat", body(sha))
    assert done.returncode == 1
    assert done.stderr.splitlines() == [later(newer, sha, "main~1")]


def test_m19_white_space_only(repo: Path) -> None:
    sha = commit(repo, "b.txt", "x\n")
    main_moves(repo)
    git(repo, "merge", "-q", "--no-ff", "--no-commit", "main")
    (repo / "b.txt").write_text("x \n", encoding="utf-8", newline="")
    git(repo, "commit", "-q", "-am", "merge")
    done = run(repo, "main", "feat", body(sha))
    assert done.returncode == 1
    assert done.stderr.splitlines() == [differs("feat", sha)]


def test_m20_a_body_that_names_no_commit(repo: Path) -> None:
    commit(repo, "b.txt")
    done = run(repo, "main", "feat", "## Ponytail review\nCommit reviewed:\n")
    assert done.returncode == 1
    assert done.stderr.splitlines() == [
        'not pasted: the "Commit reviewed:" line of ## Ponytail review names no full 40-character hash in backticks'
    ]
