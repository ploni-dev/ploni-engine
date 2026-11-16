"""Run the fast suite: ruff, mypy, the fast test tiers.

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

SKIPPED_MYPY = "print('skipped: there is no ploni/ folder to type-check')"


def steps(root: Path) -> list[Step]:
    """Return the commands of the fast suite for the repository at root.

    Why: mypy checks `ploni/` only (PROCESS.md section 4.5) and fails when given no file.
    Until that folder exists its step prints that it was skipped, so that a type check
    that did not run never looks like one that passed.

    Contract:
        Args: root, the repository root.
        Returns: (name, command) pairs in the order they run: ruff, mypy, pytest. Every
            command starts the interpreter that runs this script, so the tools come from
            the same environment.
        Raises: nothing.

    Known limits: ruff and mypy read which rules and files they check from pyproject.toml.
    """
    python = [sys.executable, "-m"]
    ignored = [f"--ignore=tests/{tier}" for tier in FULL_SUITE_ONLY]
    mypy = [*python, "mypy"] if (root / "ploni").is_dir() else [sys.executable, "-c", SKIPPED_MYPY]
    return [
        ("ruff", [*python, "ruff", "check", "."]),
        ("mypy", mypy),
        ("pytest", [*python, "pytest", "tests", *ignored]),
    ]


def run(chosen: list[Step], root: Path) -> list[str]:
    """Return the names of the steps that fail when run in root.

    Why: a run that stops at the first failure hides the others, and each costs a round trip.

    Contract:
        Args: chosen, (name, command) pairs as `steps` returns them; root, the folder each
            command starts in.
        Returns: the names of the steps whose command ended with a non-zero exit code, in
            the order they ran. Every step runs, whatever the ones before it did.
        Raises: OSError if a command cannot be started; the steps after it do not run.

    Known limits: the steps run one after another; their output is not captured.
    """
    failed = []
    for name, command in chosen:
        print(f"== {name}", flush=True)
        if subprocess.run(command, cwd=root, check=False).returncode != 0:  # noqa: S603 fixed argv, no shell
            failed.append(name)
    return failed


def main() -> int:
    """Return the exit code of the fast suite of this repository.

    Why: `make check`, the CI workflow and a person at the laptop all start here, so all
    three get the same steps.

    Contract:
        Returns: 0 when every step passed, 1 when any step failed. The last line printed
            names the steps that failed.
        Raises: OSError as `run` does.

    Known limits: the repository is the one this file lies in, wherever it is started from.
    """
    root = Path(__file__).resolve().parent.parent
    failed = run(steps(root), root)
    print("fast suite: " + (f"FAILED: {', '.join(failed)}" if failed else "ok"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
