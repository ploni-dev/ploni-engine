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
  M10 the hook file run by sh, with a stand-in for the environment's python that exits 3, and
      one that exits 0                   the hook ends as it ends: it starts that python
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


@pytest.mark.parametrize("code", [3, 0])
def test_m10_the_hook_file_starts_the_environment_s_python(tmp_path: Path, code: int) -> None:
    shutil.copy(HOOK, tmp_path / "pre-commit")
    folder = tmp_path / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    folder.mkdir(parents=True)
    stand_in = folder / ("python.exe" if os.name == "nt" else "python")
    stand_in.write_text(f"#!/bin/sh\nexit {code}\n", encoding="utf-8", newline="\n")
    stand_in.chmod(0o755)
    sh = shutil.which("sh")
    assert sh is not None
    assert hook._run([sh, "pre-commit"], tmp_path).returncode == code
