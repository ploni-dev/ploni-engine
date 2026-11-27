"""Module suite for scripts/check_phase_row.py: main() on a real git history.

Why: the check reads docs/STATUS.md at two revisions with `git show`; only a run against git
shows that each side is read at its own revision and that a revision or a file git does not
have stops the check (PROMOTION.md Level 4, #276).

Matrix:
  M1  one dated row appended                         exit 0, nothing written
  M2  a row rewritten in place (dated)               exit 1, the count line
  M3  the Date cell of the new row empty             exit 1, the date line
  M4  two commits, each appending a row: the first to the second passes, the base before both
      is refused                                     exit 0, then exit 1: each side at its own
                                                     revision
  M5  a revision git does not know                   CalledProcessError, git's "fatal" line
  M6  no docs/STATUS.md at the head                  CalledProcessError, git's "fatal" line

main() runs in the process, with the repository as the current folder, as `python -m
scripts.check_phase_row` would run it from there; git is driven through git() of
scripts/check_commit_order.py.

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import subprocess
from pathlib import Path

import pytest

from scripts import check_phase_row as check
from scripts.check_commit_order import git

IDENTITY = ["-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "core.autocrlf=false"]
TABLE = "# Status\n\n## Phases\n\n| Phase | Gate | Measured | Date | Exit demo shown |\n|---|---|---|---|---|\n"
ROW_0 = "| 0 Foundation | g | m | 2026-11-25 | yes |\n"
ROW_1 = "| 1 Detectors | g | m | 2026-12-20 | yes |\n"
ROW_2 = "| 2 Adapters | g | m | 2027-01-15 | yes |\n"


def commit(folder: Path, text: str | None) -> None:
    """Write docs/STATUS.md with text, or delete it when text is None, and commit."""
    target = folder / "docs" / "STATUS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    if text is None:
        target.unlink()
    else:
        target.write_text(text, encoding="utf-8")
    git([*IDENTITY, "add", "-A"], folder)
    git([*IDENTITY, "commit", "-q", "--allow-empty", "-m", "change"], folder)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a git repository, the current folder, whose first commit holds Phase 0's row."""
    git(["init", "-q"], tmp_path)
    commit(tmp_path, TABLE + ROW_0)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_m1_one_row_appended(repo: Path, capfd: pytest.CaptureFixture[str]) -> None:
    commit(repo, TABLE + ROW_0 + ROW_1)
    assert check.main(["HEAD^1", "HEAD"]) == 0
    assert capfd.readouterr() == ("", "")


def test_m2_a_row_rewritten_in_place(repo: Path, capfd: pytest.CaptureFixture[str]) -> None:
    commit(repo, TABLE + ROW_0.replace(" m ", " more "))
    assert check.main(["HEAD^1", "HEAD"]) == 1
    out, err = capfd.readouterr()
    assert out == ""
    assert err.splitlines() == [
        "the Phases table of docs/STATUS.md has 1 phase row(s) on the head and 1 on the base; a phase close appends exactly one"
    ]


def test_m3_the_date_cell_empty(repo: Path, capfd: pytest.CaptureFixture[str]) -> None:
    commit(repo, TABLE + ROW_0 + "| 1 Detectors | g | m | | yes |\n")
    assert check.main(["HEAD^1", "HEAD"]) == 1
    assert capfd.readouterr().err.splitlines() == [
        "the new row of the Phases table of docs/STATUS.md (1 Detectors) has no close date (YYYY-MM-DD) in its Date cell"
    ]


def test_m4_each_side_at_its_own_revision(repo: Path, capfd: pytest.CaptureFixture[str]) -> None:
    commit(repo, TABLE + ROW_0 + ROW_1)
    commit(repo, TABLE + ROW_0 + ROW_1 + ROW_2)
    assert check.main(["HEAD^1", "HEAD"]) == 0
    assert check.main(["HEAD~2", "HEAD"]) == 1
    assert capfd.readouterr().err.splitlines() == [
        "the Phases table of docs/STATUS.md has 3 phase row(s) on the head and 1 on the base; a phase close appends exactly one"
    ]


def test_m5_an_unknown_revision(repo: Path, capfd: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(subprocess.CalledProcessError):
        check.main(["no-such-revision", "HEAD"])
    assert "fatal" in capfd.readouterr().err


def test_m6_no_status_file_on_the_head(repo: Path, capfd: pytest.CaptureFixture[str]) -> None:
    commit(repo, None)
    with pytest.raises(subprocess.CalledProcessError):
        check.main(["HEAD^1", "HEAD"])
    assert "fatal" in capfd.readouterr().err
