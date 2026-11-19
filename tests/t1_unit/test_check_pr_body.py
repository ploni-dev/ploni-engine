"""Tests of scripts/check_pr_body.py and of the workflow that runs it on every PR.

Why: issue #21 (PROCESS.md section 12 item 8; PROMOTION.md section 5.2): a PR body must hold the
orientation block and the `## Ponytail review` section, both present and not empty. The check
cannot tell a good review from a bad one; it stops a PR that has none.

Test matrix:

Equivalence classes:
  EC1  a filled body (both sections with text)    no line
  EC2  no `## Orientation`                         one line: missing
  EC3  no `## Ponytail review`                     one line: missing
  EC4  a section with only labels ("Goal:"), HTML comments and blank lines    one line: empty
  EC5  a section with one label that has a value ("Goal: x")    filled
  EC6  main: a good body / a bad one / no PR_BODY at all (GitHub gives no body for a PR opened
       with an empty description)    0 / 1, each line on the error stream / 1, both missing
  EC7  the repository's own template, unfilled    both sections are there, and both are empty
  EC8  the workflow: on pull_request (opened, edited, synchronize, reopened); actions pinned by
       a full commit hash; the body reaches the script only through the environment

Boundaries:
  B1  an empty body                   both missing
  B2  a section that runs to the end of the body    its text is read
  B3  Windows line ends (GitHub sends CRLF from the web form) and spaces after the heading
                                      found
  B4  a deeper heading (`### Ponytail review`) or a longer one (`## Ponytail review notes`)
                                      not the section

Adversarial:
  A1  the heading inside a sentence ("see ## Ponytail review")    not the section
  A2  a section whose text is in Hebrew    filled
  A3  a body that tries to break out of the shell (`"; rm -rf ~; echo "`, `$(...)`, a backquote)
      reaches the script as plain text (EC8: no `${{` in a run line)

Not applicable: the document axes; the Hebrew axes of the test-matrix skill other than A2, as
the input is the text of a PR body, judged only for headings and emptiness.

Known limits:
  - A heading inside a fenced code block counts as a heading.
  - "Not empty" is mechanical: a placeholder such as "(the review comes here)" fills a section.
"""

from pathlib import Path

import pytest

from scripts import check_pr_body

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "pr-body.yml"

GOOD = """## Orientation
Goal: a goal.
Deliverable: a file.

## Phase, issue, branch
Phase 0

## Ponytail review
Looks good. Ship.

## Who merges
no
"""


def test_ec1_a_filled_body() -> None:
    assert check_pr_body.problems(GOOD) == []


def test_ec2_no_orientation() -> None:
    assert check_pr_body.problems(GOOD.replace("## Orientation", "## Overview")) == ["missing: ## Orientation"]


def test_ec3_no_ponytail_review() -> None:
    assert check_pr_body.problems(GOOD.replace("## Ponytail review", "## Review")) == ["missing: ## Ponytail review"]


def test_ec4_labels_comments_and_blank_lines_only() -> None:
    body = "## Orientation\nGoal:\nDeliverable:  \n<!-- what it is for -->\n\n## Ponytail review\n<!--\nPaste it.\n-->\n"
    assert check_pr_body.problems(body) == ["empty: ## Orientation", "empty: ## Ponytail review"]


def test_ec5_one_label_with_a_value() -> None:
    body = "## Orientation\nGoal: x\nDeliverable:\n## Ponytail review\nCommit reviewed: abc\n"
    assert check_pr_body.problems(body) == []


def test_ec6_main(capsys: pytest.CaptureFixture[str]) -> None:
    assert check_pr_body.main({"PR_BODY": GOOD}) == 0
    assert capsys.readouterr().err == ""
    assert check_pr_body.main({"PR_BODY": "## Orientation\n"}) == 1
    assert capsys.readouterr().err.splitlines() == ["empty: ## Orientation", "missing: ## Ponytail review"]
    assert check_pr_body.main({}) == 1
    assert capsys.readouterr().err.splitlines() == ["missing: ## Orientation", "missing: ## Ponytail review"]


def test_ec7_the_template_unfilled() -> None:
    template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert check_pr_body.problems(template) == ["empty: ## Orientation", "empty: ## Ponytail review"]


def test_ec8_the_workflow() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pull_request:" in text and "types: [opened, edited, synchronize, reopened]" in text
    uses = [line.split("uses:")[1].strip() for line in text.splitlines() if "uses:" in line]
    assert uses and all(len(ref.split("@")[1].split()[0]) == 40 for ref in uses)
    assert "PR_BODY: ${{ github.event.pull_request.body }}" in text
    runs = [line for line in text.splitlines() if line.strip().startswith("- run:") or line.strip().startswith("run:")]
    assert runs and not any("${{" in line for line in runs)
    assert "scripts/check_pr_body.py" in text


def test_b1_an_empty_body() -> None:
    assert check_pr_body.problems("") == ["missing: ## Orientation", "missing: ## Ponytail review"]


def test_b2_a_section_that_runs_to_the_end() -> None:
    assert check_pr_body.problems("## Orientation\nGoal: g\n## Ponytail review\nShip.") == []


def test_b3_windows_line_ends_and_trailing_spaces() -> None:
    assert check_pr_body.problems(GOOD.replace("## Ponytail review", "## Ponytail review   ").replace("\n", "\r\n")) == []


def test_b4_a_deeper_or_longer_heading() -> None:
    assert check_pr_body.problems(GOOD.replace("## Ponytail review", "### Ponytail review")) == ["missing: ## Ponytail review"]
    assert check_pr_body.problems(GOOD.replace("## Ponytail review", "## Ponytail review notes")) == ["missing: ## Ponytail review"]


def test_a1_the_heading_inside_a_sentence() -> None:
    body = "## Orientation\nGoal: see ## Ponytail review below\n"
    assert check_pr_body.problems(body) == ["missing: ## Ponytail review"]


def test_a2_a_section_in_hebrew() -> None:
    assert check_pr_body.problems("## Orientation\nמטרה: לבדוק\n## Ponytail review\nנראה טוב.\n") == []


def test_a3_a_body_that_tries_the_shell() -> None:
    body = GOOD + '\n"; rm -rf ~; echo "\n$(whoami) `id`\n'
    assert check_pr_body.main({"PR_BODY": body}) == 0
