"""Tests of .github/workflows/pr-checks.yml: its code lines, exactly as on main since #293.

Why: pr-checks runs the small checks of a PR as steps of one job (issue #209; Achia, 2026-11-25,
"Yes, add it (Recommended)", with its lines shown to him, and "Yes, trusted checks first
(Recommended)" to their order). A later workflow-only PR holds no .py file, so the changed-paths
check lets an edit of pr-checks.yml alone through that switches a check off (`run: true`, a step
removed, the edited trigger dropped), hides a check's report behind an earlier failure
(`if: ${{ !cancelled() }}` dropped) or weakens the two checks that run main's copies (the order
changed back so that the PR's files run before them, `-P` dropped, PYTHONPATH pointed at the PR,
`pip-version` given to setup-python, which would run `python -m pip` in the PR's folder before
them: the review of #229, findings 1 and 8). The PR's
fast suite runs this test on every PR, so such an edit goes red (the pattern of the other check
workflows, #166, #171, #186, #197, #200).

Equivalence class:
  F1 the workflow's code lines (tests/workflow_lines.py: comments and blank lines left out, a
     character outside ASCII refused) are the 73 on main since #293, pinned by their digest,
     NEXT_SHA256: the 48 lines of #229 (the pull_request trigger with edited among its types,
     read-only contents, the PR checked out with all its history and main under main-copy/, both
     without credentials, the two pinned actions, then the seven checks, each with
     `if: ${{ !cancelled() }}`: commit-order and reviewed-commit first, main's scripts run with
     `python -P` on HEAD^1 HEAD^2 and PYTHONPATH at main-copy, then changed-paths, pr-size,
     pr-body, ratchet and waiver with the commands their own workflows had until those were
     deleted, #258), with the two score-guard steps of issue #170 after code line 32, the run
     line of the reviewed-commit check: the 37 lines of Achia's record on #170
     (issuecomment-7200916140, "Yes, all three (Recommended)", 2026-11-26), 25 of them code. Any
     changed, added, removed or moved line is red; a comment is not. Those lines name the folder
     of the held-out batch, which no test file outside the batch's own may name (the batch's
     isolation test in tests/t8_privacy/ refuses it), so the pin holds their digest and not their
     text (see the comment beside it for how it is computed).
  F2 the pin (`pinned`):
       F2a the digest is the sha256 of the lines joined with LF, encoded as ASCII, in hex
       F2b lines whose digest is NEXT_SHA256 are accepted (shown with a made-up list and its
           digest put in its place, as the pinned lines cannot be written here)
       F2c refused: the workflow's lines without the last, with the last changed, with one line
           more; a made-up 73-line list under the real digest
       F2d main's old 48 lines (#229), taken from the workflow's lines by leaving out the 25 of
           the two steps, are refused: step 4 of the landing plan of #170 drops the old shape
     Not here: copies of the pinned form edited (one line dropped, `-P` dropped, the PR's
     workspace on the path, the check made `true`, the steps moved, one step only, the steps
     twice). Each would spell the pinned lines. They were run against the pin outside the tests,
     from a copy of the record's lines, and refused (the message of commit e1c100c, "the pin of
     pr-checks.yml accepts the approved score-guard steps too"); any one-character change of the
     73 lines changes the digest.
Hebrew and document axes: do not apply; the input is a workflow file.
Known limits: one PR with no .py file that edits fast.yml and fast-pin.yml together with
pr-checks.yml stops this test with them, every check green (the fast suite runs the PR's copy of
fast.yml, guarded only by the PR's copy of fast-pin.yml; tests/t1_unit/test_fast_pin_workflow.py,
Known limits); CI workflows are on the Level 3 list, so only the review stands against it. A PR
that edits pr-checks.yml together with a non-.py file that keeps this test from running (a
`--deselect` in pyproject.toml's pytest options, the Makefile's `check` target) passes every
check; those are on the Level 3 list too (PROMOTION.md section 4). The rule that a workflow and a
.py file may not share a PR is the changed-paths check, which runs as a step of this very file
and, since its own workflow was deleted (#258), nowhere else: the rule that guards this pin is a
step of the file it pins (the review of #229, pass 1).
The test reads the file as git checked it out, and GitHub runs the file as git stores it. A PR
with no .py file that edits pr-checks.yml together with .gitattributes could make the two
differ: `working-tree-encoding=ASCII//TRANSLIT` writes a stored no-break space as a space, so a
stored `HEAD<U+00A0>#|| true` reads here as a trailing comment and passes, while YAML runs it
with `|| true` (measured on the laptop's git in the review of this file, not on GitHub's
runner). In the fast suite tests/t1_unit/test_workflow_files.py now holds every workflow to
the file git stores: its mode, the attributes that rewrite a file on checkout, asked of the
attribute files on disk and of the stored ones, and the stored bytes against the ones on disk.
.gitattributes itself is on the Level 3 list since #248 (Achia, 2026-11-25). An edit that keeps the
code lines and would stop GitHub from running the file (a NUL character in a comment, the file
as a symbolic link to a copy) is refused by the reader since #239, and a pr-checks job that
does not run is refused by the merge gate since #241; what GitHub does with either file was
not measured (the same review, findings 2 and 8).
"""

