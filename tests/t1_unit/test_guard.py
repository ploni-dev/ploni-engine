"""Test matrix for scripts/guard.py, the script behind the Claude Code hooks.

_commands(text): one reading of a text, as the words of each simple command.
  C1    one command                                 its words
  C2    commands joined by && ; | & or a new line   one list for each
  C3    a quoted text                               one word, without its quotes, separators and
                                                    new lines kept; joined to what touches it
  C4    round and curly brackets, backticks         read as blanks: what follows a bracket stays
                                                    in its command
  C5    a backslash or a # in a word                kept as written
  C6    a quote sign that is never closed           skipped; the words after it are still read
  C7    nothing, or separators only                 no command
  C8    asked to take brackets as ends              a bracket or a backtick ends a command,
                                                    but for one inside a quoted text

segments(command): every reading of a shell command. The same simple command may be given
more than once; no caller counts them.
  S1    a command on one line                       its simple commands
  S2    a line continued with \\ or `               joined to the next
  S3    a redirection, with its target              given twice: dropped, because `2>&1` holds a
                                                    separator sign and what follows a redirection
                                                    stays in its command; and left in, because a
                                                    target the pattern does not know is no word
                                                    of the command either
  S4    a quoted text of several lines              the command it belongs to is given whole
  S5    apostrophes in two comment lines            the line between them is given by itself
  S6    a command inside "$( )", with a quoted text before it    given, by the reading that
                                                    takes every quote sign as a blank
  S7    nothing                                     no command
  S9    a name in curly brackets, ${NAME}           read as $NAME, one word
  S10   a run of 20,000 digits                      read in under two seconds
  S11   a PowerShell comment <# ... #>              given twice: as it stands, and as a blank,
                                                    wherever it stands in a command
  S8    a command in brackets, with words after the bracket    given twice: with those words
                                                    (`git -C $(pwd) push`) and without them
                                                    (`try { git push } catch { throw }`)

The same holds for commands put together by rule and not by hand: tests/t2_property/test_guard.py.

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
  A3    the words on a line of their own in a here-document or in a quoted text of several
        lines    found: the gate does not know where such a text ends, and refuses rather
        than lets through
  A4    the words inside a quoted text on one line  found, for the same reason: one reading
                                                    takes every quote sign as a blank
  A9m   `merge` as a word of another `gh pr` command (a title, a search word)    no merge
  A11m  an option before `pr` or before `merge` whose value is several words ($( ), backticks)
        found: after an option, `pr` and `merge` are looked for anywhere
  A13m  an option before `pr` whose value holds a `pr` of its own    found: after an option,
        every `pr` is tried, not the first only
  A12m  a PowerShell comment <# ... #> before the merge    found: its > is no redirection that
        takes the next word along, in the reading that leaves redirections in
  A5    upper case GH.EXE, gh.cmd                   found
  A6m   a merge between two comment lines that each hold an apostrophe    found
  A7m   a merge in PowerShell curly brackets, or inside "$( )"            found
  A8m   a number with a letter (80x); `merge` before `pr`                 no number; no merge

red(checks): why the checks of a PR's last commit are not green. "Every check" is one green
run of each of REQUIRED_CHECKS (Achia, 2026-11-22, "Yes, name all seven (Recommended)", #180).
  EC7   every check, and a second green fast-suite run    green
  EC8   every check and a green commit status       green
  EC9   a finished check with any conclusion but SUCCESS    red, named with its conclusion
  EC10  a check that has not finished               red, named with its status
  EC11  a commit status in any state but SUCCESS    red
  EC12  every check green but fast-suite, which is missing  red
  EC34  every check but one of the seven            red, one reason that names the missing one
  EC35  REQUIRED_CHECKS is every job of the workflows that run on each pull request: all jobs
        but full-suite, which starts on a label only; .yml and .yaml, a job line with a comment,
        any indentation under jobs:; a job with a name: of its own is red (the review of #187)
        a job named on PENDING_CHECKS (a new check on its way, with its issue) may run on PRs
        before its name is in REQUIRED_CHECKS, by one job only; a pending name that is already
        required or full-suite, or has no issue number (an int over 0), is red; each case is
        tested on workflows made in a temporary folder
  B4    no check at all, or no list                 red, one reason for each of the seven
  A6    a required check only as a commit status, which can be set by hand    red
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
  EC30  gh is installed                             it is asked for the rollup of that PR in
                                                    that repository, with the time limit, and
                                                    its answer is read as UTF-8
  E2    gh is not installed                         OSError

main(), with stdin swapped:
  EC31  a call that may run                         0, nothing written
  EC32  a refused call                              2, one line for each reason on stderr
  EC33  Hebrew in the payload                       read as UTF-8, written as ASCII
  E3    stdin that is not a JSON object             2

The settings file:
  EC29  .claude/settings.json runs the script before Bash, PowerShell, Monitor, Edit and Write, in
        bash, and a script that fails, cannot start or is cut off refuses the call

The script run as a program, with a stand-in for gh, is in tests/t4_integration/test_guard.py.

The Hebrew and document-structure axes of the test-matrix skill do not apply: this code
handles commands and paths, no document.
"""

import io
import itertools
import json
import re
import subprocess
import time
import types
from pathlib import Path

import pytest

from scripts import guard

REPOSITORY = Path(__file__).resolve().parents[2]
PLAIN = "gh pr merge 80 -R o/r --squash"
LF = chr(10)


