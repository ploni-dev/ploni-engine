"""Module suite for scripts/check_ratchet.py: the script run as a program on a real git history.

Why: the workflow sees only the exit code of `python -m scripts.check_ratchet <base> <head>`,
run in the checkout with the PR body in PR_BODY. Only a run against git shows that the test
files are counted at both revisions, that a deleted file counts as zero, and that the
suppressions are counted at the head against the ceiling the head's .ratchet.json holds.

Matrix:
  M1  one test function deleted, no override (bad PR 6)    exit 1, the counter and the delta
  M2  the same, with an override line                exit 0
  M3  the same, with an override line and a change under ploni/    exit 1, the refusal
  M4  a noqa line added, the ceiling not raised       exit 1
  M5  a noqa line added, the ceiling raised in the same PR    exit 0
  M6  a test file deleted                            exit 1, both counters to 0
  M7  a revision git does not know                   exit not 0, git's "fatal" line
  M8  no PR_BODY, and a test added                   exit 0
  M9  a suppression in any spelling ruff or mypy honours (no space, several, upper or mixed
      case, `ruff: noqa`, `flake8: noqa`, `mypy: ignore-errors`), the ceiling not raised
                                                     exit 1: each counts
  M11 room left under the ceiling, and a PR adds a suppression without raising it    exit 1:
      the rise shows only in a raised ceiling
  M12 a test file saved with a UTF-8 byte order mark loses a test    exit 1, counted
  M13 a Hebrew test-file name loses a test           exit 1, the name whole
  M14 shown() of a missing file is "", of a file its text; suppressions() counts, and raises
      CalledProcessError on a revision git does not know
  M10 a helper under tests/ loses a test-named function, and a Markdown file changes
                                                     exit 0: neither is a counted test file

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import check_ratchet as check

REPOSITORY = Path(__file__).resolve().parents[2]
GIT = ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "core.autocrlf=false"]
TESTS = "tests/t1_unit/test_a.py"
TWO = "def test_one():\n    assert 1\n\n\ndef test_two():\n    assert 2\n"
ONE = "def test_one():\n    assert 1\n"


def git(folder: Path, *args: str) -> None:
    """Run one git command in folder, failing the test when git fails."""
    subprocess.run([*GIT, *args], cwd=folder, check=True, capture_output=True, timeout=60)  # noqa: S603 fixed argv, no shell


def write(folder: Path, path: str, text: str) -> None:
    """Write a file at path under folder, making its folders."""
    target = folder / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Return a git repository whose base holds a test file of two tests and a ceiling of 1."""
    git(tmp_path, "init", "-q")
    write(tmp_path, TESTS, TWO)
    write(tmp_path, "ploni/a.py", "import os  # noqa: F401 kept\n")
    write(tmp_path, ".ratchet.json", '{"suppressions_ceiling": 1}\n')
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
    # GitHub's runners write UTF-8; a pipe on Windows would use the local code page, which
    # cannot write a Hebrew path (the script's Known limits).
    environment["PYTHONIOENCODING"] = "utf-8"
    if body is not None:
        environment["PR_BODY"] = body
    return subprocess.run(  # noqa: S603 fixed argv, no shell
        [sys.executable, "-m", "scripts.check_ratchet", *revisions],
        cwd=folder,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )


def test_m1_one_test_deleted(repo: Path) -> None:
    write(repo, TESTS, ONE)
    commit(repo)
    done = run(repo, "", "HEAD^1", "HEAD")
    assert done.returncode == 1 and done.stdout == ""
    assert done.stderr.splitlines() == [f"{TESTS}: test functions 2 -> 1 (-1)", f"{TESTS}: assertions 2 -> 1 (-1)"]


