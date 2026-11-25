"""Check that the commit a PR's Ponytail review names is its last, or followed only by merges of main or empty commits.

Why: `PROCESS.md` section 12 item 8: "A check that the commit named in the PR's Ponytail
section is the PR's last commit, or that every commit after it is a merge of `main` that leaves
the branch's own diff unchanged." `CLAUDE.md`, Ponytail: a commit that changes what the branch
adds or removes makes the review stale; taking main into the branch, with no other change, does
not. Issue #176, one of the four robots Achia chose on 2026-11-20 ("Yes, all four
(Recommended)"). Strict, red until a review naming the commit is pasted; since his choice of
2026-11-24, "Drop the newest-run gate (Recommended)", the merge gate counts every run on the
last commit, so after the review is pasted an empty commit is pushed, and this check lets an
empty commit through.

Contract: `python -m scripts.check_reviewed_commit <base> <head>`, run in the checkout, with
the PR body in PR_BODY. It runs as a module so that it uses `section()` of
scripts/check_pr_body.py and `git()` of scripts/check_commit_order.py. The body names a commit
on the one line of its `## Ponytail review` section that starts, past spaces, with
`Commit reviewed: ` and then the full 40-character hash, lower case, in backticks; anything may
follow. It is refused, with one line on the error stream and exit code 1, when: the section or
that line is missing, or there is more than one of either; the line names no full hash (the template's
line as it is: the review is not pasted); the named commit is not one of `base..head`; a commit
of `head` that neither the named commit nor `base` holds, oldest first, is neither a merge whose
every parent after the first `base` holds (a merge of main) nor a commit with one parent and
that parent's tree (an empty commit); or the branch's own diff at
`head` is not the one at the named commit. The branch's own diff at a revision is git's raw
diff, with full object names, from its merge base with `base` to it: equal means each path the
branch changes holds the same content before and after, byte for byte. Otherwise nothing is
written and the exit code is 0. Wrong arguments: a usage line, exit 2. A revision git does not
know, or any other git failure: git's error, a traceback, a non-zero exit.

Known limits:
- The raw diffs are compared, not patches: when main changed a file the branch changes too,
  the old content differs and the merge of main is refused, though the branch's own lines are
  the same (this only narrows; `git patch-id` would let it through, and would also let through
  a change of white space made in the merge, which it ignores).
- HTML comments are removed from the whole body first, so neither a heading nor a line inside
  one counts. A heading or a line inside a fenced code block does, as in
  scripts/check_pr_body.py: a review heading in a fence makes two sections, refused (this only
  narrows). A quoted line ("> Commit reviewed: ...") is a reviewer's report and does not count.
- Only the form of the PR bodies of this repository is read: one space after the colon, the
  hash in backticks, in lower case. Any other form is refused (this only narrows).
- `base` must be main as the PR sees it: a merge of a main newer than `base` is refused. Run
  on GitHub's merge of a PR, pass HEAD^1 HEAD^2, the PR's own head: on HEAD^1 HEAD the merge
  itself comes after the reviewed commit and brings in a branch main does not hold. The
  checkout must hold every commit of the PR, not a depth of 2.
- On Windows the error stream is written in the local code page (cp1255 on the laptop); a
  reader that expects UTF-8 sets PYTHONIOENCODING=utf-8, as the module suite does.
"""

import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path

from scripts.check_commit_order import SHORT_HASH, git
from scripts.check_pr_body import COMMENT, REVIEW, heading_of, section

USAGE = "usage: python -m scripts.check_reviewed_commit <base> <head>, with the PR body in PR_BODY"
LABEL = "Commit reviewed:"
# The form of the merged PR bodies (#99 to #197): the label, one space, the full hash in backticks.
NAMED = re.compile(re.escape(LABEL) + r" `([0-9a-f]{40})`")
MISSING_LINE = f'missing: a line that starts with "{LABEL}" in {REVIEW}'
NOT_PASTED = f'not pasted: the "{LABEL}" line of {REVIEW} names no full 40-character hash in backticks'


def label_lines(body: str) -> list[str] | None:
    """Return the lines of the body's Ponytail review that start with the label, stripped.

    Why: the commit is named on one line; comments and quoted reports are not that line.

    Contract: None when the section is absent. HTML comments are removed from the whole body
    first, so a heading inside one does not start the section; each line is stripped of white
    space at both ends, so CRLF line ends and an indent do not count.

    Known limits: only the first review section is read; `named()` refuses a body with more
    than one. A heading inside a fenced code block starts a section, as in check_pr_body.py.
    """
    review = section(COMMENT.sub("", body), REVIEW)
    if review is None:
        return None
    lines = (line.strip() for line in review.split("\n"))
    return [line for line in lines if line.startswith(LABEL)]


def named(body: str) -> tuple[str, str]:
    """Return the commit the body's Ponytail review names, as (hash, "") or ("", the refusal).

    Why: the check is strict, by Achia's choice of 2026-11-24 as the module's Why gives it:
    red until a review naming the commit is pasted, so a body that names no commit, or more
    than one, is refused.

    Contract: the hash is 40 lower-case hex characters. The refusal is one line: more than one
    review section (counted past HTML comments; the review of #201, pass 1, finding 1), the
    section missing, the label line missing, more than one, or one that names no full hash.
    """
    sections = sum(heading_of(line) == REVIEW for line in COMMENT.sub("", body).split("\n"))
    if sections > 1:
        return "", f"{sections} sections {REVIEW} in the body; keep one, with the review of the last commit"
    lines = label_lines(body)
    if lines is None:
        return "", f"missing: {REVIEW}"
    if not lines:
        return "", MISSING_LINE
    if len(lines) > 1:
        return "", f'{len(lines)} lines start with "{LABEL}" in {REVIEW}; keep one, the one that names the last commit'
    match = NAMED.match(lines[0])
    return (match.group(1), "") if match else ("", NOT_PASTED)