def check_run(conclusion: str = "SUCCESS", status: str = "COMPLETED", name: str = "fast-suite") -> dict[str, str]:
    """Return a check as `gh pr view --json statusCheckRollup` lists a workflow job."""
    return {"__typename": "CheckRun", "name": name, "status": status, "conclusion": conclusion}


def commit_status(state: str, context: str = "other") -> dict[str, str]:
    """Return a check as the same listing shows a commit status."""
    return {"__typename": "StatusContext", "context": context, "state": state}


def every_check(but: str = "") -> list[dict[str, str]]:
    """Return one green run of each required check, leaving out the one named `but`."""
    return [check_run(name=name) for name in guard.REQUIRED_CHECKS if name != but]


def never_asked(number: str, repository: str) -> list[dict[str, str]]:
    """Stand in for GitHub in a test where GitHub must not be asked."""
    raise AssertionError(f"GitHub was asked about {number} in {repository}")


@pytest.mark.parametrize(
    ("command", "found"),
    [
        ("a b", [["a", "b"]]),  # C1
        ("a && b; c | d\ne", [["a"], ["b"], ["c"], ["d"], ["e"]]),  # C2
        ("a;b&c|d", [["a"], ["b"], ["c"], ["d"]]),
        ("a 'b c' \"d;e\" f'g h'", [["a", "b c", "d;e", "fg h"]]),  # C3
        ('a "b\n\nc" d', [["a", "b\n\nc", "d"]]),
        ("a -c x='!b c' d", [["a", "-c", "x=!b c", "d"]]),
        ("a ''", [["a", ""]]),
        ("a $(b c) d", [["a", "$", "b", "c", "d"]]),  # C4
        ("if ($?) {a b}", [["if", "$?", "a", "b"]]),
        ("a `b c` d", [["a", "b", "c", "d"]]),
        ("a ${B} c", [["a", "$", "B", "c"]]),
        ("a C:\\x\\y.exe # b", [["a", "C:\\x\\y.exe", "#", "b"]]),  # C5
        ("a don't b; c", [["a", "don", "t", "b"], ["c"]]),  # C6
        ("", []),  # C7
        (" ;; \n ", []),
    ],
)
def test_commands_reads_a_text_once(command: str, found: list[list[str]]) -> None:
    assert guard._commands(command) == found


@pytest.mark.parametrize(
    ("command", "found"),
    [
        ("a $(b c) d", [["a", "$"], ["b", "c"], ["d"]]),  # C8
        ("try { a b } catch { c }", [["try"], ["a", "b"], ["catch"], ["c"]]),
        ("a `b c` d", [["a"], ["b", "c"], ["d"]]),
        ('a "(b)" c; d', [["a", "(b)", "c"], ["d"]]),
    ],
)
def test_c8_commands_can_take_brackets_as_the_end_of_a_command(command: str, found: list[list[str]]) -> None:
    assert guard._commands(command, guard.BRACKETS_END) == found


def test_s8_segments_gives_a_command_in_brackets_without_what_follows_the_bracket() -> None:
    assert ["a", "b"] in guard.segments("try { a b } catch { c }")
    assert ["try", "a", "b", "catch", "c"] in guard.segments("try { a b } catch { c }")


def test_s2_a_backtick_at_a_line_end_is_read_both_as_a_joint_and_as_the_end_of_a_command() -> None:
    # PowerShell continues a line with a backtick; in sh the same sign closes a command.
    found = guard.segments("OUT=`a b`\nc")
    assert ["a", "b"] in found
    assert ["a", "b", "c"] in found


@pytest.mark.parametrize(
    ("command", "given"),
    [
        ("a b; c", [["a", "b"], ["c"]]),  # S1
        ("a \\\nb", [["a", "b"]]),  # S2
        ("a `\r\nb", [["a", "b"]]),
        ("a 2>&1 b", [["a", "b"]]),  # S3
        ("a > out.txt b; c", [["a", "b"], ["c"]]),
        ("a 2>$null | b", [["a"], ["b"]]),
        ("a <<'EOF'\nb\nEOF", [["a", "EOF"], ["b"]]),
        ('a "b\n\nc" && d "e\nf" g', [["a", "b\n\nc"], ["d", "e\nf", "g"]]),  # S4
        ("# don't\na \"b;c\" d\n# it's", [["a", "b;c", "d"]]),  # S5
        ('x="$(a "b c" && d e)" f', [["d", "e", "f"]]),  # S6
        ("a -R ${B} c", [["a", "-R", "$B", "c"]]),  # S9
        ("a -R ${env:B} c", [["a", "-R", "$env:B", "c"]]),
        ('a b > "c d"', [["a", "b", ">", "c d"]]),  # S3, left in
        ("<# x #> a b", [["<#", "x", "#>", "a", "b"]]),
        ("a <# x #> b<# y; z #>c", [["a", "b", "c"]]),  # S11
        ("a <# never closed", [["a"]]),
    ],
)
def test_segments_gives_each_of_these_commands(command: str, given: list[list[str]]) -> None:
    found = guard.segments(command)
    assert [words for words in given if words not in found] == []


def test_s7_segments_of_nothing_is_nothing() -> None:
    assert guard.segments("") == []
    assert guard.segments(" ;\n; ") == []


