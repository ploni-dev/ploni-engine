"""Module suite for scripts/check_changed_paths.py: the script run as a program on a real git history.

Why: the workflow sees only the exit code of `python scripts/check_changed_paths.py <base>
<head>`, run in the checkout. The unit tests judge lists of paths; only a run against git
shows that the paths of a real diff reach the judgement whole (a Hebrew name, a space, a
line break, a rename, a deletion) and that the result leaves as the exit code.

Matrix:
  M1  code only between the two revisions            exit 0, nothing written
  M2  code and eval/baselines.json                   exit 1, one line on the error stream
  M3  a Hebrew .py path and a workflow               exit 1: the path is not quoted away
  M4  a .py file renamed to .txt, with a workflow    exit 1: the old name counts
  M5  a deleted .py file, with the baselines         exit 1
  M6  paths with a space and a line break, and a workflow    exit 1, the workflow named
  M7  a revision git does not know                   exit not 0 (changed() raises
                                                     CalledProcessError)
  M8  changed() returns the paths of the diff, sorted as git gives them

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts import check_changed_paths as check

REPOSITORY = Path(__file__).resolve().parents[2]
SCRIPT = REPOSITORY / "scripts" / "check_changed_paths.py"
GIT = ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "core.autocrlf=false"]


def git(folder: Path, *args: str) -> None:
    """Run one git command in folder, failing the test when git fails."""
    subprocess.run([*GIT, *args], cwd=folder, check=True, capture_output=True, timeout=60)  # noqa: S603 fixed argv, no shell


def write(folder: Path, path: str) -> None:
    """Write a one-line file at path under folder, making its folders."""
    target = folder / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x\n", encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Return a git repository with one commit holding a .py file, the baselines and a workflow."""
    git(tmp_path, "init", "-q")
    for path in ("ploni/old.py", "eval/baselines.json", ".github/workflows/fast.yml"):
        write(tmp_path, path)
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def commit(folder: Path) -> None:
    """Commit everything in folder as the head."""
    git(folder, "add", "-A")
    git(folder, "commit", "-q", "-m", "head")


def run(folder: Path, *revisions: str) -> subprocess.CompletedProcess[str]:
    """Run the script in folder as the workflow runs it."""
    return subprocess.run(  # noqa: S603 fixed argv, no shell
        [sys.executable, str(SCRIPT), *revisions], cwd=folder, capture_output=True, text=True, encoding="utf-8", timeout=60, check=False
    )


def test_m1_code_only(repo: Path) -> None:
    write(repo, "ploni/new.py")
    commit(repo)
    done = run(repo, "HEAD^1", "HEAD")
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_m2_code_and_the_baselines(repo: Path) -> None:
    write(repo, "ploni/new.py")
    (repo / "eval" / "baselines.json").write_text("{}\n", encoding="utf-8")
    commit(repo)
    done = run(repo, "HEAD^1", "HEAD")
    assert done.returncode == 1 and done.stdout == ""
    assert done.stderr.splitlines() == ["baselines changed in a code PR: eval/baselines.json"]


def test_m3_a_hebrew_python_path(repo: Path) -> None:
    write(repo, "ploni/שם.py")
    (repo / ".github" / "workflows" / "fast.yml").write_text("y\n", encoding="utf-8")
    commit(repo)
    done = run(repo, "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == ["CI workflow changed in a code PR: .github/workflows/fast.yml"]


def test_m4_a_python_file_renamed_away(repo: Path) -> None:
    git(repo, "mv", "ploni/old.py", "ploni/old.txt")
    (repo / ".github" / "workflows" / "fast.yml").write_text("y\n", encoding="utf-8")
    commit(repo)
    assert run(repo, "HEAD^1", "HEAD").returncode == 1


def test_m5_a_deleted_python_file(repo: Path) -> None:
    (repo / "ploni" / "old.py").unlink()
    (repo / "eval" / "baselines.json").write_text("{}\n", encoding="utf-8")
    commit(repo)
    assert run(repo, "HEAD^1", "HEAD").returncode == 1


def test_m6_a_space_and_a_line_break(repo: Path) -> None:
    # A line break cannot stand in a Windows file name, so both paths go into the index
    # straight, pointing at a blob, with no file on disk.
    names = ["ploni/a b.py", "ploni/a\nb.py"]
    blob = subprocess.run(  # noqa: S603 fixed argv, no shell
        [*GIT, "hash-object", "-w", "--stdin"], cwd=repo, input=b"x\n", capture_output=True, check=True, timeout=60
    ).stdout.decode("ascii").strip()
    write(repo, ".github/workflows/new.yml")
    git(repo, "add", "-A")
    entries = "".join(f"100644 {blob}\t{name}\0" for name in names).encode("utf-8")
    # Git for Windows drops a path that NTFS could not hold unless protectNTFS is off.
    index = [*GIT, "-c", "core.protectNTFS=false", "update-index", "-z", "--index-info"]
    subprocess.run(index, cwd=repo, input=entries, capture_output=True, check=True, timeout=60)  # noqa: S603 fixed argv, no shell
    git(repo, "commit", "-q", "-m", "head")
    done = run(repo, "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == ["CI workflow changed in a code PR: .github/workflows/new.yml"]
    assert sorted(check.changed("HEAD^1", "HEAD", repo)) == sorted([*names, ".github/workflows/new.yml"])


def test_m7_an_unknown_revision(repo: Path) -> None:
    assert run(repo, "no-such-revision", "HEAD").returncode != 0
    with pytest.raises(subprocess.CalledProcessError):
        check.changed("no-such-revision", "HEAD", repo)


def test_m8_changed_gives_the_diff(repo: Path) -> None:
    write(repo, "docs/a.md")
    write(repo, "ploni/new.py")
    commit(repo)
    assert check.changed("HEAD^1", "HEAD", repo) == ["docs/a.md", "ploni/new.py"]
