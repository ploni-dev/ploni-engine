"""Check that a PR keeps the ratchet of PROMOTION.md section 6.

Why: `PROMOTION.md` section 6, the ratchet: test functions and assertions per test file "may
not decrease"; "A decrease fails the build with the exact counter and the delta"; an override
line is accepted "only when the line is present and the PR touches no file under `ploni/`".
`PROCESS.md` section 4.5: a ceiling for `noqa` and `type: ignore` lines in `.ratchet.json`, "a
number that may not rise". Bad PR 6 of the closing test of Phase 0 (section 10) must go red
here. Issue #78. Achia's answers of 2026-11-19: "Count main and the PR (Recommended)", and
"Tests now, rest when real (Recommended)": fixture cases, baseline values, detectors and
system journeys are counted in PRs of their own, once the first of each exists.

Contract: `python -m scripts.check_ratchet <base> <head>`, run from the root of the checkout,
with the PR body in PR_BODY. It runs as a module so that it uses `changed()` of
scripts/check_changed_paths.py. `base` must be an ancestor of `head`, as the first parent of
GitHub's merge of a PR is: the paths are those `head` changed since it left `base`, and the
counts are taken at `base` itself. Each changed test file (tests/**/test_*.py or *_test.py) is
counted at both revisions, from git; a file gone at the head counts zero. The suppressions are
counted at both revisions with `git grep`: at the head they may not pass the ceiling of the
head's `.ratchet.json`, and a rise from base to head must be matched by at least as large a
rise of the ceiling, so it shows in the diff. An override is a line that starts with
`ratchet-override: <path> -<N> <reason>` (backquotes around it allowed); each covers one
decrease of exactly N in that file. Each problem is written on the error stream, one line
each, and the exit code is 1; otherwise nothing is written and the exit code is 0. Wrong
arguments: a usage line, exit 2. A git failure or a test file that does not parse: a
traceback and a non-zero exit.

Known limits:
- Functions are counted, not named, and parametrized cases are not counted: a renamed test
  and a shorter parameter list are not seen; assertions catch part of the second.
- Test functions are counted as pytest collects them only as far as the source shows it:
  `collected()`, `refused()` and `switched_off()` list the shapes where the two differ, none
  of which a test file here uses.
- A test file renamed counts as one file gone and one new: the old one's counters fall to
  zero and need override lines.
- A suppression is a `#`, spaces, an optional `ruff:`, `flake8:` or `mypy:`, then `noqa`,
  `type: ignore` or `ignore-errors`, in any case, anywhere on a line of a tracked .py file, also
  inside a string.
- Run by hand on two branch tips that have both moved, the counts are wrong: pass a base that
  is an ancestor of the head.
- On Windows the error stream is written in the local code page (cp1255 on the laptop), or
  with backslash-u escapes where it has no Hebrew; the exit code is the same. A reader that
  expects UTF-8 sets PYTHONIOENCODING=utf-8, as the module suite does. GitHub's runners
  write UTF-8.
- Fixture cases, baseline values, detectors and system journeys are not counted yet.
"""

import ast
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import NamedTuple

from scripts.check_changed_paths import changed

RATCHET_FILE = ".ratchet.json"
CEILING_KEY = "suppressions_ceiling"
USAGE = "usage: python -m scripts.check_ratchet <base> <head>, with the PR body in PR_BODY"
OVERRIDE_START = "ratchet-override:"
OVERRIDE = re.compile(r"ratchet-override:\s+(\S+)\s+-(\d+)\s+\S.*")
# For git grep -E -i, whose regular expressions have no \s on every platform. Each form is one
# that ruff or mypy honours after the hash sign: noqa, ruff/flake8 with noqa, type with ignore,
# mypy with ignore-errors, in any case. (Written here without the hash, so this line is none.)
SUPPRESSION = "#[[:space:]]*((ruff|flake8|mypy):[[:space:]]*)?(noqa|type:[[:space:]]*ignore|ignore-errors)"
# Well inside a CI job's minutes; each git call here reads the repository once.
GIT_TIMEOUT_SECONDS = 60


