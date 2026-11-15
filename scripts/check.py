"""Run the fast suite: ruff, mypy and the fast test tiers.

Why: one command gives the same answer on the laptop and in CI. `make check` calls this
script; the laptop has no `make`, so there it is run as `python scripts/check.py`.

Contract: run from any folder. Exit code 0 when every step passed, 1 when any failed.
Every step runs, also after a failure, so that one run shows everything that is wrong.

Known limits: the secret scan and the docstring check of PROCESS.md section 5.1 are not
steps yet; neither tool exists.
"""

import subprocess
import sys
from pathlib import Path

Step = tuple[str, list[str]]

# PROCESS.md section 5.1: these tiers belong to the full suite, not to the fast one.
FULL_SUITE_ONLY = ("t4_integration", "t5_system", "t6_metrics", "t7_perf")


def steps(root: Path) -> list[Step]:
    """Decide which commands the fast suite runs in the repository at root.

    Why: mypy checks `ploni/` only (PROCESS.md section 4.5) and fails when given no file,
    so it joins the suite once that folder exists.

    Args:
        root: the repository root.

    Returns:
        (name, command) pairs in the order they run. Every command starts the interpreter
        that runs this script, so the tools come from the same environment.
    """
    python = [sys.executable, "-m"]
    ignored = [f"--ignore=tests/{tier}" for tier in FULL_SUITE_ONLY]
    chosen = [("ruff", [*python, "ruff", "check", "."])]
    if (root / "ploni").is_dir():
        chosen.append(("mypy", [*python, "mypy"]))
    chosen.append(("pytest", [*python, "pytest", "tests", *ignored]))
    return chosen


def run(chosen: list[Step], root: Path) -> list[str]:
    """Run every step in root and report the ones that failed.

    Why: a run that stops at the first failure hides the others, and each costs a round trip.

    Args:
        chosen: (name, command) pairs, as `steps` returns them.
        root: the folder each command starts in.

    Returns:
        The names of the steps whose command ended with a non-zero exit code, in order.
    """
    failed = []
    for name, command in chosen:
        print(f"== {name}", flush=True)
        if subprocess.run(command, cwd=root, check=False).returncode != 0:  # noqa: S603 fixed argv, no shell
            failed.append(name)
    return failed


def main() -> int:
    """Run the fast suite of this repository and return its exit code.

    Returns:
        0 when every step passed, 1 when any step failed.
    """
    root = Path(__file__).resolve().parent.parent
    failed = run(steps(root), root)
    print("fast suite: " + (f"FAILED: {', '.join(failed)}" if failed else "ok"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
