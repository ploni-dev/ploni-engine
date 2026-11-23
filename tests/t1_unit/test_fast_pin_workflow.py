"""Tests of .github/workflows/fast-pin.yml: its code lines, exactly as merged in #195.

Why: fast-pin runs the pin of the fast workflow outside it (issue #173; Achia, 2026-11-20, "Yes,
all four (Recommended)"; 2026-11-23, "Yes, one workflow each (Recommended)"). A later
workflow-only PR holds no .py file, so the changed-paths check lets an edit of fast-pin.yml alone
through that switches it off (`run: true`, the PR's own test run in place of main's, Python run in
the PR's checkout); the fast suite runs this test on every PR, so such an edit goes red (the
pattern of the other check workflows, #166, #171, #186).

Equivalence class:
  F1 the workflow's code lines (tests/workflow_lines.py: comments and blank lines left out, a
     character outside ASCII refused) equal EXPECTED, the 25 lines of #195: the pull_request
     trigger, read-only contents, main checked out at the root and the PR under pr/, both
     without credentials, the two pinned actions, the hashed install of main's tools, the copy
     of the PR's fast.yml over main's, and main's pin run at the root. Any changed or added line
     is red; a comment is not.
Hebrew and document axes: do not apply; the input is a workflow file.
Known limits: a PR that edits both fast.yml and fast-pin.yml with no .py file is not caught here
(the fast suite runs the PR's copy of this test, which the PR may leave as it is, and the PR's
copy of each workflow); fast-pin.yml's header says what stands against that. A PR that edits
fast-pin.yml together with a non-.py file that keeps this test from running (a `--deselect` in
pyproject.toml's pytest options, the Makefile's `check` target) passes every check;
pyproject.toml and that make target are on the Level 3 list (PROMOTION.md section 4), so only
the review and CLAUDE.md stand against it (the review of #197, finding 1, measured).
"""

from pathlib import Path

from tests.workflow_lines import code_lines

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "fast-pin.yml"
# The code lines of fast-pin.yml as #195 merged them (code_lines()); any other line or one more
# changes what fast-pin reads or runs.
EXPECTED = [
    "name: fast-pin",
    "on:",
    "  pull_request:",
    "permissions:",
    "  contents: read",
    "jobs:",
    "  fast-pin:",
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
    "          persist-credentials: false",
    "      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0",
    "        with:",
    '          python-version: "3.13.5"',
    '          pip-version: "25.1.1"',
    "      - run: python -m pip install --require-hashes -r requirements-dev.txt",
    "      - run: cp pr/.github/workflows/fast.yml .github/workflows/fast.yml",
    "      - run: python -m pytest tests/t1_unit/test_fast_workflow.py -q -p no:cacheprovider",
]


def test_f1_the_workflow() -> None:
    assert code_lines(WORKFLOW) == EXPECTED
