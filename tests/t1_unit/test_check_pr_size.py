"""Test matrix for scripts/check_pr_size.py: product files and changed product lines against PROCESS.md 6.3.

is_product. Equivalence classes:
  EC1  a file under ploni/ or ui/, at any depth                     product
  EC2  tests/, scripts/, docs/, experiments/, eval/, the root, a .md under ploni/   tests and
       fixtures are excluded by PROCESS.md 6.3; the rest is not product code: not product,
       but for a .md under ploni/, which is product (B4)
Boundaries:
  B1  "ploni" alone, "ploniX/a.py", "uix/a.py", "src/ploni/a.py"      not product
  B4  any file kind under ploni/ or ui/ (.py, .md, .json, .html)     product: the folder decides

measure. Equivalence classes (Achia, 2026-11-20: "Count every changed line (Recommended)"):
  EC3  rows of git's numstat: added and deleted per file            product files counted,
       lines = added + deleted summed over product files
  EC4  a binary file ("-" for both counts)                          a file, no lines, its path named
  EC5  only deletions                                                each deleted line counts
  EC6  no row                                                        (0, 0, no binary)
  EC12 a rewrite in place (as many lines added as deleted)           every line counts

judge. Boundaries (PROCESS.md 6.3; "over" a limit is more than it):
  B2  files 10, 11, 15, 16                                          nothing, warning, warning, problem
  B3  lines 400, 401, 800, 801                                     nothing, warning, warning, problem
  EC7  both over                                                     one line each

main. Equivalence classes:
  EC8  wrong arguments                                               usage, exit 2
  EC9  a PR over a hard limit                                        problem on the error stream, exit 1
  EC10 a PR over a soft limit only                                   a GitHub warning line on the
                                                                     output, exit 0
  EC11 a PR within the limits                                        nothing, exit 0
  EC13 a binary product file                                         a GitHub warning naming it,
                                                                     as its lines are not counted

Not applicable: the Hebrew axes and the document axes: the input is git's paths and counts. A
Hebrew file name is a path like any other (t4).
"""

import pytest

from scripts import check_pr_size as check


@pytest.mark.parametrize("path", ["ploni/a.py", "ploni/detect/b/c.py", "ui/server.py", "ui/static/app.js"])
def test_ec1_product(path: str) -> None:
    assert check.is_product(path) is True


@pytest.mark.parametrize(
    "path",
    ["tests/t1_unit/test_a.py", "scripts/x.py", "docs/STATUS.md", "experiments/e1/run.py", "eval/baselines.json", "README.md"],
)
def test_ec2_not_product(path: str) -> None:
    assert check.is_product(path) is False


@pytest.mark.parametrize("path", ["ploni", "ploniX/a.py", "uix/a.py", "src/ploni/a.py"])
def test_b1_names_that_only_look_like_the_folders(path: str) -> None:
    assert check.is_product(path) is False


@pytest.mark.parametrize("path", ["ploni/README.md", "ploni/data.json", "ui/index.html"])
def test_b4_any_file_kind_under_the_folders(path: str) -> None:
    assert check.is_product(path) is True


def test_ec3_files_and_changed_lines_of_product_code_only() -> None:
    rows = [("10", "2", "ploni/a.py"), ("5", "5", "ploni/b.py"), ("300", "0", "tests/t1_unit/test_a.py"), ("7", "1", "ui/x.py")]
    assert check.measure(rows) == (3, 30, [])


def test_ec4_a_binary_file() -> None:
    assert check.measure([("-", "-", "ploni/model.bin"), ("3", "0", "ploni/a.py")]) == (2, 3, ["ploni/model.bin"])


def test_ec5_only_deletions() -> None:
    assert check.measure([("0", "120", "ploni/a.py")]) == (1, 120, [])


def test_ec6_no_row() -> None:
    assert check.measure([]) == (0, 0, [])


def test_ec12_a_rewrite_in_place() -> None:
    assert check.measure([("1000", "1000", "ploni/a.py")]) == (1, 2000, [])


@pytest.mark.parametrize(
    ("files", "found"),
    [(10, ([], [])), (11, ([], ["11 product files changed, over the soft limit of 10"])),
     (15, ([], ["15 product files changed, over the soft limit of 10"])),
     (16, (["16 product files changed, over the hard limit of 15"], []))],
)
def test_b2_the_file_limits(files: int, found: tuple[list[str], list[str]]) -> None:
    assert check.judge(files, 0) == found


@pytest.mark.parametrize(
    ("net", "found"),
    [(400, ([], [])), (401, ([], ["401 changed product lines, over the soft limit of 400"])),
     (800, ([], ["800 changed product lines, over the soft limit of 400"])),
     (801, (["801 changed product lines, over the hard limit of 800"], []))],
)
def test_b3_the_line_limits(net: int, found: tuple[list[str], list[str]]) -> None:
    assert check.judge(0, net) == found


def test_ec7_both_over() -> None:
    assert check.judge(20, 1000) == (
        ["20 product files changed, over the hard limit of 15", "1000 changed product lines, over the hard limit of 800"],
        [],
    )


@pytest.mark.parametrize("argv", [[], ["main"], ["a", "b", "c"]])
def test_ec8_wrong_arguments(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main(argv) == 2
    assert capsys.readouterr().err == f"{check.USAGE}\n"


def test_ec9_over_a_hard_limit(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(check, "numstat", lambda base, head, cwd: [("900", "0", "ploni/a.py")])
    assert check.main(["base", "head"]) == 1
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "900 changed product lines, over the hard limit of 800\n")


def test_ec10_over_a_soft_limit_only(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(check, "numstat", lambda base, head, cwd: [("500", "0", "ploni/a.py")])
    assert check.main(["base", "head"]) == 0
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("::warning::500 changed product lines, over the soft limit of 400\n", "")


def test_ec13_a_binary_product_file(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(check, "numstat", lambda base, head, cwd: [("-", "-", "ploni/weights.bin")])
    assert check.main(["base", "head"]) == 0
    assert capsys.readouterr().out == "::warning::binary product file, its lines not counted: ploni/weights.bin\n"


def test_ec11_within_the_limits(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(check, "numstat", lambda base, head, cwd: [("20", "3", "ploni/a.py"), ("900", "0", "tests/t1_unit/test_a.py")])
    assert check.main(["base", "head"]) == 0
    assert capsys.readouterr() == ("", "")
