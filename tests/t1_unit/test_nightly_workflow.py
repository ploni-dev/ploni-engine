"""Tests of .github/workflows/nightly.yml: its code lines, exactly as merged in #184.

Why: the nightly check reads main's last nightly full run on every PR, and after a failed night
runs the full tests on the PR (Achia, 2026-11-20, "A robot blocks the next merge (Recommended)"
and "Yes, run the full tests (Recommended)", issue #167). A later workflow-only PR holds no .py
file, so the changed-paths check lets an edit through that switches it off (an `if:` that never
holds, the script run from the PR's checkout, a smaller suite); the fast suite runs this test on
every PR, so such an edit goes red (the pattern of the other check workflows, #166 and #171).

Equivalence class:
  F1 the workflow's code lines (tests/workflow_lines.py: comments and blank lines left out, a
     character outside ASCII refused) equal EXPECTED, the 31 lines of #184: the trigger on every
     pull request, the two permissions, main checked out into main-copy and the script run from
     there, the step id and the two conditions on its output, the hashed install and `pytest
     tests` at full size. Any changed or added line is red; a comment is not.
Hebrew and document axes: do not apply; the input is a workflow file.
Known limits: a PR that edits this test (or tests/workflow_lines.py) together with the workflow
is refused by changed-paths, which refuses a workflow with any .py file. A PR that edits the
workflow together with a non-.py file that keeps this test from running (a `--deselect` in
pyproject.toml's pytest options, the Makefile's `check` target) passes every check;
pyproject.toml and that make target are on the Level 3 list (PROMOTION.md section 4), so only
the review and CLAUDE.md stand against it (the review of #186, finding 1, measured).
"""

from pathlib import Path

from tests.workflow_lines import code_lines

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "nightly.yml"
# The code lines of nightly.yml as #184 merged them (code_lines()); any other line or one more
# changes what reads the night or what runs after a failed one.
EXPECTED = [
    "name: nightly",
    "on:",
    "  pull_request:",
    "permissions:",
    "  contents: read",
    "  actions: read",
    "jobs:",
    "  nightly:",
    "    runs-on: ubuntu-24.04",
    "    timeout-minutes: 30",
    "    steps:",
    "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
    "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
    "        with:",
    "          ref: main",
    "          path: main-copy",
    "      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0",
    "        with:",
    '          python-version: "3.13.5"',
    '          pip-version: "25.1.1"',
    "      - id: night",
    "        working-directory: main-copy",
    '        run: python -m scripts.check_nightly "$GITHUB_REPOSITORY"',
    "        env:",
    "          GITHUB_TOKEN: ${{ github.token }}",
    "      - if: steps.night.outputs.failed == 'true'",
    "        run: python -m pip install --require-hashes -r requirements-dev.txt",
    "      - if: steps.night.outputs.failed == 'true'",
    "        run: python -m pytest tests -q -p no:cacheprovider",
    "        env:",
    '          PLONI_FULL_SUITE: "1"',
]


def test_f1_the_workflow() -> None:
    assert code_lines(WORKFLOW) == EXPECTED
