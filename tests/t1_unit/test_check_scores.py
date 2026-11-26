"""Test matrix for scripts/check_scores.py: two held-out reports, main's and the PR's, and any drop.

Why: Achia's answer of 2026-11-26 on issue 170, "Score main live (Recommended)": "Each PR, GitHub
scores both main and the PR on the batch and blocks any drop. No numbers are stored. If you
accept a worse score, the PR quotes your reason, and after the merge main holds that score as
the new 'before'." PROMOTION.md section 11: "any drop counts, however small, and every accuracy
number measured on the batch counts by itself" (Claude's, which only narrows). Issue 170 asks
the check to be "shown refusing a made-up drop before any detector can lower a real score":
every report here is made up, in the scorer's format, and none comes from the batch.

The report format is the one the batch's scorer prints (read from its output with a
detector that finds nothing, type names and numbers only): one line per type, `NAME tp N fp N
fn N partial N recall R precision P`; a group line, `NAME:group tp N fn N recall R`; a TOTAL line.

Test matrix:

Equivalence classes:
  EC1  the same report twice                            no line; the table on the output; exit 0
  EC2  one type's recall lower                          one line: the name, the metric, both numbers
  EC3  one type's precision lower                       one line
  EC4  every number higher, or the same                 no line
  EC5  a group line's recall lower                      one line (a group line has no precision)
  EC6  TOTAL lower                                      one line: TOTAL counts by itself
  EC7  a line of main's report missing from the PR's    one line: missing
  EC8  a line new in the PR's report (a type main lacks, OTHER)    no line
  EC9  an accepted drop: a PR body line `score-drop-accepted: <line> <metric> <before> <after>
       <reason>` naming it exactly                      no line for it; the other drops stay
  EC10 a body line that names another number, another metric or another line, or has no reason
                                                        the drop stays refused; a line that
                                                        starts like one and cannot be read is a
                                                        line of its own
  EC11 two drops                                        two lines, in the order of main's report
  EC12 the table: each line of main's report with its two numbers per metric, before and after

Boundaries:
  B1  a drop smaller than the printed precision (10000 of 10001 to 10000 of 10002: both print
      1.000)                                            refused: the counts are compared
  B2  0 of 0 on both sides (no detection, no item)      0 and 0, no drop
  B3  precision from no detection (printed 0.000) to some    a rise
  B4  recall to 0 from 1 item of 1                      refused

Error paths (exit 2, a line that names the file and the line number, never its text):
  E1  a report file that does not exist
  E2  a line that does not parse: an odd number of fields, a count that is not a whole number,
      no tp or no fn
  E3  a printed recall or precision that the counts do not give: the format changed
  E4  an empty report
  E5  the same line name twice in one report
  E6  not two arguments: the usage line

Adversarial:
  A1  a report written by PowerShell, with a byte order mark and CRLF line ends    read
  A2  a reason in Hebrew in the PR body: not on either stream
  A3  PERSON and PERSON:untitled are two lines; a drop of one does not hide behind the other
  A4  a body line quoted ("> score-drop-accepted: ...") does not accept anything

Not applicable: the Hebrew and document axes of the test-matrix skill, but A2: a report holds
type names and numbers only.
"""

from pathlib import Path

import pytest

from scripts import check_scores

FIELDS = "tp {tp}  fp {fp}  fn {fn}  partial 0  recall {recall}  precision {precision}"


def type_line(name: str, tp: int, fp: int, fn: int) -> str:
    """Write one type line as the scorer prints it, its two rates from its counts."""
    recall = f"{tp / (tp + fn) if tp + fn else 0:.3f}"
    precision = f"{tp / (tp + fp) if tp + fp else 0:.3f}"
    return f"{name:<17} " + FIELDS.format(tp=tp, fp=fp, fn=fn, recall=recall, precision=precision)


def group_line(name: str, tp: int, fn: int) -> str:
    """Write one group line as the scorer prints it."""
    return f"{name:<17} tp {tp}  fn {fn}  recall {tp / (tp + fn) if tp + fn else 0:.3f}"