def test_s10_a_long_run_of_digits_is_read_in_time() -> None:
    # A redirection may start with digits (`2>&1`). Tried from every digit of a long run,
    # the pattern took 28 seconds for 20,000 digits; the hook has 40 for everything.
    digits = "1" * 20000
    started = time.perf_counter()
    assert ["a", digits] in guard.segments("a " + digits)
    assert time.perf_counter() - started < 2


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
        # Read as sh too, where the backtick ends the command: that reading has no repository,
        # so this spelling is refused. A known wrong refusal; the merge goes on one line.
        ("gh pr merge 80 `\r\n  -R o/r --squash", [("80", None), ("80", "o/r")]),
        ("echo don't\n" + PLAIN, [("80", "o/r")]),  # A2
        ("git commit -q -F - <<'EOF'\nfix: x\n\n" + PLAIN + "\nEOF", [("80", "o/r")]),  # A3
        ('gh pr comment 5 -R o/r --body "tried gh pr merge 80 -R o/r"', [("80", "o/r")]),  # A4
        ('gh pr create -R o/r --title "the merge gate" --body-file f', []),  # A9m
        ("gh pr list -R o/r --search merge", []),
        ('OUT="$(echo "all green" && ' + PLAIN + ' 2>&1)"; echo "$OUT"', [("80", "o/r")]),  # A7m
        ('gh pr view 5 -R o/r --json title --jq "$(' + PLAIN + ')"', [("80", "o/r")]),
        ('gh pr comment 5 -R o/r --body "first line\n' + PLAIN + '\nlast line"', [("80", "o/r")]),  # A3
        ("GH.EXE pr merge 80 -R o/r", [("80", "o/r")]),  # A5
        ("gh.cmd pr merge 80 -R o/r", [("80", "o/r")]),
        ("gh.bat pr merge 80 -R o/r", [("80", "o/r")]),
        ('git commit -m "subject\n\nbody" && ' + PLAIN + ' --body "line1\nline2"', [("80", "o/r")]),  # S4
        (PLAIN + ' --body "line1\nline2"', [("80", "o/r")]),
        ("git status\n" + PLAIN + "\n" + PLAIN, [("80", "o/r")]),
        ('OUT="`' + PLAIN + '`"; echo "$OUT"', [("80", "o/r")]),  # C4, in a quoted text
        ("# don't merge before the checks\ngh pr checks 80 -R o/r\n" + PLAIN + "\n# that's it", [("80", "o/r")]),  # A6m
        ("if ($?) {" + PLAIN + "}", [("80", "o/r")]),  # A7m
        ("if ($?) { " + PLAIN + " }", [("80", "o/r")]),
        ('OUT="$(' + PLAIN + ' 2>&1)"; echo "$OUT"', [("80", "o/r")]),
        ("gh -R ${REPO} pr merge 80 --squash", [("80", "$REPO")]),  # A10m: the name in curly brackets
        ("gh --repo o/r pr merge 80", [("80", "o/r")]),  # the option before `pr` takes its value along
        ("gh -R ${env:REPO} pr merge 80", [("80", "$env:REPO")]),  # the PowerShell name
        ("gh -R $(echo o/r) pr merge 80 --squash", [("80", "$")]),  # A11m: a value of several words
        ("gh pr -R $(echo o/r) merge 80", [("80", "$")]),
        ("gh -R `echo o/r` pr merge 80", [("80", "echo")]),
        ("<# merge it #> " + PLAIN, [("80", "o/r")]),  # A12m: a PowerShell comment before it
        ("<# merge it #>" + PLAIN, [("80", "o/r")]),  # the same, with no blank after the comment
        ("gh <# note #> pr merge 80 -R o/r", [("80", "o/r")]),  # S11: a comment inside the command
        ("gh pr <# note #> merge 80 -R o/r", [("80", "o/r")]),
        # Read with the redirection `<#` dropped, the word after `merge` is `note`: a second
        # merge, with no number. So this spelling is refused whatever the checks say.
        ("gh pr merge<# note #> 80 -R o/r", [("80", "o/r"), ("", "o/r")]),
        # A13m: the value of -R is a gh command of its own, with a `pr` in it
        ("gh -R $(gh pr view 76 --json headRepository -q .x) pr merge 76 --squash", [("76", "$")]),
        ("gh api pr merge 80 -R o/r", []),  # `pr` is not the first word of gh
        ("gh pr merge 80x -R o/r", [("", "o/r")]),  # A8m
        ("gh merge pr 80 -R o/r", []),
    ],
)
def test_merges_finds_each_merge_command(command: str, found: list[tuple[str, str | None]]) -> None:
    assert guard.merges(command) == found


@pytest.mark.parametrize(
    "checks",
    [
        [*every_check(), check_run()],  # EC7
        [*every_check(), commit_status("SUCCESS")],  # EC8
        [*every_check(), check_run(name="lint")],
    ],
)
def test_red_is_empty_when_every_check_is_green(checks: list[dict[str, str]]) -> None:
    assert guard.red(checks) == []


@pytest.mark.parametrize(
    "conclusion",
    ["FAILURE", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "NEUTRAL", "SKIPPED", "STALE", "STARTUP_FAILURE", ""],
)
def test_ec9_a_finished_check_that_is_not_a_success_is_red(conclusion: str) -> None:
    reasons = guard.red([*every_check(), check_run(conclusion, name="other")])
    assert len(reasons) == 1
    assert "other" in reasons[0]
    assert (conclusion or "UNKNOWN") in reasons[0]


@pytest.mark.parametrize("status", ["QUEUED", "IN_PROGRESS", "PENDING", "WAITING", "REQUESTED", ""])
def test_ec10_a_check_that_has_not_finished_is_red_whatever_its_conclusion(status: str) -> None:
    reasons = guard.red([*every_check(), check_run("SUCCESS", status, name="other")])
    assert len(reasons) == 1
    assert (status or "UNKNOWN") in reasons[0]


