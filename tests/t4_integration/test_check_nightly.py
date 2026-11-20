"""Module suite for scripts/check_nightly.py: main() against a real HTTP server on this machine.

Why: the unit tests stub urlopen; only a real request shows that the URL, the query and the
headers reach a server as GitHub reads them, that its JSON is read as GitHub writes it, and
that an error status makes the run red.

Matrix (a server on 127.0.0.1 in a thread, check.API pointed at it; main run in-process):
  M1  the newest nightly run failed, an older one passed, a newer PR run passed   failed=true, a warning
  M2  the newest nightly run passed                                               failed=false, nothing printed
  M3  the request: its path, query and headers as GitHub reads them
  M4  the server answers 500                                                      HTTPError raised, so the run is red
"""

import json
import threading
import urllib.error
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, ClassVar

import pytest

from scripts import check_nightly as check


class Handler(BaseHTTPRequestHandler):
    """Answer every GET with the class's status and body, and record what was asked."""

    status: ClassVar[int] = 200
    body: ClassVar[dict[str, Any]] = {}
    seen: ClassVar[list[tuple[str, dict[str, str]]]] = []

    def do_GET(self) -> None:  # the name http.server calls
        type(self).seen.append((self.path, dict(self.headers.items())))
        payload = json.dumps(type(self).body).encode()
        self.send_response(type(self).status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt: str, *args: Any) -> None:
        """Write nothing: the test reads what was asked from `seen`."""


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[type[Handler]]:
    """Run a server on a free port, point check.API at it, and set the token and output file."""
    Handler.status, Handler.body, Handler.seen = 200, {}, []
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(check, "API", f"http://127.0.0.1:{httpd.server_port}")
    monkeypatch.setenv("GITHUB_TOKEN", "tkn")
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "out"))
    yield Handler
    httpd.shutdown()
    httpd.server_close()


def run(created: str, event: str, conclusion: str) -> dict[str, Any]:
    return {"created_at": created, "event": event, "head_branch": "main", "status": "completed", "conclusion": conclusion, "html_url": f"https://github.test/{created}"}


def test_m1_the_newest_nightly_run_failed(server: type[Handler], tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    server.body = {"total_count": 3, "workflow_runs": [run("2026-11-21T09:00:00Z", "pull_request", "success"), run("2026-11-21T01:17:00Z", "schedule", "failure"), run("2026-11-20T01:17:00Z", "schedule", "success")]}
    assert check.main(["owner/repo"]) == 0
    assert (tmp_path / "out").read_text(encoding="utf-8") == "failed=true\n"
    assert capsys.readouterr().out == "::warning::the last nightly full run on main ended failure: https://github.test/2026-11-21T01:17:00Z\n"


def test_m2_the_newest_nightly_run_passed(server: type[Handler], tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    server.body = {"total_count": 2, "workflow_runs": [run("2026-11-21T01:17:00Z", "schedule", "success"), run("2026-11-20T01:17:00Z", "schedule", "failure")]}
    assert check.main(["owner/repo"]) == 0
    assert (tmp_path / "out").read_text(encoding="utf-8") == "failed=false\n"
    assert capsys.readouterr().out == ""


def test_m3_the_request(server: type[Handler]) -> None:
    server.body = {"total_count": 0, "workflow_runs": []}
    check.main(["owner/repo"])
    [(path, headers)] = server.seen
    assert path == f"/repos/owner/repo/actions/workflows/full.yml/runs?branch=main&status=completed&per_page={check.RUNS_PER_PAGE}"
    assert headers["Authorization"] == "Bearer tkn"
    assert headers["X-Github-Api-Version"] == check.API_VERSION
    assert headers["Accept"] == "application/vnd.github+json"


def test_m4_an_error_status_is_raised(server: type[Handler]) -> None:
    server.status, server.body = 500, {"message": "boom"}
    with pytest.raises(urllib.error.HTTPError):
        check.main(["owner/repo"])