MAIN = [
    type_line("IL_ID", 45, 1, 5),
    type_line("PERSON", 80, 10, 20),
    type_line("PHONE", 0, 0, 50),
    group_line("PERSON:untitled", 30, 20),
    type_line("TOTAL", 125, 11, 75),
]


def write(path: Path, lines: list[str], *, bom: bool = False, crlf: bool = False) -> Path:
    """Write a report file."""
    text = ("\r\n" if crlf else "\n").join(lines) + "\n"
    path.write_bytes(("﻿" if bom else "").encode() + text.encode())
    return path


def run(tmp_path: Path, main: list[str], pr: list[str], body: str = "") -> tuple[int, str, str]:
    """Run the check on two reports; return the exit code, the output and the error stream."""
    out: list[str] = []
    err: list[str] = []
    code = check_scores.main(
        [str(write(tmp_path / "main.txt", main)), str(write(tmp_path / "pr.txt", pr))], {"PR_BODY": body}, out.append, err.append
    )
    return code, "\n".join(out), "\n".join(err)


def changed(index: int, line: str) -> list[str]:
    """Return main's report with one line replaced."""
    return [line if at == index else each for at, each in enumerate(MAIN)]


def test_ec1_the_same_report_twice(tmp_path: Path) -> None:
    code, out, err = run(tmp_path, MAIN, MAIN)
    assert (code, err) == (0, "")
    assert "IL_ID" in out and "TOTAL" in out


def test_ec2_a_lower_recall(tmp_path: Path) -> None:
    code, _, err = run(tmp_path, MAIN, changed(0, type_line("IL_ID", 44, 0, 6)))
    assert (code, err) == (1, "held-out drop: IL_ID recall 0.900 -> 0.880")


def test_ec3_a_lower_precision(tmp_path: Path) -> None:
    code, _, err = run(tmp_path, MAIN, changed(0, type_line("IL_ID", 45, 2, 5)))
    assert (code, err) == (1, "held-out drop: IL_ID precision 0.978 -> 0.957")


@pytest.mark.parametrize("line", [type_line("IL_ID", 46, 0, 4), type_line("IL_ID", 45, 1, 5)], ids=["higher", "same"])
def test_ec4_higher_or_the_same(tmp_path: Path, line: str) -> None:
    assert run(tmp_path, MAIN, changed(0, line))[::2] == (0, "")


def test_ec5_a_group_line(tmp_path: Path) -> None:
    code, _, err = run(tmp_path, MAIN, changed(3, group_line("PERSON:untitled", 29, 21)))
    assert (code, err) == (1, "held-out drop: PERSON:untitled recall 0.600 -> 0.580")


def test_ec6_total_counts_by_itself(tmp_path: Path) -> None:
    code, _, err = run(tmp_path, MAIN, changed(4, type_line("TOTAL", 125, 12, 75)))
    assert (code, err) == (1, "held-out drop: TOTAL precision 0.919 -> 0.912")


def test_ec7_a_line_missing_from_the_pr(tmp_path: Path) -> None:
    code, _, err = run(tmp_path, MAIN, MAIN[:2] + MAIN[3:])
    assert (code, err) == (1, "held-out drop: PHONE is missing from the PR's report")


@pytest.mark.parametrize("name", ["OTHER", "IBAN"])
def test_ec8_a_line_new_in_the_pr(tmp_path: Path, name: str) -> None:
    assert run(tmp_path, MAIN, [*MAIN, type_line(name, 0, 3, 0)])[::2] == (0, "")


