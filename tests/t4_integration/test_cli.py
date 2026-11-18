"""Module suite for ploni/__main__.py: the command line run as a program of its own.

Why: pytest itself loads modules, so only a fresh interpreter shows whether importing Ploni
and running `selftest` pulls in a networking module (build-plan.md Phase 0, Gate: "`ploni
selftest` prints the model inventory and "offline OK"").

Matrix (`python -m ploni ...` started in the repository):
  M1  selftest                   exit 0; the last line is "offline OK"; the lines before it
                                 are the inventory of models/
  M2  a stub                     exit 2; nothing on the output; one line on the error stream
  M3  no command                 exit 2; a usage line on the error stream

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(*argv: str) -> subprocess.CompletedProcess[str]:
    """Run `python -m ploni` with these arguments in the repository."""
    return subprocess.run([sys.executable, "-m", "ploni", *argv], cwd=ROOT, capture_output=True, text=True, timeout=60, check=False)  # noqa: S603 fixed argv, no shell


def test_m1_selftest() -> None:
    done = run("selftest")
    lines = done.stdout.splitlines()
    assert done.returncode == 0, done.stdout + done.stderr
    assert lines[-1] == "offline OK"
    assert all(line.endswith(" bytes") or line.startswith("no models in ") for line in lines[:-1])


def test_m2_a_stub() -> None:
    done = run("scan")
    assert (done.returncode, done.stdout) == (2, "") and done.stderr.count("\n") == 1


def test_m3_no_command() -> None:
    done = run()
    assert done.returncode == 2 and "usage" in done.stderr
