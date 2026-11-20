"""Module suite for scripts/pre_commit.py and its hook: the check run on this repository.

Why: the unit tests replace the programs; only a real run shows that the tools start from the
environment, that the four check tests pass on a clean tree, and that the hook file is one git
and a shell can run on every platform.

Matrix (the repository itself; what is staged is set by the test, so that a developer's own
staged files do not decide it):
  M1  nothing staged                       exit 0: the scans pass on the repository
  M2  a clean product file staged          exit 0: ruff, mypy and the scans pass
  M3  a staged file ruff refuses (in a temporary folder, staged by path)    exit 1, ruff named
  M5  what git says is staged, in a temporary repository: an added, a modified and a renamed
      file are staged; a deleted one, an unstaged edit and an untracked file are not
  M6  a git command that fails             CalledProcessError
  M7  a vendored file staged            exit 0: ruff leaves out what pyproject.toml excludes
  M8  under a GIT_INDEX_FILE of a commit's own    exit 0, and that index untouched
  M9  a tool's own output                reaches the screen
  M10 the hook run as git runs it (`git hook run`), with a stand-in for the environment's python
      that exits 3, and one that exits 0  the hook ends as it ends: it starts that python
  M11 the hook in a worktree with no .venv of its own   it starts the main checkout's
  M12 no .venv anywhere                  it says so on the error stream and starts python on PATH
  M14 no .venv and no python on PATH    the hook fails with 127: the commit is not made
  M13 a step that runs out of time (the real timeout, made one second)   it fails, "timed out"
  M4  the hook file                        LF line ends in the repository and on checkout
                                           (`.gitattributes`), a shell shebang, and it runs
                                           `scripts.pre_commit`
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import pre_commit as hook

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".githooks" / "pre-commit"


def test_m1_nothing_staged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hook, "staged", lambda cwd: [])
    assert hook.main(ROOT) == 0


def test_m2_a_clean_product_file(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hook, "staged", lambda cwd: ["ploni/errors.py"])
    assert hook.main(ROOT) == 0


def test_m3_a_file_ruff_refuses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text('"""A file ruff refuses: an unused import."""\n\nimport os\n', encoding="utf-8")
    monkeypatch.setattr(hook, "staged", lambda cwd: [str(bad)])
    assert hook.main(ROOT) == 1
    assert capsys.readouterr().out.splitlines()[-1] == "check before commit: FAILED: ruff"


def test_m4_the_hook_file() -> None:
    text = HOOK.read_bytes()
    assert b"\r" not in text
    assert text.startswith(b"#!/bin/sh\n")
    assert b"-m scripts.pre_commit" in text
    assert ".githooks/* text eol=lf" in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()


def git(folder: Path, *args: str) -> None:
    """Run one git command in a test repository, through the script's own helper."""
    hook._output([hook.GIT, "-c", "user.name=test", "-c", "user.email=test@example.invalid", *args], folder)