def test_ec9_an_accepted_drop(tmp_path: Path) -> None:
    pr = changed(0, type_line("IL_ID", 44, 2, 6))
    body = "Some text.\nscore-drop-accepted: IL_ID recall 0.900 0.880 Achia, 2026-11-27: the two-letter form is out\n"
    code, _, err = run(tmp_path, MAIN, pr, body)
    assert (code, err) == (1, "held-out drop: IL_ID precision 0.978 -> 0.957")
    body += "`score-drop-accepted: IL_ID precision 0.978 0.957 the same reason`\n"
    assert run(tmp_path, MAIN, pr, body)[::2] == (0, "")


@pytest.mark.parametrize(
    "line",
    [
        "score-drop-accepted: IL_ID recall 0.900 0.870 a reason",
        "score-drop-accepted: IL_ID precision 0.900 0.880 a reason",
        "score-drop-accepted: TOTAL recall 0.900 0.880 a reason",
    ],
    ids=["another number", "another metric", "another line"],
)
def test_ec10_a_body_line_that_names_another_drop(tmp_path: Path, line: str) -> None:
    code, _, err = run(tmp_path, MAIN, changed(0, type_line("IL_ID", 44, 0, 6)), line)
    assert (code, err) == (1, "held-out drop: IL_ID recall 0.900 -> 0.880")


@pytest.mark.parametrize("line", ["score-drop-accepted: IL_ID recall 0.900 0.880", "score-drop-accepted: IL_ID recall high low why"])
def test_ec10_a_body_line_that_cannot_be_read(tmp_path: Path, line: str) -> None:
    code, _, err = run(tmp_path, MAIN, changed(0, type_line("IL_ID", 44, 0, 6)), line)
    assert code == 1
    assert err.splitlines() == ["held-out drop: IL_ID recall 0.900 -> 0.880", "a score-drop-accepted line that cannot be read"]


def test_ec11_two_drops_in_the_order_of_mains_report(tmp_path: Path) -> None:
    pr = changed(4, type_line("TOTAL", 124, 10, 76))
    pr[0] = type_line("IL_ID", 44, 0, 6)
    code, _, err = run(tmp_path, MAIN, pr)
    assert code == 1
    assert err.splitlines() == ["held-out drop: IL_ID recall 0.900 -> 0.880", "held-out drop: TOTAL recall 0.625 -> 0.620"]


def test_ec12_the_table_shows_both_numbers(tmp_path: Path) -> None:
    _, out, _ = run(tmp_path, MAIN, changed(0, type_line("IL_ID", 46, 0, 4)))
    assert out.splitlines()[:2] == [
        "line              recall before -> after   precision before -> after",
        "IL_ID             0.900 -> 0.920           0.978 -> 1.000",
    ]
    assert "PERSON:untitled   0.600 -> 0.600           -" in out.splitlines()


def test_b1_a_drop_smaller_than_the_printed_precision(tmp_path: Path) -> None:
    main = [type_line("IL_ID", 10000, 0, 1)]
    code, _, err = run(tmp_path, main, [type_line("IL_ID", 10000, 0, 2)])
    assert (code, err) == (1, "held-out drop: IL_ID recall 1.000 -> 1.000")


def test_b2_nothing_on_either_side(tmp_path: Path) -> None:
    assert run(tmp_path, [type_line("IL_ID", 0, 0, 0)], [type_line("IL_ID", 0, 0, 0)])[::2] == (0, "")


def test_b3_precision_from_no_detection_is_a_rise(tmp_path: Path) -> None:
    assert run(tmp_path, [type_line("IL_ID", 0, 0, 50)], [type_line("IL_ID", 1, 1, 49)])[::2] == (0, "")


def test_b4_recall_to_zero(tmp_path: Path) -> None:
    code, _, err = run(tmp_path, [type_line("IL_ID", 1, 0, 0)], [type_line("IL_ID", 0, 0, 1)])
    assert code == 1
    assert err.splitlines() == ["held-out drop: IL_ID recall 1.000 -> 0.000", "held-out drop: IL_ID precision 1.000 -> 0.000"]


