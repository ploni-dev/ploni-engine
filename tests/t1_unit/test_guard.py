"""Test matrix for scripts/guard.py, the script behind the Claude Code hooks.

merges(command): the `gh pr merge` commands in a shell command, as (number, repository).
  EC1   the plain form                              gh pr merge 80 -R o/r --squash
  EC2   the repository spelled --repo, --repo=, -Ro/r, or placed before `merge`
  EC3   after another command                       && ; | and a new line
  EC4   PowerShell forms                            gh.exe, a quoted full path, the call sign &
  EC5   no merge                                    gh pr view, gh pr checks, git merge, gh issue
  EC6   two merges in one command                   both are found
  B1    no number, a URL or a branch after `merge`  found, with an empty number
  B2    no repository                               found, with no repository
  B3    an empty command                            nothing
  A1    a line continued with \\ or with `           the repository on the next line is found
  A2    an unclosed quote earlier in the command    the merge after it is still found
  A3    the words on a line of their own in a here-document    found: the gate does not
        know where a here-document ends, and refuses rather than lets through
  A4    the words inside a quoted text, on one line or several    not found: an argument
  A5    upper case GH.EXE                           found

red(checks): why the checks of a PR's last commit are not green.
  EC7   two green fast-suite runs                   green
  EC8   a green fast-suite and a green commit status    green
  EC9   a finished check with any conclusion but SUCCESS    red, named with its conclusion
  EC10  a check that has not finished               red, named with its status
  EC11  a commit status in any state but SUCCESS    red
  EC12  every check green, none of them fast-suite  red
  B4    no check at all, or no list                 red
  A6    fast-suite only as a commit status, which can be set by hand    red
  A7    one of two fast-suite runs red              red
  A8    an entry with no known shape                red

push_refusals(command): a push that reaches main, or that does not say what it reaches.
  EC13  a push that names its branches, none of them main    let through
  EC14  main as the target in any spelling          main, x:main, +main, :main, refs/heads/main
  EC15  no branch named, or HEAD                    refused: the hook does not know the branch
  EC16  --all, --mirror, --branches                 refused
  EC17  git options before `push`                   -c and -C are skipped over
  EC18  not a push                                  git stash push, git status, a branch with
                                                    main in its name, local main to another branch

no_verify_refusals(command):
  EC19  --no-verify on any command                  refused
  EC20  git commit -n, alone or among short flags   refused: the same flag
  EC21  -n on other git commands, --no-edit         let through

edit_refusals(file_path):
  EC22  each protected file                         refused
  EC23  the same file with \\, in upper case, through `..`, in another checkout    refused
  EC24  any other file, also one whose name only starts or ends alike    let through

refusals(payload, fetch): one hook payload.
  EC25  a merge, from Bash and from PowerShell      green lets through, red refuses with the PR number
  EC26  a merge without number or repository        refused, and GitHub is not asked
  EC27  a command that is no merge                  GitHub is not asked
  EC28  an edit of a protected file / another file  refused / let through
  E1    the checks cannot be read (gh missing, gh fails, timeout, no JSON, no rollup key)    refused
  B5    a payload without tool_input                refused

rollup(number, repository):
  E2    gh is not installed                         OSError

The settings file:
  EC29  .claude/settings.json runs the script before Bash, PowerShell, Edit and Write, and
        turns any failure of the script into a refusal

The script run as a program, with a stand-in for gh, is in tests/t4_integration/test_guard.py.

The Hebrew and document-structure axes of the test-matrix skill do not apply: this code
handles commands and paths, no document.
"""

import json
import subprocess
from pathlib import Path

import pytest

from scripts import guard

REPOSITORY = Path(__file__).resolve().parents[2]
PLAIN = "gh pr merge 80 -R o/r --squash"


def check_run(conclusion: str = "SUCCESS", status: str = "COMPLETED", name: str = "fast-suite") -> dict[str, str]:
    """Return a check as `gh pr view --json statusCheckRollup` lists a workflow job."""
    return {"__typename": "CheckRun", "name": name, "status": status, "conclusion": conclusion}


def commit_status(state: str, context: str = "other") -> dict[str, str]:
    """Return a check as the same listing shows a commit status."""
    return {"__typename": "StatusContext", "context": context, "state": state}


def never_asked(number: str, repository: str) -> list[dict[str, str]]:
    """Stand in for GitHub in a test where GitHub must not be asked."""
    raise AssertionError(f"GitHub was asked about {number} in {repository}")