class Counts(NamedTuple):
    """The counters of one test file.

    Why: `PROMOTION.md` section 6 names these two per test file.

    Contract: test_functions counts the test functions pytest collects, as far as the
    source shows it (`collected()`, with its Known limits): module-level `test*` functions
    and `test*` methods of `Test*` classes, nested Test* classes too, not of a class pytest
    refuses, and none in a module switched off (`switched_off()`); assertions counts
    `assert` statements anywhere in the file.
    """

    test_functions: int
    assertions: int


COUNTERS = (("test functions", 0), ("assertions", 1))


def is_test_file(path: str) -> bool:
    """Say whether a changed path is a test file the ratchet counts: tests/**/test_*.py or *_test.py.

    Why: only test files hold the counters of section 6; helpers and conftest.py do not.
    The two name forms are the ones pytest collects by default (pyproject.toml sets no other).

    Contract: `path` as git writes it, with forward slashes.
    """
    parts = PurePosixPath(path)
    named = parts.name.startswith("test_") or parts.stem.endswith("_test")
    return parts.parts[:1] == ("tests",) and named and parts.suffix == ".py"


def count(source: str) -> Counts:
    """Return the test functions and assertions of a test file's source.

    Why: the two counters of section 6, read from the code, not from a run.

    Contract: test functions 0 when the module is switched off (`switched_off()`), else
    `collected()`. Raises SyntaxError when the source does not parse.
    """
    tree = ast.parse(source)
    functions = 0 if switched_off(tree.body) else collected(tree.body)
    return Counts(functions, sum(isinstance(node, ast.Assert) for node in ast.walk(tree)))


def collected(body: list[ast.stmt]) -> int:
    """Return the number of test functions pytest collects from a module's or a Test class's body.

    Why: Achia's answer of 2026-11-20, "Count what pytest runs (Recommended)": a test swapped
    for a function pytest never runs must show as a drop.

    Contract: counts `test*` functions (sync or async) standing directly in `body`, and,
    recursively, those of each `Test*` class standing directly in it that pytest does not
    refuse (`refused()`). A function nested in a function, a method of a class whose name
    does not start with Test, or a class inside a function is not counted.

    Known limits: read from the source alone, so it differs from pytest's own collection in
    shapes no test file here uses (measured in the review of this change): tests under a
    module-level `if` or `try`, methods a Test* class inherits, a test function imported
    into the file, a `unittest.TestCase` subclass not named Test*, and a lambda bound to a
    test* name are not counted; a `@pytest.fixture` named test*, and a name defined twice
    (ruff F811 refuses that), are counted.
    """
    found = 0
    for node in body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test"):
            found += 1
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test") and not refused(node):
            found += collected(node.body)
    return found


def refused(test_class: ast.ClassDef) -> bool:
    """Say whether pytest refuses to collect a Test* class.

    Why: a test class switched off this way runs none of its tests while the suite stays
    green, so its tests must not count.

    Contract: True when the class body defines `__init__` or `__new__` (pytest warns), or
    sets `__test__` to a false value (pytest is silent), anywhere in the body.

    Known limits: read from the class's own body only (measured in the review of this
    change): an `__init__` inherited from a base class, `__init__` bound to another
    function, an `__init__` under an `if`, an `async def __init__`, an abstract Test* class, or a function given
    `.__test__ = False` after it are still counted; a class not named Test* with
    `__test__ = True` is not.
    """
    constructor = any(isinstance(node, ast.FunctionDef) and node.name in ("__init__", "__new__") for node in test_class.body)
    return constructor or switched_off(test_class.body)


