"""Check that a phase close appends exactly one dated row to the Phases table of docs/STATUS.md.

Why: `PROMOTION.md` Level 4, the row "`docs/STATUS.md` phase row appended | CI checks the
Phases table gained a row". That check was not built when Phase 0 closed: its row was
rewritten in place and only the review read it (issue #276, part 1, carried by Achia's answer
of 2026-11-25 on #210, "Yes, close it this way (Recommended)").

Contract: `python -m scripts.check_phase_row <base> <head>`, run from the root of the
checkout. It runs as a module so that it uses `shown()` of scripts/check_waiver.py, which
reads docs/STATUS.md at each revision with `git show`. It passes when the head has exactly one
more phase row than the base, every row of the base stands unchanged, cell by cell, at the top
of the head's table, and the new row's Date cell holds a YYYY-MM-DD date that exists. A row
names a phase when its first cell starts with a number; a missing table has no rows.
Passing: nothing written, exit 0. Otherwise the first reason, one line on the error stream,
exit 1. Wrong arguments: a usage line, exit 2. A revision git does not know, or no
docs/STATUS.md at a revision: git's error, a traceback, a non-zero exit.

Known limits:
- The Phases table is parsed here by `phase_rows()`, beside `closed_phases()` of
  scripts/check_waiver.py, which reads the same table the same way. That file is a checker a
  workflow step calls, a Level 3 path of PROMOTION.md, so it is left as it is; the two
  parsers may be merged later with Achia's yes.
- The check is run only on a phase close; which PR is one is not its to decide, and it is
  not wired into any workflow (that is Achia's decision, with its lines).
- As PROMOTION.md words the row, a close that fills in a row already in the table is refused
  (#276 notes this; the wording of that row is Achia's, Level 3).
- Cells are compared stripped: padding or realigning a row is not a change; an invisible
  character added inside a cell is. The header row is not compared.
- The new row's phase number is not compared with the earlier rows': a row that repeats an
  earlier phase passes; the reviewer reads which phase closed.
- Only the Date cell is read for the close; the other cells of the new row may be empty.
- An escaped `\\|` inside a cell splits the cell, in both revisions alike.
"""

import re
import sys
from datetime import date

from scripts.check_waiver import DATE, DATE_CELL, STATUS_FILE, shown

USAGE = "usage: python -m scripts.check_phase_row <base> <head>"
TABLE = f"the Phases table of {STATUS_FILE}"
HEADING = "## Phases"
PHASE_NUMBER = re.compile(r"\d+")


def phase_rows(status: str) -> list[list[str]]:
    """Return the cells of each row of the Phases table of docs/STATUS.md that names a phase.

    Why: the rows the check compares, read as `closed_phases()` of scripts/check_waiver.py
    reads them.

    Contract: only lines starting with "|" under `## Phases`, up to the next `## ` heading,
    are read; a row names a phase when its first cell starts with a number, so the header and
    the separator row are left out. Each row is its cells, stripped, in the order of the file.
    A text with no such heading gives an empty list.
    """
    rows = []
    inside = False
    for line in (raw.strip() for raw in status.splitlines()):
        if line.startswith("## "):
            inside = line == HEADING
        elif inside and line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if PHASE_NUMBER.match(cells[0]):
                rows.append(cells)
    return rows


def is_date(text: str) -> bool:
    """Say whether a cell is a close date: YYYY-MM-DD, a day that exists.

    Why: "carries a close date" read the strict way: "TBD" or "2026-02-30" is no close.

    Contract: True only when the whole text matches `DATE` of scripts/check_waiver.py and is a
    date of the calendar; anything else, also digits other than 0 to 9, is False.
    """
    if not DATE.fullmatch(text):
        return False
    try:
        date.fromisoformat(text)
    except ValueError:
        return False
    return True


def reason(base: str, head: str) -> str | None:
    """Return why the head's Phases table is not the base's with one dated row appended, or None.

    Why: the judgement of the check, apart from where the two texts come from.

    Contract: `base` and `head` are texts of docs/STATUS.md. The reasons are checked in this
    order and the first is returned: the number of phase rows; an earlier row changed, named
    by its place and its first cell in the base; the new row's Date cell.
    """
    before, after = phase_rows(base), phase_rows(head)
    if len(after) != len(before) + 1:
        return f"{TABLE} has {len(after)} phase row(s) on the head and {len(before)} on the base; a phase close appends exactly one"
    for place, (old, new) in enumerate(zip(before, after, strict=False), start=1):
        if old != new:
            return f"row {place} of {TABLE} changed ({old[0]}); a phase close changes no earlier row"
    added = after[-1]
    if len(added) <= DATE_CELL or not is_date(added[DATE_CELL]):
        return f"the new row of {TABLE} ({added[0]}) has no close date (YYYY-MM-DD) in its Date cell"
    return None


def main(argv: list[str]) -> int:
    """Check the Phases table between the two revisions in argv; return the exit code.

    Why: the entry point of the script, given its arguments so that a test can call it.

    Contract: argv is [base, head]; any other length writes the usage line, exit 2. Writes the
    reason on the error stream, exit 1, or nothing, exit 0. Raises CalledProcessError when git
    cannot show docs/STATUS.md at a revision.
    """
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    base, head = argv
    found = reason(shown(base, STATUS_FILE), shown(head, STATUS_FILE))
    if found is None:
        return 0
    print(found, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