def test_e1_a_report_that_does_not_exist(tmp_path: Path) -> None:
    err: list[str] = []
    code = check_scores.main([str(tmp_path / "none.txt"), str(write(tmp_path / "pr.txt", MAIN))], {}, print, err.append)
    assert code == 2
    assert err == [f"cannot read {tmp_path / 'none.txt'}"]


@pytest.mark.parametrize(
    "line",
    [
        "IL_ID tp 45 fp",
        "IL_ID tp 4.5 fp 1 fn 5 partial 0 recall 0.900 precision 0.978",
        "IL_ID fp 1 fn 5 partial 0 recall 0.000 precision 0.000",
        "IL_ID tp 45 fp 1 partial 0 recall 0.900 precision 0.978",
    ],
    ids=["odd fields", "not whole", "no tp", "no fn"],
)
def test_e2_a_line_that_does_not_parse(tmp_path: Path, line: str) -> None:
    code, _, err = run(tmp_path, [MAIN[1], line], MAIN)
    assert (code, err) == (2, f"{tmp_path / 'main.txt'}:2: not a line of the scorer's report")


@pytest.mark.parametrize(
    "line",
    ["IL_ID tp 45 fp 1 fn 5 partial 0 recall 0.950 precision 0.978", "IL_ID tp 45 fp 1 fn 5 partial 0 recall 0.900 precision 0.900"],
    ids=["recall", "precision"],
)
def test_e3_a_printed_rate_the_counts_do_not_give(tmp_path: Path, line: str) -> None:
    code, _, err = run(tmp_path, MAIN, [line])
    assert (code, err) == (2, f"{tmp_path / 'pr.txt'}:1: a printed rate that its counts do not give")


def test_e4_an_empty_report(tmp_path: Path) -> None:
    code, _, err = run(tmp_path, MAIN, [""])
    assert (code, err) == (2, f"{tmp_path / 'pr.txt'}: no line")


def test_e5_the_same_line_twice(tmp_path: Path) -> None:
    code, _, err = run(tmp_path, [*MAIN, MAIN[0]], MAIN)
    assert (code, err) == (2, f"{tmp_path / 'main.txt'}:6: IL_ID twice")


@pytest.mark.parametrize("argv", [[], ["one"], ["one", "two", "three"]])
def test_e6_not_two_arguments(argv: list[str]) -> None:
    err: list[str] = []
    assert check_scores.main(argv, {}, print, err.append) == 2
    assert err == [check_scores.USAGE]


def test_a1_a_report_with_a_byte_order_mark_and_crlf(tmp_path: Path) -> None:
    out: list[str] = []
    err: list[str] = []
    main = write(tmp_path / "main.txt", MAIN, bom=True, crlf=True)
    pr = write(tmp_path / "pr.txt", MAIN)
    assert check_scores.main([str(main), str(pr)], {}, out.append, err.append) == 0
    assert err == []


def test_a2_a_reason_in_hebrew_is_not_written(tmp_path: Path) -> None:
    body = "score-drop-accepted: IL_ID recall 0.900 0.880 אחיה: הצורה בת שתי האותיות בחוץ\n"
    code, out, err = run(tmp_path, MAIN, changed(0, type_line("IL_ID", 44, 0, 6)), body)
    assert code == 0
    assert "אחיה" not in out + err


def test_a3_person_and_its_group_are_two_lines(tmp_path: Path) -> None:
    pr = changed(3, group_line("PERSON:untitled", 29, 21))
    pr[1] = type_line("PERSON", 81, 10, 19)
    code, _, err = run(tmp_path, MAIN, pr)
    assert (code, err) == (1, "held-out drop: PERSON:untitled recall 0.600 -> 0.580")


def test_a4_a_quoted_body_line_accepts_nothing(tmp_path: Path) -> None:
    body = "> score-drop-accepted: IL_ID recall 0.900 0.880 a reason\n"
    code, _, err = run(tmp_path, MAIN, changed(0, type_line("IL_ID", 44, 0, 6)), body)
    assert (code, err) == (1, "held-out drop: IL_ID recall 0.900 -> 0.880")
