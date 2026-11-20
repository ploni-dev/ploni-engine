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
asks GitHub's REST API for the newest finished runs of full.yml on main, takes the newest by
`created_at` of those started by the nightly schedule (`schedule`), and writes
`failed=true` when its conclusion is anything but success, else `failed=false`, as one line
appended to the file named by GITHUB_OUTPUT (on stdout when it is not set). When it failed, it
also prints a GitHub warning line naming the conclusion and the run's page. Exit 0 either way:
the full suite, not this script, turns the PR red. Wrong arguments: a usage line, exit 2. No
token: a line on the error stream, exit 2. An HTTP or network error: a traceback, a non-zero
exit, so the check is red rather than silent.

Known limits:
- Only nightly runs count. A run started by hand from the Actions tab neither sets nor clears
  the block: his option says "the next night's run then clears the block for everyone". That
  is Claude's reading of "the last nightly result", and it only narrows.
- One page of RUNS_PER_PAGE finished runs on main is read; when all of them were started by
  hand, no nightly run is seen and the answer is failed=false. A PR's labelled runs carry the
  PR's branch, which the branch filter leaves out.
- No run at all (before the first night) is failed=false.
- A cancelled or timed-out night counts as failed: only success is green.
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
# A month of nights fits, with room for runs started by hand on main.
RUNS_PER_PAGE = 50
TIMEOUT_SECONDS = 30
USAGE = "usage: python -m scripts.check_nightly <owner/repo>"


def last_run(runs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the newest finished nightly run on main, or None when there is none.

    Why: a run started by a PR's label shows that PR's state, not main's; a run started by hand
    is not the nightly result (the module's Known limits); a run not finished has no verdict yet;
    the list's own order is not relied on.

    Contract: `runs` as GitHub lists workflow runs (dicts with created_at, event, head_branch,
    status). created_at is ISO 8601 in UTC, as GitHub writes it, so it compares as text.
    """
    counted = [r for r in runs if r.get("event") in COUNTED_EVENTS and r.get("head_branch") == BRANCH and r.get("status") == "completed"]
    return max(counted, key=lambda r: str(r.get("created_at")), default=None)


def failed(run: dict[str, Any] | None) -> str | None:
    """Return why a run counts as failed, or None when it passed or there is no run.

    Why: only success is green; a cancelled or timed-out night did not show main is sound.

    Contract: the reason is one line: a line break in the conclusion or the page address is
    replaced, so it cannot add a line to GITHUB_OUTPUT or a second workflow command.
    """
    if run is None or run.get("conclusion") == "success":
        return None
    reason = f"the last nightly full run on main ended {run.get('conclusion')}: {run.get('html_url')}"
    return " ".join(reason.splitlines())


def fetch(repo: str, token: str) -> list[dict[str, Any]]:
    """Return GitHub's newest finished runs of the full workflow on main.

    Why: the reading of the nightly result, apart from judging it, so each can be tested alone.

    Contract: `repo` is "owner/name"; `token` a GitHub token that may read Actions. One GET of
    /repos/{repo}/actions/workflows/full.yml/runs with branch=main, status=completed and
    per_page=RUNS_PER_PAGE; returns its "workflow_runs". Raises urllib.error.HTTPError or
    URLError when the request fails, and json.JSONDecodeError on a body that is not JSON.
    """
    query = urllib.parse.urlencode({"branch": BRANCH, "status": "completed", "per_page": RUNS_PER_PAGE})
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
