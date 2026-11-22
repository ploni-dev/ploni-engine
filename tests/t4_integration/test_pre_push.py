"""Module suite for .githooks/pre-push: the fast suite before the laptop sends a change to GitHub.

Why: `PROCESS.md` section 12 item 8: "A local `pre-push` git hook that runs the fast suite: the
free stand-in for required status checks, which GitHub Free does not enforce on a private
repository". Achia, 2026-11-20, "Yes, all four (Recommended)", of "1. Before-push check: before
the laptop sends a change to GitHub, the fast tests run, and a red result stops the send" (issue
#174). The hook is a shell script, so it is tested by running it as git runs it, with a stand-in
for the environment's python that exits with a chosen code.

Matrix (a repository in a temporary folder, the hook committed in its .githooks/):
  P1  the hook file: LF line ends, a sh script, runs `scripts/check.py`, LF on checkout too
  P2  the environment's python exits 0 or 3                   the hook exits the same
  P3  in a worktree with no .venv and a commit of its own      the main checkout's python runs, on the worktree
  P4  no .venv anywhere                                         a line on the error stream, python on PATH runs
  P5  no .venv and no python on PATH                            127: the push is not made
  P6  a real `git push` to a bare repository, the suite red     refused: the remote has no new commit
  P7  the same push, the suite green                            made: the remote has the commit
  P8  a push line that deletes a remote branch (all zeros)      not a reason to refuse: the suite runs
In P2 to P4 the stand-in records the checkout it runs in and its arguments: the checkout's own
top folder (the worktree's in P3), and `scripts/check.py` alone.
Adversarial (measured on 2026-11-20, the first version of this hook): in a worktree git sets
GIT_DIR for the hook, and `git -c` sets GIT_CONFIG_PARAMETERS; passed on to the suite, a test's
`git init --bare` in a temporary folder re-initialised the real repository as bare.
  A1  the suite starts with none of git's repository-local variables (`git rev-parse --local-env-vars`)
  A2  a suite that runs `git init --bare` inside a folder of its own, from a worktree: the repository stays not bare
The commits sent must be the files checked (the review of #183, finding 1): the suite reads the
folder, so a push of anything but the folder's committed HEAD is refused before it runs.
  A3  a change in the folder not committed, the suite green     refused, exit 1, the suite not started
  A4  a real push of a branch that is not checked out           refused: the remote has no new branch
  A5  a new file not added (untracked), the suite green         refused, exit 1, the suite not started
  A6  two refs sent, HEAD first and another commit second      refused, exit 1, the suite not started
  A7  an annotated tag of another commit                        refused, exit 1, the suite not started
  P9  an annotated tag of HEAD (its object is the tag, not HEAD)    sent: the commit it names is HEAD
The module's own git commands start without git's repository-local variables, so the module
run under a hook, or from a shell with GIT_DIR set, cannot write into that repository (finding 3).
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
# The names git lists as a repository's own (GIT_DIR, GIT_CONFIG_PARAMETERS and the rest), read once.
LOCAL_VARIABLES = frozenset(
    pre_commit._run([pre_commit.GIT, "rev-parse", "--local-env-vars"], ROOT, stdout=subprocess.PIPE).stdout.decode().split()
)
# The object name git writes on the hook's stdin for a ref that is deleted.
ZEROS = "0" * 40


def _git(folder: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
    """Run one git command in a test repository; do not raise.

    Why: every test makes repositories in temporary folders, and git reads GIT_DIR and the
    other repository-local variables before its folder. Started with them, as under a hook or
    from a shell that exports GIT_DIR, the module's commands would write into that repository:
    the harm of 2026-11-20, done by a test (the review of #183, finding 3).

    Contract: folder, the working folder; args, git's arguments after the fixed identity
    options; env, the environment (os.environ when None), always passed without
    LOCAL_VARIABLES. Returns the finished process, its output captured. Raises
    subprocess.TimeoutExpired after the runner's limit.

    Known limits: it runs through `scripts/pre_commit.py`'s `_run`, so the test adds no `noqa`
    line, and that runner's timeout applies.
    """
    clean = {name: value for name, value in (os.environ if env is None else env).items() if name not in LOCAL_VARIABLES}
    return pre_commit._run([*GIT, *args], folder, stdout=subprocess.PIPE, env=clean)


def _stand_in(folder: Path, name: str, code: int) -> Path:
    """Write a stand-in for python that records where it ran and exits with `code`.

    Why: the hook is tested for what it starts and where, not for the suite itself.

    Contract: folder, where the stand-in goes (made if missing); name, its file name; code, its
    exit code. Each run writes two lines to `called` beside it: the top folder of the checkout
    it ran in, and its arguments. Returns the path of `called`.

    Known limits: the top folder is read with git from where the stand-in ran, so two folders
    of one checkout are not told apart.
    """
    folder.mkdir(parents=True, exist_ok=True)
    record = folder / "called"
    body = f'#!/bin/sh\n{{ git rev-parse --show-toplevel; echo "$*"; }} > "{record.as_posix()}"\nexit {code}\n'
    (folder / name).write_text(body, encoding="utf-8", newline="\n")
    (folder / name).chmod(0o755)
    return record


def _repository(folder: Path) -> Path:
    """Make a clean repository with the hook committed in .githooks/; return the hooks folder.

    Why: the hook refuses a checkout with changes not committed, so the hook and a .gitignore
    for the stand-ins' folders (.venv/, bin/) are part of the first commit.

    Contract: folder, made if missing. Returns folder/.githooks. Raises OSError on a write.
    """
    folder.mkdir(parents=True, exist_ok=True)
    _git(folder, "init", "-q", "-b", "main")
    (folder / "a.txt").write_text("x\n", encoding="utf-8")
    (folder / ".gitignore").write_text(".venv/\nbin/\n", encoding="utf-8")
    (folder / ".githooks").mkdir()
    shutil.copy(HOOK, folder / ".githooks" / "pre-push")
    _git(folder, "add", "a.txt", ".gitignore", ".githooks")
    _git(folder, "commit", "-q", "-m", "base")
    return folder / ".githooks"


def _hook(folder: Path, hooks: Path, env: dict[str, str] | None = None, line: str | None = None) -> int:
    """Run the pre-push hook as git runs it; return its exit code.

    Why: `git hook run` starts the hook with the variables and folder git gives it.

    Contract: folder, the checkout; hooks, the hooks folder; env, as for `_git`; line, the one
    line git writes to the hook's stdin for the ref sent, by default the checkout's HEAD sent
    to refs/heads/main. Returns the hook's exit code.
    """
    if line is None:
        line = f"refs/heads/main {_head(folder)} refs/heads/main {ZEROS}"
    sent = folder.parent / f"{folder.name}-stdin"
    sent.write_text(line + "\n", encoding="utf-8", newline="\n")
    command = ["-c", f"core.hooksPath={hooks}", "hook", "run", f"--to-stdin={sent}", "pre-push", "--", "origin", "url"]
    return _git(folder, *command, env=env).returncode


def _head(folder: Path) -> str:
    """Return the object name of the checkout's HEAD."""
    return _git(folder, "rev-parse", "HEAD").stdout.decode().strip()


def _top(folder: Path) -> str:
    """Return the top folder of the checkout at `folder`, as git prints it."""
    return _git(folder, "rev-parse", "--show-toplevel").stdout.decode().strip()


def _push(folder: Path, hooks: Path, remote: Path, branch: str) -> bool:
    """Send `branch` from `folder` to the bare `remote` with the hook on; return whether git did."""
    return _git(folder, "-c", f"core.hooksPath={hooks}", "push", "-q", str(remote), branch).returncode == 0


def test_p1_the_hook_file() -> None:
    text = HOOK.read_bytes()
    assert b"\r" not in text
    assert text.startswith(b"#!/bin/sh\n")
    assert b"scripts/check.py" in text
    assert ".githooks/* text eol=lf" in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize("code", [3, 0])
def test_p2_the_hook_exits_as_the_suite(tmp_path: Path, code: int) -> None:
    hooks = _repository(tmp_path)
    record = _stand_in(tmp_path / VENV_PYTHON.parent, VENV_PYTHON.name, code)
    assert _hook(tmp_path, hooks) == code
    assert record.read_text(encoding="utf-8").splitlines() == [_top(tmp_path), "scripts/check.py"]


def test_p3_in_a_worktree_the_main_checkout_s_python(tmp_path: Path) -> None:
    hooks = _repository(tmp_path / "main")
    record = _stand_in(tmp_path / "main" / VENV_PYTHON.parent, VENV_PYTHON.name, 4)
    _git(tmp_path / "main", "worktree", "add", "-q", str(tmp_path / "wt"))
    # A commit of the worktree's own, so its HEAD is not the main checkout's.
    (tmp_path / "wt" / "b.txt").write_text("y\n", encoding="utf-8")
    _git(tmp_path / "wt", "add", "b.txt")
    _git(tmp_path / "wt", "commit", "-q", "-m", "worktree")
    assert _hook(tmp_path / "wt", hooks) == 4
    assert record.read_text(encoding="utf-8").splitlines() == [_top(tmp_path / "wt"), "scripts/check.py"]


def test_p4_with_no_environment_python_on_path(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    hooks = _repository(tmp_path)
    record = _stand_in(tmp_path / "bin", "python", 5)
    env = {**os.environ, "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}"}
    assert _hook(tmp_path, hooks, env) == 5
    assert "no .venv found here or in the main checkout" in capfd.readouterr().err
    assert record.read_text(encoding="utf-8").splitlines() == [_top(tmp_path), "scripts/check.py"]


def test_p5_with_no_python_at_all_the_push_is_not_made(tmp_path: Path) -> None:
    hooks = _repository(tmp_path)
    (tmp_path / "empty").mkdir()
    # 127: the shell found no python to start (exec: python: not found), not some other failure.
    assert _hook(tmp_path, hooks, {**os.environ, "PATH": str(tmp_path / "empty")}) == 127


@pytest.mark.parametrize(("code", "made"), [(1, False), (0, True)], ids=["p6-red", "p7-green"])
def test_p6_p7_a_real_push(tmp_path: Path, code: int, made: bool) -> None:
    hooks = _repository(tmp_path / "work")
    _stand_in(tmp_path / "work" / VENV_PYTHON.parent, VENV_PYTHON.name, code)
    _git(tmp_path, "init", "-q", "--bare", "remote.git")
    (tmp_path / "work" / "b.txt").write_text("y\n", encoding="utf-8")
    _git(tmp_path / "work", "add", "b.txt")
    _git(tmp_path / "work", "commit", "-q", "-m", "change")
    assert _push(tmp_path / "work", hooks, tmp_path / "remote.git", "main") is made
    remote = _git(tmp_path / "remote.git", "rev-parse", "--verify", "-q", "main").stdout.decode().strip()
    assert (remote == _head(tmp_path / "work")) is made


def test_p8_a_deleted_ref_is_no_reason_to_refuse(tmp_path: Path) -> None:
    hooks = _repository(tmp_path)
    record = _stand_in(tmp_path / VENV_PYTHON.parent, VENV_PYTHON.name, 0)
    assert _hook(tmp_path, hooks, line=f"(delete) {ZEROS} refs/heads/old {_head(tmp_path)}") == 0
    assert record.is_file()


def test_a1_none_of_git_s_local_variables_reach_the_suite(tmp_path: Path) -> None:
    hooks = _repository(tmp_path / "main")
    probe = 'for v in $(git rev-parse --local-env-vars); do if env | grep -q "^$v="; then exit 7; fi; done; exit 0'
    folder = tmp_path / "main" / VENV_PYTHON.parent
    folder.mkdir(parents=True)
    (folder / VENV_PYTHON.name).write_text(f"#!/bin/sh\n{probe}\n", encoding="utf-8", newline="\n")
    (folder / VENV_PYTHON.name).chmod(0o755)
    _git(tmp_path / "main", "worktree", "add", "-q", str(tmp_path / "wt"))
    assert _hook(tmp_path / "wt", hooks) == 0


def test_a2_a_suite_that_inits_a_bare_repository_leaves_the_real_one_alone(tmp_path: Path) -> None:
    hooks = _repository(tmp_path / "main")
    folder = tmp_path / "main" / VENV_PYTHON.parent
    folder.mkdir(parents=True)
    other = (tmp_path / "other.git").as_posix()
    # As the tests that did the harm ran it: in a folder of their own, with no path argument.
    (folder / VENV_PYTHON.name).write_text(f'#!/bin/sh\nmkdir -p "{other}" && cd "{other}" && git init -q --bare\n', encoding="utf-8", newline="\n")
    (folder / VENV_PYTHON.name).chmod(0o755)
    _git(tmp_path / "main", "worktree", "add", "-q", str(tmp_path / "wt"))
    assert _hook(tmp_path / "wt", hooks) == 0
    assert _git(tmp_path / "main", "config", "--bool", "core.bare").stdout.decode().strip() == "false"
    assert (tmp_path / "other.git" / "HEAD").is_file()


def test_a3_a_change_not_committed_is_refused(tmp_path: Path) -> None:
    hooks = _repository(tmp_path)
    record = _stand_in(tmp_path / VENV_PYTHON.parent, VENV_PYTHON.name, 0)
    (tmp_path / "a.txt").write_text("changed\n", encoding="utf-8")
    assert _hook(tmp_path, hooks) == 1
    assert not record.exists()


def test_a4_a_branch_not_checked_out_is_refused(tmp_path: Path) -> None:
    hooks = _repository(tmp_path / "work")
    _stand_in(tmp_path / "work" / VENV_PYTHON.parent, VENV_PYTHON.name, 0)
    _git(tmp_path, "init", "-q", "--bare", "remote.git")
    _git(tmp_path / "work", "switch", "-q", "-c", "other")
    (tmp_path / "work" / "b.txt").write_text("y\n", encoding="utf-8")
    _git(tmp_path / "work", "add", "b.txt")
    _git(tmp_path / "work", "commit", "-q", "-m", "other")
    _git(tmp_path / "work", "switch", "-q", "main")
    assert not _push(tmp_path / "work", hooks, tmp_path / "remote.git", "other")
    assert _git(tmp_path / "remote.git", "rev-parse", "--verify", "-q", "other").returncode != 0


def test_a5_a_file_not_added_is_refused(tmp_path: Path) -> None:
    hooks = _repository(tmp_path)
    record = _stand_in(tmp_path / VENV_PYTHON.parent, VENV_PYTHON.name, 0)
    (tmp_path / "new.txt").write_text("not added\n", encoding="utf-8")
    assert _hook(tmp_path, hooks) == 1
    assert not record.exists()


def test_a6_every_ref_sent_is_checked_not_only_the_first(tmp_path: Path) -> None:
    hooks = _repository(tmp_path)
    record = _stand_in(tmp_path / VENV_PYTHON.parent, VENV_PYTHON.name, 0)
    head = _head(tmp_path)
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "other")
    other = _head(tmp_path)
    _git(tmp_path, "reset", "-q", "--hard", head)
    lines = f"refs/heads/main {head} refs/heads/main {ZEROS}\nrefs/heads/other {other} refs/heads/other {ZEROS}"
    assert _hook(tmp_path, hooks, line=lines) == 1
    assert not record.exists()


def _tag(folder: Path, name: str, commit: str) -> str:
    """Make an annotated tag of `commit`; return the tag object's name, which is not the commit's."""
    _git(folder, "tag", "-a", "-m", name, name, commit)
    return _git(folder, "rev-parse", name).stdout.decode().strip()


def test_p9_an_annotated_tag_of_head_is_sent(tmp_path: Path) -> None:
    hooks = _repository(tmp_path)
    record = _stand_in(tmp_path / VENV_PYTHON.parent, VENV_PYTHON.name, 0)
    tag = _tag(tmp_path, "v1", _head(tmp_path))
    assert tag != _head(tmp_path)
    assert _hook(tmp_path, hooks, line=f"refs/tags/v1 {tag} refs/tags/v1 {ZEROS}") == 0
    assert record.is_file()


def test_a7_an_annotated_tag_of_another_commit_is_refused(tmp_path: Path) -> None:
    hooks = _repository(tmp_path)
    record = _stand_in(tmp_path / VENV_PYTHON.parent, VENV_PYTHON.name, 0)
    base = _head(tmp_path)
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "later")
    tag = _tag(tmp_path, "v0", base)
    assert _hook(tmp_path, hooks, line=f"refs/tags/v0 {tag} refs/tags/v0 {ZEROS}") == 1
    assert not record.exists()
