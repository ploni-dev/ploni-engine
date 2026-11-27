"""On GitHub, a failed test's report names the test and the line it failed on, never its values.

Why: Achia, 2026-11-27, issue #32, "Hide them on GitHub (Recommended)": "On GitHub, a failing test
shows one short line (which test, which line) and not the values. On the laptop, nothing changes:
full detail." The tests of a checksum detector make their numbers when they run; a traceback, an
assertion's explanation, an exception's message or captured output would print them into a
public log. pytest's own --tb=no hides them too, but names no line (measured on #32).

Contract: when the environment variable GITHUB_ACTIONS is "true" (GitHub sets it in every step of
a workflow run), every failed report of a test's setup, call or teardown, and of a collection,
keeps its outcome and its node id; its detail (traceback, explanation, message, captured output)
becomes one line, "<file>:<line>: failed; its values are hidden on GitHub, rerun it on the laptop",
the file and line where it failed (for a report with no such place, its node id). With any other
value, or none, nothing changes.

Known limits: the node id is still printed, a parametrize id in it: a test must not take a number
it is about as its id. What passes pytest's capture (capsys.disabled(), a child process writing to
the terminal) and the text of a warning are not hidden. Only pytest runs that collect under
tests/ load this file.
"""

import os

import pytest

ON_GITHUB = "GITHUB_ACTIONS"
HIDDEN = "failed; its values are hidden on GitHub, rerun it on the laptop"


def on_github() -> bool:
    """Say whether this run is a GitHub Actions run."""
    return os.environ.get(ON_GITHUB) == "true"


def hide(report: pytest.TestReport | pytest.CollectReport) -> None:
    """Replace a failed report's detail by the file and line it failed on."""
    crash = getattr(report.longrepr, "reprcrash", None)
    place = f"{crash.path}:{crash.lineno}" if crash is not None else report.nodeid
    report.longrepr = f"{place}: {HIDDEN}"
    report.sections = []


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> pytest.TestReport:
    """Hide the values of a failed setup, call or teardown, on GitHub."""
    report: pytest.TestReport = yield
    if report.failed and on_github():
        hide(report)
    return report


@pytest.hookimpl(wrapper=True)
def pytest_make_collect_report(collector: pytest.Collector) -> pytest.CollectReport:
    """Hide the values of a failed collection, on GitHub."""
    report: pytest.CollectReport = yield
    if report.failed and on_github():
        hide(report)
    return report
