"""The check before a commit: the quick checks of PROCESS.md section 5.6 on what is staged.

Why: `PROCESS.md` section 5.6: "ruff, mypy on changed files, secret scan, no-network AST scan,
docstring presence. Fast only." A problem caught before the commit costs no CI run and no
review round, and a secret caught here never reaches GitHub (the scan in CI runs after the
push). Achia decided on 2026-11-20 to build it, of the option "4. Check before commit": "A small
script on the laptop runs the quick checks before each commit. No new tool." The model check
(`tests/t0_contract/test_third_party.py`) runs here too: the question Achia answered with
"Laptop run is enough (Recommended)" on 2026-11-20 said it does.

Contract: `.githooks/pre-commit` runs `python -m scripts.pre_commit` in the repository root;
git runs that hook before each commit once `git config core.hooksPath .githooks` is set (once
per clone). The staged .py files are given to ruff, the staged ones under `ploni/` to mypy (it
checks `ploni/` only, `PROCESS.md` section 4.5), and the four check tests of CHECK_TESTS run in
one pytest run. Each step's name is printed before it runs, every step runs, and the exit code
is 1 when any failed (git then makes no commit), else 0.

Known limits:
- ruff and mypy read the staged files as they are in the folder, not as staged: a file staged
  and then edited again is checked as edited. The scans read every tracked file, as they do in
  the fast suite.
- The hook stops a commit only where it is turned on: a clone without `core.hooksPath` set runs
  none of it. `git commit --no-verify` skips it; the merge gate's hook refuses that flag to
  Claude (`scripts/guard.py`), and the fast suite in CI runs the same checks after the push.
- The tests and layers it does not run (unit, property, layering) run in the fast suite.
"""

import shutil
import subprocess
import sys
from pathlib import Path

# PROCESS.md section 5.6, as tests: the secret scan, the no-network scan, the docstring check;
# and the model check (Achia, 2026-11-20).
CHECK_TESTS = (
    "tests/t8_privacy/test_secrets.py",
    "tests/t8_privacy/test_imports.py",
    "tests/t0_contract/test_docstrings.py",
    "tests/t0_contract/test_third_party.py",
)
PRODUCT = "ploni/"
# git from PATH, as a full path; the seconds a step may take (the scans take about five).
GIT = shutil.which("git") or "git"
STEP_TIMEOUT_SECONDS = 300


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[bytes]:
    """Return how one program ended, with its output captured only when asked for by `_output`."""
    return subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE if command[0] == GIT else None, check=False, timeout=STEP_TIMEOUT_SECONDS)  # noqa: S603 fixed argv, no shell


def _output(command: list[str], cwd: Path) -> bytes:
    """Return what a git command printed, or raise CalledProcessError when it fails."""
    done = _run(command, cwd)
    done.check_returncode()
    return done.stdout


def _status(command: list[str], cwd: Path) -> int:
    """Return the exit code of one check, its output passed through."""
    return _run(command, cwd).returncode


def steps(paths: list[str]) -> list[tuple[str, list[str]]]:
    """Return the checks to run for the staged paths, as (name, command), in order.

    Why: what runs, apart from running it, so that a test can read it.

    Contract: `paths` as git writes them. ruff gets the .py files (any case of the ending),
    mypy those under ploni/; the scans always run. Each command starts the interpreter that
    runs this script, so the tools come from the same environment.
    """
    python = [sys.executable, "-m"]
    code = [path for path in paths if path.lower().endswith(".py")]
    product = [path for path in code if path.startswith(PRODUCT)]
    found = []
    if code:
        found.append(("ruff", [*python, "ruff", "check", *code]))
    if product:
        found.append(("mypy", [*python, "mypy", *product]))
    found.append(("scans", [*python, "pytest", "-q", "-p", "no:cacheprovider", *CHECK_TESTS]))
    return found


def staged(cwd: Path) -> list[str]:
    """Return the paths staged for the next commit, added, copied, modified or renamed.

    Why: the commit is made of them; a deleted file has nothing to check.

    Contract: runs `git diff --cached --name-only --diff-filter=ACMR -z` in `cwd`. Raises
    CalledProcessError when git fails.
    """
    listed = _output([GIT, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z"], cwd)
    return [path for path in listed.decode("utf-8").split("\0") if path]


def main(cwd: Path) -> int:
    """Run the checks for what is staged in cwd; return the exit code.

    Why: the entry point of the hook, given its folder so that a test can call it.

    Contract: prints "== <name>" before each step; every step runs; ends with a line naming the
    failed steps when any failed, and returns 1; else returns 0.
    """
    failed = []
    for name, command in steps(staged(cwd)):
        print(f"== {name}", flush=True)
        if _status(command, cwd) != 0:
            failed.append(name)
    if failed:
        print(f"check before commit: FAILED: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(Path.cwd()))
