"""Test matrix for scripts/check.py, the fast suite runner behind `make check`.

Equivalence classes:
  EC1  steps, no ploni/ folder        ruff, pytest; no mypy (mypy would have no file to read)
  EC2  steps, ploni/ folder exists    ruff, mypy, pytest, in that order
  EC3  the pytest step                leaves out the four full-suite tiers and no fast tier
  EC4  run, every step passes         nothing is reported as failed
  EC5  run, a middle step fails       its name is reported, and the step after it still ran
  EC6  run, every step fails          every name is reported, in order
  EC7  main, all pass / one fails     exit code 0 / exit code 1

Boundaries:
  B1  run with no steps               nothing failed

Error paths: none documented. Every step starts the interpreter that runs the script, so
"command not found" cannot happen.

Adversarial:
  A1  a failing step that also writes to stderr and exits with a code other than 1
      still counts as one failure and does not stop the run

The Hebrew and document-structure axes of the test-matrix skill do not apply: this code
handles no text and no document.
"""

import sys
from pathlib import Path

import pytest

from scripts import check

PASS = [sys.executable, "-c", "raise SystemExit(0)"]
FAIL = [sys.executable, "-c", "raise SystemExit(1)"]
FAIL_LOUDLY = [sys.executable, "-c", "import sys; print('boom', file=sys.stderr); raise SystemExit(3)"]
FULL_ONLY_TIERS = ("t4_integration", "t5_system", "t6_metrics", "t7_perf")
FAST_TIERS = ("t0_contract", "t1_unit", "t2_property", "t3_golden", "t8_privacy")


def touch(marker: Path) -> list[str]:
    """Return a command that creates the marker file and passes."""
    return [sys.executable, "-c", f"import pathlib; pathlib.Path({str(marker)!r}).touch()"]


def names(steps: list[tuple[str, list[str]]]) -> list[str]:
    """Return the step names in order."""
    return [name for name, _ in steps]


def test_ec1_no_ploni_folder_means_no_mypy_step(tmp_path: Path) -> None:
    assert names(check.steps(tmp_path)) == ["ruff", "pytest"]


def test_ec2_ploni_folder_adds_mypy_between_ruff_and_pytest(tmp_path: Path) -> None:
    (tmp_path / "ploni").mkdir()
    assert names(check.steps(tmp_path)) == ["ruff", "mypy", "pytest"]


def test_ec2_a_file_named_ploni_is_not_a_package(tmp_path: Path) -> None:
    (tmp_path / "ploni").write_text("", encoding="utf-8")
    assert names(check.steps(tmp_path)) == ["ruff", "pytest"]


def test_ec3_pytest_step_leaves_out_the_full_suite_tiers_only(tmp_path: Path) -> None:
    command = dict(check.steps(tmp_path))["pytest"]
    ignored = [arg.removeprefix("--ignore=tests/") for arg in command if arg.startswith("--ignore=")]
    assert sorted(ignored) == sorted(FULL_ONLY_TIERS)
    assert not set(ignored) & set(FAST_TIERS)
    assert "tests" in command


def test_ec3_every_step_runs_under_this_interpreter(tmp_path: Path) -> None:
    (tmp_path / "ploni").mkdir()
    for _, command in check.steps(tmp_path):
        assert command[:2] == [sys.executable, "-m"]


def test_ec4_all_steps_pass(tmp_path: Path) -> None:
    assert check.run([("a", PASS), ("b", PASS)], tmp_path) == []


def test_ec5_a_failed_step_is_named_and_the_next_one_still_runs(tmp_path: Path) -> None:
    marker = tmp_path / "ran"
    failed = check.run([("a", PASS), ("b", FAIL), ("c", touch(marker))], tmp_path)
    assert failed == ["b"]
    assert marker.exists()


def test_ec6_all_steps_fail(tmp_path: Path) -> None:
    assert check.run([("a", FAIL), ("b", FAIL)], tmp_path) == ["a", "b"]


def test_b1_no_steps(tmp_path: Path) -> None:
    assert check.run([], tmp_path) == []


def test_a1_a_loud_failure_with_another_exit_code_is_one_failure(tmp_path: Path) -> None:
    marker = tmp_path / "ran"
    failed = check.run([("loud", FAIL_LOUDLY), ("after", touch(marker))], tmp_path)
    assert failed == ["loud"]
    assert marker.exists()


def test_run_starts_each_step_in_the_given_folder(tmp_path: Path) -> None:
    command = [sys.executable, "-c", "import pathlib; pathlib.Path('here').touch()"]
    assert check.run([("cwd", command)], tmp_path) == []
    assert (tmp_path / "here").exists()


@pytest.mark.parametrize(("fake_steps", "expected"), [([("a", PASS)], 0), ([("a", PASS), ("b", FAIL)], 1)])
def test_ec7_main_exit_code(
    monkeypatch: pytest.MonkeyPatch, fake_steps: list[tuple[str, list[str]]], expected: int
) -> None:
    monkeypatch.setattr(check, "steps", lambda root: fake_steps)
    assert check.main() == expected