@pytest.mark.parametrize("state", ["PENDING", "FAILURE", "ERROR", "EXPECTED", ""])
def test_ec11_a_commit_status_that_is_not_a_success_is_red(state: str) -> None:
    assert len(guard.red([*every_check(), commit_status(state)])) == 1


@pytest.mark.parametrize(
    "checks",
    [
        [*every_check("fast-suite"), check_run(name="lint")],  # EC12
        [*every_check("fast-suite"), check_run(name="fast-suite-2")],
        [*every_check("fast-suite"), commit_status("SUCCESS", context="fast-suite")],  # A6
        [*every_check("nightly"), commit_status("SUCCESS", context="nightly")],
        [*every_check(), check_run("FAILURE")],  # A7
        [*every_check(), {}],  # A8
        [*every_check(), {"__typename": "CheckRun"}],
    ],
)
def test_red_gives_one_reason_for_each_of_these(checks: list[dict[str, str]] | None) -> None:
    assert len(guard.red(checks)) == 1


def test_ec34_each_required_check_that_is_missing_is_named() -> None:
    assert guard.REQUIRED_CHECKS == ("changed-paths", "fast-suite", "nightly", "pr-body", "pr-size", "ratchet", "waiver")
    for name in guard.REQUIRED_CHECKS:
        assert guard.red(every_check(name)) == [f"there is no {name} check on the last commit"]


@pytest.mark.parametrize("checks", [[], None])
def test_b4_no_check_at_all_is_one_reason_for_each_required_check(checks: list[dict[str, str]] | None) -> None:
    assert guard.red(checks) == [f"there is no {name} check on the last commit" for name in guard.REQUIRED_CHECKS]


KEY = re.compile(r"(\s*)([\w-]+):[ \t]*(.*?)\s*(#.*)?")


def _check_names(text: str) -> dict[str, str]:
    """Return the check name of each job of a workflow, by job id.

    Why: GitHub names a job's check by its id, or by the job's own `name:` when it sets one; EC35
    compares those names with REQUIRED_CHECKS (the reviews of #187, passes 1 and 2).
    Contract: text, a workflow file. Returns {job id: its check name}: the job's own `name:` read
    at the job's key level, quotes taken off, else the id. A `name:` deeper down (a step's, one
    under `with:` or `env:`) is not the job's. Raises ValueError when no line is `jobs:` (with or
    without a comment after it).
    The jobs end at the next line that is not indented (`on:` may follow `jobs:`).
    Known limits: YAML flow style (`jobs: {a: ...}`), a `name:` set by an expression, a quoted
    name that holds ` #`, and a block-scalar name (`name: >`) are not read as GitHub would; no
    workflow here has any. Each misread gives a name no check has, so EC35 fails closed.
    """
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if re.fullmatch(r"jobs:\s*(#.*)?", line)]
    if not starts:
        raise ValueError("no jobs: line")
    kept = [line for line in lines[starts[0] + 1 :] if line.strip() and not line.lstrip().startswith("#")]
    below = list(itertools.takewhile(lambda line: line[:1].isspace(), kept))
    keys = [(len(m.group(1)), m) for m in map(KEY.fullmatch, below) if m]
    if not keys:
        return {}
    job_level = keys[0][0]
    names: dict[str, str] = {}
    current, own_level = "", None
    for indent, key in keys:
        if indent == job_level:
            current, own_level = key.group(2), None
            names[current] = current
        elif current and indent > job_level:
            own_level = indent if own_level is None else own_level
            if indent == own_level and key.group(2) == "name":
                names[current] = key.group(3).strip("'\"")
    return names


# New checks on their way, each with its issue: a job named here may run on PRs before its name is
# in REQUIRED_CHECKS, as its workflow and the guard patch that names it come in two PRs (the
# changed-paths check refuses a workflow with a .py file). The guard patch that adds a name also
# updates EC34's pin and takes the name off this list, in one patch. Achia, 2026-11-23, "A short
# pending list (Recommended)". Each name added loosens EC35 and needs his decision on that check;
# fast-pin, commit-order and reviewed-commit have it ("Yes, one workflow each (Recommended)").
PENDING_CHECKS: dict[str, int] = {"fast-pin": 173}


def _workflow_problems(folder: Path, required: tuple[str, ...], pending: dict[str, int]) -> list[str]:
    """Return why the check names of the workflows in `folder` do not match the gate's list.

    Why: EC35's rule in one place, so that its cases are tested on workflows made for them.
    Contract: folder, a folder of workflow files (.yml and .yaml); required, the gate's
    REQUIRED_CHECKS; pending, PENDING_CHECKS. Returns one line per problem, empty when every
    job's check name is required, full-suite, or pending and run by one job only.
    Known limits: those of `_check_names`.
    """
    names: list[str] = []
    for workflow in sorted([*folder.glob("*.yml"), *folder.glob("*.yaml")]):
        names += _check_names(workflow.read_text(encoding="utf-8")).values()
    listed = [name for name in names if name in pending]
    problems = []
    # A list, not a set: two jobs under one check name would let one stand in for the other.
    if sorted(names) != sorted([*required, "full-suite", *listed]):
        problems.append(f"the check names {sorted(names)} are not the required, full-suite and pending ones")
    if len(listed) != len(set(listed)):
        problems.append("two jobs under one pending check name")
    return problems


