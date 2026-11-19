"""Tests of scripts/check_waiver.py: a waiver cited in a PR body exists, is in force, and covers the PR.

Why: `PROMOTION.md` section 8.4: "A PR relying on a waiver carries `waiver: WAIVER-003` in its
body. CI asserts that the ID exists in `docs/WAIVERS.md`, that it has not expired, and that the
PR's changed paths fall inside the waiver's scope. An invented or expired ID fails the build."
Bad PR 8 of the closing test of Phase 0 (section 10) cites `waiver: WAIVER-999`. Issue #78.
How it runs and how expiry is read is Achia's answer of 2026-11-19, "New workflow file
(Recommended)", whose text said: "A waiver whose expiry is a date has expired after that date;
one whose expiry is a phase has expired once that phase's close is dated in docs/STATUS.md. A
PR that cites no waiver passes."

Test matrix:

Equivalence classes (problems):
  EC1  no citation                                   no line, whatever the paths
  EC2  an active waiver, in force, covering every path    no line
  EC3  an ID not in the file (WAIVER-999)            "WAIVER-999 is not in docs/WAIVERS.md"
  EC4  an ID listed under `## Expired`               a line: under Expired
  EC5  an active waiver past its date                a line: expired, with the expiry
  EC6  an active waiver whose phase is closed in the STATUS table    a line: expired
  EC7  an active waiver whose phase is not closed    no line
  EC8  a changed path outside the scope              one line per such path
  EC9  two citations, one good, one bad              one line, for the bad one
  EC10 a citation that is not a waiver ID (`waiver: none`)    a line: not a waiver ID

Equivalence classes (the parts):
  EC11 waivers(): entries under Active and Expired, with their fields; the format example
       above the first section is not a waiver; the repository's own docs/WAIVERS.md has none
  EC12 closed_phases(): a dated row is closed, an undated one is open; the repository's own
       STATUS table has phase 0 open
  EC13 covers(): an exact path; a folder ending in "/"; `*` within one folder; `**` across
       folders; several entries separated by commas, with spaces and backquotes

Boundaries:
  B1  an expiry date equal to today                  in force; the day after, expired
  B2  "Phase 3", "end of Phase 3", "3", "end of phase 3"    all read as phase 3
  B3  an expiry that is neither ("soon", empty)      a line: no readable expiry
  B4  a waiver with no scope line, or an empty one   a line: no scope
  B5  no changed path                                no scope line, only the other checks
  B6  `*` does not cross a "/": "ploni/*.py" does not cover "ploni/a/b.py"
  B7  "Waiver:" in another case, and no space after the colon    still a citation
  B8  the same ID cited twice                        its lines once

Error paths (main):
  E1  wrong argument count                           exit 2, a usage line
  E2  no PR_BODY                                     an empty body: exit 0, git not called
      (the module suite)

Adversarial:
  A1  an ID under both Active and Expired            expired: the stricter reading
  A2  a waiver entry inside a code fence under Active    read like any other
  A3  a scope entry "**" or "*"                       "**" covers everything, as Achia wrote
      it; "*" covers a root file only
  A4  a waiver the PR adds to docs/WAIVERS.md itself  not seen: the file is read from the
      base (the module suite)
  A5  a Hebrew path in the PR                        judged like any other path

Not applicable: the document axes; the Hebrew axes of the test-matrix skill other than A5, as
the inputs are a PR body judged for one token, a list of paths and two Markdown files of the
repository.

Known limits:
  - A citation is found anywhere in the body, quotes and code spans included: a PR body that
    talks about the check must not write the token itself.
"""

from datetime import date
from pathlib import Path

import pytest

from scripts import check_waiver as check

ROOT = Path(__file__).resolve().parents[2]
TODAY = date(2026, 11, 19)

