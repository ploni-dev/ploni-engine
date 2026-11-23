"""Check that a PR commits the failing tests of each module it changes before the module, on their own.

Why: `PROMOTION.md` section 5.2, the row "Test written before implementation": "the first
commit touching `tests/.../test_X.py` must precede the first commit touching the module `X`
implements ... The failing tests are a commit of their own, with no implementation in it. This
covers every PR that changes code under `ploni/`, `eval/` or `scripts/`." `CLAUDE.md`, Tests:
"Write the failing test first, in a commit of its own before the implementation." Issue #175,
one of the four robots Achia chose on 2026-11-20 ("Yes, all four (Recommended)").

Contract: `python -m scripts.check_commit_order <base> <head>`, run from the root of the
checkout. It runs as a module so that it uses `is_code()` of scripts/check_changed_paths.py.
The commits of `base..head` are read from git oldest first, merge commits left out, each with
the paths it touched and how (added, modified, deleted, type changed; a rename is a deletion
and an addition). A module is a .py file under ploni/, eval/ or scripts/. A test file for
module X is a file under tests/, at any depth, named `test_` plus any tail of X's path joined
by `_`, plus `.py`: for ploni/safety/atomic.py, test_atomic.py, test_safety_atomic.py or
test_ploni_safety_atomic.py. For each module X the PR touches and has not deleted at its last
touch, one line on the error stream when no commit before X's first touches a test file for X,
and one line for each commit before X's first that touches a test file for X and any module
(the row: "with no implementation in it"). A later commit may change X and its tests together.
A merge is left out when each of its parents after the first is held by `base` (a merge of
main, which carries main's changes, not the branch's); a merge that brings in a commit `base`
does not hold, as a merge of another open branch does, gets one line per such parent. Any line
written: exit code 1. Otherwise nothing is written and the exit code is 0. Wrong arguments: a
usage line, exit 2. A revision git does not know: git's error, a traceback, a non-zero exit.

Known limits:
- No module is exempt, though six have no test file named for them today (issue #175, measured
  on 7aca103): ploni/__init__.py, ploni/safety/__init__.py, ploni/__main__.py (tested by
  tests/t1_unit/test_cli.py, which does not count), ploni/errors.py (its suite is
  tests/t4_integration/test_types_errors.py, which does not count),
  scripts/download_e1_model.py and scripts/download_e5_models.py. A PR that changes one of
  them must first add or touch a test file named by the rule. This narrows Claude only: the
  row names no exemption.
- The check sees paths, not content: a test commit that changes a comment counts as the
  failing test, and nothing shows that the test failed.
- A tail names a test file for every module that ends in it: test_atomic.py counts for any
  atomic.py, and test___init__.py for every __init__.py.
- A merge of main is left out whole, also what it resolved by hand: a module written in the
  resolution passes with no test (this does less than the row).
- A test file deleted counts as touched: a commit that only deletes X's test file, before X,
  satisfies the first rule (this does less than the row).
- A module deleted at its last touch needs no test (the brief). A test commit that deletes a
  module is refused: a deletion is a change of code (this only narrows).
- A test commit is judged once for each module it holds tests of, and only before that
  module's first commit: a commit of tests and code that comes after the module's first commit
  is not refused.
- Run on GitHub's merge of a PR, pass HEAD^1 HEAD^2, the PR's own head: HEAD^1 HEAD takes in
  that merge, whose second parent main does not hold, and is refused. The checkout must hold
  every commit of the PR, not a depth of 2.
- On Windows the error stream is written in the local code page (cp1255 on the laptop), or with
  backslash-u escapes where it has no Hebrew; the exit code is the same. A reader that expects
  UTF-8 sets PYTHONIOENCODING=utf-8, as the module suite does. GitHub's runners write UTF-8.
"""

import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import NamedTuple

from scripts.check_changed_paths import is_code

USAGE = "usage: python -m scripts.check_commit_order <base> <head>"
# PROMOTION.md section 5.2: the folders whose code the row covers.
MODULE_FOLDERS = ("ploni", "eval", "scripts")
TESTS = "tests"
DELETED = "D"
# 12: unique across this repository and short enough to read (git abbreviates to 7 here).
SHORT_HASH = 12
# Well inside a CI job's minutes; each git call here reads one commit or one range.
GIT_TIMEOUT_SECONDS = 60
GIT = "git"


class Commit(NamedTuple):
    """One commit of the PR, with what it touched.

    Why: the check judges the order of commits, so each keeps its paths apart.

    Contract: sha is the commit's hash; changes maps each path it touched, as git writes it with
    forward slashes, to git's status letter (A, M, D or T).
    """

    sha: str
    changes: dict[str, str]


def is_module(path: str) -> bool:
    """Say whether a path is a module the row covers: a .py file under ploni/, eval/ or scripts/.

    Why: the row covers code under those three folders only; tests/ and experiments/ are not.

    Contract: `path` as git writes it. The end is compared in any case, as `is_code()` does.
    """
    return PurePosixPath(path).parts[0] in MODULE_FOLDERS and is_code(path)


