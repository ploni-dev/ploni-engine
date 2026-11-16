"""Module suite for scripts/guard.py: the script run as a hook, from end to end.

Why: the unit tests give each function a command or a list of checks. A hook is a
program: it reads one payload on stdin, may ask `gh`, and answers with its exit code.
Whether those parts fit together shows only when the program runs.

Matrix (each run starts the script as Claude Code does, with the payload on stdin; `gh`
is a stand-in program that is found first on PATH, prints a fixed answer and ends with
a fixed exit code, so no test reaches GitHub):
  M1  a merge, every check green              exit code 0, nothing on stderr
  M2  a merge, one check red                  exit code 2, stderr names the PR and the check
  M3  a merge, no check                       exit code 2
  M4  a merge, gh ends with an error          exit code 2
  M5  a merge, gh prints no JSON              exit code 2
  M6  the same merge from PowerShell          exit code 2 on red
  M7  a command that is no merge              exit code 0, and gh is not started
  M8  a push to main, a --no-verify           exit code 2
  M9  an edit of docs/WAIVERS.md              exit code 2, stderr names the file
  M10 an edit of another file                 exit code 0
  M11 stdin that is not JSON, or not an object    exit code 2
  M12 a command with Hebrew text in it        exit code 0: the payload is read as UTF-8

Known limits: the stand-in is a .cmd file on Windows and a shell script elsewhere. The
real `gh` and the real hook call of Claude Code are tried by hand on a red PR
(PROMOTION.md section 10) and are not part of this suite.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "guard.py"
MERGE = "gh pr merge 80 -R o/r --squash"
GREEN = {"__typename": "CheckRun", "name": "fast-suite", "status": "COMPLETED", "conclusion": "SUCCESS"}
RED = {"__typename": "CheckRun", "name": "lint", "status": "COMPLETED", "conclusion": "FAILURE"}


def stand_in_gh(folder: Path, answer: str, exit_code: int = 0) -> None:
    """Write a `gh` into folder that prints answer, leaves a mark and ends with exit_code."""
    (folder / "answer.json").write_text(answer, encoding="utf-8")
    (folder / "gh.cmd").write_text(
        f'@echo off\r\ntype "%~dp0answer.json"\r\necho x> "%~dp0started"\r\nexit /b {exit_code}\r\n', encoding="utf-8"
    )
    script = folder / "gh"
    script.write_text(
        f'#!/bin/sh\ncat "$(dirname "$0")/answer.json"\ntouch "$(dirname "$0")/started"\nexit {exit_code}\n',
        encoding="utf-8",
        newline="\n",
    )
    script.chmod(0o755)


def hook(stdin: bytes, gh_folder: Path) -> subprocess.CompletedProcess[bytes]:
    """Run the script with stdin as its payload and gh_folder first on PATH."""
    env = dict(os.environ, PATH=str(gh_folder) + os.pathsep + os.environ["PATH"])
    return subprocess.run([sys.executable, str(SCRIPT)], input=stdin, capture_output=True, env=env, check=False)  # noqa: S603 the script under test


def payload(tool: str, **tool_input: str) -> bytes:
    """Return a PreToolUse payload as Claude Code writes it, in UTF-8."""
    return json.dumps({"tool_name": tool, "tool_input": tool_input}, ensure_ascii=False).encode("utf-8")


def rollup(*checks: dict[str, str]) -> str:
    """Return what `gh pr view --json statusCheckRollup` prints for these checks."""
    return json.dumps({"statusCheckRollup": list(checks)})


def test_m1_a_merge_with_every_check_green_is_let_through(tmp_path: Path) -> None:
    stand_in_gh(tmp_path, rollup(GREEN, GREEN))
    done = hook(payload("Bash", command=MERGE), tmp_path)
    assert done.returncode == 0
    assert done.stderr == b""
    assert (tmp_path / "started").exists()


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])  # M2, M6
def test_m2_a_merge_with_a_red_check_is_refused(tmp_path: Path, tool: str) -> None:
    stand_in_gh(tmp_path, rollup(GREEN, RED))
    done = hook(payload(tool, command=MERGE), tmp_path)
    assert done.returncode == 2
    assert b"80" in done.stderr
    assert b"lint" in done.stderr
    assert b"FAILURE" in done.stderr


@pytest.mark.parametrize(
    ("answer", "exit_code"),
    [(rollup(), 0), (rollup(GREEN), 1), ("no pull requests found", 0), ("{}", 0)],  # M3, M4, M5
)
def test_a_merge_is_refused_when_gh_does_not_show_green_checks(tmp_path: Path, answer: str, exit_code: int) -> None:
    stand_in_gh(tmp_path, answer, exit_code)
    done = hook(payload("Bash", command=MERGE), tmp_path)
    assert done.returncode == 2
    assert b"80" in done.stderr


def test_m7_a_command_that_is_no_merge_does_not_start_gh(tmp_path: Path) -> None:
    stand_in_gh(tmp_path, rollup(RED))
    done = hook(payload("Bash", command="git status && gh pr view 80 -R o/r"), tmp_path)
    assert done.returncode == 0
    assert not (tmp_path / "started").exists()


@pytest.mark.parametrize("command", ["git push origin main", "git commit --no-verify -m x"])
def test_m8_a_push_to_main_and_a_no_verify_are_refused(tmp_path: Path, command: str) -> None:
    assert hook(payload("PowerShell", command=command), tmp_path).returncode == 2


def test_m9_an_edit_of_the_waiver_file_is_refused(tmp_path: Path) -> None:
    done = hook(payload("Edit", file_path="C:\\r\\docs\\WAIVERS.md", old_string="a", new_string="b"), tmp_path)
    assert done.returncode == 2
    assert b"docs/WAIVERS.md" in done.stderr


def test_m10_an_edit_of_another_file_is_let_through(tmp_path: Path) -> None:
    assert hook(payload("Write", file_path="C:\\r\\docs\\STATUS.md", content="x"), tmp_path).returncode == 0


@pytest.mark.parametrize("stdin", [b"", b"not json", b"[]", b'"gh pr merge"', b"\xff\xfe"])
def test_m11_stdin_that_is_no_payload_is_refused(tmp_path: Path, stdin: bytes) -> None:
    assert hook(stdin, tmp_path).returncode == 2


def test_m12_a_command_with_hebrew_text_is_read_as_utf8(tmp_path: Path) -> None:
    done = hook(payload("Bash", command="echo 'פלוני אלמוני'"), tmp_path)
    assert done.returncode == 0
    assert done.stderr == b""
