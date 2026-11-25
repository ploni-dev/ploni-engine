"""Tests of .github/workflows/pr-checks.yml: its code lines, exactly as merged in #229.

Why: pr-checks runs the small checks of a PR as steps of one job (issue #209; Achia, 2026-11-25,
"Yes, add it (Recommended)", with its lines shown to him, and "Yes, trusted checks first
(Recommended)" to their order). A later workflow-only PR holds no .py file, so the changed-paths
check lets an edit of pr-checks.yml alone through that switches a check off (`run: true`, a step
removed, `if: ${{ !cancelled() }}` dropped, the edited trigger dropped) or weakens the two checks
that run main's copies (the order changed back so that the PR's files run before them, `-P`
dropped, PYTHONPATH pointed at the PR, `pip-version` given to setup-python, which would run
`python -m pip` in the PR's folder before them: the review of #229, findings 1 and 8). The PR's
fast suite runs this test on every PR, so such an edit goes red (the pattern of the other check
workflows, #166, #171, #186, #197, #200).

Equivalence class:
  F1 the workflow's code lines (tests/workflow_lines.py: comments and blank lines left out, a
     character outside ASCII refused) equal EXPECTED, the 48 lines of #229, in their order: the
     pull_request trigger with edited among its types, read-only contents, the PR checked out
     with all its history and main under main-copy/, both without credentials, the two pinned
     actions, then the seven checks, each with `if: ${{ !cancelled() }}`: commit-order and
     reviewed-commit first, main's scripts run with `python -P` on HEAD^1 HEAD^2 and PYTHONPATH
     at main-copy, then changed-paths, pr-size, pr-body, ratchet and waiver with the commands of
     their own workflows. Any changed, added, removed or moved line is red; a comment is not.
Hebrew and document axes: do not apply; the input is a workflow file.
Known limits: one PR with no .py file that edits fast.yml and fast-pin.yml together with
pr-checks.yml stops this test with them, every check green (the fast suite runs the PR's copy of
fast.yml, guarded only by the PR's copy of fast-pin.yml; tests/t1_unit/test_fast_pin_workflow.py,
Known limits); CI workflows are on the Level 3 list, so only the review stands against it. A PR
that edits pr-checks.yml together with a non-.py file that keeps this test from running (a
`--deselect` in pyproject.toml's pytest options, the Makefile's `check` target) passes every
check; those are on the Level 3 list too (PROMOTION.md section 4). The rule that a workflow and a
.py file may not share a PR is the changed-paths check, which runs today in changed-paths.yml and
as a step of this very file: if that workflow is removed, the rule that guards this pin is a step
of the file it pins (the review of #229, pass 1).
"""

from pathlib import Path

from tests.workflow_lines import code_lines

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "pr-checks.yml"
# The code lines of pr-checks.yml as #229 merged them (code_lines()); any other line, one more,
# one fewer or another order changes what pr-checks reads or runs.
EXPECTED = [
    "name: pr-checks",
    "on:",
    "  pull_request:",
    "    types: [opened, edited, synchronize, reopened]",
    "permissions:",
    "  contents: read",
    "jobs:",
    "  pr-checks:",
    "    runs-on: ubuntu-24.04",
    "    timeout-minutes: 5",
    "    steps:",
    "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
    "        with:",
    "          fetch-depth: 0",
    "          persist-credentials: false",
    "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
    "        with:",
    "          ref: main",
    "          path: main-copy",
    "          persist-credentials: false",
    "      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0",
    "        with:",
    '          python-version: "3.13.5"',
    "      - if: ${{ !cancelled() }}",
    "        env:",
    "          PYTHONPATH: ${{ github.workspace }}/main-copy",
    "        run: python -P -m scripts.check_commit_order HEAD^1 HEAD^2",
    "      - if: ${{ !cancelled() }}",
    "        env:",
    "          PYTHONPATH: ${{ github.workspace }}/main-copy",
    "          PR_BODY: ${{ github.event.pull_request.body }}",
    "        run: python -P -m scripts.check_reviewed_commit HEAD^1 HEAD^2",
    "      - if: ${{ !cancelled() }}",
    "        run: python scripts/check_changed_paths.py HEAD^1 HEAD",
    "      - if: ${{ !cancelled() }}",
    "        run: python -m scripts.check_pr_size HEAD^1 HEAD",
    "      - if: ${{ !cancelled() }}",
    "        run: python scripts/check_pr_body.py",
    "        env:",
    "          PR_BODY: ${{ github.event.pull_request.body }}",
    "      - if: ${{ !cancelled() }}",
    "        run: python -m scripts.check_ratchet HEAD^1 HEAD",
    "        env:",
    "          PR_BODY: ${{ github.event.pull_request.body }}",
    "      - if: ${{ !cancelled() }}",
    "        run: python -m scripts.check_waiver HEAD^1 HEAD",
    "        env:",
    "          PR_BODY: ${{ github.event.pull_request.body }}",
]


def test_f1_the_workflow() -> None:
    assert code_lines(WORKFLOW) == EXPECTED