@pytest.mark.parametrize(
    ("command", "found"),
    [
        (PLAIN, [("80", "o/r")]),  # EC1
        ("gh pr merge 80 --squash --repo o/r", [("80", "o/r")]),  # EC2
        ("gh pr merge 80 --repo=o/r --squash", [("80", "o/r")]),
        ("gh pr merge 80 -Ro/r --squash", [("80", "o/r")]),
        ("gh pr -R o/r merge 80 --squash", [("80", "o/r")]),
        ("cd x && " + PLAIN, [("80", "o/r")]),  # EC3
        ("git status; " + PLAIN, [("80", "o/r")]),
        ("git status;" + PLAIN, [("80", "o/r")]),
        ("echo y | " + PLAIN, [("80", "o/r")]),
        ("git status\n" + PLAIN, [("80", "o/r")]),
        ("git status\r\n" + PLAIN, [("80", "o/r")]),
        ("gh.exe pr merge 80 -R o/r --squash", [("80", "o/r")]),  # EC4
        ('& "C:\\Program Files\\GitHub CLI\\gh.exe" pr merge 80 -R o/r --squash', [("80", "o/r")]),
        ("/usr/bin/gh pr merge 80 -R o/r", [("80", "o/r")]),
        ("gh pr view 80 -R o/r --json mergeable", []),  # EC5
        ("gh pr checks 80 -R o/r", []),
        ("git merge feat/x", []),
        ("gh issue view 69 -R o/r", []),
        ("gh pr merge 80 -R o/r --squash && gh pr merge 81 -R o/r --squash", [("80", "o/r"), ("81", "o/r")]),  # EC6
        ("gh pr merge --squash -R o/r", [("", "o/r")]),  # B1
        ("gh pr merge https://github.com/o/r/pull/80 -R o/r", [("", "o/r")]),
        ("gh pr merge feat/x -R o/r", [("", "o/r")]),
        ("gh pr merge -R o/r 80", [("", "o/r")]),
        ("gh pr merge 80 --squash", [("80", None)]),  # B2
        ("gh pr merge 80 -R", [("80", None)]),
        ("", []),  # B3
        ("gh pr merge 80 \\\n  -R o/r --squash", [("80", "o/r")]),  # A1
        ("gh pr merge 80 `\r\n  -R o/r --squash", [("80", "o/r")]),
        ("echo don't\n" + PLAIN, [("80", "o/r")]),  # A2
        ("git commit -q -F - <<'EOF'\nfix: x\n\n" + PLAIN + "\nEOF", [("80", "o/r")]),  # A3
        ('gh pr comment 5 -R o/r --body "tried gh pr merge 80 -R o/r"', []),  # A4
        ('gh pr comment 5 -R o/r --body "first line\n' + PLAIN + '\nlast line"', []),
        ("GH.EXE pr merge 80 -R o/r", [("80", "o/r")]),  # A5
    ],
)
def test_merges_finds_each_merge_command(command: str, found: list[tuple[str, str | None]]) -> None:
    assert guard.merges(command) == found


@pytest.mark.parametrize(
    "checks",
    [
        [check_run(), check_run()],  # EC7
        [check_run(), commit_status("SUCCESS")],  # EC8
        [check_run(), check_run(name="lint")],
    ],
)
def test_red_is_empty_when_every_check_is_green(checks: list[dict[str, str]]) -> None:
    assert guard.red(checks) == []


