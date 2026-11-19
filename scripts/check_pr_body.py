"""Check that a PR body holds the orientation block and the Ponytail review, both filled.

Why: issue #21 (PROCESS.md section 12 item 8; PROMOTION.md section 5.2). A PR with no review
section, or with the template left as it is, must not look ready. CI cannot judge a review
(PROCESS.md section 5.4: Ponytail is an agent-side skill), so this checks presence only.

Contract: `python scripts/check_pr_body.py`, with the body in the environment variable PR_BODY
(the workflow `.github/workflows/pr-body.yml` puts it there, so that the body is never part of
a shell command). Each section that is missing or empty is written on the error stream, one
line each, and the exit code is 1; otherwise nothing is written and the exit code is 0.

Known limits:
- A section is empty when each of its lines is blank, inside an HTML comment, or a line of the
  same section of `.github/pull_request_template.md` left as it is. Any other line fills it,
  a placeholder such as "(the review comes here)" too.
- A heading inside a fenced code block counts as a heading.
"""

import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[1] / ".github" / "pull_request_template.md"
# The two sections issue #21 names.
REQUIRED = ("## Orientation", "## Ponytail review")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def section(body: str, heading: str) -> str | None:
    """Return the text under a level-two heading, up to the next one; None when it is absent.

    Why: the two sections are judged one at a time, each on its own text.

    Contract: the heading is a line equal to `heading` once spaces and a carriage return at
    either end are removed; the text runs to the next line that begins with "## " or to the end.
    """
    lines = body.split("\n")
    for start, line in enumerate(lines):
        if line.strip() == heading:
            rest = lines[start + 1 :]
            end = next((i for i, later in enumerate(rest) if later.startswith("## ")), len(rest))
            return "\n".join(rest[:end])
    return None


def filled(text: str, unfilled: set[str]) -> bool:
    """Say whether a section has a line of its own, past comments, blanks and template lines.

    Why: a section copied from the template unfilled is as empty as a missing one.

    Contract: `unfilled` holds the stripped lines that do not count, those of the template.
    """
    lines = (line.strip() for line in COMMENT.sub("", text).split("\n"))
    return any(line and line not in unfilled for line in lines)


def problems(body: str, template: str | None = None) -> list[str]:
    """Return one line per required section that is missing or empty, in the order of REQUIRED.

    Why: the one judgement of the check, apart from where the body comes from.

    Contract: `template` is the text of the PR template; by default the repository's own.
    """
    template = TEMPLATE.read_text(encoding="utf-8") if template is None else template
    found = []
    for heading in REQUIRED:
        text = section(body, heading)
        unfilled = {line.strip() for line in COMMENT.sub("", section(template, heading) or "").split("\n")}
        if text is None:
            found.append(f"missing: {heading}")
        elif not filled(text, unfilled):
            found.append(f"empty: {heading}")
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
