"""Check that each waiver a PR body cites exists, is in force, and covers what the PR changes.

Why: `PROMOTION.md` section 8.4: "A PR relying on a waiver carries `waiver: WAIVER-003` in its
body. CI asserts that the ID exists in `docs/WAIVERS.md`, that it has not expired, and that the
PR's changed paths fall inside the waiver's scope. An invented or expired ID fails the build."
Bad PR 8 of the closing test of Phase 0 (section 10) must go red here. Issue #78. Expiry is
read as Achia's answer of 2026-11-19 said: "A waiver whose expiry is a date has expired after
that date; one whose expiry is a phase has expired once that phase's close is dated in
docs/STATUS.md. A PR that cites no waiver passes."

Contract: `python -m scripts.check_waiver <base> <head>`, run from the root of the checkout,
with the PR body in the environment variable PR_BODY. It runs as a module so that it uses
`changed()` of scripts/check_changed_paths.py for the PR's changed paths. `docs/WAIVERS.md`
and `docs/STATUS.md` are read from `base` with `git show`, so a PR cannot add the waiver it
cites: a waiver is on the base before a PR may rely on it. Each problem is written on the
error stream, one line each, and the exit code is 1; otherwise nothing is written and the
exit code is 0. A body that cites nothing exits 0 without calling git. Wrong arguments: a
usage line, exit 2. A git failure: git's error, a traceback, a non-zero exit.

Known limits:
- A citation counts only at the start of a line, as Achia answered on 2026-11-19 ("Only
  own-line citations count (Recommended)"), also as a list item or in emphasis: a quote in a
  quoted block or mid-sentence is not read, and neither is a citation written mid-sentence or
  with its ID on the next line; the reviewer reads the body.
- Achia's own PR that adds a waiver to docs/WAIVERS.md cannot cite that waiver: the base does
  not have it yet.
- A green run is not run again when a cited waiver expires while the PR is open; the merge
  gate reads that old run. A push or an edit of the body runs it again.
- Today is the date at UTC+3 (`today()`), whatever the machine's own zone.
- A waiver is read only as `docs/WAIVERS.md` writes one: the ID alone on a line under
  `## Active` or `## Expired`, then `key: value` lines up to a blank or other line.
- A scope entry is a path, a folder ending in "/", or a pattern where `*` stays inside one
  folder and `**` crosses folders. How wide a scope is stays Achia's to write.
"""

import os
import re
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

from scripts.check_changed_paths import changed

WAIVERS_FILE = "docs/WAIVERS.md"
STATUS_FILE = "docs/STATUS.md"
USAGE = "usage: python -m scripts.check_waiver <base> <head>, with the PR body in PR_BODY"
# A citation starts a line (Achia, 2026-11-19: "Only own-line citations count"), also as a list
# item, the stricter side. Backquotes (PROMOTION.md 8.4 writes it in them), emphasis marks and
# direction marks, which a Hebrew body may hold and which cannot be seen, are skipped around
# the token and are never part of the ID.
MARKS = "‎‏؜"
SKIPPED = rf"[ \t`*_{MARKS}]*"
LIST_ITEM = r"(?:(?:[-*+]|\d+[.)])[ \t]+)?"
CITATION = re.compile(
    rf"^[ \t{MARKS}]*{LIST_ITEM}{SKIPPED}waiver:{SKIPPED}([^\s`*_{MARKS}]+)", re.IGNORECASE | re.MULTILINE
)
# The date of Israel's summer offset, UTC+3: a date waiver never lives past Israel's midnight;
# in winter (UTC+2) it ends an hour early, the stricter side. No tz database is needed.
ISRAEL_SUMMER = timezone(timedelta(hours=3))
# Well inside the job's 2-minute timeout; git show of one file takes well under a second.
GIT_TIMEOUT_SECONDS = 60
WAIVER_ID = re.compile(r"WAIVER-\d+")
FIELD = re.compile(r"([a-z]+):\s*(.*)")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
PHASE = re.compile(r"(?:end of\s+)?(?:phase\s+)?(\d+)", re.IGNORECASE)
SECTIONS = ("Active", "Expired")
# docs/STATUS.md, "## Phases": the first cell names the phase, the fourth is the date of its close.
DATE_CELL = 3