def outside_problem(sha: str, base: str, head: str, cwd: Path) -> str:
    """Return the refusal of a named commit that is not one of base..head, or "".

    Why: a review of a commit of main, of another branch or of nothing git holds reviewed
    nothing of this PR.

    Contract: `git rev-list base..head`, compared by full hash. Raises CalledProcessError when
    git fails.
    """
    if sha in git(["rev-list", f"{base}..{head}"], cwd).split():
        return ""
    return f"{sha[:SHORT_HASH]}: the commit the review names is not one of {base}..{head}"


def changes_nothing(commit: str, parents: list[str], cwd: Path) -> bool:
    """Say whether a commit has one parent whose tree is its own: an empty commit.

    Why: after the review is pasted into the PR body, an empty commit is pushed so that every
    check runs on a fresh last commit (Achia, 2026-11-24, "Drop the newest-run gate
    (Recommended)", issue #176). It changes nothing the review read.

    Contract: `git rev-parse <revision>^{tree}` of the commit and of its one parent, compared
    as text. False for a commit with no parent or with more than one. Raises
    CalledProcessError when git fails.

    Known limits: `parents` is the caller's list, as `git rev-list --parents` printed it; it
    is not checked against the commit, so a wrong list gives a wrong answer.
    """
    return len(parents) == 1 and git(["rev-parse", f"{commit}^{{tree}}"], cwd) == git(["rev-parse", f"{parents[0]}^{{tree}}"], cwd)


def later_problem(sha: str, base: str, head: str, cwd: Path) -> str:
    """Return the refusal of the oldest commit after the reviewed one that is neither a merge of main nor empty, or "".

    Why: the item allows only merges of main after the reviewed commit; main's own commits,
    which such a merge brings in, are held by base and are not the branch's. An empty commit
    is let through too (`changes_nothing`).

    Contract: the commits of `git rev-list --parents head ^sha ^base`, oldest first; a merge of
    main has two parents or more and `git rev-list base..<parent>` is empty for each after the
    first. Each commit is judged by its own change: two commits that undo each other are
    refused at the first. Raises CalledProcessError when git fails.
    """
    listed = git(["rev-list", "--reverse", "--topo-order", "--parents", head, f"^{sha}", f"^{base}"], cwd)
    for line in listed.splitlines():
        commit, *parents = line.split()
        if changes_nothing(commit, parents, cwd):
            continue
        if len(parents) < 2 or any(git(["rev-list", f"{base}..{parent}"], cwd).strip() for parent in parents[1:]):
            return f"{commit[:SHORT_HASH]}: comes after the reviewed commit {sha[:SHORT_HASH]} and is not a merge of {base}; review the last commit"
    return ""


def own_diff(revision: str, base: str, cwd: Path) -> str:
    """Return the branch's own diff at a revision: git's raw diff from its merge base with base.

    Why: what the branch changes against main, in a form that two revisions can be compared in
    byte for byte (the Known limits of the module say why not `git patch-id`).

    Contract: `git diff-tree -r -z --no-renames <merge base> <revision>`: for each path changed,
    the modes, the full object names before and after, the status and the path, NUL-separated.
    Raises CalledProcessError when git fails, as when the two share no history.

    Known limits: one merge base. When there are several, `git merge-base` picks one. Main is
    linear (squash merges only), so a branch and main have one; a scratch branch that the merge
    gate's own test targets (PROMOTION.md sections 10 and 11) may not be linear.
    """
    fork = git(["merge-base", revision, base], cwd).strip()
    return git(["diff-tree", "-r", "-z", "--no-renames", fork, revision], cwd)


def diff_problem(sha: str, base: str, head: str, cwd: Path) -> str:
    """Return the refusal of a head whose own diff is not the reviewed commit's, or "".

    Why: the item's last words, "a merge of `main` that leaves the branch's own diff
    unchanged": a merge whose resolution changed the branch must be reviewed again.

    Contract: compares `own_diff()` of the two. Raises CalledProcessError when git fails.
    """
    if own_diff(sha, base, cwd) == own_diff(head, base, cwd):
        return ""
    return f"the branch's own diff at {head} is not the one of the reviewed commit {sha[:SHORT_HASH]}; review the last commit"


def history_problem(sha: str, base: str, head: str, cwd: Path) -> str:
    """Return the first refusal of the history for a named commit, or "".

    Why: the three judgements of the history in the order the item states them; the first
    that refuses is the one line written.

    Contract: `outside_problem()`, then `later_problem()`, then `diff_problem()`. Raises
    CalledProcessError when git fails.
    """
    return outside_problem(sha, base, head, cwd) or later_problem(sha, base, head, cwd) or diff_problem(sha, base, head, cwd)


def main(argv: list[str], environ: Mapping[str, str]) -> int:
    """Check the review named in PR_BODY against the revisions in argv; return the exit code.

    Why: the entry point of a workflow, given its arguments and environment so that a test can
    call it.

    Contract: argv is [base, head]; any other length writes the usage line, exit 2. A missing
    PR_BODY is an empty body. The history is read only when the body names a commit. Writes
    the one refusal on the error stream.
    """
    if len(argv) != 2:
        print(USAGE, file=sys.stderr)
        return 2
    sha, problem = named(environ.get("PR_BODY", ""))
    problem = problem or history_problem(sha, argv[0], argv[1], Path.cwd())
    if problem:
        print(problem, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], os.environ))
