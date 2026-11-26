"""Check that a PR lowers no number of the held-out batch: main's report against the PR's.

Why: Achia's answer of 2026-11-26 on issue 170, "Score main live (Recommended)": "Each PR,
GitHub scores both main and the PR on the batch and blocks any drop. No numbers are stored. If
you accept a worse score, the PR quotes your reason, and after the merge main holds that score
as the new 'before'." PROMOTION.md section 11: "any drop counts, however small, and every
accuracy number measured on the batch counts by itself".

Contract: `python -m scripts.check_scores <main report> <PR report>`, run from the root of the
checkout, with the PR body in PR_BODY (missing: an empty body). A report is the output of
`python -m eval.heldout.scorer`: one line per type, `NAME tp N fp N fn N partial N recall R
precision P`, a group line with tp, fn and recall only, and TOTAL; blank lines are skipped, a
byte order mark is read. Every line has a recall (tp and fn are required); a line with fp has a
precision. For each line of main's report and each of its rates, the PR's rate is compared with
main's as fractions of the counts (tp / (tp + fn), tp / (tp + fp), 0 when the count below is 0,
as the scorer prints them), so a drop smaller than the printed three decimals is a drop. A drop
line gives the rate printed and as its counts: `held-out drop: <line> <metric> <before> ->
<after> (<tp>/<count> -> <tp>/<count>)`.

A PR body line `score-drop-accepted: <line> <metric> <before counts> <after counts> <reason>`
(the counts as the drop line gives them, for example `IL_ID recall 45/50 44/50 <reason>`), after
spaces and backquotes, lifts that one drop. Each drop needs a line of its own: an accepted
recall drop whose line also lost precision below the printed decimals shows a second drop line,
for precision, with its own counts, and is lifted only by a second body line. A line that starts
so and cannot be read (no reason, or rates in place of counts) is a problem of its own; a quoted
line ("> ...") is not read.

A line of main's that the PR's report lacks, and a precision that main's line has and the PR's
lacks, are a change of the batch or of its scorer, not a drop of a detector: they are refused,
and no body line lifts them. A line only in the PR's report, or a precision only on the PR's
line, is not compared.

The output gets a table of every line of main's, before and after; the error stream gets one
line per problem not lifted, in the order of main's report. Exit 0: no problem; 1: one or more;
2: wrong arguments (the usage line), a report that cannot be read, or one whose line does not
parse, repeats a name, or prints a rate its counts do not give (the file and line number only).

Known limits: nothing but type names and numbers is written, never the reason of a body line
nor a line of a report. Whether a body line quotes Achia is the reviewer's to check, not this
script's. The two reports must come from the same batch; a change of the batch that keeps
every line and its shape is not seen here.
"""

import os
import re
import sys
from collections.abc import Callable, Mapping
from fractions import Fraction
from pathlib import Path
from typing import NamedTuple

USAGE = "usage: python -m scripts.check_scores <main report> <PR report>"
ACCEPT_START = "score-drop-accepted:"
ACCEPT = re.compile(r"score-drop-accepted: (\S+) (recall|precision) (\d+/\d+) (\d+/\d+) (\S.*)")
PRINTED = "{:.3f}"
CHANGE = "a change of the batch, which no body line lifts"

Writer = Callable[[str], object]


class ReportError(Exception):
    """A report that cannot be read or does not parse.

    Why: every way a report can be wrong ends the check the same way, exit 2, with one line.

    Contract: its message names the file and the line number, never the line's text.
    """


class Rate(NamedTuple):
    """One rate of a report's line, as its counts: hits of a whole.

    Why: the counts are exact and show a drop that the three printed decimals hide.

    Contract: `hits` and `whole` are counts, 0 <= hits <= whole; the rate is 0 when whole is 0,
    as the scorer prints it.
    """

    hits: int
    whole: int

    def value(self) -> Fraction:
        """Return the rate as an exact fraction, 0 when the whole is 0.

        Why: two rates are compared as numbers, not as their printed decimals.

        Contract: a Fraction in [0, 1].
        """
        return Fraction(self.hits, self.whole) if self.whole else Fraction(0)

    def counts(self) -> str:
        """Return the rate's counts as hits/whole.

        Why: a drop line and a body line name a drop by its counts.

        Contract: "<hits>/<whole>", whole numbers, unreduced.
        """
        return f"{self.hits}/{self.whole}"

    def printed(self) -> str:
        """Return the rate as the scorer prints it.

        Why: the table and the drop lines show the rate as the report does.

        Contract: three decimals.
        """
        return PRINTED.format(float(self.value()))