@pytest.mark.parametrize(
    "conclusion",
    ["FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "NEUTRAL", "SKIPPED", "STALE", "STARTUP_FAILURE", ""],
)
def test_ec9_a_finished_check_that_is_not_a_success_is_red(conclusion: str) -> None:
    reasons = guard.red([check_run(), check_run(conclusion, name="other")])
    assert len(reasons) == 1
    assert "other" in reasons[0]
    assert (conclusion or "UNKNOWN") in reasons[0]


@pytest.mark.parametrize("status", ["QUEUED", "IN_PROGRESS", "PENDING", "WAITING", "REQUESTED", ""])
def test_ec10_a_check_that_has_not_finished_is_red_whatever_its_conclusion(status: str) -> None:
    reasons = guard.red([check_run(), check_run("SUCCESS", status, name="other")])
    assert len(reasons) == 1
    assert (status or "UNKNOWN") in reasons[0]


@pytest.mark.parametrize("state", ["PENDING", "FAILURE", "ERROR", "EXPECTED", ""])
def test_ec11_a_commit_status_that_is_not_a_success_is_red(state: str) -> None:
    assert len(guard.red([check_run(), commit_status(state)])) == 1


@pytest.mark.parametrize(
    "checks",
    [
        [check_run(name="lint")],  # EC12
        [check_run(name="fast-suite-2")],
        [],  # B4
        None,
        [commit_status("SUCCESS", context="fast-suite")],  # A6
        [commit_status("SUCCESS", context="fast-suite"), check_run(name="lint")],
        [check_run(), check_run("FAILURE")],  # A7
        [check_run(), {}],  # A8
        [check_run(), {"__typename": "CheckRun"}],
    ],
)
def test_red_gives_one_reason_for_each_of_these(checks: list[dict[str, str]] | None) -> None:
    assert len(guard.red(checks)) == 1


GIT = "git -c credential.helper= -c credential.helper='!gh auth git-credential' "


@pytest.mark.parametrize(
    "command",
    [
        "git push origin feat/0-merge-gate",  # EC13
        "git push -u origin feat/0-merge-gate",
        "git push --force-with-lease origin feat/x",
        "git push origin feat/a feat/b",
        "git push origin --delete docs/old",
        "git push origin HEAD:feat/x",
        "git push origin tag v1.0",
        GIT + "push -u origin feat/0-merge-gate",  # EC17
        "git -C ../other push origin feat/x",
        "git stash push -m wip",  # EC18
        "git status",
        "git push origin feat/main",
        "git push origin maintenance",
        "git push origin main:scratch/gate-test",
        "git fetch origin main",
        "git checkout main && git pull",
        "git commit -m 'refuse a push to main'",
        "",
    ],
)
def test_push_refusals_lets_through(command: str) -> None:
    assert guard.push_refusals(command) == []


@pytest.mark.parametrize(
    "command",
    [
        "git push origin main",  # EC14
        "git push -u origin main",
        "git push origin feat/x:main",
        "git push origin HEAD:main",
        "git push origin +main",
        "git push origin +feat/x:main",
        "git push origin :main",
        "git push origin refs/heads/main",
        "git push origin HEAD:refs/heads/main",
        "git push origin feat/x main",
        "git push --force origin main",
        'git push origin "main"',
        "git push origin --delete main",
        "git.exe push origin main",
        "git push",  # EC15
        "git push origin",
        "git push -u origin",
        "git push origin HEAD",
        "git push origin @",
        "git push --all origin",  # EC16
        "git push origin --mirror",
        "git push --branches origin",
        GIT + "push origin main",  # EC17
        GIT + "push",
        "git -C ../other push origin main",
        "cd x && git push origin main",
        "git status\ngit push origin main",
    ],
)
def test_push_refusals_refuses(command: str) -> None:
    assert len(guard.push_refusals(command)) == 1


@pytest.mark.parametrize(
    "command",
    [
        "git commit --no-verify -m x",  # EC19
        "git push --no-verify origin feat/x",
        "git merge --no-verify feat/x",
        "cd x && git commit -m x --no-verify",
        "git commit -n -m x",  # EC20
        "git commit -nm x",
        "git commit -anm x",
        "git commit -m x -n",
        GIT + "commit -n -m x",
    ],
)
def test_no_verify_refusals_refuses(command: str) -> None:
    assert len(guard.no_verify_refusals(command)) == 1


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m x",  # EC21
        "git commit -q -F -",
        "git commit --amend --no-edit",
        "git push -n origin feat/x",
        "git log -n 5",
        "git commit -q -F - <<'EOF'\nfix: x\n\nthe -n flag is refused\nEOF",
        "",
    ],
)
def test_no_verify_refusals_lets_through(command: str) -> None:
    assert guard.no_verify_refusals(command) == []


@pytest.mark.parametrize(
    "file_path",
    [
        "C:/Users/a/ploni-engine/.claude/settings.json",  # EC22
        "C:/Users/a/ploni-engine/.claude/settings.local.json",
        "C:/Users/a/ploni-engine/docs/WAIVERS.md",
        "C:/Users/a/ploni-engine/scripts/guard.py",
        "C:\\Users\\a\\ploni-engine\\docs\\WAIVERS.md",  # EC23
        "c:/users/a/ploni-engine/DOCS/waivers.MD",
        "C:/Users/a/ploni-engine/docs/../docs/WAIVERS.md",
        "C:/Temp/another-checkout/.claude/settings.json",
        "docs/WAIVERS.md",
        "/home/a/ploni-engine/scripts/guard.py",
    ],
)
def test_edit_refusals_refuses_the_protected_files(file_path: str) -> None:
    assert len(guard.edit_refusals(file_path)) == 1