def switched_off(body: list[ast.stmt]) -> bool:
    """Say whether a module's or a class's body sets `__test__` to a false value.

    Why: pytest reads `__test__` on a module and on a class by its truth: `False`, `None`
    or `0` there switches off every test inside, silently.

    Contract: reads plain and annotated assignments of a constant to the name `__test__`,
    chained ones too, standing directly in `body`.

    Known limits: read from the body alone (measured in the review of this change): a
    `__test__` set from another name (`OFF = False` then `__test__ = OFF`) or under an `if`
    is not seen, so its tests still count; a false value set and then set true again counts
    as switched off, a false drop, the safe side.
    """
    for node in body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        value = getattr(node, "value", None)
        named = any(isinstance(target, ast.Name) and target.id == "__test__" for target in targets)
        if named and isinstance(value, ast.Constant) and not value.value:
            return True
    return False


def overrides(body: str) -> tuple[list[tuple[str, int]], list[str]]:
    """Parse the override lines of a PR body.

    Why: an override must be exact; a line that starts like one and is not read fails, so a
    typo never passes as an override nor goes unseen.

    Contract: returns the lines read, as (path, N), and the lines that start like one and
    cannot be read. A line counts when, after spaces and backquotes, it starts with the token;
    a quoted line ("> ...") does not. The reason may be any text, Hebrew too.
    """
    read: list[tuple[str, int]] = []
    unread: list[str] = []
    for raw in body.splitlines():
        line = raw.strip().strip("`").strip()
        if not line.startswith(OVERRIDE_START):
            continue
        match = OVERRIDE.fullmatch(line)
        if match:
            read.append((match.group(1), int(match.group(2))))
        else:
            unread.append(raw.strip())
    return read, unread


def decreases(before: dict[str, Counts], after: dict[str, Counts]) -> list[tuple[str, str, int, int]]:
    """Return each counter that fell, as (path, counter, before, after), by path.

    Why: section 6 names the exact counter and the delta.

    Contract: a path in `before` and not in `after` counts zero after; a path only in
    `after` is new and has nothing to fall from.
    """
    found = []
    for path in sorted(before):
        old, new = before[path], after.get(path, Counts(0, 0))
        found += [(path, name, old[index], new[index]) for name, index in COUNTERS if new[index] < old[index]]
    return found


def ceiling(text: str) -> int | None:
    """Return the suppressions ceiling of a .ratchet.json text, or None when it has no whole number.

    Why: the ceiling of PROCESS.md section 4.5, the one number Achia's answer keeps in the file.

    Contract: None for text that is not a JSON object, a missing key, or a value that is not
    an integer (a bool is not one).
    """
    try:
        value = json.loads(text).get(CEILING_KEY)
    except (ValueError, AttributeError):
        return None
    return value if type(value) is int else None


def ceiling_problems(before: int, after: int, base_text: str, head_text: str) -> list[str]:
    """Return the problem of the suppressions against the ceiling, if any.

    Why: a suppression is allowed only when the PR raises the ceiling where the diff shows it
    (Achia's answer: "which a PR raises in that file when it adds one, so the rise shows").

    Contract: `before` and `after` are the counts at base and head, the texts the two
    .ratchet.json files. One line when the head has no whole-number ceiling, when `after` is
    over it, or when the count rose by more than the ceiling did. A ceiling lowered while the
    count stays or falls passes. A base with no ceiling (the PR that sets it) counts as a
    ceiling of 0, which no rise under the head's ceiling passes.
    """
    limit = ceiling(head_text)
    if limit is None:
        return [f"{RATCHET_FILE} has no whole-number {CEILING_KEY}"]
    if after > limit:
        return [f"suppressions {after}, ceiling {limit} in {RATCHET_FILE}: raise {CEILING_KEY} in the PR that adds one"]
    old = ceiling(base_text) or 0
    if after > before and after - before > limit - old:
        return [
            f"suppressions rose by {after - before} ({before} -> {after}), {CEILING_KEY} by {limit - old} "
            f"({old} -> {limit}): raise it in {RATCHET_FILE} by the rise"
        ]
    return []


