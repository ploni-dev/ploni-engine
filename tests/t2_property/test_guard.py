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
deep, and len(ALLOWED) * len(SHAPES) for I2, the same times len(SHAPES) two deep in the full
suite (tests/sizes.py). The test at the end holds the counts over
the 500 that CLAUDE.md, Tests, asks of an invariant.

Not held, and listed: I1 fails for a command whose own quoted text holds a separator sign
(`git commit -m "a; b" -n`) in the shapes that put it inside another quoted text. Those
commands are in KNOWN_MISSED with the exact shapes, not in REFUSED. Two more are let
through alone and in every shape (KNOWN_MISSED_EVERYWHERE): their quoted text also holds
a quote sign that does not close it. All but one are commits that skip the git hooks.
The one push needs a separator sign in a quoted option of git before `push`
(`git -c user.name="A; B" push origin main`); no merge is known to get through.

Known limits: the shapes are a fixed list, not a grammar of two shells. A shape that is
not in the list is not tested. Nothing here starts a shell: that a shell really runs the
command in each shape was looked at by hand in the review of this branch, not here.
I2 is not held two deep: a shape may put a word next to another shape's bracket, which
the reader then takes for a branch name it cannot know.
"""

import pytest

from scripts import guard
from tests.sizes import INVARIANT_FULL, full

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

# Each is let through in the shapes listed with it, and refused in every other shape and
# alone. The words of these commands are split by a separator sign inside their own quoted
# text (`;`, a new line), and the shapes are the ones that hide that quoted text from the
# readings that follow quotes (`segments`, Known limits). Listed exactly, so that a change
# in either direction shows: a shape that starts to catch one, or a new shape that misses one.
INSIDE_QUOTES = [
    'OUT="$({c})"',
    'OUT="$({c} 2>&1)"; echo "$OUT"',
    'OUT="`{c}`"',
    'OUT="$(echo "all green" && {c} 2>&1)"; echo "$OUT"',
    'OUT="$(cd "/c/my dir" && {c})"',
    'Write-Output "it`"s done"; {c}',
]
KNOWN_MISSED = {
    'git commit -m "a; b" -n': INSIDE_QUOTES,
    'git -c user.name="A; B" push origin main': INSIDE_QUOTES,
    'git commit -m "s\n\nb" -n': [
        *INSIDE_QUOTES[:5],
        "# don't run this before the checks\n{c}\n# that's it",
        INSIDE_QUOTES[5],
    ],
}
# Each is let through alone and in every shape: its quoted text holds a separator sign and
# also a quote sign that does not close it (escaped with a backslash, or inside a
# here-document), so no reading keeps the command whole.
KNOWN_MISSED_EVERYWHERE = [
    'git commit -m "say \\"a; b\\"" -n',
    "git commit -m \"$(cat <<'EOF'\nthe 5\" pipe | x\nEOF\n)\" -n",
]

ALLOWED = [
    "git status",
    "git log --oneline -5",
    "git diff --stat main..HEAD",
    "git add -A",
    "git fetch origin main",
    "gh pr checks 80 -R o/r",
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


# The shapes an allowed command is put inside before its own shape: none in the fast suite (I2
# above holds it one deep); every shape in the full suite, 13 * 41 * 41 = 21,853 cases.
OUTER_FOR_ALLOWED = SHAPES if full() else ["{c}"]


# Measured in the first full run, 2026-11-20: a push that names its branch, inside a command
# substitution inside another (20 of the 41 * 41 pairs each), is refused although it would not
# reach main. That errs to the safe side; guard.py's Known limits do not name it, and changing
# guard.py needs a decision of Achia's (PROMOTION.md, Level 3), so it is named here and in
# docs/STATUS.md.
KNOWN_REFUSED_TWO_DEEP = {
    "git push -u origin feat/x",
    "git -c credential.helper= -c credential.helper='!gh auth git-credential' push -q -u origin feat/x",
}


@pytest.mark.parametrize("outer", OUTER_FOR_ALLOWED)
def test_i2_an_allowed_command_is_let_through_in_every_shape_inside_every_shape(outer: str) -> None:
    wrongly = [
        outer.format(c=inner.format(c=command))
        for inner in SHAPES
        for command in ALLOWED
        if command not in KNOWN_REFUSED_TWO_DEEP and refused(outer.format(c=inner.format(c=command)))
    ]
    assert wrongly == []


def test_the_allowed_commands_known_to_be_refused_two_deep_are() -> None:
    assert KNOWN_REFUSED_TWO_DEEP <= set(ALLOWED)
    for command in KNOWN_REFUSED_TWO_DEEP:
        assert any(refused(outer.format(c=inner.format(c=command))) for outer in SHAPES for inner in SHAPES), command


@pytest.mark.parametrize("command", KNOWN_MISSED)
def test_the_known_misses_are_exactly_the_listed_shapes(command: str) -> None:
    assert refused(command)
    assert [shape for shape in SHAPES if not refused(shape.format(c=command))] == KNOWN_MISSED[command]


@pytest.mark.parametrize("command", KNOWN_MISSED_EVERYWHERE)
def test_the_commands_known_to_be_missed_everywhere_are_missed_in_every_shape(command: str) -> None:
    assert [shape for shape in SHAPES if refused(shape.format(c=command))] == []


def test_the_sample_is_over_the_minimum_for_an_invariant() -> None:
    # CLAUDE.md, Tests: an invariant is held over 500 generated cases.
    assert len(REFUSED) * len(SHAPES) >= 500
    assert len(REFUSED) * len(SHAPES) * len(SHAPES) >= 5000
    assert len(ALLOWED) * len(SHAPES) >= 500
    assert len(ALLOWED) * len(SHAPES) * len(OUTER_FOR_ALLOWED) >= (INVARIANT_FULL if full() else 500)