WAIVERS = """# Waivers

Format:

```
WAIVER-001
rule:    the rule or gate being waived
scope:   which files or paths
expires: a phase number or a date
```

## Active

WAIVER-003
rule:    test-first commit order
scope:   tests/t2_property/test_projection.py, ploni/resolve/
reason:  hypothesis strategy had to exist before the invariant could be stated
granted: 2026-11-14
expires: end of Phase 3
issue:   #41

WAIVER-004
rule:    a size limit
scope:   ploni/*.py
granted: 2026-11-01
expires: 2026-11-19

WAIVER-005
rule:    a size limit
scope:   ploni/
expires: 2026-11-18

WAIVER-006
rule:    no scope
expires: 2026-12-31

WAIVER-007
rule:    an unreadable expiry
scope:   ploni/
expires: soon

WAIVER-008
rule:    a closed phase
scope:   ploni/
expires: Phase 0

```
WAIVER-009
rule:    inside a fence
scope:   docs/
expires: 2026-12-31
```

## Expired

WAIVER-002
rule:    an old one
scope:   ploni/
expires: 2026-11-01

WAIVER-008
rule:    listed twice
scope:   ploni/
expires: 2026-12-31
"""

STATUS = """# Status

## Phases

| Phase | Gate | Measured | Date | Exit demo shown |
|---|---|---|---|---|
| 0 Foundation and safety | selftest | all green | 2026-11-20 | yes |
| 1 Deterministic detectors | detectors | | | |
| 3 Hebrew NER | ner | started | | |
"""


def problems(body: str, paths: list[str], today: date = TODAY) -> list[str]:
    """Run problems() on the fixture files above."""
    return check.problems(body, paths, WAIVERS, STATUS, today)


def test_ec1_no_citation() -> None:
    assert problems("## Orientation\nGoal: x\n", ["ploni/a.py", "eval/baselines.json"]) == []


def test_ec2_a_waiver_in_force_covering_every_path() -> None:
    paths = ["tests/t2_property/test_projection.py", "ploni/resolve/a.py", "ploni/resolve/b/c.py"]
    assert problems("waiver: WAIVER-003\n", paths) == []


def test_ec3_an_id_not_in_the_file() -> None:
    assert problems("waiver: WAIVER-999", ["ploni/a.py"]) == ["WAIVER-999 is not in docs/WAIVERS.md"]


def test_ec4_an_id_under_expired() -> None:
    assert problems("waiver: WAIVER-002", ["ploni/a.py"]) == ["WAIVER-002 is under Expired in docs/WAIVERS.md"]


def test_ec5_past_its_date() -> None:
    assert problems("waiver: WAIVER-005", ["ploni/a.py"]) == ["WAIVER-005 has expired: 2026-11-18"]


def test_ec6_its_phase_is_closed() -> None:
    status = STATUS.replace("| 3 Hebrew NER | ner | started | |", "| 3 Hebrew NER | ner | started | 2026-11-19 |")
    found = check.problems("waiver: WAIVER-003", ["ploni/resolve/a.py"], WAIVERS, status, TODAY)
    assert found == ["WAIVER-003 has expired: end of Phase 3"]


def test_ec7_its_phase_is_open() -> None:
    assert problems("waiver: WAIVER-003", ["ploni/resolve/a.py"]) == []


def test_ec8_a_path_outside_the_scope() -> None:
    found = problems("waiver: WAIVER-003", ["ploni/resolve/a.py", "ploni/x.py", "docs/a.md"])
    assert found == ["WAIVER-003 does not cover docs/a.md", "WAIVER-003 does not cover ploni/x.py"]


def test_ec9_one_good_one_bad() -> None:
    found = problems("waiver: WAIVER-003\nand waiver: WAIVER-999\n", ["ploni/resolve/a.py"])
    assert found == ["WAIVER-999 is not in docs/WAIVERS.md"]


def test_ec10_not_a_waiver_id() -> None:
    assert problems("waiver: none", ["ploni/a.py"]) == ["waiver: none is not a waiver ID"]


def test_ec11_waivers() -> None:
    found = check.waivers(WAIVERS)
    assert sorted(found) == [f"WAIVER-00{n}" for n in range(2, 10)]
    assert "WAIVER-001" not in found
    assert found["WAIVER-003"]["section"] == "Active"
    assert found["WAIVER-003"]["scope"] == "tests/t2_property/test_projection.py, ploni/resolve/"
    assert found["WAIVER-003"]["expires"] == "end of Phase 3"
    assert found["WAIVER-002"]["section"] == "Expired"
    assert check.waivers((ROOT / "docs" / "WAIVERS.md").read_text(encoding="utf-8")) == {}