def test_m2_with_an_override(repo: Path) -> None:
    write(repo, TESTS, ONE)
    commit(repo)
    body = f"ratchet-override: {TESTS} -1 merged into one\nratchet-override: {TESTS} -1 its assertion with it\n"
    done = run(repo, body, "HEAD^1", "HEAD")
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_m3_an_override_and_ploni(repo: Path) -> None:
    write(repo, TESTS, ONE)
    write(repo, "ploni/a.py", "import os  # noqa: F401 kept\nX = 1\n")
    commit(repo)
    body = f"ratchet-override: {TESTS} -1 merged\nratchet-override: {TESTS} -1 merged\n"
    done = run(repo, body, "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines()[0] == "ratchet-override refused: the PR changes files under ploni/"


def test_m4_a_noqa_without_the_ceiling(repo: Path) -> None:
    write(repo, "ploni/b.py", "import sys  # noqa: F401 kept\n")
    commit(repo)
    done = run(repo, "", "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == ["suppressions 2, ceiling 1 in .ratchet.json: raise suppressions_ceiling in the PR that adds one"]


def test_m5_a_noqa_with_the_ceiling_raised(repo: Path) -> None:
    write(repo, "ploni/b.py", "import sys  # type: ignore[import]\n")
    write(repo, ".ratchet.json", '{"suppressions_ceiling": 2}\n')
    commit(repo)
    done = run(repo, "", "HEAD^1", "HEAD")
    assert (done.returncode, done.stderr) == (0, "")


@pytest.mark.parametrize(
    "line",
    [
        "x = 1  #type:ignore\n",
        "x = 1  #  type:  ignore[misc]\n",
        "import os  #noqa\n",
        "import os  # NOQA\n",
        "import os  # NoQA: F401\n",
        "# ruff: noqa\n",
        "# ruff: noqa: F401\n",
        "# flake8: noqa\n",
        "# mypy: ignore-errors\n",
        "x = 1  # Type: Ignore\n",
    ],
)
def test_m9_a_suppression_written_tight_or_wide(repo: Path, line: str) -> None:
    write(repo, "ploni/c.py", line)
    commit(repo)
    done = run(repo, "", "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == ["suppressions 2, ceiling 1 in .ratchet.json: raise suppressions_ceiling in the PR that adds one"]


def test_m10_files_that_are_not_counted(repo: Path) -> None:
    write(repo, "tests/helper.py", "def test_like():\n    assert 1\n")
    commit(repo)
    write(repo, "tests/helper.py", "X = 1\n")
    write(repo, "docs/a.md", "not python: [\n")
    commit(repo)
    done = run(repo, "", "HEAD^1", "HEAD")
    assert (done.returncode, done.stderr) == (0, "")


def test_m11_a_rise_under_room_left_in_the_ceiling(repo: Path) -> None:
    write(repo, ".ratchet.json", '{"suppressions_ceiling": 3}\n')
    commit(repo)
    write(repo, "ploni/b.py", "import sys  # noqa: F401 kept\n")
    commit(repo)
    done = run(repo, "", "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == [
        "suppressions rose by 1 (1 -> 2), suppressions_ceiling by 0 (3 -> 3): raise it in .ratchet.json by the rise"
    ]


def test_m12_a_test_file_with_a_byte_order_mark(repo: Path) -> None:
    (repo / TESTS).write_bytes(b"\xef\xbb\xbf" + ONE.encode("utf-8"))
    commit(repo)
    done = run(repo, "", "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == [f"{TESTS}: test functions 2 -> 1 (-1)", f"{TESTS}: assertions 2 -> 1 (-1)"]


def test_m13_a_hebrew_test_file_name(repo: Path) -> None:
    name = "tests/t1_unit/test_שמות.py"
    write(repo, name, TWO)
    commit(repo)
    write(repo, name, ONE)
    commit(repo)
    done = run(repo, "", "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == [f"{name}: test functions 2 -> 1 (-1)", f"{name}: assertions 2 -> 1 (-1)"]


def test_m14_shown_and_suppressions_on_their_own(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(repo)
    assert check.shown("HEAD", "missing.py") == ""
    assert check.shown("HEAD", TESTS).replace("\r\n", "\n") == TWO
    assert check.suppressions("HEAD") == 1
    with pytest.raises(subprocess.CalledProcessError):
        check.suppressions("no-such-revision")


def test_m6_a_test_file_deleted(repo: Path) -> None:
    git(repo, "rm", "-q", TESTS)
    commit(repo)
    done = run(repo, "", "HEAD^1", "HEAD")
    assert done.returncode == 1
    assert done.stderr.splitlines() == [f"{TESTS}: test functions 2 -> 0 (-2)", f"{TESTS}: assertions 2 -> 0 (-2)"]


def test_m7_an_unknown_revision(repo: Path) -> None:
    done = run(repo, "", "no-such-revision", "HEAD")
    assert done.returncode != 0
    assert "fatal" in done.stderr


def test_m8_no_body_and_a_test_added(repo: Path) -> None:
    write(repo, TESTS, TWO + "\n\ndef test_three():\n    assert 3\n")
    commit(repo)
    done = run(repo, None, "HEAD^1", "HEAD")
    assert (done.returncode, done.stderr) == (0, "")
