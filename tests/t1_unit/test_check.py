"""Test matrix for scripts/check.py, the fast suite runner behind `make check`.

Equivalence classes:
  EC1  steps, no ploni/ folder        ruff, a mypy step that only says it was skipped, pytest
  EC2  steps, ploni/ folder exists    ruff, mypy, pytest, in that order
  EC3  the pytest step                leaves out the four full-suite tiers and no fast tier
  EC4  run, every step passes         nothing is reported as failed
  EC5  run, a middle step fails       its name is reported, and the step after it still ran
  EC6  run, every step fails          every name is reported, in order
  EC7  main, all pass / one fails     exit code 0 / exit code 1
  EC8  what each tool is given        ruff checks the whole repository; mypy takes its files
                                      from pyproject.toml; every tool runs under this interpreter
  EC9  run, where a step starts       in the folder it was given

Boundaries:
  B1  run with no steps               nothing failed
  B2  ploni exists but is a file      as EC1: it is not a package folder

Error paths:
  E1  run, a command that cannot be started    OSError, and the steps after it do not run.
      The steps of the fast suite all start the interpreter that runs the script, so
      there it cannot happen.

The script run as a program, from end to end, is in tests/t4_integration/test_check.py.

Adversarial:
  A1  a failing step that also writes to stderr and exits with a code other than 1
      still counts as one failure and does not stop the run

The Hebrew and document-structure axes of the test-matrix skill do not apply: this code
handles no text and no document.
"""

import subprocess
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


def test_ec1_no_ploni_folder_keeps_a_mypy_step_that_says_it_was_skipped(tmp_path: Path) -> None:
    chosen = check.steps(tmp_path)
    assert names(chosen) == ["ruff", "mypy", "pytest"]
    command = dict(chosen)["mypy"]
    assert "mypy" not in command
    done = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603 the step under test
    assert done.returncode == 0
    assert "skipped" in done.stdout
    assert "ploni" in done.stdout


def test_ec2_ploni_folder_runs_mypy_between_ruff_and_pytest(tmp_path: Path) -> None:
    (tmp_path / "ploni").mkdir()
    chosen = check.steps(tmp_path)
    assert names(chosen) == ["ruff", "mypy", "pytest"]
    assert dict(chosen)["mypy"] == [sys.executable, "-m", "mypy"]


def test_b2_a_file_named_ploni_is_not_a_package_folder(tmp_path: Path) -> None:
    (tmp_path / "ploni").write_text("", encoding="utf-8")
    assert "mypy" not in dict(check.steps(tmp_path))["mypy"]


def test_ec3_pytest_step_leaves_out_the_full_suite_tiers_only(tmp_path: Path) -> None:
    command = dict(check.steps(tmp_path))["pytest"]
    ignored = [arg.removeprefix("--ignore=tests/") for arg in command if arg.startswith("--ignore=")]
    assert sorted(ignored) == sorted(FULL_ONLY_TIERS)
    assert not set(ignored) & set(FAST_TIERS)
    assert command[:4] == [sys.executable, "-m", "pytest", "tests"]


def test_ec8_ruff_checks_the_whole_repository(tmp_path: Path) -> None:
    assert dict(check.steps(tmp_path))["ruff"] == [sys.executable, "-m", "ruff", "check", "."]


@pytest.mark.parametrize("with_ploni", [False, True])
def test_ec8_every_step_runs_under_this_interpreter(tmp_path: Path, with_ploni: bool) -> None:
    if with_ploni:
        (tmp_path / "ploni").mkdir()
    for _, command in check.steps(tmp_path):
        assert command[0] == sys.executable


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


def test_e1_a_command_that_cannot_be_started_raises_oserror(tmp_path: Path) -> None:
    marker = tmp_path / "ran"
    with pytest.raises(OSError):
        check.run([("missing", ["no-such-program-of-ploni"]), ("after", touch(marker))], tmp_path)
    assert not marker.exists()


def test_ec9_run_starts_each_step_in_the_given_folder(tmp_path: Path) -> None:
    command = [sys.executable, "-c", "import pathlib; pathlib.Path('here').touch()"]
    assert check.run([("cwd", command)], tmp_path) == []
    assert (tmp_path / "here").exists()


@pytest.mark.parametrize(("fake_steps", "expected"), [([("a", PASS)], 0), ([("a", PASS), ("b", FAIL)], 1)])
def test_ec7_main_exit_code(
    monkeypatch: pytest.MonkeyPatch, fake_steps: list[tuple[str, list[str]]], expected: int
) -> None:
    monkeypatch.setattr(check, "steps", lambda root: fake_steps)
    assert check.main() == expected
