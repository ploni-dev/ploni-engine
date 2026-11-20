"""Tests of scripts/check_waiver.py: a waiver cited in a PR body exists, is in force, and covers the PR.

Why: `PROMOTION.md` section 8.4: "A PR relying on a waiver carries `waiver: WAIVER-003` in its
body. CI asserts that the ID exists in `docs/WAIVERS.md`, that it has not expired, and that the
PR's changed paths fall inside the waiver's scope. An invented or expired ID fails the build."
Bad PR 8 of the closing test of Phase 0 (section 10) cites `waiver: WAIVER-999`. Issue #78.
How it runs and how expiry is read is Achia's answer of 2026-11-19, "New workflow file
(Recommended)", whose text said: "A waiver whose expiry is a date has expired after that date;
one whose expiry is a phase has expired once that phase's close is dated in docs/STATUS.md. A
PR that cites no waiver passes." What a citation is, is his answer of the same day, "Only
own-line citations count (Recommended)", described as: "A citation counts when it stands at
the start of a line (backquotes allowed), as a PR that relies on a waiver writes it. Quotes,
which sit in quoted blocks or mid-sentence, are not read. Risk: a PR that writes its citation
mid-sentence is not checked; the reviewer still reads the body."

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
  EC9  two citations, each on its own line, one good, one bad    one line, for the bad one
  EC10 a citation that is not a waiver ID (`waiver: none`)    a line: not a waiver ID

Equivalence classes (the parts):
  EC11 waivers(): entries under Active and Expired, with their fields; the format example
       above the first section is not a waiver, also in the repository's own docs/WAIVERS.md
  EC12 closed_phases(): a dated row is closed, an undated one is open; the repository's own
       Phases table has its Date column where the check reads it
  EC14 main(), with git and the clock stubbed: it judges by today(), not the machine's date
  EC16 `.github/workflows/waiver.yml`: its code lines, comments and blank lines left out,
       exactly as merged, the body in PR_BODY under the run step itself.
       Why: a later workflow-only PR holds no .py file, so the changed-paths check
       lets an edit through that switches this check off; the pin built from patterns let
       most such edits through (#166, measured: a checkout of another ref, a BASH_ENV, a
       second `- run :` step, a push trigger, more permissions). Not refused: a comment.
  EC13 covers(): an exact path; a folder ending in "/"; `*` within one folder; `**` across
       folders; several entries separated by commas, with spaces and backquotes

Boundaries:
  B1  an expiry date equal to today                  in force; the day after, expired
  B2  "Phase 3", "end of Phase 3", "3", "end of phase 3"    all read as phase 3
  B3  an expiry that is neither ("soon", empty)      a line: no readable expiry
  B4  a waiver with no scope line, or an empty one   a line: no scope
  B5  no changed path                                no scope line, only the other checks
  B6  `*` does not cross a "/": "ploni/*.py" does not cover "ploni/a/b.py"
  B7  "Waiver:" in another case, no space after the colon, spaces before it on the line,
      text after the ID                              still a citation
  B16 the ID alone in backquotes after the colon, with or without a space or a mark
                                                     read as the ID (an invented one is red)
  B17 the citation as a list item ("- ", "* ", "+ ", "1. ", "12) "), also nested (indented),
      or in bold or italics                          read: the start of a line, the stricter side
  B8  the same ID cited twice                        its lines once
  B9  a key written twice in one entry               the first counts
  B10 a `key: value` line after a blank line         not part of the entry before it
  B11 a numbered, dated row in another table of STATUS    does not close a phase
  B12 `WAIVER-003.`, `WAIVER-003x`, `xWAIVER-003`     not a waiver ID
  B13 a scope of commas and backquotes only          no scope
  B14 a waiver with no expiry line                   no readable expiry (section 8.5: every
                                                     waiver has one)
  B15 today is the date at UTC+3, Israel's summer offset: a date waiver never lives past
      Israel's midnight; in winter it ends an hour early, the stricter side
  EC2, EC3 also written in backquotes, as PROMOTION.md 8.4 and docs/WAIVERS.md write a
      citation: the backquote is not part of the ID

Error paths (main):
  E1  wrong argument count                           exit 2, a usage line
  E2  no PR_BODY                                     an empty body: exit 0, git not called
      (the module suite)

Adversarial:
  A1  an ID under both Active and Expired, in either order    expired: the stricter reading
  A2  a waiver entry inside a code fence under Active    read like any other
  A3  a scope entry "**" or "*"                       "**" covers everything, as Achia wrote
      it; "*" covers a root file only
  A4  a waiver the PR adds to docs/WAIVERS.md itself  not seen: the file is read from the
      base (the module suite)
  A5  a Hebrew path in the PR                        judged like any other path
  A6  Hebrew text after a citation, and a direction mark (U+200F, U+200E, U+061C) at the
      line's start or next to the ID                the mark is not part of the ID
  A7  the token in a quoted block ("> ", also "> - "), mid-sentence, after other text on the
      line, or with the ID on the next line          not a citation: no line

Not applicable: the document axes; the Hebrew axes of the test-matrix skill other than A5
and A6, as the inputs are a PR body judged for one token, a list of paths and two Markdown
files of the repository.

Known limits:
  - A citation written mid-sentence is not read (A7), by Achia's answer: the reviewer reads it.
"""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from scripts import check_waiver as check
from tests.workflow_lines import code_lines

