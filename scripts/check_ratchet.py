"""Check that a PR lowers no test counter without an override, and adds no unbudgeted suppression.

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
scripts/check_changed_paths.py. Each changed test file (tests/**/test_*.py) is counted at both
revisions, from git; a file gone at the head counts zero. The suppressions are counted at the
head with `git grep` and compared with the ceiling of the head's `.ratchet.json`, so a PR that
adds one raises the ceiling in the same diff. An override is a line that starts with
`ratchet-override: <path> -<N> <reason>` (backquotes around it allowed); each covers one
decrease of exactly N in that file. Each problem is written on the error stream, one line
each, and the exit code is 1; otherwise nothing is written and the exit code is 0. Wrong
arguments: a usage line, exit 2. A git failure or a test file that does not parse: a
traceback and a non-zero exit.

Known limits:
- Functions are counted, not named, and parametrized cases are not counted: a renamed test
  and a shorter parameter list are not seen; assertions catch part of the second.
- A test file renamed counts as one file gone and one new: the old one's counters fall to
  zero and need override lines.
- A suppression is a `#`, spaces, then `noqa` or `type: ignore`, anywhere on a line of a
  tracked .py file, also inside a string.
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
# For git grep -E, whose regular expressions have no \s on every platform.
SUPPRESSION = "#[[:space:]]*(noqa|type:[[:space:]]*ignore)"
# Well inside a CI job's minutes; each git call here reads the repository once.
GIT_TIMEOUT_SECONDS = 60


class Counts(NamedTuple):
    """The counters of one test file.

    Why: `PROMOTION.md` section 6 names these two per test file.

    Contract: test_functions counts functions whose name starts with "test", as pytest
    collects them; assertions counts `assert` statements anywhere in the file.
    """

    test_functions: int
    assertions: int


COUNTERS = (("test functions", 0), ("assertions", 1))


def is_test_file(path: str) -> bool:
    """Say whether a changed path is a test file the ratchet counts: tests/**/test_*.py.

    Why: only test files hold the counters of section 6; helpers and conftest.py do not.

    Contract: `path` as git writes it, with forward slashes.
    """
    parts = PurePosixPath(path)
    return parts.parts[:1] == ("tests",) and parts.name.startswith("test_") and parts.suffix == ".py"


def count(source: str) -> Counts:
    """Return the test functions and assertions of a test file's source.

    Why: the two counters of section 6, read from the code, not from a run.

    Contract: raises SyntaxError when the source does not parse.
    """
    nodes = list(ast.walk(ast.parse(source)))
    functions = sum(isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test") for node in nodes)
    return Counts(functions, sum(isinstance(node, ast.Assert) for node in nodes))


def overrides(body: str) -> tuple[list[tuple[str, int]], list[str]]:
    """Return the override lines of a PR body as (path, N), and the lines that could not be read.

    Why: an override must be exact; a line that starts like one and is not read fails, so a
    typo never passes as an override nor goes unseen.

    Contract: a line counts when, after spaces and backquotes, it starts with the token; a
    quoted line ("> ...") does not. The reason may be any text, Hebrew too.
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


def ceiling_problems(suppressions: int, ratchet_text: str) -> list[str]:
    """Return the problem of the suppressions against the ceiling, if any.

    Why: a suppression is allowed only when the PR raises the ceiling where the diff shows it.

    Contract: one line when there is no whole-number ceiling or the count is over it.
    """
    limit = ceiling(ratchet_text)
    if limit is None:
        return [f"{RATCHET_FILE} has no whole-number {CEILING_KEY}"]
    if suppressions > limit:
        return [f"suppressions {suppressions}, ceiling {limit} in {RATCHET_FILE}: raise {CEILING_KEY} in the PR that adds one"]
    return []


def problems(
    body: str, paths: list[str], before: dict[str, Counts], after: dict[str, Counts], suppressions: int, ratchet_text: str
) -> list[str]:
    """Return one line per problem: unread overrides, a refusal, uncovered decreases, the ceiling.

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
    return found + uncovered + ceiling_problems(suppressions, ratchet_text)


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
    return done.stdout.decode("utf-8")


def suppressions(revision: str) -> int:
    """Return the number of noqa and type-ignore lines in the tracked .py files of a revision.

    Why: the count the ceiling of PROCESS.md section 4.5 bounds.

    Contract: runs `git grep -c` on the revision; no match is zero. Raises CalledProcessError
    when git fails.
    """
    done = subprocess.run(  # noqa: S603 fixed argv, no shell
        ["git", "grep", "-c", "-E", SUPPRESSION, revision, "--", "*.py"],  # noqa: S607 git from PATH, as in CI
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
    found = problems(environ.get("PR_BODY", ""), paths, before, after, suppressions(head), shown(head, RATCHET_FILE))
    for line in found:
        print(line, file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ))
