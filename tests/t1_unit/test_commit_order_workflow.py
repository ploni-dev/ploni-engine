"""Tests of .github/workflows/commit-order.yml: its code lines, exactly as merged in #198.

Why: commit-order checks that a PR's tests come before its code (issue #175; Achia, 2026-11-20,
"Yes, all four (Recommended)"; 2026-11-23, "Yes, one workflow each (Recommended)"). A later
workflow-only PR holds no .py file, so the changed-paths check lets an edit of commit-order.yml
alone through that switches it off (`run: true`, the PR's own copy of the script run, Python run
with pr/ on its import path, a shallow fetch, the edited trigger dropped); the fast suite runs
this test on every PR, so such an edit goes red (the pattern of the other check workflows, #166,
#171, #186, #197).

Equivalence class:
  F1 the workflow's code lines (tests/workflow_lines.py: comments and blank lines left out, a
     character outside ASCII refused) equal EXPECTED, the 27 lines of #198: the pull_request
     trigger with edited among its types, read-only contents, main checked out at the root and
     the PR with all its history under pr/, both without credentials, the two pinned actions, and
     main's script run with `python -P` from pr/ on HEAD^1 HEAD^2, PYTHONPATH the root. Any
     changed or added line is red; a comment is not.
Hebrew and document axes: do not apply; the input is a workflow file.
Known limits: a PR that edits commit-order.yml together with a non-.py file that keeps this test
from running (a `--deselect` in pyproject.toml's pytest options, the Makefile's `check` target)
passes every check; pyproject.toml and that make target are on the Level 3 list (PROMOTION.md
section 4), so only the review and CLAUDE.md stand against it (as the pin of fast-pin.yml, the
review of #197, finding 1).
"""

from pathlib import Path

from tests.workflow_lines import code_lines

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "commit-order.yml"
# The code lines of commit-order.yml as #198 merged them (code_lines()); any other line or one
# more changes what commit-order reads or runs.
EXPECTED = [
    "name: commit-order",
    "on:",
    "  pull_request:",
    "    types: [opened, edited, synchronize, reopened]",
    "permissions:",
    "  contents: read",
    "jobs:",
    "  commit-order:",
    "    runs-on: ubuntu-24.04",
    "    timeout-minutes: 5",
    "    steps:",
    "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
    "        with:",
    "          ref: main",
    "          persist-credentials: false",
    "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
    "        with:",
    "          path: pr",
    "          fetch-depth: 0",
    "          persist-credentials: false",
    "      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0",
    "        with:",
    '          python-version: "3.13.5"',
    "      - working-directory: pr",
    "        env:",
    "          PYTHONPATH: ${{ github.workspace }}",
    "        run: python -P -m scripts.check_commit_order HEAD^1 HEAD^2",
]


def test_f1_the_workflow() -> None:
    assert code_lines(WORKFLOW) == EXPECTED