def problems(body: str, paths: list[str], before: dict[str, Counts], after: dict[str, Counts]) -> list[str]:
    """Return one line per problem of the counters: unread overrides, a refusal, uncovered decreases.

    Why: the judgement of the check, apart from where the body, the counts and the files come from.

    Contract: overrides are refused, and listed once, when any path is under ploni/. Each
    decrease is covered by one override line of its path and delta; an override line that
    covers none is a problem too.
    """
    read, unread = overrides(body)
    found = [f"ratchet-override line not read: {line}" for line in unread]
    if read and any(PurePosixPath(path).parts[:1] == ("ploni",) for path in paths):
        found.append("ratchet-override refused: the PR changes files under ploni/")
        read = []
    uncovered = []
    for path, name, old, new in decreases(before, after):
        if (path, old - new) in read:
            read.remove((path, old - new))
        else:
            uncovered.append(f"{path}: {name} {old} -> {new} (-{old - new})")
    found += [f"ratchet-override names no decrease: {path} -{delta}" for path, delta in read]
    return found + uncovered


def shown(revision: str, path: str) -> str:
    """Return a file as it stands at a revision, or "" when it is not there.

    Why: both sides are counted from git, so the checkout's state does not matter; a file
    that is not there counts zero, as an empty one does.

    Contract: the revision must exist (main checks it through changed() first). Raises
    CalledProcessError when git fails on a file that is there.
    """
    there = subprocess.run(  # noqa: S603 fixed argv, no shell
        ["git", "cat-file", "-e", f"{revision}:{path}"],  # noqa: S607 git from PATH, as in CI
        capture_output=True,
        check=False,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    if there.returncode != 0:
        return ""
    done = subprocess.run(  # noqa: S603 fixed argv, no shell
        ["git", "show", f"{revision}:{path}"],  # noqa: S607 git from PATH, as in CI
        stdout=subprocess.PIPE,
        check=True,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    # utf-8-sig: a file saved with a byte order mark is still valid Python to pytest.
    return done.stdout.decode("utf-8-sig")


def suppressions(revision: str) -> int:
    """Return the number of noqa and type-ignore lines in the tracked .py files of a revision.

    Why: the count the ceiling of PROCESS.md section 4.5 bounds.

    Contract: runs `git grep -c` on the revision; no match is zero. Raises CalledProcessError
    when git fails.
    """
    done = subprocess.run(  # noqa: S603 fixed argv, no shell
        ["git", "grep", "-c", "-i", "-E", SUPPRESSION, revision, "--", "*.py"],  # noqa: S607 git from PATH, as in CI
        stdout=subprocess.PIPE,
        check=False,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    # git grep exits 1 when nothing matches; any other code but 0 is an error.
    if done.returncode not in (0, 1):
        raise subprocess.CalledProcessError(done.returncode, done.args)
    return sum(int(line.rsplit(":", 1)[1]) for line in done.stdout.decode("utf-8").splitlines())


def main(argv: list[str], environ: Mapping[str, str]) -> int:
    """Check the PR between the revisions in argv against the ratchet; return the exit code.

    Why: the entry point of the workflow, given its arguments and environment so that a test
    can call it.

    Contract: argv is [base, head]; any other length writes the usage line, exit 2. A missing
    PR_BODY is an empty body. Writes each problem on the error stream.
    """
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    base, head = argv
    paths = changed(base, head, Path.cwd())
    tests = [path for path in paths if is_test_file(path)]
    before = {path: count(shown(base, path)) for path in tests}
    after = {path: count(shown(head, path)) for path in tests}
    found = problems(environ.get("PR_BODY", ""), paths, before, after)
    found += ceiling_problems(suppressions(base), suppressions(head), shown(base, RATCHET_FILE), shown(head, RATCHET_FILE))
    for line in found:
        print(line, file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ))
