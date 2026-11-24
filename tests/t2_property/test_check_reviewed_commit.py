"""Invariants of scripts/check_reviewed_commit.py's reading of the body, over every short review section drawn from a labelled pool.

Why: `CLAUDE.md`, Tests: an invariant is held over 500 generated cases. Each line of the pool
below is labelled by hand (not a label line; a label line naming a full hash; a label line
naming none), so the expected answer of each section comes from the labels and the strict
reading Achia chose on 2026-11-22 (issue #176), not from the code under test.

Invariants:
  I1  the section's lines, in any order: no label line gives the missing line; two or more give
      the line naming how many; one gives its hash when it names a full one, else not pasted.
  I2  the same body with CRLF line ends gives the same answer.
  I3  the same section after other sections and before another gives the same answer.

Sample: every sequence of one to three lines from a pool of twelve, 1,884 cases; in the full
suite (tests/sizes.py) sequences of up to four lines, 22,620 cases.

Known limits: the pool is fixed; the forms of a single line are covered one by one by the unit
tests (tests/t1_unit/test_check_reviewed_commit.py).
"""

from collections.abc import Iterator
from itertools import product

from scripts import check_reviewed_commit as check
from tests.sizes import full

SHA = "eb204fb480c917394e2923d54d9736840bfebbcc"
OTHER = "d1141580eddda31e023b8db44d79b5302cb6097c"
# Lines that are not a label line: text, a quoted report, a bold label, a comment, a blank.
PLAIN = [
    "Reviewed by: a subagent that did not write the change.",
    f"> Commit reviewed: `{OTHER}`, the head.",
    f"> **Commit reviewed:** {OTHER}",
    f"<!-- Commit reviewed: `{OTHER}` -->",
    "",
    "- pass 1, on 48b7d5a, Fix first: https://github.com/x/y/pull/1#issuecomment-1",
]
# Label lines with the hash each names, "" when it names none.
LABELLED = {
    f"Commit reviewed: `{SHA}`, the head, in pass 3: Ship.": SHA,
    f"  Commit reviewed: `{OTHER}`": OTHER,
    "Commit reviewed:": "",
    "Commit reviewed: `eb204fb`, the head.": "",
    f"Commit reviewed: {SHA}": "",
    f"Commit reviewed: `{SHA.upper()}`": "",
}
POOL = [*PLAIN, *LABELLED]
LONGEST = 4 if full() else 3
NOT_PASTED = 'not pasted: the "Commit reviewed:" line of ## Ponytail review names no full 40-character hash in backticks'
MISSING_LINE = 'missing: a line that starts with "Commit reviewed:" in ## Ponytail review'


def sections() -> Iterator[list[str]]:
    """Yield every sequence of one to LONGEST lines of the pool, one at a time."""
    for length in range(1, LONGEST + 1):
        for picked in product(POOL, repeat=length):
            yield list(picked)


def expected(lines: list[str]) -> tuple[str, str]:
    """Return the answer the labels give for a section of these lines."""
    labelled = [line for line in lines if line in LABELLED]
    if not labelled:
        return "", MISSING_LINE
    if len(labelled) > 1:
        return "", f'{len(labelled)} lines start with "Commit reviewed:" in ## Ponytail review; keep one, the one that names the last commit'
    sha = LABELLED[labelled[0]]
    return (sha, "") if sha else ("", NOT_PASTED)


def body(lines: list[str]) -> str:
    """Return a body holding only the review section with these lines."""
    return "## Ponytail review\n" + "\n".join(lines)


def test_the_sample_is_over_500() -> None:
    assert sum(1 for _ in sections()) == (22620 if full() else 1884)


def test_i1_the_answer_follows_the_labels() -> None:
    for lines in sections():
        assert check.named(body(lines)) == expected(lines), lines


def test_i2_crlf_changes_nothing() -> None:
    for lines in sections():
        assert check.named(body(lines).replace("\n", "\r\n")) == expected(lines), lines


def test_i3_other_sections_change_nothing() -> None:
    for lines in sections():
        text = "## Orientation\nGoal: x\n\n" + body(lines) + "\n## Who merges\n" + f"Commit reviewed: `{SHA}`\n"
        assert check.named(text) == expected(lines), lines
