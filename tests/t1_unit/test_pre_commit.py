"""Test matrix for scripts/pre_commit.py: the check before a commit.

steps. Equivalence classes:
  EC1  nothing staged                    the scans only: the four check tests, in one pytest run
  EC2  .py files staged, none under ploni/    ruff on those files, then the scans
  EC3  .py files under ploni/ staged     ruff on the staged .py files, mypy on the ploni/ ones, then the scans
  EC4  only files that are not .py       the scans only
Boundaries:
  B1  `x.PY`, a Python file in upper case    checked as Python (Windows imports it)
  B2  `ploni` as a prefix of another folder (`ploniX/a.py`)    ruff only, no mypy

staged. Equivalence classes:
  EC5  git's -z list of staged paths, a Hebrew name and a space among them    each path whole
  EC6  nothing staged                    no path

main. Equivalence classes:
  EC9  a step that runs out of time      it fails; the others run
  EC10 the environment git gives a hook  the tools run without GIT_INDEX_FILE, GIT_DIR and
       GIT_WORK_TREE, so that a test that runs git elsewhere cannot write into the commit's index
  EC7  every step passes                 exit 0, each step's name printed before it runs
  EC8  a step fails                      exit 1, the failing steps named at the end; every step runs

The scans are the four checks PROCESS.md 5.6 names and the model check Achia was told runs
here (2026-11-20, "Laptop run is enough (Recommended)"): CHECK_TESTS.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts import pre_commit as hook

SCANS = ("scans", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *hook.CHECK_TESTS])


def test_ec1_nothing_staged() -> None:
    assert hook.steps([]) == [SCANS]


def test_ec2_python_outside_ploni() -> None:
    assert hook.steps(["scripts/x.py", "tests/t1_unit/test_x.py"]) == [
        ("ruff", [sys.executable, "-m", "ruff", "check", "--force-exclude", "scripts/x.py", "tests/t1_unit/test_x.py"]),
        SCANS,
    ]


def test_ec3_python_under_ploni() -> None:
    assert hook.steps(["ploni/a.py", "scripts/x.py", "docs/a.md"]) == [
        ("ruff", [sys.executable, "-m", "ruff", "check", "--force-exclude", "ploni/a.py", "scripts/x.py"]),
        ("mypy", [sys.executable, "-m", "mypy", "ploni/a.py"]),
        SCANS,
    ]


def test_ec4_no_python() -> None:
    assert hook.steps(["docs/STATUS.md", ".ratchet.json"]) == [SCANS]


def test_b1_python_in_upper_case() -> None:
    assert hook.steps(["ploni/A.PY"])[0] == ("ruff", [sys.executable, "-m", "ruff", "check", "--force-exclude", "ploni/A.PY"])


def test_b2_a_folder_that_only_begins_like_ploni() -> None:
    assert [name for name, _ in hook.steps(["ploniX/a.py"])] == ["ruff", "scans"]


def test_ec5_staged_paths_whole(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hook, "_output", lambda command, cwd: "ploni/a.py\0docs/שמות שונים.md\0x y.py\0".encode())
    assert hook.staged(Path(".")) == ["ploni/a.py", "docs/שמות שונים.md", "x y.py"]


def test_ec6_nothing_staged_from_git(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hook, "_output", lambda command, cwd: b"")
    assert hook.staged(Path(".")) == []


def test_ec7_every_step_passes(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(hook, "staged", lambda cwd: ["ploni/a.py"])
    ran: list[str] = []
    monkeypatch.setattr(hook, "_status", lambda command, cwd: ran.append(command[2]) or 0)
    assert hook.main(Path(".")) == 0
    assert ran == ["ruff", "mypy", "pytest"]
    assert capsys.readouterr().out == "== ruff\n== mypy\n== scans\n"


def test_ec8_a_step_fails_and_every_step_runs(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(hook, "staged", lambda cwd: ["ploni/a.py"])
    ran: list[str] = []
    monkeypatch.setattr(hook, "_status", lambda command, cwd: ran.append(command[2]) or (1 if command[2] == "ruff" else 0))
    assert hook.main(Path(".")) == 1
    assert ran == ["ruff", "mypy", "pytest"]
    assert capsys.readouterr().out.splitlines()[-1] == "check before commit: FAILED: ruff"


def test_the_check_tests_are_the_four_named() -> None:
    assert hook.CHECK_TESTS == (
        "tests/t8_privacy/test_secrets.py",
        "tests/t8_privacy/test_imports.py",
        "tests/t0_contract/test_docstrings.py",
        "tests/t0_contract/test_third_party.py",
    )


def test_ec9_a_step_out_of_time_fails_and_the_others_run(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def slow(command: list[str], cwd: Path, *, stdout: int | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
        if command[2] == "ruff":
            raise subprocess.TimeoutExpired(command, hook.STEP_TIMEOUT_SECONDS)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(hook, "staged", lambda cwd: ["ploni/a.py"])
    monkeypatch.setattr(hook, "_run", slow)
    assert hook.main(Path(".")) == 1
    assert capsys.readouterr().out.splitlines()[-1] == "check before commit: FAILED: ruff"


def test_ec10_the_tools_run_without_the_index_git_gives_a_hook(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE"):
        monkeypatch.setenv(name, "set by git")
    monkeypatch.setenv("KEPT", "yes")
    seen: list[dict[str, str] | None] = []
    monkeypatch.setattr(hook, "_run", lambda command, cwd, *, stdout=None, env=None: seen.append(env) or subprocess.CompletedProcess(command, 0))
    assert hook._status(["tool"], Path(".")) == 0
    [env] = seen
    assert env is not None and env["KEPT"] == "yes"
    assert not {"GIT_INDEX_FILE", "GIT_DIR", "GIT_WORK_TREE"} & set(env)
