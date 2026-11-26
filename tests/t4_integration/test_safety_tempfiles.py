"""Module suite for ploni/safety/tempfiles.py: the module used by programs of their own.

Why: the unit tests and the canary test run inside one pytest process. What matters for a temp
folder is what is on disk after a program has ended, in each way a program ends, and what the
next program finds. Only separate processes show that.

Matrix (each program gets a root in a temp folder of the test):
  M1  a program works in a block, writes through the folder and through plain tempfile calls,
      and ends normally                  exit code 0, and the root holds nothing
  M2  a program's block ends in an error that nothing catches
                                         exit code 1, the error on the standard error, and
                                         the root holds nothing
  M3  programs are killed inside their block, one after the other, and then one ends normally.
      Every program sweeps when it starts
                                         a killed program leaves its folder and its lock
                                         file; the next one reports 1 swept; after the last
                                         the root holds nothing

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PROGRAM = """
import os, sys, tempfile
from pathlib import Path
from ploni.safety import tempfiles

root, ending = Path(sys.argv[1]), sys.argv[2]
swept = tempfiles.sweep(root)
with tempfiles.private_dir(root) as folder:
    (folder / "page.txt").write_text("text of a page", encoding="utf-8")
    with tempfile.NamedTemporaryFile(delete=False) as kept:
        kept.write(b"bytes of a library")
    sys.stdout.write(f"swept={swept} inside={len(list(folder.iterdir()))}")
    sys.stdout.flush()
    if ending == "error":
        raise RuntimeError("stopped")
    if ending == "kill":
        os._exit(9)
"""


def run(root: Path, ending: str) -> subprocess.CompletedProcess[bytes]:
    """Start the program on a root and return how it ended."""
    command = [sys.executable, "-c", PROGRAM, str(root), ending]
    return subprocess.run(command, cwd=ROOT, capture_output=True, check=False)  # noqa: S603 fixed argv, no shell


def test_m1_a_program_that_ends_normally_leaves_nothing(tmp_path: Path) -> None:
    ended = run(tmp_path, "normal")
    assert (ended.returncode, ended.stdout, ended.stderr) == (0, b"swept=0 inside=2", b"")
    assert list(tmp_path.iterdir()) == []


def test_m2_a_program_that_ends_in_an_error_leaves_nothing(tmp_path: Path) -> None:
    ended = run(tmp_path, "error")
    assert ended.returncode == 1
    assert ended.stdout == b"swept=0 inside=2"
    assert b"RuntimeError: stopped" in ended.stderr
    assert list(tmp_path.iterdir()) == []


def test_m3_the_next_program_sweeps_what_killed_ones_left(tmp_path: Path) -> None:
    assert [run(tmp_path, "kill").returncode, run(tmp_path, "kill").returncode] == [9, 9]
    # The second killed program swept the first one's folder before it made its own: one
    # folder is left, with its lock file beside it (issue #212).
    entries = list(tmp_path.iterdir())
    assert len([entry for entry in entries if entry.is_dir()]) == 1
    assert len([entry for entry in entries if entry.name.endswith(".lock")]) == 1
    assert len(entries) == 2
    assert run(tmp_path, "kill").stdout == b"swept=1 inside=2"
    ended = run(tmp_path, "normal")
    assert (ended.returncode, ended.stdout) == (0, b"swept=1 inside=2")
    assert list(tmp_path.iterdir()) == []