import hashlib
import sys
from pathlib import Path

import pytest

from tests.workflow_lines import code_lines

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "pr-checks.yml"
# The 73 code lines on main since #293, read with code_lines(): the 48 lines of #229 with the 37
# lines of Achia's record on #170 (issuecomment-7200916140, the block after "The 37 lines inserted
# after it, exactly as they would be committed"), byte for byte, inserted after code line 32, the
# run line of the reviewed-commit check. Their text cannot stand here: they name the folder of the
# held-out batch, and the batch's isolation test in tests/t8_privacy/ refuses a test file that
# does. So they are pinned by their digest. To recompute it: read .github/workflows/pr-checks.yml
# with code_lines() (or main's file of #229 with the record's 37 lines inserted after its line
# 84), join the 73 lines with "\n" and no line end after the last, encode as ASCII, take sha256,
# and write it in lowercase hex.
NEXT_SHA256 = "95c26cc497753dc710532fe2dc1d7b404cf5248e77843ef0777bcf2294a3b3a2"
# The run line of the reviewed-commit check is code line 32 (index 31).
AFTER = 32
# The code lines of the two score-guard steps, after AFTER: 73 - 48.
STEPS = 25
# The workflow's code lines as they are, and main's old 48 of #229 taken from them.
LINES = code_lines(WORKFLOW)
OLD = LINES[:AFTER] + LINES[AFTER + STEPS :]
# A made-up 73-line list, for F2b and F2c only: it is not the pinned form.
MADE_UP = OLD[:AFTER] + ["      - run: echo made up"] * STEPS + OLD[AFTER:]


def digest(lines: list[str]) -> str:
    """Return the sha256, in hex, of code lines joined with LF and encoded as ASCII."""
    return hashlib.sha256("\n".join(lines).encode("ascii")).hexdigest()


def pinned(lines: list[str]) -> bool:
    """Say whether a workflow's code lines are the ones the pin accepts: those with the digest NEXT_SHA256."""
    return digest(lines) == NEXT_SHA256


def test_f1_the_workflow() -> None:
    assert pinned(code_lines(WORKFLOW))


def test_f2a_the_digest() -> None:
    assert digest(["a", "b"]) == hashlib.sha256(b"a\nb").hexdigest()
    assert len(NEXT_SHA256) == 64 and set(NEXT_SHA256) <= set("0123456789abcdef")
    assert digest(OLD) != NEXT_SHA256 and len(MADE_UP) == 73


def test_f2b_lines_with_the_pinned_digest_are_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys.modules[__name__], "NEXT_SHA256", digest(MADE_UP))
    assert pinned(MADE_UP)
    assert not pinned(LINES)


@pytest.mark.parametrize(
    "lines",
    [LINES[:-1], [*LINES[:-1], "          PR_BODY: x"], [*LINES, "      - run: true"], MADE_UP],
    ids=["one line fewer", "one line changed", "one line more", "73 made-up lines"],
)
def test_f2c_other_lines_are_refused(lines: list[str]) -> None:
    assert not pinned(lines)


def test_f2d_the_old_48_lines_are_refused() -> None:
    assert len(OLD) == 48 and not pinned(OLD)