def test_ec35_the_required_checks_are_the_jobs_that_run_on_every_pull_request() -> None:
    # full-suite starts on a label only, so it is on no PR by default.
    assert _workflow_problems(REPOSITORY / ".github" / "workflows", guard.REQUIRED_CHECKS, PENDING_CHECKS) == []


@pytest.mark.parametrize(
    ("workflows", "pending", "fine"),
    [
        ({"a.yml": "jobs:\n  a:\n    runs-on: x\n"}, {}, True),
        ({"a.yml": "jobs:\n  a:\n    runs-on: x\n", "n.yml": "jobs:\n  new:\n    runs-on: x\n"}, {}, False),
        ({"a.yml": "jobs:\n  a:\n    runs-on: x\n", "n.yml": "jobs:\n  new:\n    runs-on: x\n"}, {"new": 175}, True),
        ({"a.yml": "jobs:\n  a:\n    runs-on: x\n", "n.yml": "jobs:\n  new:\n    runs-on: x\n  again:\n    name: new\n"}, {"new": 175}, False),
        ({"a.yml": "jobs:\n  a:\n    runs-on: x\n", "n.yml": "jobs:\n  lint:\n    runs-on: x\n"}, {"new": 175}, False),
        ({"a.yml": "jobs:\n  a:\n    runs-on: x\n"}, {"new": 175}, True),
        ({"a.yaml": "jobs:\n  a:\n    runs-on: x\n"}, {}, True),
        ({}, {}, False),
        ({"a.yml": "jobs:\n  a:\n    runs-on: x\n", "b.yml": "jobs:\n  b:\n    name: a\n"}, {}, False),
    ],
    ids=["required-only", "new-unlisted", "new-listed", "two-of-a-pending-name", "other-new-unlisted", "listed-no-workflow-yet", "yaml", "required-missing", "two-of-a-required-name"],
)
def test_ec35_workflow_problems_in_each_case(tmp_path: Path, workflows: dict[str, str], pending: dict[str, int], fine: bool) -> None:
    for name, text in workflows.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    (tmp_path / "full.yml").write_text("jobs:\n  full-suite:\n    runs-on: x\n", encoding="utf-8")
    assert (_workflow_problems(tmp_path, ("a",), pending) == []) is fine


def _pending_problems(pending: dict[str, int], required: tuple[str, ...]) -> list[str]:
    """Return why PENDING_CHECKS holds a name it may not.

    Why: a name on the list is new, so it may not be one the gate requires or full-suite, and it
    names its issue. Contract: pending, PENDING_CHECKS; required, REQUIRED_CHECKS. Returns one
    line per problem, empty when the list is fine.
    """
    problems = [f"{name} is already a check of the gate" for name in pending if name in {*required, "full-suite"}]
    problems += [f"{name} names no issue" for name, issue in pending.items() if type(issue) is not int or issue <= 0]
    return problems


def test_ec35_the_pending_list_holds_new_checks_only() -> None:
    assert _pending_problems(PENDING_CHECKS, guard.REQUIRED_CHECKS) == []


@pytest.mark.parametrize(
    ("pending", "count"),
    [({}, 0), ({"new": 175}, 0), ({"a": 175}, 1), ({"full-suite": 175}, 1), ({"new": 0}, 1), ({"new": True}, 1), ({"new": "175"}, 1), ({"a": 0}, 2)],
    ids=["empty", "new", "required", "full-suite", "issue-0", "issue-true", "issue-text", "both"],
)
def test_ec35_pending_problems_in_each_case(pending: dict[str, int], count: int) -> None:
    assert len(_pending_problems(pending, ("a",))) == count


@pytest.mark.parametrize(
    ("text", "names"),
    [
        ("jobs:\n  a:\n    runs-on: x\n  b:\n    runs-on: y\n", {"a": "a", "b": "b"}),
        ("jobs:\n  lint: # the linter\n    runs-on: x\n", {"lint": "lint"}),
        ("jobs:\n    deep:\n      runs-on: x\n", {"deep": "deep"}),
        ("jobs: # the jobs\n  a:\n    runs-on: x\n", {"a": "a"}),
        ("jobs:\n  # a comment: here\n  a:\n    steps:\n      - name: x\n", {"a": "a"}),
        # A job's own name: is its check's name; one deeper down is not.
        ("jobs:\n  a:\n    name: Lint\n    runs-on: x\n", {"a": "Lint"}),
        ("jobs:\n  a:\n    name: 'Lint it' # quoted\n", {"a": "Lint it"}),
        ("jobs:\n  a:\n    steps:\n      - uses: x\n        with:\n          name: results\n", {"a": "a"}),
        ("jobs:\n  a:\n    steps:\n      - run: x\n        name: second line\n", {"a": "a"}),
        ("jobs:\n  a:\n    env:\n      name: x\n    runs-on: y\n", {"a": "a"}),
        # A top-level key after jobs: ends the jobs.
        ("jobs:\n  a:\n    runs-on: x\non:\n  pull_request:\n", {"a": "a"}),
    ],
)
def test_ec35_check_names_are_read_in_each_shape(text: str, names: dict[str, str]) -> None:
    assert _check_names(text) == names


def test_ec35_a_workflow_with_no_jobs_line_raises() -> None:
    with pytest.raises(ValueError):
        _check_names("on: push\n")


def test_red_raises_attributeerror_for_an_entry_that_is_no_mapping() -> None:
    with pytest.raises(AttributeError):
        guard.red([check_run(), "fast-suite"])  # type: ignore[list-item]