def is_test_for(path: str, module: str) -> bool:
    """Say whether a path is a test file for a module: tests/**/test_<a tail of its path>.py.

    Why: the row pairs `tests/.../test_X.py` with module X; any tail of X's path joined by `_`
    lets test_safety_atomic.py and test_atomic.py both name ploni/safety/atomic.py.

    Contract: both as git writes them. The name is compared exactly, in its case.
    """
    test = PurePosixPath(path)
    parts = PurePosixPath(module).with_suffix("").parts
    names = {f"test_{'_'.join(parts[start:])}.py" for start in range(len(parts))}
    return test.parts[0] == TESTS and test.name in names


def problems(commits: list[Commit]) -> list[str]:
    """Return one line per module whose failing tests do not come first, on their own.

    Why: the judgement of the check, apart from where the commits come from.

    Contract: `commits` oldest first, merges left out. For each module touched and not
    deleted at its last touch, by path: a line when no commit before its first touches a test
    file for it, then the line of `mixed()` for each commit before its first that has one.
    """
    modules = sorted({path for commit in commits for path in commit.changes if is_module(path)})
    found = []
    for module in modules:
        touching = [index for index, commit in enumerate(commits) if module in commit.changes]
        if commits[touching[-1]].changes[module] == DELETED:
            continue
        first = touching[0]
        if not any(is_test_for(path, module) for commit in commits[:first] for path in commit.changes):
            found.append(f"{module}: no test file for it is touched before its first commit, {commits[first].sha[:SHORT_HASH]}")
        found += [line for commit in commits[:first] if (line := mixed(commit, module))]
    return found


def mixed(commit: Commit, module: str) -> str:
    """Return the line of a test commit of a module that also changes code, or "".

    Why: the row's second sentence: "The failing tests are a commit of their own, with no
    implementation in it."

    Contract: "" when the commit touches no test file for `module`, or no module at all;
    otherwise the line names each module the commit touches, sorted. The caller gives only
    commits before the module's first.
    """
    code = sorted(path for path in commit.changes if is_module(path))
    if not code or not any(is_test_for(path, module) for path in commit.changes):
        return ""
    return (
        f"{commit.sha[:SHORT_HASH]}: a test commit of {module} also changes {', '.join(code)}; "
        "the failing tests are a commit of their own, with no implementation in it"
    )


def git(arguments: list[str], cwd: Path) -> str:
    """Return what one git command wrote on its output stream.

    Why: every read of the history goes through one place, with a time limit.

    Contract: runs git with `arguments` in `cwd`; git's error stream is passed through. The
    output is decoded as UTF-8, which -z output is. Raises CalledProcessError when git fails.
    """
    done = subprocess.run([GIT, *arguments], cwd=cwd, stdout=subprocess.PIPE, check=True, timeout=GIT_TIMEOUT_SECONDS)  # noqa: S603 fixed argv, no shell
    return done.stdout.decode("utf-8")


def commits(base: str, head: str, cwd: Path) -> list[Commit]:
    """Return the commits of base..head oldest first, merges left out, with what each touched.

    Why: the row inspects the commit order within the PR; a merge of main is not the branch's.

    Contract: `git rev-list --reverse --topo-order --no-merges base..head`, then for each
    `git diff-tree -r --no-renames -z --name-status`, so a path with a line break or a Hebrew
    name arrives whole. Raises CalledProcessError when git fails, as on an unknown revision.
    """
    listed = git(["rev-list", "--reverse", "--topo-order", "--no-merges", f"{base}..{head}"], cwd).split()
    found = []
    for sha in listed:
        fields = git(["diff-tree", "-r", "--no-commit-id", "--no-renames", "-z", "--name-status", sha], cwd).split("\0")[:-1]
        found.append(Commit(sha, dict(zip(fields[1::2], fields[0::2], strict=True))))
    return found


def merge_problems(base: str, head: str, cwd: Path) -> list[str]:
    """Return one line per parent a merge of base..head brings in that base does not hold.

    Why: a merge of main is left out, as it carries main's changes; a merge of another open
    branch would bring that branch's code in with no commit of the PR to judge it by.

    Contract: each merge of `git rev-list --merges --parents base..head`, oldest first; each
    parent after its first is held by base when `git rev-list base..<parent>` is empty. Raises
    CalledProcessError when git fails.
    """
    found = []
    for line in git(["rev-list", "--reverse", "--topo-order", "--merges", "--parents", f"{base}..{head}"], cwd).splitlines():
        merge, _first, *others = line.split()
        found += [
            f"{merge[:SHORT_HASH]}: merges {parent[:SHORT_HASH]}, which {base} does not hold; merge only main into the branch"
            for parent in others
            if git(["rev-list", f"{base}..{parent}"], cwd).strip()
        ]
    return found


def main(argv: list[str]) -> int:
    """Check the commit order between the two revisions in argv; return the exit code.

    Why: the entry point of a workflow, given its arguments so that a test can call it.

    Contract: argv is [base, head]. Any other length: the usage line on the error stream,
    exit 2. Writes each problem on the error stream.
    """
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    found = problems(commits(argv[0], argv[1], Path.cwd())) + merge_problems(argv[0], argv[1], Path.cwd())
    for line in found:
        print(line, file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
