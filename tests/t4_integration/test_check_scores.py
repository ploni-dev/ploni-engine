"""Module suite for scripts/check_scores.py: the check run as the workflow will run it.

Why: `CLAUDE.md`, Tests: every module gets a suite over its public surface. The unit matrix
calls `main` with its writers; this runs the module as `python -m scripts.check_scores` does
(its `__main__` block, through runpy), with the PR body in PR_BODY, and reads its exit code
and both streams. The reports are made up, in the scorer's format; none comes from the batch.

Matrix:
  M1  no drop: exit 0; the table on the output; nothing on the error stream
  M2  a made-up drop (issue 170: "shown refusing a made-up drop"): exit 1; one line on the
      error stream, with the name and both numbers
  M3  the same drop, accepted by a line in PR_BODY with a reason in Hebrew: exit 0; the reason
      on neither stream
  M4  no argument: the usage line, exit 2

Known limits: in process, not a fresh interpreter: the workflow's own start of Python is not
run here.
"""

import runpy
import sys
from pathlib import Path

import pytest

MAIN = "IL_ID             tp 45  fp 1  fn 5  partial 0  recall 0.900  precision 0.978\n"
DROPPED = "IL_ID             tp 44  fp 0  fn 6  partial 0  recall 0.880  precision 1.000\n"
REASON = "אחיה, 2026-11-27: מקובל"


def check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pr: str, body: str = "", *, argv: list[str] | None = None) -> int:
    """Run the module as a program on main's report and a PR's; return its exit code."""
    (tmp_path / "main.txt").write_text(MAIN, encoding="utf-8")
    (tmp_path / "pr.txt").write_text(pr, encoding="utf-8")
    args = [str(tmp_path / "main.txt"), str(tmp_path / "pr.txt")] if argv is None else argv
    monkeypatch.setattr(sys, "argv", ["check_scores", *args])
    monkeypatch.setenv("PR_BODY", body)
    # As a fresh `python -m` would: runpy warns when the module was imported before (by T1).
    monkeypatch.delitem(sys.modules, "scripts.check_scores", raising=False)
    with pytest.raises(SystemExit) as stop:
        runpy.run_module("scripts.check_scores", run_name="__main__")
    assert isinstance(stop.value.code, int)
    return stop.value.code


def test_m1_no_drop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert check(tmp_path, monkeypatch, MAIN) == 0
    out, err = capsys.readouterr()
    assert err == ""
    assert "IL_ID             0.900 -> 0.900           0.978 -> 0.978" in out.splitlines()


def test_m2_a_made_up_drop_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert check(tmp_path, monkeypatch, DROPPED) == 1
    assert capsys.readouterr().err == "held-out drop: IL_ID recall 0.900 -> 0.880\n"


def test_m3_an_accepted_drop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert check(tmp_path, monkeypatch, DROPPED, f"score-drop-accepted: IL_ID recall 0.900 0.880 {REASON}\n") == 0
    out, err = capsys.readouterr()
    assert err == ""
    assert REASON not in out


def test_m4_no_argument(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert check(tmp_path, monkeypatch, MAIN, argv=[]) == 2
    assert capsys.readouterr().err.startswith("usage: python -m scripts.check_scores")
