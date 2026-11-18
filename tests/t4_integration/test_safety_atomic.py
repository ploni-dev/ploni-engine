"""Module suite for ploni/safety/atomic.py: a process killed between the write and the rename.

Why: a crash simulated inside pytest runs the module's own clean-up. A real crash does not:
the process is gone, and the partial file stays on disk. Only a separate process that dies
between the write and the rename shows what the next run finds, and that `sweep_partials`
removes it (build-plan.md Phase 0: "simulated crash between write and rename"; journey S12).

Matrix (one program per case, killed with os._exit at the rename):
  M1  a target that is already there    after the kill the target holds the old bytes; one
                                        partial file is left; sweep_partials removes it and
                                        returns 1; the target is untouched
  M2  no target yet                     after the kill there is no target; one partial file
  M3  the same program not killed       the target holds the new bytes; nothing else is left

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from ploni.safety import atomic

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = """
import os, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from ploni.safety import atomic
if sys.argv[3] == "kill":
    atomic.os.replace = lambda source, destination: os._exit(9)
atomic.write_atomic(Path(sys.argv[2]), "ישראל ישראלי".encode())
"""


def run(target: Path, mode: str) -> int:
    """Run the program on a target, killed at the rename or not, and return its exit code."""
    done = subprocess.run([sys.executable, "-c", PROGRAM, str(ROOT), str(target), mode], capture_output=True, timeout=60, check=False)
    return done.returncode


def partials(folder: Path) -> list[str]:
    """Return the names of the partial files in a folder."""
    return [name for name in os.listdir(folder) if name.startswith(atomic.PARTIAL_PREFIX)]


@pytest.mark.parametrize("existing", [True, False])
def test_m1_m2_killed_between_the_write_and_the_rename(tmp_path: Path, existing: bool) -> None:
    target = tmp_path / "out.docx"
    if existing:
        target.write_bytes(b"old")
    assert run(target, "kill") == 9
    assert (target.read_bytes() == b"old") if existing else not target.exists()
    assert len(partials(tmp_path)) == 1
    assert atomic.sweep_partials(tmp_path) == 1
    assert partials(tmp_path) == []
    assert (target.read_bytes() == b"old") if existing else not target.exists()


def test_m3_not_killed(tmp_path: Path) -> None:
    target = tmp_path / "out.docx"
    assert run(target, "write") == 0
    assert target.read_bytes() == "ישראל ישראלי".encode() and os.listdir(tmp_path) == ["out.docx"]