def test_m5_what_git_says_is_staged(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q")
    for name in ("kept.py", "edited.py", "moved.py", "gone.py", "later.py"):
        (tmp_path / name).write_text("x = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    (tmp_path / "edited.py").write_text("x = 2\n", encoding="utf-8")
    (tmp_path / "new.py").write_text("x = 3\n", encoding="utf-8")
    git(tmp_path, "mv", "moved.py", "renamed.py")
    git(tmp_path, "rm", "-q", "gone.py")
    git(tmp_path, "add", "edited.py", "new.py")
    (tmp_path / "later.py").write_text("x = 4\n", encoding="utf-8")
    (tmp_path / "untracked.py").write_text("x = 5\n", encoding="utf-8")
    assert sorted(hook.staged(tmp_path)) == ["edited.py", "new.py", "renamed.py"]


def test_m6_a_git_command_that_fails(tmp_path: Path) -> None:
    with pytest.raises(subprocess.CalledProcessError):
        hook._output([hook.GIT, "rev-parse", "no-such-revision"], tmp_path)


def test_m7_a_vendored_file(monkeypatch: pytest.MonkeyPatch) -> None:
    vendored = next(ROOT.glob("experiments/*/vendored/**/*.py"))
    monkeypatch.setattr(hook, "staged", lambda cwd: [vendored.relative_to(ROOT).as_posix()])
    assert hook.main(ROOT) == 0


def test_m8_under_an_index_of_a_commit_s_own(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    index = tmp_path / "commit-index"
    monkeypatch.setenv("GIT_INDEX_FILE", str(index))
    monkeypatch.setattr(hook, "staged", lambda cwd: [])
    assert hook.main(ROOT) == 0
    assert not index.exists()


def test_m9_a_tool_s_own_output_reaches_the_screen(monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(hook, "staged", lambda cwd: [])
    monkeypatch.setattr(hook, "steps", lambda paths: [("say", [sys.executable, "-c", "print('the reason, from the tool')"])])
    assert hook.main(ROOT) == 0
    assert "the reason, from the tool" in capfd.readouterr().out


def _stand_in(folder: Path, name: str, code: int) -> None:
    """Write a stand-in for python that exits with `code`, as an executable sh script."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(f"#!/bin/sh\nexit {code}\n", encoding="utf-8", newline="\n")
    (folder / name).chmod(0o755)


def _repository(folder: Path) -> Path:
    """Make a git repository with one commit and this branch's hook in .githooks/; return that folder."""
    git(folder, "init", "-q", "-b", "main")
    (folder / "a.txt").write_text("x\n", encoding="utf-8")
    git(folder, "add", "a.txt")
    git(folder, "commit", "-q", "-m", "base")
    (folder / ".githooks").mkdir()
    shutil.copy(HOOK, folder / ".githooks" / "pre-commit")
    return folder / ".githooks"


def _hook(folder: Path, hooks: Path, env: dict[str, str] | None = None) -> int:
    """Run the pre-commit hook in a repository as git runs it before a commit; return its exit code."""
    return hook._run([hook.GIT, "-c", f"core.hooksPath={hooks}", "hook", "run", "pre-commit"], folder, env=env).returncode


VENV_PYTHON = Path(".venv", "Scripts", "python.exe") if os.name == "nt" else Path(".venv", "bin", "python")


@pytest.mark.parametrize("code", [3, 0])
def test_m10_the_hook_starts_the_environment_s_python(tmp_path: Path, code: int) -> None:
    hooks = _repository(tmp_path)
    _stand_in(tmp_path / VENV_PYTHON.parent, VENV_PYTHON.name, code)
    assert _hook(tmp_path, hooks) == code


def test_m11_in_a_worktree_the_hook_starts_the_main_checkout_s_python(tmp_path: Path) -> None:
    main = tmp_path / "main"
    main.mkdir()
    hooks = _repository(main)
    _stand_in(main / VENV_PYTHON.parent, VENV_PYTHON.name, 4)
    git(main, "worktree", "add", "-q", str(tmp_path / "wt"))
    assert _hook(tmp_path / "wt", hooks) == 4


def test_m12_with_no_environment_the_hook_says_so_and_runs_python_on_path(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    hooks = _repository(tmp_path)
    bin_folder = tmp_path / "bin"
    _stand_in(bin_folder, "python", 5)
    env = {**os.environ, "PATH": f"{bin_folder}{os.pathsep}{os.environ['PATH']}"}
    assert _hook(tmp_path, hooks, env) == 5
    assert "no .venv found here or in the main checkout" in capfd.readouterr().err


def test_m13_a_step_out_of_time(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(hook, "STEP_TIMEOUT_SECONDS", 1)
    assert hook._status([sys.executable, "-c", "import time; time.sleep(10)"], ROOT) == 1
    assert "timed out after 1 seconds" in capsys.readouterr().out


def test_m14_with_no_python_at_all_the_hook_fails(tmp_path: Path) -> None:
    hooks = _repository(tmp_path)
    empty = tmp_path / "empty"
    empty.mkdir()
    # 127: the shell found no python to start (exec: python: not found), not some other failure.
    assert _hook(tmp_path, hooks, {**os.environ, "PATH": str(empty)}) == 127
