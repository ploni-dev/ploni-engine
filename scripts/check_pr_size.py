"""Check that a PR stays within the size limits of PROCESS.md section 6.3 for product code.

Why: `PROCESS.md` section 6.3: "Production files changed: 10 soft, 15 hard"; "Net production
lines: 400 soft, 800 hard (tests, fixtures, golden files excluded)"; and section 1: a diff
nobody can read means nobody is reviewing. `PROMOTION.md` section 5.1 lists "PR size limits:
the changed-files and diff-size test" among the Class A checks (issue #78). Achia decided on
2026-11-20 to build it, of the option "3. PR size limit": "A new GitHub robot: a change over 15
product files or 800 product lines turns red; over 10 files or 400 lines gets a warning."

Contract: `python -m scripts.check_pr_size <base> <head>`, run inside the checkout.

Known limits: stub.
"""

import sys


def is_product(path: str) -> bool:
    """Say whether a changed path is product code."""
    return False


def measure(rows: list[tuple[str, str, str]]) -> tuple[int, int]:
    """Return the product files a PR changes and its net product lines."""
    return 0, 0


def judge(files: int, net: int) -> tuple[list[str], list[str]]:
    """Return the problems over a hard limit and the warnings over a soft one."""
    return [], []


def main(argv: list[str]) -> int:
    """Check the PR between the two revisions in argv; return the exit code."""
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
