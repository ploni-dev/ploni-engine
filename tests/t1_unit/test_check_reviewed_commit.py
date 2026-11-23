"""Tests of scripts/check_reviewed_commit.py: how it reads the commit a PR body's review names.

Why: `PROCESS.md` section 12 item 8: "A check that the commit named in the PR's Ponytail
section is the PR's last commit, or that every commit after it is a merge of `main` that leaves
the branch's own diff unchanged." Issue #176, one of the four robots Achia chose on 2026-11-20
("Yes, all four (Recommended)"), strict by his choice of 2026-11-22 ("Gate reads newest run
(Recommended)": "red until a review naming the last commit is pasted"). This file holds the
reading of the body, which needs no git; the history is judged in the module suite,
tests/t4_integration/test_check_reviewed_commit.py, against real repositories.

Test matrix:

Equivalence classes (named):
  EC1  the shape of the merged PR bodies: "Commit reviewed: `<40 hex>`, the head, in pass 3:
       Ship." (#197)                                                    the hash
  EC2  the line with more after the hash: "..., which found nothing open: Ship. Reviewed by:
       ..." (#183)                                                      the hash
  EC3  the line indented by spaces                                      the hash
  EC4  the body with CRLF line ends, as a body edited on GitHub has     the hash
  EC5  quoted review reports in the section, "> Commit reviewed: ..." and
       "> **Commit reviewed:** ...", before and after the line (#154, #160)    the line's hash:
       a quote is a reviewer's report, not the PR's own line
  EC6  the line only in another section                                 missing line
  EC7  the line inside an HTML comment, one line or several             missing line
  EC8  the section followed by another section, and the section last in the body    the hash
  EC9  main: a body that names a commit reaches the history (stubbed here, the history is
       the module suite's); a body that refuses never calls git        exit 1, one line

Boundaries:
  B1  an empty body, and no PR_BODY at all                              missing section
  B2  the section with nothing under it                                 missing line
  B3  the template's line as it is: "Commit reviewed:" with nothing after    not pasted
  B4  39 and 41 hex characters in the backticks                         not pasted
  B5  two lines that start with the label                               one line naming two
  B6  three such lines                                                  one line naming three

Error paths:
  E1  main with no argument, one, three                                 exit 2, a usage line

Adversarial:
  A1  a short hash, `eb204fb` (#117, #152)                              not pasted
  A2  the full hash without backticks (#139's quoted form, unquoted)    not pasted
  A3  the hash in upper case                                            not pasted
  A4  40 characters with one that is not hex (g)                        not pasted
  A5  two lines naming the same commit, one short and one full (#152)   refused: two lines
       (Claude's choice: one line only; it only narrows)
  A6  "**Commit reviewed:** `<hash>`", "- Commit reviewed: `<hash>`", "commit reviewed:
       `<hash>`"                                                        missing line: not the
       label at the start of a line, in its case
  A7  two spaces, or none, between the colon and the backtick          not pasted (the form
       of the PR bodies only; it only narrows)
  A8  "### Ponytail review" and "## Ponytail reviewer" headings         missing section
  A9  Hebrew after the hash, and an RTL mark before the label           the hash; missing line
       (the mark is not stripped, so the line does not start with the label)

Not applicable: the document axes, and the Hebrew axes other than A9: the body is read for one
line of fixed ASCII text.
"""

from collections.abc import Mapping
from pathlib import Path

import pytest

from scripts import check_reviewed_commit as check

SHA = "eb204fb480c917394e2923d54d9736840bfebbcc"
OTHER = "d1141580eddda31e023b8db44d79b5302cb6097c"
MISSING_SECTION = "missing: ## Ponytail review"
MISSING_LINE = 'missing: a line that starts with "Commit reviewed:" in ## Ponytail review'
NOT_PASTED = 'not pasted: the "Commit reviewed:" line of ## Ponytail review names no full 40-character hash in backticks'


def body(*review: str, before: str = "## Orientation\nGoal: x\n", after: str = "\n## Who merges\nx\n") -> str:
    """Return a PR body whose Ponytail review section holds the given lines."""
    return before + "\n## Ponytail review\n" + "\n".join(review) + after


def many(count: int) -> str:
    """Return the refusal of a section with `count` lines that start with the label."""
    return f'{count} lines start with "Commit reviewed:" in ## Ponytail review; keep one, the one that names the last commit'


def test_ec1_the_shape_of_197() -> None:
    assert check.named(body(f"Commit reviewed: `{SHA}`, the head, in pass 3: Ship.")) == (SHA, "")


def test_ec2_more_after_the_hash() -> None:
    line = f"Commit reviewed: `{SHA}`, the head, in pass 5, which found nothing open: Ship. Reviewed by: a subagent."
    assert check.named(body(line)) == (SHA, "")


def test_ec3_indented() -> None:
    assert check.named(body(f"   Commit reviewed: `{SHA}`")) == (SHA, "")


def test_ec4_crlf() -> None:
    text = body("Reviewed by: x", f"Commit reviewed: `{SHA}`, the head.", "Findings: none").replace("\n", "\r\n")
    assert check.named(text) == (SHA, "")


def test_ec5_quoted_reports_do_not_count() -> None:
    lines = (
        f"> Commit reviewed: `{OTHER}` on the branch.",
        f"Commit reviewed: `{SHA}`, the head, in pass 2.",
        f"> **Commit reviewed:** {OTHER}, the PR's head per gh pr view.",
    )
    assert check.named(body(*lines)) == (SHA, "")