def test_state_gives_the_name_of_a_check_with_where_it_stands() -> None:
    assert guard._state(check_run()) == ("fast-suite", "SUCCESS")
    assert guard._state(check_run("FAILURE", name="lint")) == ("lint", "FAILURE")
    assert guard._state(check_run("SUCCESS", "IN_PROGRESS")) == ("fast-suite", "IN_PROGRESS")
    assert guard._state(commit_status("PENDING", "deploy")) == ("deploy", "PENDING")
    assert guard._state({}) == (None, "UNKNOWN")


def test_calls_gives_the_words_after_each_word_that_names_the_program() -> None:
    assert guard._calls(["sudo", "-u", "git", "GIT.EXE", "push"], "git") == [["GIT.EXE", "push"], ["push"]]
    assert guard._calls(["C:\\tools\\gh.cmd", "pr"], "gh") == [["pr"]]
    assert guard._calls(["/usr/bin/gh.bat"], "gh") == [[]]
    assert guard._calls(["git-credential", "!gh", "ghx", "exegh"], "gh") == []
    assert guard._calls([], "gh") == []
    assert guard._calls(["#>gh", "pr"], "gh") == [["pr"]]
    assert guard._calls(["<#x#>C:\\tools\\gh.exe", "pr"], "gh") == [["pr"]]


@pytest.mark.parametrize(
    ("words", "found"),
    [
        ("pr merge 80 --squash", ["80"]),  # `pr` leads, `merge` follows it
        ("pr merge", [""]),
        ("pr merge --squash 80", ["--squash"]),
        ("pr -R o/r merge 80", ["80"]),  # an option after `pr`: every `merge` after it
        ("pr -R o/r merge 80 merge 81", ["80", "81"]),
        ("-R o/r pr merge 80", ["80"]),  # an option leads: every `pr`
        ("-R $ gh pr view 76 pr merge 77", ["77"]),
        ("-R o/r pr merge 80 pr merge 80", ["80"]),  # the same word once
        ("-R o/r pr -x merge 80 pr merge 81", ["80", "81"]),  # in the order they stand
        ("pr view 80", []),  # no merge
        ("pr list --search merge", []),
        ("pr create --title merge 80", []),
        ("api pr merge 80", []),  # `pr` neither leads nor follows an option
        ("--paginate api", []),
        ("", []),
    ],
)
def test_merge_words_gives_the_word_where_each_merge_has_its_number(words: str, found: list[str]) -> None:
    assert guard._merge_words(words.split()) == found


def test_repository_gives_the_one_repository_that_is_named() -> None:
    assert guard._repository(["pr", "merge", "80", "-R", "o/r"]) == "o/r"
    assert guard._repository(["--repo", "o/r", "pr"]) == "o/r"
    assert guard._repository(["--repo=o/r"]) == "o/r"
    assert guard._repository(["-Ro/r"]) == "o/r"
    assert guard._repository(["-R", "o/r", "-R", "o/r"]) is None
    assert guard._repository(["pr", "merge", "80", "-R"]) is None
    assert guard._repository(["pr", "merge", "80"]) is None


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
        "git commit -m 'the pushes are refused'",
        "git push origin 2026",
        "git push origin feat/x 2>$null",
        "git push origin feat/x > push.log",
        "git push -u origin feat/x # main is protected",  # a comment is no branch
        'git push origin feat/x > "push.log"',  # EC13r: a branch before any spelling of a redirection
        "git push origin feat/x *>&1",
        "git push origin feat/x 2> 'err.log'",
        "git push origin feat/x 2>&1",  # EC13r
        "git push -u origin feat/x 2>&1 | tail -3",
        "git push origin feat/x 2>/dev/null",
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
        "git push origin heads/main",
        "git push origin 2>&1",  # EC15r: the 2 of a redirection is no branch
        "git push -u origin 2>&1 | tail -3",
        "git push origin 2>/dev/null",
        "git push origin 2>$null",
        "git push origin $(git branch --show-current)",  # EC15v: a branch the hook cannot read
        "git push origin $BRANCH",
        "git push origin ${BRANCH}",
        "git push origin feat/x:$TARGET",
        "git push --all -o x origin",  # EC16: only the flag gives these away
        "git push --mirror -o x origin",
        "git push --branches -o x origin",
        "if ($?) {git push origin main}",  # S8
        "if ($?) { git push origin main}",
        'echo "$(git push origin main 2>&1)"',  # S6
        'git -C "$(pwd)" push origin main',
        "git push # ok",  # EC15: a comment is neither remote nor branch
        "git push #ok",
        "git push origin #x",  # a comment needs no blank after its sign
        "<# note #>git push origin main",  # a command glued to the end of a PowerShell comment
        "git push origin feat/x <# note #> main",  # S11: a comment inside the command
        "git <# note #>push origin main",
        "git push <# a #> origin <# b #> main",
        "git push origin feat/x `" + LF + "<# note #> main",  # S11 with S2: a comment after a line joined by a backtick
        "git push origin *>&1",  # EC15r: no spelling of a redirection is a branch
        "git push origin *> $null",
        'git push origin > "push.log"',
        "git push origin 2> 'err.log'",
        'git push origin <<< "y"',
        "echo a >out.txt;git push origin main",  # a redirection target glued to the next command
        "git push origin # x",
        "git push origin $A feat/x",
        "git -C ${REPO_DIR} push origin main",  # C4: brackets are blanks
        "git -C $(pwd) push origin main",
        'OUT="$(cd "/c/my dir" && git push origin main 2>&1)"',  # S6
        'OUT="$(echo "all green" && ' + GIT + 'push origin main 2>&1)"',
        "git commit -m 'refuse a push to main'",  # a known wrong refusal: the words in a message
        "git push origin $env:BRANCH",  # EC15v, PowerShell
        "git push origin feat/x:$env:TARGET",
        'git commit -m "s\n\nb" && git push origin main && gh pr create --title "t" --body "one\ntwo"',  # S4
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
        "pre-commit run --no-verify",  # EC19: any command, not git alone
        "git commit -m \"$(cat <<'EOF'\nfix: x\nEOF\n)\" -n",  # S4: the flag after the quoted text
        'git commit -m "$(cat msg.txt)" -n',
        "git -C ${REPO_DIR} commit -n -m x",  # C4: brackets are blanks
        "git commit -m ${MSG} -n",
        "git commit -m $(cat msg.txt) -n",
        "git commit -m x 2>&1 -n",  # S3
        "<# note #> git commit -m x 2>&1 -n",  # S3: the > that ends a comment takes no word along
        "<# note #>git commit -n -m x",  # a command glued to the end of a PowerShell comment
        "git commit -m x <# note #>-n",  # S11: a comment inside the command
        "git commit <# note #> --no-verify -m x",
        'git commit -m "fix: the `"fast`" suite" -n',  # a PowerShell escaped quote
        'OUT="$(git commit -m "fix: a" -n 2>&1)"',  # S6
        'git commit -m "fix: x\n\nbody" -n',  # S4
        'echo "a\nb" && git commit --no-verify -m "t" -m "c\nd"',
        "if ($?) {git commit -n -m x}",  # S8
        "if ($?) {git commit -m x --no-verify}",
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
        "C:/Users/a/ploni-engine/docs/x/../WAIVERS.md",
        "C:/Users/a/ploni-engine/docs/WAIVERS.md.",
        "C:/Users/a/ploni-engine/docs/WAIVERS.md ",
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
        return [*every_check(), check_run()]

    assert guard.refusals(payload, green) == []
    assert asked == [("80", "o/r")]
    reasons = guard.refusals(payload, lambda number, repository: [*every_check(), check_run("FAILURE")])
    assert len(reasons) == 1
    assert "80" in reasons[0]
    assert "FAILURE" in reasons[0]


