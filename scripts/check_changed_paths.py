"""Check that a PR which changes code changes neither the baselines nor a CI workflow.

Why: `PROMOTION.md` section 5.1, the rows "Baselines not changed in a code PR" and "CI
workflows not edited by a code PR"; `CLAUDE.md`, "Code changes and baseline or gate changes
never share a PR". A code PR that also moves a baseline or edits the workflow that judges it
can make its own check pass. Bad PR 7 of the closing test of Phase 0 (`PROMOTION.md`
section 10) must go red here. Issue #78. Code is any .py file anywhere: Achia's answer of
2026-11-19, "New workflow file (Recommended)", whose text said "'Code' means any .py file
anywhere in the repo."

Contract: `python scripts/check_changed_paths.py <base> <head>`, run inside the checkout. The
paths changed between the two revisions are read from git. Each baselines or workflow path
changed together with code is written on the error stream, one line each, and the exit code
is 1; otherwise nothing is written and the exit code is 0. Wrong arguments: a usage line,
exit 2. A revision git does not know: git's error, a traceback, a non-zero exit.

Known limits:
- `.github/actions/` (composite actions a workflow may call) is not watched; none exists.
- A gate value outside `eval/baselines.json`, such as the `config.py` of a later phase, is
  not watched yet.
- The check sees paths, not content: it cannot tell a code change from a comment change.
"""

import subprocess
import sys
from pathlib import Path

BASELINES = "eval/baselines.json"
WORKFLOWS = ".github/workflows/"
USAGE = "usage: python scripts/check_changed_paths.py <base> <head>"


def is_code(path: str) -> bool:
    """Say whether a changed path is code: a file whose name ends in .py, in any case.

    Why: Achia's answer of 2026-11-19 defines code as any .py file. The end is compared in
    lower case because Windows imports `x.PY` as the module `x`.

    Contract: `path` as git writes it, with forward slashes. "x.py.txt" and "x.pyc" are not code.
    """
    return path.lower().endswith(".py")


def problems(paths: list[str]) -> list[str]:
    """Return one line per baselines or workflow path changed in a PR that also changes code.

    Why: the judgement of the check, apart from where the paths come from.

    Contract: `paths` as git writes them, relative to the repository root. The lines are
    sorted by path, each path once; empty when no path is code or none is protected.
    """
    if not any(is_code(path) for path in paths):
        return []
    found = []
    for path in sorted(set(paths)):
        if path == BASELINES:
            found.append(f"baselines changed in a code PR: {path}")
        elif path.startswith(WORKFLOWS):
            found.append(f"CI workflow changed in a code PR: {path}")
    return found


def changed(base: str, head: str, cwd: Path) -> list[str]:
    """Return the paths changed between two revisions, as git sorts them.

    Why: a renamed file counts under its old name too, so that a .py file renamed away is
    still a code change; and a path with a line break or a Hebrew name must arrive whole.

    Contract: runs `git diff --name-only --no-renames -z base head` in `cwd`. Raises
    CalledProcessError when git fails, as on an unknown revision.
    """
    done = subprocess.run(  # noqa: S603 fixed argv, no shell
        ["git", "diff", "--name-only", "--no-renames", "-z", base, head],  # noqa: S607 git from PATH, as in CI
        cwd=cwd,
        capture_output=True,
        check=True,
        timeout=60,
    )
    return [path for path in done.stdout.decode("utf-8").split("\0") if path]


def main(argv: list[str]) -> int:
    """Check the paths changed between the two revisions in argv; return the exit code.

    Why: the entry point of the workflow, given its arguments so that a test can call it.

    Contract: argv is [base, head]. Any other length: the usage line on the error stream,
    exit 2. Writes each problem on the error stream.
    """
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    found = problems(changed(argv[0], argv[1], Path.cwd()))
    for line in found:
        print(line, file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
