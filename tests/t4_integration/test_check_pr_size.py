"""Module suite for scripts/check_pr_size.py: the check run on real git histories.

Why: the unit tests feed `measure` and `judge` rows by hand; only a real repository shows that
git's numstat is read as the check means it: a branch's changes since it left its base, a
rename counted on both sides, a binary file, a Hebrew file name.

Matrix (a repository made in a temporary folder; `main` run in it):
  M1  a PR within the limits                         exit 0, nothing written
  M2  a PR of 16 product files                       exit 1, the files line
  M3  a PR of 401 changed product lines                  exit 0, a warning line
  M4  what the base gained after the branch was cut  not counted
  M5  a product file renamed                         counted (git's --no-renames: a deletion and an addition)
  M6  a binary product file, and one with a Hebrew name    counted as files
  M7  a rewrite in place of 1,000 product lines (1,000 added, 1,000 deleted)    exit 1
  M8  a base git does not know                        CalledProcessError, so the run is red
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import check_pr_size as check

# git from PATH, as a full path; the identity and line ends of the test repository.
GIT = [shutil.which("git") or "git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "core.autocrlf=false"]
GIT_TIMEOUT_SECONDS = 60


def git(folder: Path, *args: str) -> str:
    """Return what one git command printed in the test repository."""
    return subprocess.run(  # noqa: S603 fixed argv, no shell
        [*GIT, *args], cwd=folder, capture_output=True, text=True, check=True, timeout=GIT_TIMEOUT_SECONDS
    ).stdout


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a repository with one commit on main and a branch `pr` cut from it, as cwd."""
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "ploni").mkdir()
    (tmp_path / "ploni" / "base.py").write_text("x = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "pr")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def commit(repo: Path, files: dict[str, str | bytes]) -> None:
    """Write the files and commit them on the current branch."""
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "change")


def test_m1_within_the_limits(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    commit(repo, {"ploni/a.py": "y = 2\n", "tests/t1_unit/test_a.py": "z = 3\n" * 900})
    assert check.main(["main", "pr"]) == 0
    assert capsys.readouterr() == ("", "")


def test_m2_sixteen_product_files(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    commit(repo, {f"ploni/m{number}.py": "y = 2\n" for number in range(16)})
    assert check.main(["main", "pr"]) == 1
    assert capsys.readouterr().err == "16 product files changed, over the hard limit of 15\n"


def test_m3_four_hundred_and_one_net_lines(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    commit(repo, {"ui/server.py": "y = 2\n" * 401})
    assert check.main(["main", "pr"]) == 0
    assert capsys.readouterr().out == "::warning::401 changed product lines, over the soft limit of 400\n"


def test_m4_what_the_base_gained_later_is_not_counted(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    commit(repo, {"ploni/a.py": "y = 2\n"})
    git(repo, "checkout", "-q", "main")
    commit(repo, {f"ploni/late{number}.py": "y = 2\n" * 100 for number in range(20)})
    git(repo, "checkout", "-q", "pr")
    assert check.main(["main", "pr"]) == 0
    assert capsys.readouterr() == ("", "")


def test_m5_a_renamed_product_file(repo: Path) -> None:
    git(repo, "mv", "ploni/base.py", "ploni/moved.py")
    git(repo, "commit", "-q", "-m", "rename")
    assert check.measure(check.numstat("main", "pr", repo)) == (2, 2, [])


def test_m6_a_binary_file_and_a_hebrew_name(repo: Path) -> None:
    commit(repo, {"ploni/weights.bin": bytes(range(256)), "ploni/שמות.py": "y = 2\n"})
    assert check.measure(check.numstat("main", "pr", repo)) == (2, 1, ["ploni/weights.bin"])


def test_m7_a_rewrite_in_place(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    git(repo, "checkout", "-q", "main")
    commit(repo, {"ploni/big.py": "".join(f"old = {n}\n" for n in range(1000))})
    git(repo, "checkout", "-q", "-B", "pr")
    git(repo, "branch", "-f", "main")
    commit(repo, {"ploni/big.py": "".join(f"new = {n}\n" for n in range(1000))})
    assert check.main(["main", "pr"]) == 1
    assert capsys.readouterr().err == "2000 changed product lines, over the hard limit of 800\n"


def test_m8_a_base_git_does_not_know(repo: Path) -> None:
    with pytest.raises(subprocess.CalledProcessError):
        check.main(["no-such-branch", "pr"])