class Rates(NamedTuple):
    """The rates of one line of a report.

    Why: a type line has two accuracy numbers, a group line one; each counts by itself.

    Contract: precision is None on a line with no fp, a group line.
    """

    recall: Rate
    precision: Rate | None


class Problem(NamedTuple):
    """One problem of a PR's report against main's.

    Why: a drop names its counts so a body line can lift it; a change of the batch has none, so
    none can.

    Contract: `metric` is "recall" or "precision"; `before` and `after` are counts, or both
    None for a line or a precision that the PR lacks (`metric` "" for a whole line).
    """

    line: str
    metric: str
    before: Rate | None
    after: Rate | None


def parse_line(line: str, where: str) -> tuple[str, Rates]:
    """Read one line of a report into its name and rates.

    Why: the rates are taken from the counts, which are exact, and the printed ones are only
    checked against them, so that a change of the scorer's format fails here and not silently.

    Contract: `line` is one non-blank line; `where` is "file:line" for a message. Returns the
    name and its Rates. Raises ReportError when the fields are not name and pairs, a count is
    not a whole number, tp or fn is missing, or a printed recall or precision is not the one the
    counts give.

    Known limits: fields other than tp, fp, fn, recall and precision are read and not judged.
    """
    name, *rest = line.split()
    fields = dict(zip(rest[::2], rest[1::2], strict=False))
    counts = {key: fields[key] for key in ("tp", "fp", "fn") if key in fields}
    if len(rest) % 2 or "tp" not in counts or "fn" not in counts or not all(value.isdigit() for value in counts.values()):
        raise ReportError(f"{where}: not a line of the scorer's report")
    tp, fn = int(counts["tp"]), int(counts["fn"])
    rates = Rates(Rate(tp, tp + fn), Rate(tp, tp + int(counts["fp"])) if "fp" in counts else None)
    printed = [("recall", rates.recall), ("precision", rates.precision)]
    if any(value is not None and fields.get(key) != value.printed() for key, value in printed):
        raise ReportError(f"{where}: a printed rate that its counts do not give")
    return name, rates


def read_report(path: str) -> dict[str, Rates]:
    """Read a report file into its lines' rates, in its order.

    Why: both reports are read the same way, and every way a report can be wrong is one
    ReportError, so the check stops before comparing anything half read.

    Contract: returns {name: Rates} in the file's order. Raises ReportError when the file
    cannot be read, holds no line, repeats a name, or has a line `parse_line` refuses.

    Known limits: the file is read as UTF-8, with or without a byte order mark.
    """
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise ReportError(f"cannot read {path}") from error
    lines: dict[str, Rates] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        name, rates = parse_line(line, f"{path}:{number}")
        if name in lines:
            raise ReportError(f"{path}:{number}: {name} twice")
        lines[name] = rates
    if not lines:
        raise ReportError(f"{path}: no line")
    return lines


def accepted(body: str) -> tuple[set[tuple[str, str, str, str]], int]:
    """Read the accepted drops of a PR body.

    Why: a drop Achia accepted is lifted by a line in the PR that quotes his reason (his answer
    of 2026-11-26 on issue 170); a line that starts like one and is not read must not pass as
    one nor go unseen.

    Contract: returns the (line, metric, before counts, after counts) of each line read, and how
    many lines start like one and cannot be read. A line counts when, after spaces and
    backquotes, it starts with ACCEPT_START; a quoted line ("> ...") does not. The reason may be
    any text.

    Known limits: whether the reason is Achia's is not checked.
    """
    read: set[tuple[str, str, str, str]] = set()
    unread = 0
    for raw in body.splitlines():
        line = raw.strip().strip("`").strip()
        if not line.startswith(ACCEPT_START):
            continue
        match = ACCEPT.fullmatch(line)
        if match:
            read.add((match.group(1), match.group(2), match.group(3), match.group(4)))
        else:
            unread += 1
    return read, unread