@pytest.mark.parametrize(
    "file_path",
    [
        "C:/Users/a/ploni-engine/docs/STATUS.md",  # EC24
        "C:/Users/a/ploni-engine/docs/WAIVERS.md.bak",
        "C:/Users/a/ploni-engine/xdocs/WAIVERS.md",
        "C:/Users/a/ploni-engine/tests/t1_unit/test_guard.py",
        "C:/Users/a/ploni-engine/scripts/check.py",
        "C:/Users/a/ploni-engine/.claude/skills/ponytail/SKILL.md",
        "",
    ],
)
def test_edit_refusals_lets_other_files_through(file_path: str) -> None:
    assert guard.edit_refusals(file_path) == []


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_ec25_a_merge_is_let_through_on_green_and_refused_on_red(tool: str) -> None:
    payload = {"tool_name": tool, "tool_input": {"command": PLAIN}}
    asked = []

    def green(number: str, repository: str) -> list[dict[str, str]]:
        asked.append((number, repository))
        return [check_run(), check_run()]

    assert guard.refusals(payload, green) == []
    assert asked == [("80", "o/r")]
    reasons = guard.refusals(payload, lambda number, repository: [check_run("FAILURE")])
    assert len(reasons) == 1
    assert "80" in reasons[0]
    assert "FAILURE" in reasons[0]


@pytest.mark.parametrize("command", ["gh pr merge 80 --squash", "gh pr merge -R o/r --squash", "gh pr merge"])
def test_ec26_a_merge_without_number_or_repository_is_refused_unasked(command: str) -> None:
    assert len(guard.refusals({"tool_name": "Bash", "tool_input": {"command": command}}, never_asked)) == 1


@pytest.mark.parametrize("command", ["git status", "gh pr view 80 -R o/r", "git push -u origin feat/x", ""])
def test_ec27_a_command_that_is_no_merge_does_not_ask_github(command: str) -> None:
    assert guard.refusals({"tool_name": "PowerShell", "tool_input": {"command": command}}, never_asked) == []


@pytest.mark.parametrize("tool", ["Edit", "Write"])
def test_ec28_an_edit_is_refused_for_a_protected_file_only(tool: str) -> None:
    def payload(file_path: str) -> dict[str, object]:
        return {"tool_name": tool, "tool_input": {"file_path": file_path}}

    assert len(guard.refusals(payload("C:/r/docs/WAIVERS.md"), never_asked)) == 1
    assert guard.refusals(payload("C:/r/docs/STATUS.md"), never_asked) == []


def test_refusals_gives_every_reason_of_one_command() -> None:
    command = "git push --no-verify origin main && " + PLAIN
    reasons = guard.refusals({"tool_input": {"command": command}}, lambda number, repository: [])
    assert len(reasons) == 3


@pytest.mark.parametrize(
    "failure",
    [
        OSError("gh was not found"),
        subprocess.CalledProcessError(1, ["gh"], stderr="no pull requests found"),
        subprocess.TimeoutExpired(["gh"], 30),
        ValueError("no JSON"),
        KeyError("statusCheckRollup"),
        TypeError("not a mapping"),
    ],
)
def test_e1_a_merge_is_refused_when_the_checks_cannot_be_read(failure: Exception) -> None:
    def failing(number: str, repository: str) -> list[dict[str, str]]:
        raise failure

    reasons = guard.refusals({"tool_name": "Bash", "tool_input": {"command": PLAIN}}, failing)
    assert len(reasons) == 1
    assert "80" in reasons[0]


@pytest.mark.parametrize("payload", [{}, {"tool_name": "Bash"}, {"tool_input": None}, {"tool_input": "gh pr merge"}])
def test_b5_a_payload_without_tool_input_is_refused(payload: dict[str, object]) -> None:
    assert len(guard.refusals(payload, never_asked)) == 1


def test_e2_rollup_raises_oserror_when_gh_is_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guard.shutil, "which", lambda name: None)
    with pytest.raises(OSError):
        guard.rollup("80", "o/r")


def test_ec29_the_settings_file_runs_the_script_before_the_four_tools() -> None:
    settings = json.loads((REPOSITORY / ".claude" / "settings.json").read_text(encoding="utf-8"))
    (entry,) = settings["hooks"]["PreToolUse"]
    (hook,) = entry["hooks"]
    assert set(entry["matcher"].split("|")) == {"Bash", "PowerShell", "Edit", "Write"}
    assert hook["type"] == "command"
    assert hook["command"] == 'python "$CLAUDE_PROJECT_DIR/scripts/guard.py" || exit 2'
    assert hook["timeout"] > guard.GH_TIMEOUT_SECONDS