Waiver = dict[str, str]


def cited(body: str) -> list[str]:
    """Return what each citation at the start of a line names, each once, sorted.

    Why: one citation rule for the check and for the early exit when nothing is cited.

    Contract: the token is matched in any case, after nothing but spaces, tabs, backquotes and
    direction marks on its line; what follows, up to the next space, backquote or mark, is
    returned whole, an ID or not.
    """
    return sorted(set(CITATION.findall(body)))


def waivers(text: str) -> dict[str, Waiver]:
    """Return the waivers of a docs/WAIVERS.md text by ID: their fields and their section.

    Why: the file is Achia's own, written by hand; only entries under `## Active` and
    `## Expired` are waivers, not the format example above them.

    Contract: each value is a dict of the entry's `key: value` lines, the first of each key,
    plus "section", "Active" or "Expired". An ID listed under Expired anywhere is Expired,
    the stricter reading. A code fence around an entry is read through.
    """
    found: dict[str, Waiver] = {}
    section = ""
    current: Waiver | None = None
    for line in (raw.strip() for raw in text.splitlines()):
        field = FIELD.fullmatch(line)
        if line.startswith("## "):
            section, current = line[3:].strip(), None
        elif section in SECTIONS and WAIVER_ID.fullmatch(line):
            before = found.get(line, {}).get("section")
            current = found[line] = {"section": "Expired" if before == "Expired" else section}
        elif current is not None and field:
            current.setdefault(field.group(1), field.group(2).strip())
        else:
            current = None
    return found


def closed_phases(status: str) -> set[int]:
    """Return the numbers of the phases whose close is dated in the Phases table of docs/STATUS.md.

    Why: Achia's answer reads a phase expiry against that table: a phase has closed once its
    row has a date.

    Contract: only rows under `## Phases`, up to the next `## ` heading, are read; a row whose
    first cell starts with a number and whose fourth cell is not empty is closed.
    """
    closed = set()
    inside = False
    for line in (raw.strip() for raw in status.splitlines()):
        if line.startswith("## "):
            inside = line == "## Phases"
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        number = re.match(r"\d+", cells[0])
        if inside and line.startswith("|") and number and len(cells) > DATE_CELL and cells[DATE_CELL]:
            closed.add(int(number.group()))
    return closed


def expired(expires: str, today: date, closed: set[int]) -> bool:
    """Say whether a waiver's expiry has passed.

    Why: the two kinds of expiry of docs/WAIVERS.md, "a phase number or a date", read as
    Achia's answer of 2026-11-19 says.

    Contract: a date YYYY-MM-DD has passed when today is after it; "Phase 3", "end of Phase 3"
    or "3" has passed when 3 is in `closed`. Raises ValueError, naming the expiry, when it is
    neither, or a date that does not exist.
    """
    text = expires.strip()
    if DATE.fullmatch(text):
        try:
            return today > date.fromisoformat(text)
        except ValueError as error:
            raise ValueError(f"no readable expiry: {expires}") from error
    phase = PHASE.fullmatch(text)
    if phase is None:
        raise ValueError(f"no readable expiry: {expires}")
    return int(phase.group(1)) in closed


def scope_entries(scope: str) -> list[str]:
    """Return the entries of a scope line: split on commas, spaces and backquotes taken off.

    Why: a scope may name several files or folders, written by hand.

    Contract: empty entries are dropped.
    """
    return [entry for entry in (part.strip().strip("`").strip() for part in scope.split(",")) if entry]


