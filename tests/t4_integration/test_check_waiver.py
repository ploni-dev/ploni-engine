"""Module suite for scripts/check_waiver.py: the script run as a program on a real git history.

Why: the workflow sees only the exit code of `python -m scripts.check_waiver <base> <head>`,
run in the checkout with the body in PR_BODY. Only a run against git shows that the waivers
file and the status file are read from the base, not from the PR, and that the changed paths
reach the judgement.

Matrix:
  M1  no PR_BODY, and revisions git does not know    exit 0: nothing is cited, git is not called
  M2  a citation of WAIVER-999                       exit 1, one line on the error stream
  M3  a waiver on the base, in force, covering the PR    exit 0, nothing written
  M4  a waiver the PR adds to docs/WAIVERS.md itself, cited    exit 1: not in the file of
                                                     the base
  M5  a changed path outside the scope               exit 1, the path named
  M6  a waiver past its date                         exit 1
  M7  a citation and a revision git does not know    exit not 0, git's "fatal" line
  M8  a citation, and the base has no docs/WAIVERS.md    exit not 0, git's "fatal" line

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]
GIT = ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "core.autocrlf=false"]
WAIVERS = """# Waivers

## Active

WAIVER-010
rule:    a rule
scope:   ploni/
granted: 2026-11-19
expires: 2099-12-31

WAIVER-011
rule:    an old rule
scope:   ploni/
expires: 2000-01-01

## Expired

None.
"""
STATUS = "# Status\n\n## Phases\n\n| Phase | Gate | Measured | Date | Exit demo shown |\n|---|---|---|---|---|\n| 0 Foundation | g | | | |\n"


def git(folder: Path, *args: str) -> None:
    """Run one git command in folder, failing the test when git fails."""
    subprocess.run([*GIT, *args], cwd=folder, check=True, capture_output=True, timeout=60)  # noqa: S603 fixed argv, no shell


def write(folder: Path, path: str, text: str = "x\n") -> None:
    """Write a file at path under folder, making its folders."""
    target = folder / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Return a git repository whose base commit holds the waivers and status files."""
    git(tmp_path, "init", "-q")
    write(tmp_path, "docs/WAIVERS.md", WAIVERS)
    write(tmp_path, "docs/STATUS.md", STATUS)
    write(tmp_path, "ploni/old.py")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def commit(folder: Path) -> None:
    """Commit everything in folder as the head."""
    git(folder, "add", "-A")
    git(folder, "commit", "-q", "-m", "head")


def run(folder: Path, body: str | None, *revisions: str) -> subprocess.CompletedProcess[str]:
    """Run the script in folder as the workflow runs it, with the body in PR_BODY."""
    environment = {key: value for key, value in os.environ.items() if key != "PR_BODY"}
    environment["PYTHONPATH"] = str(REPOSITORY)
    if body is not None:
        environment["PR_BODY"] = body
    return subprocess.run(  # noqa: S603 fixed argv, no shell
        [sys.executable, "-m", "scripts.check_waiver", *revisions],
        cwd=folder,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )


def test_m1_no_body(repo: Path) -> None:
    done = run(repo, None, "no-such-base", "no-such-head")
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_m2_an_invented_id(repo: Path) -> None:
    write(repo, "ploni/new.py")
    commit(repo)
    done = run(repo, "waiver: WAIVER-999\n", "HEAD^1", "HEAD")
    assert done.returncode == 1 and done.stdout == ""
    assert done.stderr.splitlines() == ["WAIVER-999 is not in docs/WAIVERS.md"]


def test_m3_a_waiver_in_force(repo: Path) -> None:
    write(repo, "ploni/new.py")
    commit(repo)
    done = run(repo, "waiver: WAIVER-010\n", "HEAD^1", "HEAD")
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_m4_a_waiver_the_pr_adds_itself(repo: Path) -> None:
    write(repo, "docs/WAIVERS.md", WAIVERS.replace("## Expired", "WAIVER-012\nrule: mine\nscope: ploni/\nexpires: 2099-12-31\n\n## Expired"))
    write(repo, "ploni/new.py")
    commit(repo)
    done = run(repo, "waiver: WAIVER-012\n", "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == ["WAIVER-012 is not in docs/WAIVERS.md"]


def test_m5_a_path_outside_the_scope(repo: Path) -> None:
    write(repo, "ploni/new.py")
    write(repo, "docs/a.md")
    commit(repo)
    done = run(repo, "waiver: WAIVER-010\n", "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == ["WAIVER-010 does not cover docs/a.md"]


def test_m6_a_waiver_past_its_date(repo: Path) -> None:
    write(repo, "ploni/new.py")
    commit(repo)
    done = run(repo, "waiver: WAIVER-011\n", "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == ["WAIVER-011 has expired: 2000-01-01"]


def test_m8_no_waivers_file_on_the_base(repo: Path) -> None:
    git(repo, "rm", "-q", "docs/WAIVERS.md")
    commit(repo)
    write(repo, "ploni/new.py")
    commit(repo)
    done = run(repo, "waiver: WAIVER-010\n", "HEAD^1", "HEAD")
    assert done.returncode != 0
    assert "fatal" in done.stderr


def test_m7_an_unknown_revision(repo: Path) -> None:
    done = run(repo, "waiver: WAIVER-010\n", "no-such-revision", "HEAD")
    assert done.returncode != 0
    assert "fatal" in done.stderr
