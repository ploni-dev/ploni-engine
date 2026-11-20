"""Say whether the last nightly full run on main failed, for the workflow that then runs the full suite.

Why: the full workflow (`.github/workflows/full.yml`, #165) runs nightly on main, and its check
lands on main's commit, which no PR reads (issue #167). Achia decided on 2026-11-20, of the
option "A robot blocks the next merge (Recommended)": "I add a small check to every PR that reads
the last nightly result on main and goes red if it failed, so nothing more merges until the
failure is fixed." Asked next how the PR that fixes the failure can merge, he chose "Yes, run the
full tests (Recommended)": "After a failed night every PR waits about a minute more while the
full tests run on it. A PR that does not fix the failure stays red; the one that fixes it goes
green and merges; the next night's run then clears the block for everyone." This script is the
reading; the workflow that calls it, in a PR of its own, runs the full suite when it says so.

Contract: `python -m scripts.check_nightly <owner/repo>`, with the token in GITHUB_TOKEN. It
asks GitHub's REST API for the newest runs of full.yml on main started by the nightly schedule
(`event=schedule`), takes the newest by `created_at` that has a verdict or was run again by
hand, and writes `failed=true` unless it is a first attempt that succeeded, else
`failed=false`, as one line
appended to the file named by GITHUB_OUTPUT (on stdout when it is not set). When it failed, it
also prints a GitHub warning line naming the conclusion and the run's page. Exit 0 either way:
the full suite, not this script, turns the PR red. Wrong arguments: a usage line, exit 2. No
token: a line on the error stream, exit 2. An HTTP or network error: a traceback, a non-zero
exit, so the check is red rather than silent.

Known limits, each Claude's reading of "the last nightly result" that only narrows, as his
option says "the next night's run then clears the block for everyone":
- Only nightly runs count. A run started by hand from the Actions tab neither sets nor clears
  the block, and by-hand runs are not asked for, so they cannot push a night off the page.
- A night run again by hand (its `run_attempt` above 1) is never green, finished or not: a
  re-run that passes does not show the night's failure fixed, and while it runs the night
  before is not read in its place (the review of #178, finding 1).
- A cancelled or timed-out night counts as failed: only success is green.
Readings of his words that neither narrow nor widen:
- A first attempt not yet finished has no verdict; the night before is read.
- No nightly run at all (before the first night) is failed=false.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API = "https://api.github.com"
# GitHub's REST API version this was written against (docs.github.com, "API Versions").
API_VERSION = "2022-11-28"
WORKFLOW_FILE = "full.yml"
BRANCH = "main"
COUNTED_EVENTS = ("schedule",)
# A month and more of nights; only nightly runs are asked for.
RUNS_PER_PAGE = 50
TIMEOUT_SECONDS = 30
USAGE = "usage: python -m scripts.check_nightly <owner/repo>"


def last_run(runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the newest nightly run on main that has a verdict or was run again, or None.

    Why: a run started by a PR's label shows that PR's state, not main's; a run started by hand
    is not the nightly result (the module's Known limits); a first attempt not finished has no
    verdict yet, but a re-run is counted while it runs, so the night before is not read for it;
    the list's own order is not relied on.

    Contract: `runs` as GitHub lists workflow runs (dicts with created_at, event, head_branch,
    status, run_attempt; a missing run_attempt is 1). created_at is ISO 8601 in UTC, as GitHub
    writes it, so it compares as text.
    """
    counted = [r for r in runs if r.get("event") in COUNTED_EVENTS and r.get("head_branch") == BRANCH and (r.get("status") == "completed" or attempt(r) > 1)]
    return max(counted, key=lambda r: str(r.get("created_at")), default=None)


def attempt(run: dict[str, Any]) -> int:
    """Return which attempt of its run a run is: 1, or more once it was run again by hand.

    Why: GitHub keeps a re-run as a new attempt of the same run, with the same event and date.

    Contract: the run's `run_attempt`; 1 when the field is missing. Raises ValueError or
    TypeError when it is not a number, so the check is red rather than read a garbled re-run as
    a first attempt.
    """
    return int(run.get("run_attempt", 1))


def failed(run: dict[str, Any] | None) -> str | None:
    """Return why a run counts as failed, or None when it passed or there is no run.

    Why: only a first attempt that succeeded is green: a cancelled or timed-out night did not show
    main is sound, and a re-run by hand does not clear the block (the module's Known limits).

    Contract: the reason is one line: a line break in the conclusion or the page address is
    replaced, so it cannot add a line to GITHUB_OUTPUT or a second workflow command.
    """
    if run is None:
        return None
    if attempt(run) > 1:
        reason = f"the last nightly full run on main was run again by hand (attempt {attempt(run)}, ended {run.get('conclusion')}): {run.get('html_url')}"
    elif run.get("conclusion") == "success":
        return None
    else:
        reason = f"the last nightly full run on main ended {run.get('conclusion')}: {run.get('html_url')}"
    return " ".join(reason.splitlines())


def fetch(repo: str, token: str) -> list[dict[str, Any]]:
    """Return GitHub's newest nightly runs of the full workflow on main.

    Why: the reading of the nightly result, apart from judging it, so each can be tested alone.

    Contract: `repo` is "owner/name"; `token` a GitHub token that may read Actions. One GET of
    /repos/{repo}/actions/workflows/full.yml/runs with branch=main, event=schedule and
    per_page=RUNS_PER_PAGE, in any status; returns its "workflow_runs". Raises urllib.error.HTTPError or
    URLError when the request fails, and json.JSONDecodeError on a body that is not JSON.
    """
    query = urllib.parse.urlencode({"branch": BRANCH, "event": COUNTED_EVENTS[0], "per_page": RUNS_PER_PAGE})
    request = urllib.request.Request(  # noqa: S310 the address starts with API, a fixed https constant
        f"{API}/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/runs?{query}",
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "X-GitHub-Api-Version": API_VERSION},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310 the request built above, to API
        runs: list[dict[str, Any]] = json.load(response)["workflow_runs"]
    return runs


def main(argv: list[str]) -> int:
    """Write whether the last nightly run on main failed; return the exit code.

    Why: the entry point of the workflow, given its arguments so that a test can call it.

    Contract: argv is [owner/repo]; the token is read from GITHUB_TOKEN. See the module docstring.
    """
    if len(argv) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not set", file=sys.stderr)
        return 2
    reason = failed(last_run(fetch(argv[0], token)))
    line = f"failed={'true' if reason else 'false'}\n"
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as out:
            out.write(line)
    else:
        sys.stdout.write(line)
    if reason:
        print(f"::warning::{reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