def test_ec12_closed_phases() -> None:
    assert check.closed_phases(STATUS) == {0}
    assert 0 not in check.closed_phases((ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("scope", "path", "covered"),
    [
        ("ploni/a.py", "ploni/a.py", True),
        ("ploni/a.py", "ploni/a.pyc", False),
        ("ploni/", "ploni/a/b.py", True),
        ("ploni/", "ploni_x/a.py", False),
        ("ploni/*.py", "ploni/a.py", True),
        ("ploni/**/*.py", "ploni/a/b/c.py", True),
        ("docs/a.md, `ploni/a.py`", "ploni/a.py", True),
        ("docs/a.md ,ploni/a.py", "ploni/b.py", False),
    ],
)
def test_ec13_covers(scope: str, path: str, covered: bool) -> None:
    assert check.covers(scope, path) is covered


def test_b1_an_expiry_on_today() -> None:
    assert problems("waiver: WAIVER-004", ["ploni/a.py"]) == []
    assert problems("waiver: WAIVER-004", ["ploni/a.py"], date(2026, 11, 20)) == [
        "WAIVER-004 has expired: 2026-11-19"
    ]


@pytest.mark.parametrize("expires", ["Phase 3", "end of Phase 3", "3", "end of phase 3", "  Phase 3  "])
def test_b2_phase_spellings(expires: str) -> None:
    assert check.expired(expires, TODAY, {3}) is True
    assert check.expired(expires, TODAY, {0}) is False


@pytest.mark.parametrize("expires", ["soon", "", "Phase three", "2026-13-01"])
def test_b3_an_unreadable_expiry(expires: str) -> None:
    with pytest.raises(ValueError, match="expiry"):
        check.expired(expires, TODAY, set())


def test_b3_an_unreadable_expiry_in_problems() -> None:
    assert problems("waiver: WAIVER-007", ["ploni/a.py"]) == ["WAIVER-007 has no readable expiry: soon"]


def test_b4_no_scope() -> None:
    assert problems("waiver: WAIVER-006", ["ploni/a.py"]) == ["WAIVER-006 has no scope"]


def test_b5_no_changed_path() -> None:
    assert problems("waiver: WAIVER-006", []) == ["WAIVER-006 has no scope"]
    assert problems("waiver: WAIVER-003", []) == []


def test_b6_a_star_does_not_cross_a_folder() -> None:
    assert problems("waiver: WAIVER-004", ["ploni/a/b.py"]) == ["WAIVER-004 does not cover ploni/a/b.py"]


@pytest.mark.parametrize("body", ["Waiver: WAIVER-999", "WAIVER:WAIVER-999", "text waiver:  WAIVER-999 more"])
def test_b7_case_and_spacing(body: str) -> None:
    assert problems(body, ["ploni/a.py"]) == ["WAIVER-999 is not in docs/WAIVERS.md"]


def test_b8_the_same_id_twice() -> None:
    assert problems("waiver: WAIVER-999\nwaiver: WAIVER-999", ["ploni/a.py"]) == [
        "WAIVER-999 is not in docs/WAIVERS.md"
    ]


@pytest.mark.parametrize("argv", [[], ["HEAD^1"], ["a", "b", "c"]])
def test_e1_main_needs_two_revisions(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main(argv, {"PR_BODY": "waiver: WAIVER-999"}) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("usage: ")


def test_a1_listed_under_both() -> None:
    assert problems("waiver: WAIVER-008", ["ploni/a.py"]) == ["WAIVER-008 is under Expired in docs/WAIVERS.md"]


def test_a2_an_entry_inside_a_fence() -> None:
    assert problems("waiver: WAIVER-009", ["docs/a.md"]) == []


@pytest.mark.parametrize(("scope", "path", "covered"), [("**", "a/b/c.py", True), ("*", "a.py", True), ("*", "a/b.py", False)])
def test_a3_wide_scopes(scope: str, path: str, covered: bool) -> None:
    assert check.covers(scope, path) is covered


def test_a5_a_hebrew_path() -> None:
    assert problems("waiver: WAIVER-003", ["ploni/resolve/שם.py"]) == []
    assert problems("waiver: WAIVER-003", ["ploni/שם.py"]) == ["WAIVER-003 does not cover ploni/שם.py"]
