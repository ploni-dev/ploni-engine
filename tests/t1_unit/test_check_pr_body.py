"""Tests of scripts/check_pr_body.py and of the workflow that runs it on every PR.

Why: issue #21 (PROCESS.md section 12 item 8; PROMOTION.md section 5.2): a PR body must hold the
orientation block, with its goal, deliverable, gate and downstream-risk lines (the 5.2 row
"Orientation step performed"), and the `## Ponytail review` section, both present and not
empty. The check cannot tell a good review from a bad one; it stops a PR that has none.

Test matrix:

Equivalence classes:
  EC1  a filled body (the four orientation lines with values, a review with text)    no line
  EC2  no `## Orientation`                         one line: missing
  EC3  no `## Ponytail review`                     one line: missing
  EC4  sections with only labels ("Goal:"), HTML comments and blank lines    one line per
       empty orientation line, one for the review
  EC5  an orientation with one line of the four filled ("Goal: x")    one line for each other
  EC6  main: a good body / a bad one / no PR_BODY at all (GitHub gives no body for a PR opened
       with an empty description)    0 / 1, each line on the error stream / 1, both missing
  EC7  the repository's own template, unfilled    both sections are there, and all is empty
  EC8  the workflow: on pull_request (opened, edited, synchronize, reopened); actions pinned by
       a full commit hash; the body reaches the script only through the environment
  EC9  heading_of(), section(), labelled(), filled() each on its own; problems() without a template file
       raises FileNotFoundError

Boundaries:
  B1  an empty body                   both missing
  B2  a section that runs to the end of the body    its text is read
  B3  Windows line ends (GitHub sends CRLF from the web form) and spaces after the heading
                                      found
  B4  a deeper heading (`### Ponytail review`) or a longer one (`## Ponytail review notes`)
                                      not the section
  B5  a section ends at the next `## ` heading, not at a `### ` one
  B6  up to three spaces before a heading, at the start of a section and at its end    a
      heading (Markdown); four spaces are a code block, not a heading
  B7  blank lines are not text, whatever the template holds
  B8  an orientation line with spaces only after its colon    empty

Adversarial:
  A1  the heading inside a sentence ("see ## Ponytail review")    not the section
  A2  a section whose text is in Hebrew    filled
  A3  a body that tries to break out of the shell (`"; rm -rf ~; echo "`, `$(...)`, a backquote)
      reaches the script as plain text (EC8: no `${{` in a run line)
  A4  both headings inside a fenced code block    counted as headings (the Known limit, pinned)

Not applicable: the document axes; the Hebrew axes of the test-matrix skill other than A2, as
the input is the text of a PR body, judged only for headings and emptiness.

Known limits:
  - A heading inside a fenced code block counts as a heading (A4).
  - "Not empty" is mechanical: a placeholder such as "(the review comes here)" fills the review.
"""

from pathlib import Path

import pytest

from scripts import check_pr_body

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "pr-body.yml"
EMPTY_ORIENTATION = [
    "empty: ## Orientation, Goal:",
    "empty: ## Orientation, Deliverable:",
    "empty: ## Orientation, Gate:",
    "empty: ## Orientation, Downstream risk if wrong:",
]

GOOD = """## Orientation
Goal: a goal.
Deliverable: a file.
Gate: none.
Downstream risk if wrong: little.

## Phase, issue, branch
Phase 0

## Ponytail review
Looks good. Ship.

## Who merges
no
"""


def test_ec1_a_filled_body() -> None:
    assert check_pr_body.problems(GOOD) == []


def test_ec3_no_ponytail_review() -> None:
    assert check_pr_body.problems(GOOD.replace("## Ponytail review", "## Review")) == ["missing: ## Ponytail review"]


def test_ec4_labels_comments_and_blank_lines_only() -> None:
    body = "## Orientation\nGoal:\nDeliverable:  \n<!-- what it is for -->\nGate:\nDownstream risk if wrong:\n\n## Ponytail review\n<!--\nPaste it.\n-->\n"
    assert check_pr_body.problems(body) == [*EMPTY_ORIENTATION, "empty: ## Ponytail review"]


def test_ec5_one_orientation_line_of_four() -> None:
    body = "## Orientation\nGoal: x\nDeliverable:\nGate:\nDownstream risk if wrong:\n## Ponytail review\nCommit reviewed: abc\n"
    assert check_pr_body.problems(body) == EMPTY_ORIENTATION[1:]


def test_ec6_main(capsys: pytest.CaptureFixture[str]) -> None:
    assert check_pr_body.main({"PR_BODY": GOOD}) == 0
    assert capsys.readouterr().err == ""
    assert check_pr_body.main({"PR_BODY": "## Orientation\n"}) == 1
    assert capsys.readouterr().err.splitlines() == [*EMPTY_ORIENTATION, "missing: ## Ponytail review"]
    assert check_pr_body.main({}) == 1
    assert capsys.readouterr().err.splitlines() == ["missing: ## Orientation", "missing: ## Ponytail review"]


def test_ec7_the_template_unfilled() -> None:
    template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert check_pr_body.problems(template) == [*EMPTY_ORIENTATION, "empty: ## Ponytail review"]


