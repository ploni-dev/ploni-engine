"""Module suite for .githooks/pre-push: the fast suite before the laptop sends a change to GitHub.

Why: `PROCESS.md` section 12 item 8: "A local `pre-push` git hook that runs the fast suite: the
free stand-in for required status checks, which GitHub Free does not enforce on a private
repository". Achia, 2026-11-20, "Yes, all four (Recommended)", of "1. Before-push check: before
the laptop sends a change to GitHub, the fast tests run, and a red result stops the send" (issue
#174). The hook is a shell script, so it is tested by running it as git runs it, with a stand-in
for the environment's python that exits with a chosen code.

Matrix (a repository in a temporary folder, the hook copied into its .githooks/):
  P1  the hook file: LF line ends, a sh script, runs `scripts/check.py`, LF on checkout too
  P2  the environment's python exits 0 or 3                   the hook exits the same
  P3  in a worktree with no .venv of its own                   the main checkout's python runs
  P4  no .venv anywhere                                         a line on the error stream, python on PATH runs
  P5  no .venv and no python on PATH                            127: the push is not made
  P6  a real `git push` to a bare repository, the suite red     refused: the remote has no new commit
  P7  the same push, the suite green                            made: the remote has the commit
Hebrew and document axes: do not apply; the input is a git push.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import pre_commit

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".githooks" / "pre-push"
# git as the check before a commit finds it, with the identity and line ends of the test repository.
GIT = [pre_commit.GIT, "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "core.autocrlf=false"]
VENV_PYTHON = Path(".venv", "Scripts", "python.exe") if os.name == "nt" else Path(".venv", "bin", "python")


def git(folder: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
    """Run one git command in a test repository through the hook script's runner; do not raise."""
    return pre_commit._run([*GIT, *args], folder, stdout=subprocess.PIPE, env=env)


def stand_in(folder: Path, name: str, code: int) -> None:
    """Write a stand-in for python that exits with `code`, as an executable sh script."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(f"#!/bin/sh\nexit {code}\n", encoding="utf-8", newline="\n")
    (folder / name).chmod(0o755)


def repository(folder: Path) -> Path:
    """Make a repository with one commit and the hook in .githooks/; return the hooks folder."""
    folder.mkdir(parents=True, exist_ok=True)
    git(folder, "init", "-q", "-b", "main")
    (folder / "a.txt").write_text("x\n", encoding="utf-8")
    git(folder, "add", "a.txt")
    git(folder, "commit", "-q", "-m", "base")
    (folder / ".githooks").mkdir()
    shutil.copy(HOOK, folder / ".githooks" / "pre-push")
    return folder / ".githooks"


def hook(folder: Path, hooks: Path, env: dict[str, str] | None = None) -> int:
    """Run the pre-push hook as git runs it before a push; return its exit code."""
    return git(folder, "-c", f"core.hooksPath={hooks}", "hook", "run", "pre-push", "--", "origin", "url", env=env).returncode


def test_p1_the_hook_file() -> None:
    text = HOOK.read_bytes()
    assert b"\r" not in text
    assert text.startswith(b"#!/bin/sh\n")
    assert b"scripts/check.py" in text
    assert ".githooks/* text eol=lf" in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("code", [3, 0])
def test_p2_the_hook_exits_as_the_suite(tmp_path: Path, code: int) -> None:
    hooks = repository(tmp_path)
    stand_in(tmp_path / VENV_PYTHON.parent, VENV_PYTHON.name, code)
    assert hook(tmp_path, hooks) == code


def test_p3_in_a_worktree_the_main_checkout_s_python(tmp_path: Path) -> None:
    hooks = repository(tmp_path / "main")
    stand_in(tmp_path / "main" / VENV_PYTHON.parent, VENV_PYTHON.name, 4)
    git(tmp_path / "main", "worktree", "add", "-q", str(tmp_path / "wt"))
    assert hook(tmp_path / "wt", hooks) == 4


def test_p4_with_no_environment_python_on_path(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    hooks = repository(tmp_path)
    stand_in(tmp_path / "bin", "python", 5)
    env = {**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"}
    assert hook(tmp_path, hooks, env) == 5
    assert "no .venv found here or in the main checkout" in capfd.readouterr().err


def test_p5_with_no_python_at_all_the_push_is_not_made(tmp_path: Path) -> None:
    hooks = repository(tmp_path)
    (tmp_path / "empty").mkdir()
    # 127: the shell found no python to start (exec: python: not found), not some other failure.
    assert hook(tmp_path, hooks, {**os.environ, "PATH": str(tmp_path / "empty")}) == 127


@pytest.mark.parametrize(("code", "made"), [(1, False), (0, True)], ids=["p6-red", "p7-green"])
def test_p6_p7_a_real_push(tmp_path: Path, code: int, made: bool) -> None:
    hooks = repository(tmp_path / "work")
    stand_in(tmp_path / "work" / VENV_PYTHON.parent, VENV_PYTHON.name, code)
    git(tmp_path, "init", "-q", "--bare", "remote.git")
    (tmp_path / "work" / "b.txt").write_text("y\n", encoding="utf-8")
    git(tmp_path / "work", "add", "b.txt")
    git(tmp_path / "work", "commit", "-q", "-m", "change")
    head = git(tmp_path / "work", "rev-parse", "HEAD").stdout.decode().strip()
    pushed = git(tmp_path / "work", "-c", f"core.hooksPath={hooks}", "push", "-q", str(tmp_path / "remote.git"), "main")
    assert (pushed.returncode == 0) is made
    remote = git(tmp_path / "remote.git", "rev-parse", "--verify", "-q", "main").stdout.decode().strip()
    assert (remote == head) is made