def drops(main: dict[str, Rates], pr: dict[str, Rates]) -> list[Problem]:
    """Return each rate of main's report that the PR's lowers or lacks.

    Why: the decision of the check, apart from reading and writing, so that it is tested alone.

    Contract: in main's order, recall before precision. A line the PR lacks is one Problem with
    metric "" and no counts; a precision the PR's line lacks is one with metric "precision" and
    no counts; a lower rate has both counts. The comparison is of the fractions.

    Known limits: a rise is not reported.
    """
    found: list[Problem] = []
    for name, before in main.items():
        after = pr.get(name)
        if after is None:
            found.append(Problem(name, "", None, None))
            continue
        for metric, old, new in (("recall", before.recall, after.recall), ("precision", before.precision, after.precision)):
            if old is None:
                continue
            if new is None:
                found.append(Problem(name, metric, None, None))
            elif new.value() < old.value():
                found.append(Problem(name, metric, old, new))
    return found


def described(problem: Problem) -> str:
    """Write one problem as its line on the error stream.

    Why: a drop shows its counts, so one below the printed decimals is visible; a change of the
    batch says that no body line lifts it.

    Contract: "held-out drop: ..." in the forms of the module docstring.
    """
    if problem.after is None or problem.before is None:
        what = "is missing from the PR's report" if not problem.metric else f"{problem.metric} is missing from the PR's line"
        return f"held-out drop: {problem.line} {what}: {CHANGE}"
    old, new = problem.before, problem.after
    return f"held-out drop: {problem.line} {problem.metric} {old.printed()} -> {new.printed()} ({old.counts()} -> {new.counts()})"


def lifted(problem: Problem, accepted_drops: set[tuple[str, str, str, str]]) -> bool:
    """Say whether a body line lifts a problem: a drop with counts, named by them exactly.

    Why: a change of the batch has no counts, so no body line can name it.

    Contract: True only for a Problem with both counts whose (line, metric, before, after) is in
    `accepted_drops`.
    """
    if problem.before is None or problem.after is None:
        return False
    return (problem.line, problem.metric, problem.before.counts(), problem.after.counts()) in accepted_drops


def table(main: dict[str, Rates], pr: dict[str, Rates]) -> list[str]:
    """Write the numbers of each line of main's report, before and after.

    Why: build-plan.md section 7: "Every PR carries the numbers of the batch, before and after."

    Contract: a header, then one row per line of main's report, in its order: the name, the
    recall and the precision as "before -> after"; "-" where main's line has no precision;
    "missing" where the PR's report lacks the line or the PR's line lacks the rate.
    """

    def pair(old: Rate | None, new: Rate | None) -> str:
        """Write one rate as before -> after."""
        if old is None:
            return "-"
        return f"{old.printed()} -> {'missing' if new is None else new.printed()}"

    rows = [f"{'line':<18}{'recall before -> after':<25}precision before -> after"]
    for name, before in main.items():
        after = pr.get(name)
        recall = pair(before.recall, None if after is None else after.recall)
        precision = pair(before.precision, None if after is None else after.precision)
        rows.append(f"{name:<18}{recall:<25}{precision}")
    return rows


def main(argv: list[str], environ: Mapping[str, str], out: Writer, err: Writer) -> int:
    """Check a PR's report against main's; return the exit code.

    Why: the entry point of the workflow, given its arguments, environment and writers so that a
    test can call it.

    Contract: argv is [main report, PR report]; any other length writes USAGE, exit 2. Writes
    the table with `out` and each problem with `err`; the exit codes are the module's.
    """
    if len(argv) != 2:
        err(USAGE)
        return 2
    try:
        before, after = read_report(argv[0]), read_report(argv[1])
    except ReportError as error:
        err(str(error))
        return 2
    for row in table(before, after):
        out(row)
    accepted_drops, unread = accepted(environ.get("PR_BODY", ""))
    problems = [described(problem) for problem in drops(before, after) if not lifted(problem, accepted_drops)]
    problems += ["a score-drop-accepted line that cannot be read"] * unread
    for line in problems:
        err(line)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ, print, lambda line: print(line, file=sys.stderr)))
