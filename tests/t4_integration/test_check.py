"""Module suite for scripts/check.py: the script run as a program, from end to end.

Why: the unit tests call `steps`, `run` and `main` with stand-ins. Only a real run shows
that the script finds the repository it lies in, whatever folder it is started from.

Matrix (each repository is a temp folder holding a copy of the script, a copy of
pyproject.toml and one test):
  M1  a repository whose one test passes    exit code 0, last line "fast suite: ok"
  M2  a repository whose one test fails     exit code 1, last line "fast suite: FAILED: pytest"
Both are started from a folder outside that repository. M1 is the one that fails when the
script looks for the repository in the wrong place: it then finds no tests at all.

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import runpy
import shutil
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("test_body", "exit_code", "last_line"),
    [("pass", 0, "fast suite: ok"), ("raise AssertionError", 1, "fast suite: FAILED: pytest")],
)
def test_the_script_checks_the_repository_it_lies_in(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    test_body: str,
    exit_code: int,
    last_line: str,
) -> None:
    repository, elsewhere = tmp_path / "repository", tmp_path / "elsewhere"
    (repository / "scripts").mkdir(parents=True)
    (repository / "tests").mkdir()
    elsewhere.mkdir()
    copy = shutil.copy(REPOSITORY / "scripts" / "check.py", repository / "scripts" / "check.py")
    # Without the project's own settings ruff takes whatever configuration the machine has.
    shutil.copy(REPOSITORY / "pyproject.toml", repository)
    (repository / "tests" / "test_one.py").write_text(f"def test_one():\n    {test_body}\n", encoding="utf-8")
    monkeypatch.chdir(elsewhere)

    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(str(copy), run_name="__main__")

    assert stopped.value.code == exit_code
    assert capfd.readouterr().out.strip().splitlines()[-1] == last_line
