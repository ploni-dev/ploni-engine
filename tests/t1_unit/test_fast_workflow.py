"""Tests of .github/workflows/fast.yml: its code lines, exactly as on main since #77.

Why: fast-suite is the check the merge gate has asked for by name since #80, and a workflow-only
PR holds no .py file, so the changed-paths check lets an edit through that keeps it green while
it runs less (an ignored tier, a `|| true`, `run: true`). A pin inside the fast suite alone cannot
hold it, as such an edit stops the pin too; so this test runs in the fast suite and, by itself,
from a workflow of its own outside it (issue #173; Achia, 2026-11-20, "Yes, all four
(Recommended)", of "4. Guard for the fast robot: a test, run outside the fast-test robot, that
goes red if someone edits that robot to run fewer tests"; 2026-11-23, "Yes, one workflow each
(Recommended)").

Equivalence class:
  F1 the workflow's code lines (tests/workflow_lines.py: comments and blank lines left out, a
     character outside ASCII refused) equal EXPECTED, the 18 lines on main: the push and
     pull_request triggers, read-only contents, the job fast-suite with its runner and its five
     minutes, the two pinned actions, the hashed install and `make check`. Any changed or added
     line is red; a comment is not.
Hebrew and document axes: do not apply; the input is a workflow file.
Known limits: `make check` is pinned by its name only. A PR that changes only the `Makefile`'s
`check` target, or adds a pytest configuration file (`pytest.ini`, say, with `--collect-only` in
its options), has no .py file and no workflow, and passes every check; `scripts/check.py` is
guarded only by its own tests, which a code PR may change with it. The Makefile target and the
pytest configuration files are on the Level 3 list (PROMOTION.md section 4), so only the review
and CLAUDE.md stand against such a PR (the review of #193, finding 1). On a pull request GitHub
runs the PR's own copy of each workflow, so one PR with no .py file that edits both fast.yml and
the workflow that runs this test outside it switches off both, every check green, and only the
review stands against it. Reading the test and the pytest configuration from main's copy, as
nightly.yml reads its script, closes only the route through the PR's test file or pytest
configuration, not that one; whether `pull_request_target` (which runs the base branch's copy of
the workflow) can close it, with its check on the PR's head where the gate reads it, can be
measured only now that that workflow, fast-pin.yml (#195), is on main, as its header says (the
reviews of #193, findings 2 and 4, and of #195, finding 4). Its pin is
tests/t1_unit/test_fast_pin_workflow.py.
"""

from pathlib import Path

from tests.workflow_lines import code_lines

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "fast.yml"
# The code lines of fast.yml as on main (code_lines()); any other line or one more changes what
# the fast suite runs or when.
EXPECTED = [
    "name: fast",
    "on:",
    "  push:",
    "  pull_request:",
    "permissions:",
    "  contents: read",
    "jobs:",
    "  fast-suite:",
    "    runs-on: ubuntu-24.04",
    "    timeout-minutes: 5",
    "    steps:",
    "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
    "      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0",
    "        with:",
    '          python-version: "3.13.5"',
    '          pip-version: "25.1.1"',
    "      - run: python -m pip install --require-hashes -r requirements-dev.txt",
    "      - run: make check",
]


def test_f1_the_workflow() -> None:
    assert code_lines(WORKFLOW) == EXPECTED