@pytest.mark.parametrize(
    "command",
    [
        "gh pr merge 80 --squash",
        "gh pr merge -R o/r --squash",
        "gh pr merge",
        "gh pr merge 80 -R o/r -R other/r --squash",
    ],
)
def test_ec26_a_merge_without_number_or_one_repository_is_refused_unasked(command: str) -> None:
    assert len(guard.merge_refusals(command, never_asked)) == 1


@pytest.mark.parametrize("pair", ["pr merge ", "pr -x merge "])
def test_merges_reads_a_line_of_a_thousand_pr_merge_pairs_in_time(pair: str) -> None:
    # After an option every `pr` and every `merge` counts. Trying each `merge` again for
    # each `pr`, and reading the repository again for each pair, took over five minutes
    # for 1,000 pairs with an option between them; the hook has 40 seconds for everything.
    started = time.perf_counter()
    assert guard.merges("gh -R o/r pr comment 5 --body " + pair * 1000) == [("", "o/r")]
    assert time.perf_counter() - started < 3


def test_merge_refusals_judges_each_merge_of_a_command() -> None:
    def by_number(number: str, repository: str) -> list[dict[str, str]]:
        return [*every_check(), check_run("SUCCESS" if number == "80" else "FAILURE")]

    reasons = guard.merge_refusals("gh pr merge 80 -R o/r && gh pr merge 81 -R o/r", by_number)
    assert len(reasons) == 1
    assert "PR 81 of o/r" in reasons[0]


@pytest.mark.parametrize("command", ["git status", "gh pr view 80 -R o/r", "git push -u origin feat/x", ""])
def test_ec27_a_command_that_is_no_merge_does_not_ask_github(command: str) -> None:
    assert guard.refusals({"tool_name": "PowerShell", "tool_input": {"command": command}}, never_asked) == []


@pytest.mark.parametrize("tool", ["Edit", "Write"])
def test_ec28_an_edit_is_refused_for_a_protected_file_only(tool: str) -> None:
    def payload(file_path: str) -> dict[str, object]:
        return {"tool_name": tool, "tool_input": {"file_path": file_path}}

    assert len(guard.refusals(payload("C:/r/docs/WAIVERS.md"), never_asked)) == 1
    assert guard.refusals(payload("C:/r/docs/STATUS.md"), never_asked) == []


def test_a_refusal_says_which_words_it_read_as_the_command() -> None:
    # The words of a refused command in a text are refused on purpose. The reason has to
    # show what was taken for the command, or a wrong refusal costs several tries.
    assert "git commit -m fix the push" in guard.push_refusals("git commit -m 'fix the push'")[0]
    assert "git commit -m use the -n flag" in guard.no_verify_refusals('git commit -m "use the -n flag"')[0]
    assert "grep --no-verify docs" in guard.no_verify_refusals("grep --no-verify docs")[0]
    unplain = guard.merge_refusals("gh pr merge 80 --squash", never_asked)[0]
    assert "number 80" in unplain
    assert "no repository" in unplain
    no_number = guard.merge_refusals("gh pr merge -R o/r", never_asked)[0]
    assert "no number" in no_number
    assert "repository o/r" in no_number
    two_lines = "git push origin # don't push main\ngit status # that's it"
    assert LF not in guard.push_refusals(two_lines)[0]
    long = guard.push_refusals("git push origin main " + "x" * 500)[0]
    assert len(long) < 250


