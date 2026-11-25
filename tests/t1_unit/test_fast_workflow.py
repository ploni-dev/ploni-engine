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
     line is red; a comment is not. Until step 10 of the plan on issue #209 the lines may also
     equal NEXT: EXPECTED with the one line that keeps the push trigger to main.
  F2 in the fast-pin job, where main is checked out at the root and the PR under pr/, the
     fast.yml under test holds the bytes that the PR's commit stores, line ends apart: the job
     copies the PR's checked-out file, and a .gitattributes line of the PR could have rewritten
     it on checkout (issue #239). Outside that job there is no pr/ and the case asks nothing;
     the comparison itself is tested on a small repository: the stored bytes, the same with CRLF,
     other bytes.
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

import pytest

from scripts.check_commit_order import git
from tests.workflow_lines import code_lines

REPOSITORY = Path(__file__).resolve().parents[2]
WORKFLOW = REPOSITORY / ".github" / "workflows" / "fast.yml"
STORED_NAME = ".github/workflows/fast.yml"
# In the fast-pin job main is checked out at the root and the PR under this folder (fast-pin.yml).
PR_FOLDER = "pr"
# The names git lists as a repository's own (GIT_DIR and the rest): a test started under a hook
# would otherwise ask the hook's repository (as tests/t1_unit/test_workflow_files.py).
LOCAL_VARIABLES = git(["rev-parse", "--local-env-vars"], REPOSITORY).split()
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
# Step 8 of the plan on issue #209 (Achia, 2026-11-25, "Yes, once per PR push (Recommended)"): the
# next PR adds this one line under `push:`, after the first three lines (name, on, push), so that
# a push to a PR's branch runs the suite once, for the PR. Until the third PR drops the old
# shape, the pin accepts either exact shape and no other.
NEXT = [*EXPECTED[:3], "    branches: [main]", *EXPECTED[3:]]


@pytest.fixture(autouse=True)
def no_local_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop git's repository-local variables for the test, in this process and in what it starts."""
    for name in LOCAL_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def test_f1_the_workflow() -> None:
    assert code_lines(WORKFLOW) in (EXPECTED, NEXT)


def _is_the_stored_file(workflow: Path, checkout: Path) -> bool:
    """Say whether a workflow file holds the bytes that the checkout's last commit stores for fast.yml.

    Why: the fast-pin job copies the PR's checked-out fast.yml beside main's tests, and a
    .gitattributes line of the PR can make that copy differ from the stored file, which is the
    one GitHub runs (issue #239; the review of its fix, finding 1). Contract: workflow, the
    file under test; checkout, a git checkout whose HEAD stores STORED_NAME. Line ends apart.
    Raises CalledProcessError when git fails, as when the commit stores no such file;
    UnicodeDecodeError when the stored file is not UTF-8; OSError when the file under test
    cannot be read.
    """
    stored = git(["cat-file", "blob", f"HEAD:{STORED_NAME}"], checkout).replace("\r\n", "\n")
    return workflow.read_bytes().decode("utf-8", errors="replace").replace("\r\n", "\n") == stored


def _held_to_the_stored_file(root: Path) -> bool:
    """Say whether, in the fast-pin job's layout under root, fast.yml holds the bytes the PR stores.

    Why: F2 must bite in the job and ask nothing outside it, and both halves need a case that
    runs (the review of the fix of #239, pass 2, finding 10: with the choice inside the test,
    three one-line edits switched it off and every test passed). Contract: root, a folder with
    STORED_NAME in it. True where no git checkout stands under PR_FOLDER; otherwise what
    _is_the_stored_file says of root's file and that checkout.
    """
    checkout = root / PR_FOLDER
    return not (checkout / ".git").exists() or _is_the_stored_file(root / STORED_NAME, checkout)


def test_f2_in_the_fast_pin_job_the_file_is_the_stored_one() -> None:
    assert _held_to_the_stored_file(REPOSITORY)


def test_f2_the_job_checks_the_pr_out_under_that_folder() -> None:
    assert f"          path: {PR_FOLDER}" in code_lines(REPOSITORY / ".github" / "workflows" / "fast-pin.yml")


def stored_fast_yml(repository: Path) -> None:
    """Make a repository whose one commit stores fast.yml as the line `x`."""
    folder = repository / ".github" / "workflows"
    folder.mkdir(parents=True)
    (folder / "fast.yml").write_bytes(b"x\n")
    git(["init", "-q"], repository)
    git(["-c", "core.autocrlf=false", "add", "-A"], repository)
    git(["-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-q", "-m", "x"], repository)


@pytest.mark.parametrize(("on_disk", "same"), [("x\n", True), ("x\r\n", True), ("x #|| true\n", False)], ids=["as-stored", "crlf", "rewritten"])
def test_f2_the_comparison(tmp_path: Path, on_disk: str, same: bool) -> None:
    stored_fast_yml(tmp_path)
    copy = tmp_path / "copy.yml"
    copy.write_bytes(on_disk.encode("utf-8"))
    assert _is_the_stored_file(copy, tmp_path) is same


@pytest.mark.parametrize(
    ("layout", "on_disk", "held"),
    [("pr", "x\n", True), ("pr", "x #|| true\n", False), ("none", "x #|| true\n", True), ("pull", "x #|| true\n", True)],
    ids=["the-job-as-stored", "the-job-rewritten", "no-checkout", "a-checkout-under-another-name"],
)
def test_f2_the_layout(tmp_path: Path, layout: str, on_disk: str, held: bool) -> None:
    root = tmp_path / "root"
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / STORED_NAME).write_bytes(on_disk.encode("utf-8"))
    if layout != "none":
        stored_fast_yml(root / layout)
    assert _held_to_the_stored_file(root) is held
