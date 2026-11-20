"""Tests of .github/workflows/full.yml: its code lines, exactly as merged in #165.

Why: the full suite runs at full size before a phase closes, nightly and on request (Achia,
2026-11-20, "Yes, all four (Recommended)"). A later workflow-only PR holds no .py file, so the
changed-paths check lets an edit through that switches it off; the fast suite runs this test on
every PR, so such an edit goes red (issue #168; the pattern of the other check workflows, #166).

Equivalence class:
  F1 the workflow's code lines (tests/workflow_lines.py: comments and blank lines left out, a
     character outside ASCII refused) equal EXPECTED, the 26 lines of #165: its triggers (a
     label added, the nightly cron, a start by hand), the job condition on the two labels,
     PLONI_FULL_SUITE=1, the hashed install, ruff, mypy and `pytest tests`. Any changed or added
     line is red; a comment is not.
Hebrew and document axes: do not apply; the input is a workflow file.
"""

from pathlib import Path

from tests.workflow_lines import code_lines

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "full.yml"
# The code lines of full.yml as #165 merged them (code_lines()); any other line or one more
# changes how the full suite runs.
EXPECTED = [
    "name: full",
    "on:",
    "  pull_request:",
    "    types: [labeled]",
    "  schedule:",
    '    - cron: "17 1 * * *"',
    "  workflow_dispatch:",
    "permissions:",
    "  contents: read",
    "jobs:",
    "  full-suite:",
    "    if: github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'run-full') || contains(github.event.pull_request.labels.*.name, 'phase-close')",
    "    runs-on: ubuntu-24.04",
    "    timeout-minutes: 30",
    "    env:",
    '      PLONI_FULL_SUITE: "1"',
    "    steps:",
    "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
    "      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0",
    "        with:",
    '          python-version: "3.13.5"',
    '          pip-version: "25.1.1"',
    "      - run: python -m pip install --require-hashes -r requirements-dev.txt",
    "      - run: python -m ruff check .",
    "      - run: python -m mypy",
    "      - run: python -m pytest tests -q -p no:cacheprovider",
]


def test_f1_the_workflow() -> None:
    assert code_lines(WORKFLOW) == EXPECTED