def test_ec6_only_in_another_section() -> None:
    text = body("Reviewed by: x", after=f"\n## Who merges\nCommit reviewed: `{SHA}`\n")
    assert check.named(text) == ("", MISSING_LINE)


@pytest.mark.parametrize(
    "lines",
    [
        (f"<!-- Commit reviewed: `{SHA}` -->",),
        ("<!-- the review comes here", f"Commit reviewed: `{SHA}`", "-->"),
    ],
)
def test_ec7_inside_a_comment(lines: tuple[str, ...]) -> None:
    assert check.named(body(*lines)) == ("", MISSING_LINE)


@pytest.mark.parametrize("after", ["\n## Who merges\nx\n", "", "\n"])
def test_ec8_followed_or_last(after: str) -> None:
    assert check.named(body(f"Commit reviewed: `{SHA}`", after=after)) == (SHA, "")


def test_ec9_main_reaches_the_history(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    seen = []

    def history(sha: str, base: str, head: str, cwd: Path) -> str:
        seen.append((sha, base, head))
        return "the history refuses"

    monkeypatch.setattr(check, "history_problem", history)
    assert check.main(["base", "head"], {"PR_BODY": body(f"Commit reviewed: `{SHA}`")}) == 1
    assert seen == [(SHA, "base", "head")]
    assert capsys.readouterr() == ("", "the history refuses\n")
    monkeypatch.setattr(check, "history_problem", lambda *_: "")
    assert check.main(["base", "head"], {"PR_BODY": body(f"Commit reviewed: `{SHA}`")}) == 0
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("environ", [{}, {"PR_BODY": ""}, {"PR_BODY": body("Commit reviewed:")}])
def test_ec9_a_refused_body_calls_no_git(
    environ: Mapping[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def history(*_: object) -> str:
        raise AssertionError("git was called")

    monkeypatch.setattr(check, "history_problem", history)
    assert check.main(["base", "head"], environ) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert len(err.splitlines()) == 1


@pytest.mark.parametrize("text", ["", "\n", "## Orientation\nGoal: x\n"])
def test_b1_no_section(text: str) -> None:
    assert check.named(text) == ("", MISSING_SECTION)


def test_b1_no_pr_body(capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main(["base", "head"], {}) == 1
    assert capsys.readouterr() == ("", MISSING_SECTION + "\n")


def test_b2_an_empty_section() -> None:
    assert check.named(body()) == ("", MISSING_LINE)


@pytest.mark.parametrize("line", ["Commit reviewed:", "Commit reviewed: ", "Commit reviewed: ``"])
def test_b3_the_template_line(line: str) -> None:
    assert check.named(body(line)) == ("", NOT_PASTED)


@pytest.mark.parametrize("sha", [SHA[:39], SHA + "a"])
def test_b4_39_and_41(sha: str) -> None:
    assert check.named(body(f"Commit reviewed: `{sha}`")) == ("", NOT_PASTED)


def test_b5_two_lines() -> None:
    assert check.named(body(f"Commit reviewed: `{SHA}`", f"Commit reviewed: `{OTHER}`")) == ("", many(2))


def test_b6_three_lines() -> None:
    assert check.named(body("Commit reviewed:", f"Commit reviewed: `{SHA}`", "Commit reviewed: x")) == ("", many(3))


@pytest.mark.parametrize("argv", [[], ["base"], ["a", "b", "c"]])
def test_e1_main_needs_two_revisions(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main(argv, {"PR_BODY": body(f"Commit reviewed: `{SHA}`")}) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("usage: ")


def test_a1_a_short_hash() -> None:
    assert check.named(body("Commit reviewed: `eb204fb`, the head.")) == ("", NOT_PASTED)


def test_a2_no_backticks() -> None:
    assert check.named(body(f"Commit reviewed: {SHA}, the head.")) == ("", NOT_PASTED)


def test_a3_upper_case() -> None:
    assert check.named(body(f"Commit reviewed: `{SHA.upper()}`")) == ("", NOT_PASTED)


def test_a4_not_hex() -> None:
    assert check.named(body(f"Commit reviewed: `{SHA[:39]}g`")) == ("", NOT_PASTED)


def test_a5_the_same_commit_short_and_full() -> None:
    assert check.named(body("Commit reviewed: `eb204fb`, the head.", f"Commit reviewed: `{SHA}`, the head.")) == ("", many(2))


@pytest.mark.parametrize(
    "line", [f"**Commit reviewed:** `{SHA}`", f"- Commit reviewed: `{SHA}`", f"commit reviewed: `{SHA}`"]
)
def test_a6_not_the_label(line: str) -> None:
    assert check.named(body(line)) == ("", MISSING_LINE)


@pytest.mark.parametrize("line", [f"Commit reviewed:  `{SHA}`", f"Commit reviewed:`{SHA}`"])
def test_a7_other_spacing(line: str) -> None:
    assert check.named(body(line)) == ("", NOT_PASTED)


@pytest.mark.parametrize("heading", ["### Ponytail review", "## Ponytail reviewer", "Ponytail review"])
def test_a8_not_the_heading(heading: str) -> None:
    assert check.named(f"## Orientation\n{heading}\nCommit reviewed: `{SHA}`\n") == ("", MISSING_SECTION)


def test_a9_hebrew_after_the_hash() -> None:
    assert check.named(body(f"Commit reviewed: `{SHA}`, הראש, סבב 3: לשלוח.")) == (SHA, "")


def test_a9_an_rtl_mark_before_the_label() -> None:
    assert check.named(body(f"‏Commit reviewed: `{SHA}`")) == ("", MISSING_LINE)
