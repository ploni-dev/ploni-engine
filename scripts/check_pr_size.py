"""Check that a PR stays within the size limits of PROCESS.md section 6.3 for product code.

Why: `PROCESS.md` section 6.3: "Production files changed: 10 soft, 15 hard"; "Net production
lines: 400 soft, 800 hard (tests, fixtures, golden files excluded)"; and section 1: a diff
nobody can read means nobody is reviewing. `PROMOTION.md` section 5.1 lists "PR size limits:
the changed-files and diff-size test" among the Class A checks (issue #78). Achia decided on
2026-11-20 to build it, of the option "3. PR size limit": "A new GitHub robot: a change over 15
product files or 800 product lines turns red; over 10 files or 400 lines gets a warning." Asked
the same day whether a rewrite in place counts, he chose "Count every changed line
(Recommended)": "Lines added plus lines removed. A 1,000-line rewrite turns red, a 450-line one
gets a warning. Stricter: big rewrites must be split, as big additions are." So a line is
counted when added and when removed, where PROCESS.md 6.3 says "net".

Contract: `python -m scripts.check_pr_size <base> <head>`, run inside the checkout. What `head`
changed since it left `base` is read from git (`base...head`). Product code is every file under
`ploni/` and `ui/`, the product's two folders (`build-plan.md` section 4.7). Over a hard limit:
one line per limit on the error stream, exit 1. Over a soft limit only: one GitHub warning line
per limit on the output (`::warning::...`), exit 0. A binary product file, whose lines git does
not count, is named in a warning of its own. Within: nothing, exit 0. Wrong arguments: a
usage line, exit 2. A revision git does not know: git's error, a traceback, a non-zero exit.

Known limits:
- "Over" a limit is more than it: 15 files and 800 lines pass with a warning.
- Lines are counted as git counts them: a changed line is one added and one deleted, two lines.
- A file git takes as binary (by its content, or by a `-diff` in `.gitattributes`) counts as a
  file with no lines; the warning that names it is what shows it to the reviewer.
- Only `ploni/` and `ui/` count, as Achia's option said "product". Scripts, experiments and
  the documentation of a PR are not limited here; tests, fixtures and golden files are excluded
  by PROCESS.md 6.3 itself.
- "One phase per PR" and "Reviewable in 15 minutes" of section 6.3 are not checked: no machine
  can tell them. They stand on the review.
"""

import shutil
import subprocess
import sys
from pathlib import Path

# build-plan.md section 4.7: the product's two folders.
PRODUCT = ("ploni/", "ui/")
# PROCESS.md section 6.3.
SOFT_FILES = 10
HARD_FILES = 15
SOFT_LINES = 400
HARD_LINES = 800
# git's count for a binary file.
BINARY = "-"
USAGE = "usage: python -m scripts.check_pr_size <base> <head>"
# git from PATH, as a full path, as in CI; the seconds git may take.
GIT = shutil.which("git") or "git"
GIT_TIMEOUT_SECONDS = 60


def is_product(path: str) -> bool:
    """Say whether a changed path is product code: a file under ploni/ or ui/.

    Why: PROCESS.md 6.3 limits production code, and Achia's option named product files.

    Contract: `path` as git writes it, relative to the repository root, with forward slashes.
    """
    return path.startswith(PRODUCT)


def measure(rows: list[tuple[str, str, str]]) -> tuple[int, int, list[str]]:
    """Return what a PR changes of product code: its files, its changed lines, its binary files.

    Why: the two numbers PROCESS.md 6.3 limits, apart from where the rows come from, and the
    files whose lines cannot be counted.

    Contract: `rows` as git's numstat gives them: (added, deleted, path), the counts as text,
    "-" for a binary file. Changed lines are added plus deleted over product files; a binary
    file counts as a file and as no line, and its path is returned. Returns (files, lines,
    binary paths in row order).
    """
    product = [(added, deleted, path) for added, deleted, path in rows if is_product(path)]
    lines = sum(int(added) + int(deleted) for added, deleted, _ in product if added != BINARY)
    binary = [path for added, _, path in product if added == BINARY]
    return len(product), lines, binary


def judge(files: int, lines: int) -> tuple[list[str], list[str]]:
    """Return the problems over a hard limit and the warnings over a soft one.

    Why: the judgement of the check, apart from how the numbers were counted.

    Contract: returns (problems, warnings); a limit is reported once, as a problem when over
    its hard value, else as a warning when over its soft value. The files line comes first.
    """
    problems: list[str] = []
    warnings: list[str] = []
    for count, soft, hard, what in ((files, SOFT_FILES, HARD_FILES, "product files changed"), (lines, SOFT_LINES, HARD_LINES, "changed product lines")):
        if count > hard:
            problems.append(f"{count} {what}, over the hard limit of {hard}")
        elif count > soft:
            warnings.append(f"{count} {what}, over the soft limit of {soft}")
    return problems, warnings


def numstat(base: str, head: str, cwd: Path) -> list[tuple[str, str, str]]:
    """Return git's added and deleted lines per file that `head` changed since it left `base`.

    Why: a PR is judged on what it changes, not on what its base gained since; a renamed file
    counts on both sides, so that a move is not a way around the file limit; and a path with a
    Hebrew name or a line break must arrive whole.

    Contract: runs `git diff --numstat --no-renames -z base...head` in `cwd`; returns (added,
    deleted, path) per file, the counts as git writes them. Raises CalledProcessError when git
    fails.
    """
    done = subprocess.run(  # noqa: S603 fixed argv, no shell
        [GIT, "diff", "--numstat", "--no-renames", "-z", f"{base}...{head}"],
        cwd=cwd,
        stdout=subprocess.PIPE,
        check=True,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    rows = []
    for entry in done.stdout.decode("utf-8").split("\0"):
        if entry:
            added, deleted, path = entry.split("\t", 2)
            rows.append((added, deleted, path))
    return rows


def main(argv: list[str]) -> int:
    """Check the PR between the two revisions in argv; return the exit code.

    Why: the entry point of the workflow, given its arguments so that a test can call it.

    Contract: argv is [base, head]. Any other length: the usage line on the error stream, exit 2.
    """
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    files, lines, binary = measure(numstat(argv[0], argv[1], Path.cwd()))
    problems, warnings = judge(files, lines)
    warnings += [f"binary product file, its lines not counted: {path}" for path in binary]
    for line in warnings:
        print(f"::warning::{line}")
    for line in problems:
        print(line, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