def covers(scope: str, path: str) -> bool:
    """Say whether a changed path falls inside a waiver's scope.

    Why: `PROMOTION.md` section 8.4: the PR's changed paths fall inside the waiver's scope.

    Contract: an entry ending in "/" covers everything below it; any other entry covers the
    paths that match it whole, where `*` stays inside one folder and `**` crosses folders.
    """
    return any(
        path.startswith(entry) if entry.endswith("/") else PurePosixPath(path).full_match(entry)
        for entry in scope_entries(scope)
    )


def judge(waiver_id: str, entry: Waiver | None, paths: list[str], today: date, closed: set[int]) -> list[str]:
    """Return the problems of one cited waiver: unknown, expired, unreadable, or not covering.

    Why: each citation is judged on its own, and stops at its first kind of problem.

    Contract: `entry` is the waiver as `waivers()` gives it, or None. Paths outside the scope
    are named one line each, sorted.
    """
    if not WAIVER_ID.fullmatch(waiver_id):
        return [f"waiver: {waiver_id} is not a waiver ID"]
    if entry is None:
        return [f"{waiver_id} is not in {WAIVERS_FILE}"]
    if entry["section"] == "Expired":
        return [f"{waiver_id} is under Expired in {WAIVERS_FILE}"]
    expires = entry.get("expires", "")
    try:
        if expired(expires, today, closed):
            return [f"{waiver_id} has expired: {expires}"]
    except ValueError:
        return [f"{waiver_id} has no readable expiry: {expires}"]
    scope = entry.get("scope", "")
    if not scope_entries(scope):
        return [f"{waiver_id} has no scope"]
    return [f"{waiver_id} does not cover {path}" for path in sorted(set(paths)) if not covers(scope, path)]


def problems(body: str, paths: list[str], waivers_text: str, status_text: str, today: date) -> list[str]:
    """Return one line per problem of the waivers the body cites.

    Why: the judgement of the check, apart from where the body, the paths and the files come from.

    Contract: empty when nothing is cited. Citations are judged in sorted order.
    """
    listed = waivers(waivers_text)
    closed = closed_phases(status_text)
    return [line for waiver_id in cited(body) for line in judge(waiver_id, listed.get(waiver_id), paths, today, closed)]


def shown(revision: str, path: str) -> str:
    """Return a file as it stands at a revision.

    Why: the waivers and the phases are read from the base, never from the PR.

    Contract: runs `git show revision:path` in the current folder; git's error stream is
    passed through. Raises CalledProcessError when git fails.
    """
    done = subprocess.run(  # noqa: S603 fixed argv, no shell
        ["git", "show", f"{revision}:{path}"],  # noqa: S607 git from PATH, as in CI
        stdout=subprocess.PIPE,
        check=True,
        timeout=GIT_TIMEOUT_SECONDS,
    )
    return done.stdout.decode("utf-8")


def today(now: datetime | None = None) -> date:
    """Return the date at UTC+3 of a moment, by default of now.

    Why: GitHub's runners keep UTC, which would leave a date waiver in force up to three hours
    into Israel's next day; Achia's answer reads "has expired after that date" by his calendar.

    Contract: `now` must carry a time zone. In winter the date turns an hour before Israel's
    midnight, so a waiver ends that hour early.
    """
    return (now or datetime.now(UTC)).astimezone(ISRAEL_SUMMER).date()


def main(argv: list[str], environ: Mapping[str, str]) -> int:
    """Check the waivers cited in PR_BODY against the revisions in argv; return the exit code.

    Why: the entry point of the workflow, given its arguments and environment so that a test
    can call it.

    Contract: argv is [base, head]; any other length writes the usage line, exit 2. A missing
    PR_BODY is an empty body. Writes each problem on the error stream.
    """
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    body = environ.get("PR_BODY", "")
    if not cited(body):
        return 0
    base, head = argv
    paths = changed(base, head, Path.cwd())
    found = problems(body, paths, shown(base, WAIVERS_FILE), shown(base, STATUS_FILE), today())
    for line in found:
        print(line, file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ))
