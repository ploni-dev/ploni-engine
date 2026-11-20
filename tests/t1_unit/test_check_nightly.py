"""Tests of scripts/check_nightly.py: did the last nightly full run on main fail?

The check reads GitHub's list of runs of `.github/workflows/full.yml` and says whether the newest
finished nightly one on main failed. The workflow that calls it (a PR of
its own) then runs the full suite on the PR (Achia, 2026-11-20: "A robot blocks the next merge
(Recommended)", then "Yes, run the full tests (Recommended)").

last_run(), equivalence classes:
  L1 no runs                                                     None
  L2 one finished nightly run on main                            that run
  L3 several, in any order                                       the newest by created_at
  L4 a pull_request run, newer than a nightly one                the nightly one (PR runs do not count)
  L5 a run on another branch                                     not counted
  L6 a run not finished (queued, in_progress)                    not counted
  L7 a by-hand run (workflow_dispatch) on main, newer            not counted: only the nightly result
failed(), equivalence classes:
  F1 no run                                                      None
  F2 conclusion success                                          None
  F3 conclusion failure                                          a reason naming it and the run's page
  F4 any other conclusion (cancelled, timed_out, startup_failure, action_required, neutral,
     skipped, none at all)                                       a reason: only success is green
fetch(), with urlopen stubbed:
  G1 the URL: the repository, full.yml, branch main, finished runs, one page of RUNS_PER_PAGE
  G2 the headers: the token as a Bearer token, the API version
  G3 returns the list under "workflow_runs"; G4 an HTTP error is raised, not swallowed
main():
  M1 wrong arguments: usage, exit 2
  M2 no GITHUB_TOKEN, or an empty one: a line on the error stream, exit 2
  M3 the last run failed: "failed=true" in the file named by GITHUB_OUTPUT, a warning line, exit 0
  M4 the last run passed, or none: "failed=false", nothing printed, exit 0
  M5 no GITHUB_OUTPUT: the output line on stdout
Adversarial:
  A1 a conclusion or page address holding a line break: the reason is one line, so it cannot add
     a line to GITHUB_OUTPUT or a second workflow command
  A2 created_at of runs on different days compared as dates, not by list order (L3)
Hebrew and document axes: do not apply; the input is GitHub's run list.
"""

import io
import json
import urllib.error
from email.message import Message
from pathlib import Path
from typing import Any

import pytest

from scripts import check_nightly as check


def run(created: str, *, event: str = "schedule", branch: str = "main", status: str = "completed", conclusion: str | None = "success", url: str = "https://github.test/r/1") -> dict[str, Any]:
    return {"created_at": created, "event": event, "head_branch": branch, "status": status, "conclusion": conclusion, "html_url": url}


def test_l1_no_runs() -> None:
    assert check.last_run([]) is None


def test_l2_one_nightly_run() -> None:
    only = run("2026-11-21T01:17:00Z")
    assert check.last_run([only]) == only


def test_l3_the_newest_in_any_order() -> None:
    old, new = run("2026-11-20T01:17:00Z", conclusion="failure"), run("2026-11-21T01:17:00Z")
    assert check.last_run([old, new]) == new
    assert check.last_run([new, old]) == new


def test_l4_a_pull_request_run_does_not_count() -> None:
    nightly = run("2026-11-21T01:17:00Z")
    assert check.last_run([run("2026-11-21T09:00:00Z", event="pull_request", conclusion="failure"), nightly]) == nightly


def test_l5_another_branch_does_not_count() -> None:
    assert check.last_run([run("2026-11-21T01:17:00Z", branch="feat/x", conclusion="failure")]) is None


@pytest.mark.parametrize("status", ["queued", "in_progress", "waiting", "requested", "pending"])
def test_l6_a_run_not_finished_does_not_count(status: str) -> None:
    done = run("2026-11-20T01:17:00Z")
    assert check.last_run([run("2026-11-21T01:17:00Z", status=status, conclusion=None), done]) == done


@pytest.mark.parametrize("conclusion", ["success", "failure"])
def test_l7_a_run_by_hand_does_not_count(conclusion: str) -> None:
    nightly = run("2026-11-21T01:17:00Z", conclusion="failure" if conclusion == "success" else "success")
    by_hand = run("2026-11-21T10:00:00Z", event="workflow_dispatch", conclusion=conclusion)
    assert check.last_run([nightly, by_hand]) == nightly


