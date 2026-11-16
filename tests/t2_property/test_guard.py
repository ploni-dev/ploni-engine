"""Invariants of scripts/guard.py over commands put together by rule.

Why: three reviews in a row found a refused command that got through once it was put in
another shape (inside curly brackets, in `"$( )"`, after a quoted text of several lines),
and two of the fixes opened new shapes. Cases thought of one by one do not cover that.
So the shapes are a list here, every command goes into every shape, and into every shape
inside every shape.

Invariants:
  I1  A command that is refused alone is refused in every shape of SHAPES, and in every
      shape inside every shape. The shapes are ways in which a shell still runs the
      command: after or before another command, in brackets, captured in a variable, with
      a redirection, between comment lines with an apostrophe, after a quoted text of
      several lines, and the PowerShell forms of the same.
  I2  A command that is let through alone is let through in every shape of SHAPES. A
      shape only puts the command somewhere; it adds nothing that is refused.

Sample: len(REFUSED) * len(SHAPES) cases for I1 one deep, the same times len(SHAPES) two
deep, and len(ALLOWED) * len(SHAPES) for I2. The test at the end holds the counts over
the 500 that CLAUDE.md, Tests, asks of an invariant.

Known limits: the shapes are a fixed list, not a grammar of two shells. A shape that is
not in the list is not tested. Nothing here starts a shell: that a shell really runs the
command in each shape was looked at by hand in the review of this branch, not here.
I2 is not held two deep: a shape may put a word next to another shape's bracket, which
the reader then takes for a branch name it cannot know.
"""

import pytest

from scripts import guard

GIT = "git -c credential.helper= -c credential.helper='!gh auth git-credential' "

# Each is refused alone: a merge of a PR whose checks are red here, a push that reaches
# main or names no branch, a commit that skips the git hooks.
REFUSED = [
    "gh pr merge 80 -R o/r --squash",
    "gh pr merge 80 --squash -R o/r",
    "gh.exe pr merge 80 --repo o/r",
    "gh pr merge 80 --squash",
    "git push origin main",
    "git push -u origin HEAD:main",
    "git push",
    GIT + "push origin main",
    "git -C ${REPO_DIR} push origin main",
    'git -C "$(pwd)" push origin main',
    "git commit -n -m x",
    "git commit -m x --no-verify",
    'git commit -m "fix: a b" -n',
    'git commit -m "$(cat msg.txt)" -n',
    "git commit -m x 2>&1 -n",
]

ALLOWED = [
    "git status",
    "git push -u origin feat/x",
    GIT + "push -q -u origin feat/x",
    "gh pr view 80 -R o/r --json statusCheckRollup",
    "gh pr create -R o/r --title t --body-file body.md",
    "git commit -q -F message.txt",
    "git stash push -m wip",
    "python scripts/check.py",
]

SHAPES = [
    "{c}",
    "cd x && {c}",
    "{c} && echo done",
    "echo a; {c}",
    "echo a;{c}",
    "echo a | cat; {c}",
    "true || {c}",
    "{c} 2>&1",
    "{c} 2>&1 | tail -3",
    "{c} > out.txt",
    "{c} 2>/dev/null",
    "{c} &",
    "({c})",
    "{{ {c}; }}",
    "if true; then {c}; fi",
    "time {c}",
    "OUT=$({c})",
    'OUT="$({c})"',
    'OUT="$({c} 2>&1)"; echo "$OUT"',
    "OUT=`{c}`",
    'OUT="`{c}`"',
    'echo "all green" && {c}',
    'OUT="$(echo "all green" && {c} 2>&1)"; echo "$OUT"',
    'OUT="$(cd "/c/my dir" && {c})"',
    "# don't run this before the checks\n{c}\n# that's it",
    "echo 'a'\n{c}",
    '{c}\necho "b c"',
    "cat <<'EOF'\nit's a text\nEOF\n{c}",
    'git commit -q -m "subject\n\nbody" && {c}',
    '{c} && gh pr comment 5 -R o/r --body "line one\nline two"',
    "git status\r\n{c}\r\ngit status",
    # PowerShell
    "if ($?) {{{c}}}",
    "if ($?) {{ {c} }}",
    "{c}; if (-not $?) {{ exit 1 }}",
    "$out = {c}",
    "$out = ({c})",
    "& {{ {c} }}",
    "try {{ {c} }} catch {{ throw }}",
    'Write-Output "it`"s done"; {c}',
    "{c} 2>$null",
    "{c} | Select-Object -First 3",
]


def red(number: str, repository: str) -> list[dict[str, str]]:
    """Stand in for GitHub: every PR has one failed check."""
    return [{"__typename": "CheckRun", "name": "fast-suite", "status": "COMPLETED", "conclusion": "FAILURE"}]


def refused(command: str) -> bool:
    """Return whether the hook would refuse this command."""
    return guard.refusals({"tool_input": {"command": command}}, red) != []


@pytest.mark.parametrize("command", REFUSED + ALLOWED)
def test_each_command_is_alone_what_its_list_says(command: str) -> None:
    assert refused(command) == (command in REFUSED)


@pytest.mark.parametrize("shape", SHAPES)
def test_i1_a_refused_command_is_refused_in_every_shape(shape: str) -> None:
    assert [command for command in REFUSED if not refused(shape.format(c=command))] == []


@pytest.mark.parametrize("outer", SHAPES)
def test_i1_a_refused_command_is_refused_in_every_shape_inside_every_shape(outer: str) -> None:
    missed = [
        outer.format(c=inner.format(c=command))
        for inner in SHAPES
        for command in REFUSED
        if not refused(outer.format(c=inner.format(c=command)))
    ]
    assert missed == []


@pytest.mark.parametrize("shape", SHAPES)
def test_i2_an_allowed_command_is_let_through_in_every_shape(shape: str) -> None:
    assert [command for command in ALLOWED if refused(shape.format(c=command))] == []


def test_the_sample_is_over_the_minimum_for_an_invariant() -> None:
    # CLAUDE.md, Tests: an invariant is held over 500 generated cases.
    assert len(REFUSED) * len(SHAPES) >= 500
    assert len(REFUSED) * len(SHAPES) * len(SHAPES) >= 5000
    assert len(ALLOWED) * len(SHAPES) >= 300