def test_refusals_gives_every_reason_of_one_command() -> None:
    command = "git push --no-verify origin main && " + PLAIN
    reasons = guard.refusals({"tool_input": {"command": command}}, lambda number, repository: every_check("fast-suite"))
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

    reasons = guard.merge_refusals(PLAIN, failing)
    assert len(reasons) == 1
    assert "80" in reasons[0]


def test_e1_a_merge_is_refused_when_an_entry_of_the_checks_is_no_mapping() -> None:
    reasons = guard.merge_refusals(PLAIN, lambda number, repository: ["fast-suite"])  # type: ignore[list-item]
    assert len(reasons) == 1
    assert "could not be read" in reasons[0]


def test_e1_the_refusal_carries_what_gh_wrote() -> None:
    def failing(number: str, repository: str) -> list[dict[str, str]]:
        raise subprocess.CalledProcessError(1, ["gh"], stderr="no pull requests found\n")

    assert guard.merge_refusals(PLAIN, failing)[0].endswith("no pull requests found")


def test_a_failure_outside_the_known_ones_is_not_swallowed() -> None:
    def broken(number: str, repository: str) -> list[dict[str, str]]:
        raise ZeroDivisionError

    with pytest.raises(ZeroDivisionError):
        guard.merge_refusals(PLAIN, broken)


@pytest.mark.parametrize("payload", [{}, {"tool_name": "Bash"}, {"tool_input": None}, {"tool_input": "gh pr merge"}])
def test_b5_a_payload_without_tool_input_is_refused(payload: dict[str, object]) -> None:
    assert len(guard.refusals(payload, never_asked)) == 1


def test_e2_rollup_raises_oserror_when_gh_is_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(guard.shutil, "which", lambda name: None)
    with pytest.raises(OSError):
        guard.rollup("80", "o/r")


def test_rollup_asks_gh_for_the_checks_of_that_pr_with_a_time_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_run(argv: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        calls.append((argv, options))
        return subprocess.CompletedProcess(argv, 0, stdout='{"statusCheckRollup": [{"name": "\u05e4"}]}')

    monkeypatch.setattr(guard.shutil, "which", lambda name: "X:/tools/gh.exe")
    monkeypatch.setattr(guard.subprocess, "run", fake_run)
    assert guard.rollup("80", "o/r") == [{"name": "\u05e4"}]
    ((argv, options),) = calls
    assert argv == ["X:/tools/gh.exe", "pr", "view", "80", "-R", "o/r", "--json", "statusCheckRollup"]
    assert options == {
        "capture_output": True,
        "encoding": "utf-8",
        "timeout": guard.GH_TIMEOUT_SECONDS,
        "check": True,
    }


def stdin_of(monkeypatch: pytest.MonkeyPatch, payload: bytes) -> None:
    """Give `main` these bytes as its stdin."""
    monkeypatch.setattr(guard.sys, "stdin", types.SimpleNamespace(buffer=io.BytesIO(payload)))


def test_main_returns_0_and_writes_nothing_for_a_call_that_may_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stdin_of(monkeypatch, b'{"tool_name": "Bash", "tool_input": {"command": "git status"}}')
    assert guard.main() == 0
    assert capsys.readouterr() == ("", "")


def test_main_returns_2_with_each_reason_on_stderr_for_a_refused_call(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    stdin_of(monkeypatch, b'{"tool_name": "Bash", "tool_input": {"command": "git push --no-verify origin main"}}')
    assert guard.main() == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert len(err.splitlines()) == 2
    assert all(line.startswith("guard: ") for line in err.splitlines())


@pytest.mark.parametrize("payload", [b"", b"not json", b"[]", b"\xff\xfe"])
def test_main_refuses_stdin_that_is_no_payload(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], payload: bytes
) -> None:
    stdin_of(monkeypatch, payload)
    assert guard.main() == 2
    assert capsys.readouterr().err.startswith("guard: ")


def test_main_reads_the_payload_as_utf8_and_writes_ascii(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    command = "gh pr merge 80 -R \u05e4\u05dc\u05d5\u05e0\u05d9/r --squash"
    stdin_of(monkeypatch, json.dumps({"tool_input": {"command": command}}, ensure_ascii=False).encode("utf-8"))
    monkeypatch.setattr(guard.shutil, "which", lambda name: None)
    assert guard.main() == 2
    err = capsys.readouterr().err
    assert "PR 80 of \\u05e4\\u05dc\\u05d5\\u05e0\\u05d9/r" in err
    assert err.isascii()


def test_ec29_the_settings_file_runs_the_script_before_the_five_tools() -> None:
    settings = json.loads((REPOSITORY / ".claude" / "settings.json").read_text(encoding="utf-8"))
    (entry,) = settings["hooks"]["PreToolUse"]
    (hook,) = entry["hooks"]
    assert set(entry["matcher"].split("|")) == {"Bash", "PowerShell", "Monitor", "Edit", "Write"}
    assert hook["type"] == "command"
    assert hook["shell"] == "bash"
    assert hook["command"] == 'python "$CLAUDE_PROJECT_DIR/scripts/guard.py" || exit 2'
    assert hook["timeout"] > guard.GH_TIMEOUT_SECONDS
    # A hook that is cut off, or cannot start, refuses the call (Claude Code 2.1.295 or later).
    assert hook["onFailure"] == "block"