def test_f1_no_run() -> None:
    assert check.failed(None) is None


def test_f2_success() -> None:
    assert check.failed(run("2026-11-21T01:17:00Z")) is None


def test_f3_failure() -> None:
    reason = check.failed(run("2026-11-21T01:17:00Z", conclusion="failure", url="https://github.test/r/9"))
    assert reason == "the last nightly full run on main ended failure: https://github.test/r/9"


@pytest.mark.parametrize("conclusion", ["cancelled", "timed_out", "startup_failure", "action_required", "neutral", "skipped", None])
def test_f4_only_success_is_green(conclusion: str | None) -> None:
    reason = check.failed(run("2026-11-21T01:17:00Z", conclusion=conclusion))
    assert reason == f"the last nightly full run on main ended {conclusion}: https://github.test/r/1"


@pytest.mark.parametrize("field", ["conclusion", "html_url"])
def test_a1_a_line_break_stays_in_one_line(field: str) -> None:
    bad = run("2026-11-21T01:17:00Z", conclusion="failure")
    bad[field] = "x\r\n::error::y\nfailed=false"
    reason = check.failed(bad)
    assert reason is not None
    assert "\n" not in reason and "\r" not in reason


class Response(io.BytesIO):
    """A stand-in for what urlopen returns: a readable body that is a context manager."""


def test_g1_g2_g3_the_request(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def urlopen(request: Any, timeout: float) -> Response:
        seen["url"], seen["headers"], seen["timeout"] = request.full_url, dict(request.header_items()), timeout
        return Response(json.dumps({"total_count": 1, "workflow_runs": [run("2026-11-21T01:17:00Z")]}).encode())

    monkeypatch.setattr(check.urllib.request, "urlopen", urlopen)
    runs = check.fetch("owner/repo", "tkn")
    assert seen["url"] == f"https://api.github.com/repos/owner/repo/actions/workflows/full.yml/runs?branch=main&status=completed&per_page={check.RUNS_PER_PAGE}"
    assert seen["headers"]["Authorization"] == "Bearer tkn"
    assert seen["headers"]["X-github-api-version"] == check.API_VERSION
    assert seen["timeout"] == check.TIMEOUT_SECONDS
    assert runs == [run("2026-11-21T01:17:00Z")]


def test_g4_an_http_error_is_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    def urlopen(request: Any, timeout: float) -> Response:
        raise urllib.error.HTTPError(request.full_url, 500, "boom", Message(), None)

    monkeypatch.setattr(check.urllib.request, "urlopen", urlopen)
    with pytest.raises(urllib.error.HTTPError):
        check.fetch("owner/repo", "tkn")


@pytest.mark.parametrize("argv", [[], ["a", "b"]])
def test_m1_usage(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main(argv) == 2
    assert capsys.readouterr().err == check.USAGE + "\n"


@pytest.mark.parametrize("token", [None, ""], ids=["unset", "empty"])
def test_m2_no_token(token: str | None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    if token is None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    else:
        monkeypatch.setenv("GITHUB_TOKEN", token)
    assert check.main(["owner/repo"]) == 2
    assert capsys.readouterr().err == "GITHUB_TOKEN is not set\n"


@pytest.mark.parametrize(
    ("runs", "line", "printed"),
    [
        ([run("2026-11-21T01:17:00Z", conclusion="failure")], "failed=true\n", "::warning::the last nightly full run on main ended failure: https://github.test/r/1\n"),
        ([run("2026-11-21T01:17:00Z")], "failed=false\n", ""),
        ([], "failed=false\n", ""),
    ],
    ids=["m3-failed", "m4-passed", "m4-none"],
)
def test_m3_m4_the_output(runs: list[dict[str, Any]], line: str, printed: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "out"
    out.write_text("before=1\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN", "tkn")
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setattr(check, "fetch", lambda repo, token: runs)
    assert check.main(["owner/repo"]) == 0
    assert out.read_text(encoding="utf-8") == "before=1\n" + line
    assert capsys.readouterr() == (printed, "")


def test_m5_no_github_output(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "tkn")
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.setattr(check, "fetch", lambda repo, token: [])
    assert check.main(["owner/repo"]) == 0
    assert capsys.readouterr().out == "failed=false\n"