def test_ec8_the_workflow() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pull_request:" in text and "types: [opened, edited, synchronize, reopened]" in text
    uses = [line.split("uses:")[1].strip() for line in text.splitlines() if "uses:" in line]
    assert uses and all(len(ref.split("@")[1].split()[0]) == 40 for ref in uses)
    assert "PR_BODY: ${{ github.event.pull_request.body }}" in text
    runs = [line for line in text.splitlines() if line.strip().startswith("- run:") or line.strip().startswith("run:")]
    assert runs and not any("${{" in line for line in runs)
    assert "scripts/check_pr_body.py" in text


def test_ec9_section_on_its_own() -> None:
    assert check_pr_body.section("## A\nx\n## B\ny\n", "## B") == "y\n"
    assert check_pr_body.section("## A\nx\n", "## B") is None


def test_ec9_heading_of_on_its_own() -> None:
    assert check_pr_body.heading_of("  ## Ponytail review \r") == "## Ponytail review"
    assert check_pr_body.heading_of("### x") is None
    assert check_pr_body.heading_of("    ## x") is None
    assert check_pr_body.heading_of("## ") == "## "


def test_ec9_labelled_on_its_own() -> None:
    assert check_pr_body.labelled("Goal: g\nGate:\n", "Goal")
    assert not check_pr_body.labelled("Goal: g\nGate:\n", "Gate")
    assert not check_pr_body.labelled("<!-- Gate: g -->\n", "Gate")
    assert not check_pr_body.labelled("<!--\nGate: g\n-->\n", "Gate")
    assert not check_pr_body.labelled("The Gate: g\n", "Gate")


def test_ec9_filled_on_its_own() -> None:
    assert check_pr_body.filled("x\n", {"y"})
    assert not check_pr_body.filled("y\n\n<!-- x -->\n", {"y"})


def test_ec9_no_template_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(check_pr_body, "TEMPLATE", tmp_path / "missing.md")
    with pytest.raises(FileNotFoundError):
        check_pr_body.problems(GOOD)


def test_b1_an_empty_body() -> None:
    assert check_pr_body.problems("") == ["missing: ## Orientation", "missing: ## Ponytail review"]


def test_b2_a_section_that_runs_to_the_end() -> None:
    body = "## Orientation\nGoal: g\nDeliverable: d\nGate: x\nDownstream risk if wrong: r\n## Ponytail review\nShip."
    assert check_pr_body.problems(body) == []


def test_b3_windows_line_ends_and_trailing_spaces() -> None:
    assert check_pr_body.problems(GOOD.replace("## Ponytail review", "## Ponytail review   ").replace("\n", "\r\n")) == []


def test_b4_a_deeper_or_longer_heading() -> None:
    assert check_pr_body.problems(GOOD.replace("## Ponytail review", "### Ponytail review")) == ["missing: ## Ponytail review"]
    assert check_pr_body.problems(GOOD.replace("## Ponytail review", "## Ponytail review notes")) == ["missing: ## Ponytail review"]


def test_b5_a_section_ends_at_the_next_heading_of_its_level() -> None:
    body = "## Orientation\n\n## Phase, issue, branch\nGoal: g\n## Ponytail review\n### Pass 1\nShip.\n"
    assert check_pr_body.problems(body) == EMPTY_ORIENTATION


def test_b6_spaces_before_a_heading() -> None:
    assert check_pr_body.problems(GOOD.replace("## Ponytail review", "   ## Ponytail review")) == []
    assert check_pr_body.problems(GOOD.replace("## Ponytail review", "    ## Ponytail review")) == ["missing: ## Ponytail review"]
    body = "## Orientation\n  ## Phase\nGoal: g\nDeliverable: d\nGate: x\nDownstream risk if wrong: r\n## Ponytail review\nCommit reviewed:\n   ## Who merges\nno\n"
    assert check_pr_body.problems(body) == [*EMPTY_ORIENTATION, "empty: ## Ponytail review"]


def test_b7_a_blank_line_is_not_text_with_any_template() -> None:
    template = "## Orientation\nGoal:\n## Ponytail review\nCommit reviewed:\n"
    assert check_pr_body.problems("## Orientation\n## Ponytail review\n\n   \n", template) == [*EMPTY_ORIENTATION, "empty: ## Ponytail review"]


def test_b8_spaces_only_after_the_colon() -> None:
    assert check_pr_body.problems(GOOD.replace("Gate: none.", "Gate:    ")) == ["empty: ## Orientation, Gate:"]


def test_a1_the_heading_inside_a_sentence() -> None:
    body = GOOD.replace("## Ponytail review", "see ## Ponytail review")
    assert check_pr_body.problems(body) == ["missing: ## Ponytail review"]


def test_a2_a_section_in_hebrew() -> None:
    body = "## Orientation\nGoal: לבדוק\nDeliverable: קובץ\nGate: אין\nDownstream risk if wrong: מעט\n## Ponytail review\nנראה טוב.\n"
    assert check_pr_body.problems(body) == []


def test_a3_a_body_that_tries_the_shell() -> None:
    body = GOOD + '\n"; rm -rf ~; echo "\n$(whoami) `id`\n'
    assert check_pr_body.main({"PR_BODY": body}) == 0


def test_a4_headings_inside_a_fenced_code_block() -> None:
    assert check_pr_body.problems("```\n" + GOOD + "```\n") == []