# The code lines of waiver.yml as #128 merged them (code_lines()); any other line or one more
# changes how the check runs.
EXPECTED_WORKFLOW = [
    'name: waiver',
    'on:',
    '  pull_request:',
    '    types: [opened, edited, synchronize, reopened]',
    'permissions:',
    '  contents: read',
    'jobs:',
    '  waiver:',
    '    runs-on: ubuntu-24.04',
    '    timeout-minutes: 2',
    '    steps:',
    '      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1',
    '        with:',
    '          fetch-depth: 2',
    '      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0',
    '        with:',
    '          python-version: "3.13.5"',
    '      - run: python -m scripts.check_waiver HEAD^1 HEAD',
    '        env:',
    '          PR_BODY: ${{ github.event.pull_request.body }}',
]

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
    found = problems("waiver: WAIVER-003\nwaiver: WAIVER-999\n", ["ploni/resolve/a.py"])
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
    real = check.waivers((ROOT / "docs" / "WAIVERS.md").read_text(encoding="utf-8"))
    assert all(entry.get("scope") != "which files or paths" for entry in real.values())


def test_ec12_closed_phases() -> None:
    assert check.closed_phases(STATUS) == {0}
    # What stays true of the real file: its Phases table has the Date column where the check reads it.
    status = (ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8")
    header = next(line for line in status.splitlines() if line.startswith("| Phase |"))
    assert [cell.strip() for cell in header.strip().strip("|").split("|")][check.DATE_CELL] == "Date"


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


@pytest.mark.parametrize("body", ["Waiver: WAIVER-999", "WAIVER:WAIVER-999", "intro\n   waiver:  WAIVER-999 more text"])
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


def test_a1_expired_listed_before_active() -> None:
    text = "## Expired\n\nWAIVER-020\nscope: ploni/\nexpires: 2099-01-01\n\n## Active\n\nWAIVER-020\nscope: ploni/\nexpires: 2099-01-01\n"
    assert check.waivers(text)["WAIVER-020"]["section"] == "Expired"


def test_b9_a_key_twice_keeps_the_first() -> None:
    text = "## Active\n\nWAIVER-021\nscope: ploni/\nexpires: 2000-01-01\nexpires: 2099-01-01\n"
    assert check.waivers(text)["WAIVER-021"]["expires"] == "2000-01-01"


def test_b10_an_entry_ends_at_a_blank_line() -> None:
    text = "## Active\n\nWAIVER-022\nrule: r\n\nscope: everything/\nexpires: 2099-01-01\n"
    assert check.waivers(text)["WAIVER-022"] == {"section": "Active", "rule": "r"}


def test_b11_only_the_phases_table_closes_a_phase() -> None:
    other = "## Done\n\n| What | Where | PRs | Date |\n|---|---|---|---|\n| 2 things | x | y | 2026-11-19 |\n\n"
    assert check.closed_phases(other + STATUS) == {0}


@pytest.mark.parametrize("token", ["WAIVER-003.", "WAIVER-003x", "xWAIVER-003"])
def test_b12_an_id_with_more_around_it(token: str) -> None:
    assert problems(f"waiver: {token}", ["ploni/resolve/a.py"]) == [f"waiver: {token} is not a waiver ID"]


def test_b13_a_scope_of_commas_and_backquotes_only() -> None:
    text = "## Active\n\nWAIVER-023\nscope: , `` ,\nexpires: 2099-01-01\n"
    assert check.problems("waiver: WAIVER-023", ["ploni/a.py"], text, STATUS, TODAY) == ["WAIVER-023 has no scope"]


@pytest.mark.parametrize("body", ["`waiver: WAIVER-003`", "`waiver: WAIVER-003` (granted 2026-11-14)"])
def test_ec2_a_citation_in_backquotes(body: str) -> None:
    assert problems(body, ["ploni/resolve/a.py"]) == []


def test_ec3_an_invented_id_in_backquotes() -> None:
    assert problems("`waiver: WAIVER-999`", ["ploni/a.py"]) == ["WAIVER-999 is not in docs/WAIVERS.md"]


def test_b14_no_expiry_line() -> None:
    text = "## Active\n\nWAIVER-024\nscope: ploni/\n"
    assert check.problems("waiver: WAIVER-024", ["ploni/a.py"], text, STATUS, TODAY) == [
        "WAIVER-024 has no readable expiry: "
    ]


@pytest.mark.parametrize(
    ("now", "day"),
    [
        (datetime(2026, 11, 19, 20, 59, tzinfo=UTC), date(2026, 11, 19)),
        (datetime(2026, 11, 19, 21, 0, tzinfo=UTC), date(2026, 11, 20)),
        (datetime(2026, 7, 1, 23, 30, tzinfo=UTC), date(2026, 7, 2)),
    ],
)
def test_b15_today_is_the_date_at_utc_plus_3(now: datetime, day: date) -> None:
    assert check.today(now) == day


def test_ec14_main_judges_by_today_at_utc_plus_3(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(check, "changed", lambda base, head, cwd: ["ploni/a.py"])
    monkeypatch.setattr(check, "shown", lambda revision, path: WAIVERS if path == check.WAIVERS_FILE else STATUS)
    monkeypatch.setattr(check, "today", lambda: date(2026, 12, 1))
    assert check.main(["HEAD^1", "HEAD"], {"PR_BODY": "waiver: WAIVER-005"}) == 1
    assert capsys.readouterr().err.splitlines() == ["WAIVER-005 has expired: 2026-11-18"]
    monkeypatch.setattr(check, "today", lambda: date(2026, 11, 18))
    assert check.main(["HEAD^1", "HEAD"], {"PR_BODY": "waiver: WAIVER-005"}) == 0


@pytest.mark.parametrize("mark", ["‏", "‎", "؜"])
def test_a6_a_direction_mark_next_to_the_id(mark: str) -> None:
    assert problems(f"{mark}waiver: WAIVER-999{mark} לפי ההחלטה", ["ploni/a.py"]) == ["WAIVER-999 is not in docs/WAIVERS.md"]
    assert problems(f"waiver: {mark}WAIVER-999{mark}", ["ploni/a.py"]) == ["WAIVER-999 is not in docs/WAIVERS.md"]


@pytest.mark.parametrize(
    "body",
    [
        "> waiver: WAIVER-999",
        "> > waiver: WAIVER-999",
        "PROMOTION.md says a PR carries `waiver: WAIVER-999` in its body.",
        "see waiver: WAIVER-999",
        "בקשה waiver: WAIVER-999",
        "waiver:\nWAIVER-999",
        "> - waiver: WAIVER-999",
    ],
)
def test_a7_a_quote_or_a_mention_is_not_a_citation(body: str) -> None:
    assert problems(body, ["ploni/a.py"]) == []


@pytest.mark.parametrize("body", ["waiver: `WAIVER-999`", "waiver:`WAIVER-999`", "waiver: ‏`WAIVER-999`", "`waiver:` `WAIVER-999`"])
def test_b16_the_id_alone_in_backquotes(body: str) -> None:
    assert problems(body, ["ploni/a.py"]) == ["WAIVER-999 is not in docs/WAIVERS.md"]


@pytest.mark.parametrize(
    "body",
    ["- waiver: WAIVER-999", "* waiver: WAIVER-999", "+ `waiver: WAIVER-999`", "1. waiver: WAIVER-999", "12) waiver: WAIVER-999", "**waiver:** WAIVER-999", "- **waiver: WAIVER-999**", "_waiver: WAIVER-999_", "‏- waiver: WAIVER-999", "  - waiver: WAIVER-999", "\t1. waiver: WAIVER-999"],
)
def test_b17_a_list_item_or_emphasis(body: str) -> None:
    assert problems(body, ["ploni/a.py"]) == ["WAIVER-999 is not in docs/WAIVERS.md"]


def test_ec16_the_workflow() -> None:
    assert code_lines(ROOT / ".github" / "workflows" / "waiver.yml") == EXPECTED_WORKFLOW


def test_a5_a_hebrew_path() -> None:
    assert problems("waiver: WAIVER-003", ["ploni/resolve/שם.py"]) == []
    assert problems("waiver: WAIVER-003", ["ploni/שם.py"]) == ["WAIVER-003 does not cover ploni/שם.py"]
