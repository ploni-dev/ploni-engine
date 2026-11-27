"""Tests of scripts/check_phase_row.py: a phase close appends one dated row to the Phases table.

Why: `PROMOTION.md` Level 4, the row "`docs/STATUS.md` phase row appended | CI checks the
Phases table gained a row", is not built (#276, part 1). At the close of Phase 0 the row was
rewritten in place and only the review read it.

Test matrix (reason(), on the text of docs/STATUS.md at the base and at the head):

Equivalence classes:
  EC1  one row appended, naming a phase, dated       passes (None)
  EC2  a row rewritten in place, none appended (an undated row given its date)
                                                     the count line: 1 on the head, 1 on the base
  EC3  no change                                     the count line
  EC4  a row removed                                 the count line
  EC5  the table missing on the head                 the count line: 0 on the head
  EC6  the Date cell of the new row empty            the date line, naming the phase
  EC7  two rows appended                             the count line: 3 on the head
  EC8  an earlier row changed, and one row appended  the changed line, naming the row
  EC9  the new row inserted above an earlier one     the changed line
  EC10 the new row names no phase (its first cell starts with no number)
                                                     the count line: it is not a phase row
  EC11 main(), with git stubbed: a pass writes nothing, exit 0; a refusal writes the reason
       on the error stream, exit 1; the base is read at the base, the head at the head
  EC12 is_date(): an existing YYYY-MM-DD date        True
  EC13 the repository's own docs/STATUS.md: its Phase 0 row is read, with a date in the cell
       the check reads
  EC14 phase_rows(): the cells of each row of the Phases table that names a phase, stripped,
       in order; header, separator, an unnumbered row and another table give none

Boundaries:
  B1  a base table of header and separator only, one row appended    passes
  B2  no table on the base, the head adds it with one dated row      passes
  B3  a Date cell that is no date: "TBD", a day that does not exist, a date with text after
      it, another date order, no Date cell at all    the date line
  B4  an earlier row padded or realigned, its cells the same         passes
  B5  the head written with CRLF line ends, the base with LF        passes

Error paths (main):
  E1  wrong argument count                           exit 2, a usage line
  E2  docs/STATUS.md missing at a revision, a revision git does not know    git's error, a
      non-zero exit (the module suite)

Adversarial:
  A1  another table of STATUS (## Done) gains a dated, numbered row; Phases does not
                                                     the count line: only Phases counts
  A2  an earlier row changed by one invisible direction mark (U+200F)    the changed line
  A3  a Hebrew phase name in the new row             passes
  A4  the new row repeats the number of an earlier phase    passes: a known limit (below)
  A5  a date in Arabic-Indic digits, which `\\d` matches     not a date

Not applicable: the document axes; the Hebrew axes of the test-matrix skill other than A2,
A3 and A5, as the input is one Markdown table of the repository.

Known limits:
  - A4: the check does not compare phase numbers; the reviewer reads which phase closed.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from scripts import check_phase_row as check

ROOT = Path(__file__).resolve().parents[2]

HEADER = "| Phase | Gate | Measured | Date | Exit demo shown |\n|---|---|---|---|---|\n"
ROW_0 = "| 0 Foundation and safety | selftest | all green | 2026-11-25 | yes |\n"
ROW_1 = "| 1 Deterministic detectors | detectors | measured | 2026-12-20 | yes |\n"
ROW_2 = "| 2 Document adapters | adapters | measured | 2027-01-15 | yes |\n"
BEFORE = "# Status\n\n## Done\n\n| What | Where | PRs | Date |\n|---|---|---|---|\n| 3 things | x | y | 2026-11-19 |\n\n"
AFTER = "\n## Open waivers\n\nNone.\n"


def status(*rows: str, header: str = HEADER) -> str:
    """Return a docs/STATUS.md text whose Phases table holds the given rows."""
    return f"{BEFORE}## Phases\n\n{header}{''.join(rows)}{AFTER}"


BASE = status(ROW_0)
COUNT_1_1 = "the Phases table of docs/STATUS.md has 1 phase row(s) on the head and 1 on the base; a phase close appends exactly one"
CHANGED_1 = "row 1 of the Phases table of docs/STATUS.md changed (0 Foundation and safety); a phase close changes no earlier row"


def count_line(head: int, base: int) -> str:
    """Return the count line of reason() for the given numbers of phase rows."""
    return f"the Phases table of docs/STATUS.md has {head} phase row(s) on the head and {base} on the base; a phase close appends exactly one"


def date_line(phase: str) -> str:
    """Return the date line of reason() for a new row whose first cell is phase."""
    return f"the new row of the Phases table of docs/STATUS.md ({phase}) has no close date (YYYY-MM-DD) in its Date cell"


def test_ec1_one_row_appended() -> None:
    assert check.reason(BASE, status(ROW_0, ROW_1)) is None


def test_ec2_a_row_rewritten_in_place() -> None:
    undated = "| 0 Foundation and safety | selftest | all green | | |\n"
    assert check.reason(status(undated), BASE) == COUNT_1_1


def test_ec3_no_change() -> None:
    assert check.reason(BASE, BASE) == COUNT_1_1


def test_ec4_a_row_removed() -> None:
    assert check.reason(status(ROW_0, ROW_1), BASE) == count_line(1, 2)


def test_ec5_the_table_missing_on_the_head() -> None:
    assert check.reason(BASE, BEFORE + AFTER) == count_line(0, 1)


def test_ec6_the_date_cell_empty() -> None:
    undated = "| 1 Deterministic detectors | detectors | measured | | yes |\n"
    assert check.reason(BASE, status(ROW_0, undated)) == date_line("1 Deterministic detectors")


def test_ec7_two_rows_appended() -> None:
    assert check.reason(BASE, status(ROW_0, ROW_1, ROW_2)) == count_line(3, 1)


def test_ec8_an_earlier_row_changed_and_one_appended() -> None:
    changed = ROW_0.replace("all green", "all green, and more")
    assert check.reason(BASE, status(changed, ROW_1)) == CHANGED_1


def test_ec9_the_new_row_above_an_earlier_one() -> None:
    assert check.reason(BASE, status(ROW_1, ROW_0)) == CHANGED_1


def test_ec10_the_new_row_names_no_phase() -> None:
    unnamed = "| Deterministic detectors | detectors | measured | 2026-12-20 | yes |\n"
    assert check.reason(BASE, status(ROW_0, unnamed)) == count_line(1, 1)


def stub_shown(texts: dict[str, str]) -> Callable[[str, str], str]:
    """Return a stand-in for shown() that gives the text of each revision, of docs/STATUS.md only."""

    def shown(revision: str, path: str) -> str:
        assert path == "docs/STATUS.md"
        return texts[revision]

    return shown


def test_ec11_main_passes_quietly(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(check, "shown", stub_shown({"base": BASE, "head": status(ROW_0, ROW_1)}))
    assert check.main(["base", "head"]) == 0
    assert capsys.readouterr() == ("", "")


def test_ec11_main_writes_the_reason(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(check, "shown", stub_shown({"base": BASE, "head": BASE}))
    assert check.main(["base", "head"]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert err.splitlines() == [COUNT_1_1]


def test_ec11_main_reads_each_revision_at_its_own(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(check, "shown", stub_shown({"base": status(ROW_0, ROW_1), "head": BASE}))
    assert check.main(["base", "head"]) == 1
    assert capsys.readouterr().err.splitlines() == [count_line(1, 2)]


@pytest.mark.parametrize("text", ["2026-11-25", "2024-02-29", "2027-01-01"])
def test_ec12_is_date(text: str) -> None:
    assert check.is_date(text)


def test_ec13_the_repository_status_file() -> None:
    rows = check.phase_rows((ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8"))
    assert rows[0][0].startswith("0 ")
    assert check.is_date(rows[0][check.DATE_CELL])


def test_ec14_phase_rows() -> None:
    assert check.phase_rows(status(ROW_0, "| Later | x | | | |\n", ROW_1)) == [
        ["0 Foundation and safety", "selftest", "all green", "2026-11-25", "yes"],
        ["1 Deterministic detectors", "detectors", "measured", "2026-12-20", "yes"],
    ]


def test_b1_a_table_of_header_only() -> None:
    assert check.reason(status(), status(ROW_0)) is None


def test_b2_no_table_on_the_base() -> None:
    assert check.reason(BEFORE + AFTER, BASE) is None


@pytest.mark.parametrize(
    "row",
    [
        "| 1 Deterministic detectors | detectors | measured | TBD | yes |\n",
        "| 1 Deterministic detectors | detectors | measured | 2026-02-30 | yes |\n",
        "| 1 Deterministic detectors | detectors | measured | 2026-12-20 (laptop) | yes |\n",
        "| 1 Deterministic detectors | detectors | measured | 20.12.2026 | yes |\n",
        "| 1 Deterministic detectors | detectors | measured |\n",
    ],
)
def test_b3_a_date_cell_that_is_no_date(row: str) -> None:
    assert check.reason(BASE, status(ROW_0, row)) == date_line("1 Deterministic detectors")


@pytest.mark.parametrize("text", ["", "TBD", "2026-02-30", "2026-13-01", "20261125", "2026-11-25 (laptop)", "25.11.2026"])
def test_b3_is_date_refuses(text: str) -> None:
    assert not check.is_date(text)


def test_b4_an_earlier_row_realigned() -> None:
    padded = "|   0 Foundation and safety   |  selftest | all green |   2026-11-25 | yes|\n"
    assert check.reason(BASE, status(padded, ROW_1)) is None


def test_b5_crlf_on_the_head() -> None:
    assert check.reason(BASE, status(ROW_0, ROW_1).replace("\n", "\r\n")) is None


def test_e1_main_needs_two_revisions(capsys: pytest.CaptureFixture[str]) -> None:
    for argv in ([], ["HEAD^1"], ["a", "b", "c"]):
        assert check.main(argv) == 2
        out, err = capsys.readouterr()
        assert out == ""
        assert err.startswith("usage: ")


def test_a1_another_table_gains_a_row() -> None:
    head = BASE.replace("| 3 things | x | y | 2026-11-19 |\n", "| 3 things | x | y | 2026-11-19 |\n| 4 more | x | y | 2026-11-20 |\n")
    assert check.reason(BASE, head) == COUNT_1_1


def test_a2_a_direction_mark_in_an_earlier_row() -> None:
    marked = ROW_0.replace("all green", "all‏ green")
    assert check.reason(BASE, status(marked, ROW_1)) == CHANGED_1


def test_a3_a_hebrew_phase_name() -> None:
    assert check.reason(BASE, status(ROW_0, "| 1 גלאים דטרמיניסטיים | גלאים | נמדד | 2026-12-20 | כן |\n")) is None


def test_a4_the_new_row_repeats_an_earlier_phase() -> None:
    assert check.reason(BASE, status(ROW_0, ROW_0)) is None


def test_a5_a_date_in_arabic_indic_digits() -> None:
    assert not check.is_date("٢٠٢٦-١١-٢٥")
