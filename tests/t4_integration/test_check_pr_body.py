"""Module suite for scripts/check_pr_body.py: the script run as a program, as the workflow runs it.

Why: the workflow sees only the exit code of `python scripts/check_pr_body.py`. The unit tests
call `main()`; only a real run shows that the program passes its result on as its exit code
(a lost `sys.exit` would make the check green on every PR).

Matrix:
  M1  an empty PR_BODY        exit 1, both sections named missing on the error stream
  M2  a filled body           exit 0, nothing written
  M3  no PR_BODY at all       exit 1

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import os
import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
SCRIPT = REPOSITORY / "scripts" / "check_pr_body.py"
GOOD = "## Orientation\nGoal: g\nDeliverable: d\nGate: x\nDownstream risk if wrong: r\n## Ponytail review\nShip.\n"


def run(body: str | None) -> subprocess.CompletedProcess[str]:
    """Run the script with the body in PR_BODY, or with no PR_BODY when it is None."""
    environment = {key: value for key, value in os.environ.items() if key != "PR_BODY"}
    if body is not None:
        environment["PR_BODY"] = body
    return subprocess.run([sys.executable, str(SCRIPT)], env=environment, capture_output=True, text=True, timeout=60, check=False)  # noqa: S603 fixed argv, no shell


def test_m1_an_empty_body() -> None:
    done = run("")
    assert done.returncode == 1 and done.stdout == ""
    assert done.stderr.splitlines() == ["missing: ## Orientation", "missing: ## Ponytail review"]


def test_m2_a_filled_body() -> None:
    done = run(GOOD)
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_m3_no_body_at_all() -> None:
    assert run(None).returncode == 1
