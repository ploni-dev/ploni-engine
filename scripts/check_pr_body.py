"""Check that a PR body holds the orientation block and the Ponytail review, both filled.

Why: issue #21 (PROCESS.md section 12 item 8; PROMOTION.md section 5.2). A PR with no review
section, or with the template left as it is, must not look ready. CI cannot judge a review
(PROCESS.md section 5.5: Ponytail is an agent-side skill), so this checks presence only.

Contract: `python scripts/check_pr_body.py`, with the body in the environment variable PR_BODY
(the workflow `.github/workflows/pr-body.yml` puts it there, so that the body is never part of
a shell command). Each problem is written on the error stream, one line each, and the exit
code is 1; otherwise nothing is written and the exit code is 0. A problem is a missing
section, an orientation line of the four of PROMOTION.md section 5.2 with no value, or an
empty review.

Known limits:
- The review is empty when each of its lines is blank, inside an HTML comment, or a line of
  the same section of `.github/pull_request_template.md` left as it is. Any other line fills
  it, a placeholder such as "(the review comes here)" too.
- A heading inside a fenced code block counts as a heading.
"""

import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / ".github" / "pull_request_template.md"
ORIENTATION = "## Orientation"
REVIEW = "## Ponytail review"
# PROMOTION.md section 5.2, "Orientation step performed": the goal, deliverable, gate and
# downstream-risk lines, by their labels in the template.
LABELS = ("Goal", "Deliverable", "Gate", "Downstream risk if wrong")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# A level-two heading: up to three spaces before it, as in Markdown; four make a code block.
HEADING = re.compile(r" {0,3}(## .*?)\s*")


def heading_of(line: str) -> str | None:
    """Return the level-two heading a line is, without its indent and trailing spaces, or None.

    Why: the start and the end of a section must be found by one rule.

    Contract: "  ## Ponytail review \\r" gives "## Ponytail review"; "### x" and "    ## x" give None.
    """
    match = HEADING.fullmatch(line)
    return match.group(1) if match else None


def section(body: str, heading: str) -> str | None:
    """Return the text under a level-two heading, up to the next one; None when it is absent.

    Why: each section is judged on its own text.

    Contract: the text runs from the line after the heading to the line before the next
    level-two heading, or to the end of the body.
    """
    lines = body.split("\n")
    for start, line in enumerate(lines):
        if heading_of(line) == heading:
            rest = lines[start + 1 :]
            end = next((i for i, later in enumerate(rest) if heading_of(later)), len(rest))
            return "\n".join(rest[:end])
    return None


def labelled(text: str, label: str) -> bool:
    """Say whether a line of the text begins with the label and a colon, with a value after it.

    Why: PROMOTION.md section 5.2 asks for each orientation line, not for any text at all.

    Contract: comments do not count; spaces before the label and after the colon are ignored.
    """
    lines = (line.strip() for line in COMMENT.sub("", text).split("\n"))
    return any(line.startswith(f"{label}:") and line[len(label) + 1 :].strip() for line in lines)


def filled(text: str, unfilled: set[str]) -> bool:
    """Say whether a section has a line of its own, past comments, blanks and template lines.

    Why: a section copied from the template unfilled is as empty as a missing one.

    Contract: `unfilled` holds the stripped lines that do not count, those of the template.
    """
    lines = (line.strip() for line in COMMENT.sub("", text).split("\n"))
    return any(line and line not in unfilled for line in lines)


def problems(body: str, template: str | None = None) -> list[str]:
    """Return one line per problem of the body: the orientation first, then the review.

    Why: the judgement of the check, apart from where the body comes from.

    Contract: `template` is the text of the PR template; by default the repository's own.
    Raises FileNotFoundError when that file is not there.
    """
    template = TEMPLATE.read_text(encoding="utf-8") if template is None else template
    found = []
    orientation = section(body, ORIENTATION)
    if orientation is None:
        found.append(f"missing: {ORIENTATION}")
    else:
        found += [f"empty: {ORIENTATION}, {label}:" for label in LABELS if not labelled(orientation, label)]
    review = section(body, REVIEW)
    unfilled = {line.strip() for line in COMMENT.sub("", section(template, REVIEW) or "").split("\n")}
    if review is None:
        found.append(f"missing: {REVIEW}")
    elif not filled(review, unfilled):
        found.append(f"empty: {REVIEW}")
    return found


def main(environ: Mapping[str, str]) -> int:
    """Check the body in PR_BODY; return the exit code.

    Why: the entry point of the workflow, given the environment so that a test can call it.

    Contract: a missing PR_BODY is an empty body. Writes each problem on the error stream.
    """
    found = problems(environ.get("PR_BODY", ""))
    for line in found:
        print(line, file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(os.environ))
