"""The check before a commit: the quick checks of PROCESS.md section 5.6 on what is staged.

Why: stub.
"""

import sys
from pathlib import Path

CHECK_TESTS = (
    "tests/t8_privacy/test_secrets.py",
    "tests/t8_privacy/test_imports.py",
    "tests/t0_contract/test_docstrings.py",
    "tests/t0_contract/test_third_party.py",
)


def steps(paths: list[str]) -> list[tuple[str, list[str]]]:
    """Return the checks to run for the staged paths."""
    return []


def staged(cwd: Path) -> list[str]:
    """Return the paths staged for the next commit."""
    return []


def main(cwd: Path) -> int:
    """Run the checks for what is staged in cwd; return the exit code."""
    return 0


if __name__ == "__main__":
    sys.exit(main(Path.cwd()))
