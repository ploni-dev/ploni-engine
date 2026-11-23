"""Module suite for scripts/guard.py: the script run as a hook, from end to end.

Why: the unit tests give each function a command or a list of checks. A hook is a
program: it reads one payload on stdin, may ask `gh`, and answers with its exit code.
Whether those parts fit together shows only when the program runs.

Matrix (each run starts the script as Claude Code does, with the payload on stdin; `gh`
is a stand-in program that is found first on PATH, answers `gh api` with the runs of the
commit and every other call with the checks, writes down the words of each call, and ends
with a fixed exit code, so no test reaches GitHub):
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
  M12 Hebrew text in the payload              read as UTF-8: a harmless command is let
                                              through, and a refusal names a Hebrew
                                              repository letter for letter, in ASCII
  M13 a merge, every check green but one required check missing    exit code 2, stderr
                                              names the missing check (issue #180)
  M14 a check red, then green again on the same trigger (a PR body edit)    exit code 0,
                                              and gh was asked for the runs of the commit
                                              that the checks name (issue #137)
  M15 a check green, then red on the same trigger    exit code 2
  M16 fast-suite red on push, green on pull_request  exit code 2: each trigger counts
  M17 the runs cannot be read: gh api ends with an error, or prints no JSON, or no runs
                                              exit code 2
  M18 the red run is not among the runs gh api lists  exit code 2: it is kept
  M19 pr-body red in the run of the newer event, green in the run of the older event whose
      job started later                           exit code 2 (the review of PR #192)

Every refusal is told from a script that never ran by its stderr: each line starts with
`guard: `. Python itself ends with 2 when it cannot open the script.

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
# The last commit of the PR, and the start times of PR #135's two ratchet runs (2026-11-19).
SHA = "64785f9cf09d42e0e296ab8400bab181b6977055"
EARLY = "2026-11-19T23:20:30Z"
LATE = "2026-11-19T23:21:47Z"
NO_RUNS = json.dumps({"workflow_runs": []})
# One green run of each check the gate asks for (scripts/guard.py, REQUIRED_CHECKS; issue #180),
# written out here so that the program is tested against the list, not against itself.
EVERY = [
    {**GREEN, "name": name} for name in ("changed-paths", "fast-suite", "nightly", "pr-body", "pr-size", "ratchet", "waiver")
]


def stand_in_gh(folder: Path, answer: str, exit_code: int = 0, runs: str = NO_RUNS, runs_exit: int = 0) -> None:
    """Write a stand-in `gh` that answers by its first word, noting the words of each call.

    `gh api` prints runs and ends with runs_exit; every other call prints answer and ends
    with exit_code. The words of each call go on a line of the file `started`.
    """
    (folder / "answer.json").write_text(answer, encoding="utf-8")
    (folder / "runs.json").write_text(runs, encoding="utf-8")
    if os.name == "nt":
        # The redirection stands first: in `echo ... 100>>file` cmd takes the 0 for a handle.
        batch = (
            '@echo off\r\n>>"%~dp0started" echo %*\r\n'
            f'if "%~1"=="api" (\r\ntype "%~dp0runs.json"\r\nexit /b {runs_exit}\r\n)\r\n'
            f'type "%~dp0answer.json"\r\nexit /b {exit_code}\r\n'
        )
        (folder / "gh.cmd").write_text(batch, encoding="utf-8", newline="")
        return
    script = folder / "gh"
    shell = (
        '#!/bin/sh\nhere="$(dirname "$0")"\necho "$*" >> "$here/started"\n'
        f'if [ "$1" = api ]; then cat "$here/runs.json"; exit {runs_exit}; fi\n'
        f'cat "$here/answer.json"\nexit {exit_code}\n'
    )
    script.write_text(shell, encoding="utf-8", newline="\n")
    script.chmod(0o755)


def hook(stdin: bytes, gh_folder: Path) -> subprocess.CompletedProcess[bytes]:
    """Run the script with stdin as its payload and gh_folder first on PATH."""
    env = dict(os.environ, PATH=str(gh_folder) + os.pathsep + os.environ["PATH"])
    return subprocess.run([sys.executable, str(SCRIPT)], input=stdin, capture_output=True, env=env, check=False)  # noqa: S603 the script under test


def payload(tool: str, **tool_input: str) -> bytes:
    """Return a PreToolUse payload as Claude Code writes it, in UTF-8."""
    return json.dumps({"tool_name": tool, "tool_input": tool_input}, ensure_ascii=False).encode("utf-8")


def rollup(*checks: dict[str, str]) -> str:
    """Return what `gh pr view --json headRefOid,statusCheckRollup` prints for these checks."""
    return json.dumps({"headRefOid": SHA, "statusCheckRollup": list(checks)})


def job(name: str, conclusion: str, started: str, run: int) -> dict[str, str]:
    """Return a finished workflow job of run, in a workflow of its own name, as the rollup lists it."""
    url = f"https://github.com/o/r/actions/runs/{run}/job/{run + 1000}"
    finished = {**GREEN, "name": name, "conclusion": conclusion, "workflowName": name}
    return {**finished, "startedAt": started, "detailsUrl": url}


def runs(*events: tuple[int, str, str]) -> str:
    """Return what `gh api .../actions/runs` prints for runs given as (id, event, created_at)."""
    listed = [{"id": run, "event": event, "created_at": created} for run, event, created in events]
    return json.dumps({"workflow_runs": listed})


def but(name: str) -> list[dict[str, str]]:
    """Return EVERY without the check of that name."""
    return [check for check in EVERY if check["name"] != name]


def refused(done: subprocess.CompletedProcess[bytes]) -> bytes:
    """Return the stderr of a run, after checking that the script itself refused the call.

    Python too ends with 2 when it cannot open the script, so the exit code alone does not
    tell a refusal from a script that never ran. Every line of a refusal starts with `guard: `.
    """
    assert done.returncode == 2
    lines = done.stderr.splitlines()
    assert lines
    assert all(line.startswith(b"guard: ") for line in lines)
    return done.stderr


def test_m1_a_merge_with_every_check_green_is_let_through(tmp_path: Path) -> None:
    stand_in_gh(tmp_path, rollup(*EVERY, GREEN))
    done = hook(payload("Bash", command=MERGE), tmp_path)
    assert done.returncode == 0
    assert done.stderr == b""
    assert (tmp_path / "started").exists()


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])  # M2, M6
def test_m2_a_merge_with_a_red_check_is_refused(tmp_path: Path, tool: str) -> None:
    stand_in_gh(tmp_path, rollup(*EVERY, RED))
    stderr = refused(hook(payload(tool, command=MERGE), tmp_path))
    assert b"PR 80 of o/r: check lint is FAILURE" in stderr


@pytest.mark.parametrize(
    ("answer", "exit_code"),
    [(rollup(), 0), (rollup(GREEN), 1), ("no pull requests found", 0), ("{}", 0)],  # M3, M4, M5
)
def test_a_merge_is_refused_when_gh_does_not_show_green_checks(tmp_path: Path, answer: str, exit_code: int) -> None:
    stand_in_gh(tmp_path, answer, exit_code)
    assert b"PR 80 of o/r" in refused(hook(payload("Bash", command=MERGE), tmp_path))


def test_m13_a_merge_with_a_required_check_missing_is_refused(tmp_path: Path) -> None:
    stand_in_gh(tmp_path, rollup(*[check for check in EVERY if check["name"] != "waiver"]))
    stderr = refused(hook(payload("Bash", command=MERGE), tmp_path))
    assert b"PR 80 of o/r: there is no waiver check on the last commit" in stderr


def test_m7_a_command_that_is_no_merge_does_not_start_gh(tmp_path: Path) -> None:
    stand_in_gh(tmp_path, rollup(RED))
    done = hook(payload("Bash", command="git status && gh pr view 80 -R o/r"), tmp_path)
    assert done.returncode == 0
    assert not (tmp_path / "started").exists()


@pytest.mark.parametrize("command", ["git push origin main", "git commit --no-verify -m x"])
def test_m8_a_push_to_main_and_a_no_verify_are_refused(tmp_path: Path, command: str) -> None:
    refused(hook(payload("PowerShell", command=command), tmp_path))


def test_m9_an_edit_of_the_waiver_file_is_refused(tmp_path: Path) -> None:
    done = hook(payload("Edit", file_path="C:\\r\\docs\\WAIVERS.md", old_string="a", new_string="b"), tmp_path)
    assert b"docs/WAIVERS.md" in refused(done)


def test_m10_an_edit_of_another_file_is_let_through(tmp_path: Path) -> None:
    assert hook(payload("Write", file_path="C:\\r\\docs\\STATUS.md", content="x"), tmp_path).returncode == 0


@pytest.mark.parametrize("stdin", [b"", b"not json", b"[]", b'"gh pr merge"', b"\xff\xfe"])
def test_m11_stdin_that_is_no_payload_is_refused(tmp_path: Path, stdin: bytes) -> None:
    refused(hook(stdin, tmp_path))


def test_m12_a_command_with_hebrew_text_is_read_as_utf8(tmp_path: Path) -> None:
    done = hook(payload("Bash", command="echo 'פלוני אלמוני'"), tmp_path)
    assert done.returncode == 0
    assert done.stderr == b""


def test_m12_a_refusal_names_a_hebrew_repository_letter_for_letter(tmp_path: Path) -> None:
    stand_in_gh(tmp_path, rollup(*EVERY, RED))
    repository = "פלוני/r"
    stderr = refused(hook(payload("Bash", command=f"gh pr merge 80 -R {repository} --squash"), tmp_path))
    written = repository.encode("ascii", "backslashreplace")
    assert written.isascii()
    assert b"PR 80 of " + written + b": check lint is FAILURE" in stderr


def test_m14_a_check_red_then_green_again_on_the_same_trigger_is_let_through(tmp_path: Path) -> None:
    checks = (job("ratchet", "FAILURE", EARLY, 1), job("ratchet", "SUCCESS", LATE, 2))
    stand_in_gh(tmp_path, rollup(*but("ratchet"), *checks), runs=runs((1, "pull_request", EARLY), (2, "pull_request", LATE)))
    done = hook(payload("Bash", command=MERGE), tmp_path)
    assert done.stderr == b""
    assert done.returncode == 0
    calls = (tmp_path / "started").read_text(encoding="utf-8")
    assert "pr view 80 -R o/r" in calls
    assert "repos/o/r/actions/runs" in calls
    assert f"head_sha={SHA}" in calls


def test_m15_a_check_green_then_red_on_the_same_trigger_is_refused(tmp_path: Path) -> None:
    checks = (job("ratchet", "SUCCESS", EARLY, 1), job("ratchet", "FAILURE", LATE, 2))
    stand_in_gh(tmp_path, rollup(*but("ratchet"), *checks), runs=runs((1, "pull_request", EARLY), (2, "pull_request", LATE)))
    assert b"PR 80 of o/r: check ratchet is FAILURE" in refused(hook(payload("Bash", command=MERGE), tmp_path))


def test_m16_fast_suite_counts_by_the_newest_run_of_each_trigger(tmp_path: Path) -> None:
    checks = (job("fast-suite", "FAILURE", EARLY, 1), job("fast-suite", "SUCCESS", LATE, 2))
    stand_in_gh(tmp_path, rollup(*but("fast-suite"), *checks), runs=runs((1, "push", EARLY), (2, "pull_request", LATE)))
    assert b"PR 80 of o/r: check fast-suite is FAILURE" in refused(hook(payload("Bash", command=MERGE), tmp_path))


@pytest.mark.parametrize(("answer", "exit_code"), [(NO_RUNS, 1), ("not json", 0), ("{}", 0)])  # M17
def test_m17_a_merge_is_refused_when_the_runs_cannot_be_read(tmp_path: Path, answer: str, exit_code: int) -> None:
    stand_in_gh(tmp_path, rollup(*EVERY), runs=answer, runs_exit=exit_code)
    assert b"PR 80 of o/r: the checks could not be read" in refused(hook(payload("Bash", command=MERGE), tmp_path))


def test_m18_a_red_run_that_gh_api_does_not_list_is_kept(tmp_path: Path) -> None:
    checks = (job("ratchet", "FAILURE", EARLY, 1), job("ratchet", "SUCCESS", LATE, 2))
    stand_in_gh(tmp_path, rollup(*but("ratchet"), *checks), runs=runs((2, "pull_request", LATE)))
    assert b"PR 80 of o/r: check ratchet is FAILURE" in refused(hook(payload("Bash", command=MERGE), tmp_path))


def test_m19_an_older_run_whose_job_starts_last_does_not_hide_the_newer_red_run(tmp_path: Path) -> None:
    stale = job("pr-body", "SUCCESS", "2026-11-23T10:06:00Z", 1)
    current = job("pr-body", "FAILURE", "2026-11-23T10:05:02Z", 2)
    events = runs((1, "pull_request", "2026-11-23T10:04:20Z"), (2, "pull_request", "2026-11-23T10:04:58Z"))
    stand_in_gh(tmp_path, rollup(*but("pr-body"), stale, current), runs=events)
    assert b"PR 80 of o/r: check pr-body is FAILURE" in refused(hook(payload("Bash", command=MERGE), tmp_path))
