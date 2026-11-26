"""Module suite for ploni/safety/locks.py, with the two sweeps: a live run is skipped, a crashed one is swept.

Why: issue #212. Measured at the close of Phase 0: process B's `tempfiles.sweep` wrote zeros
over a file that process A held open in its private folder, and removed A's folder when the
file was closed. Achia chose on 2026-11-26 "Each run locks its own (Recommended)" (issue
#212, issuecomment-7188059248). Each case starts a second Python process, as two runs of the
product are, and kills it where a crash is the case.

Test matrix:

Equivalence classes:
  EC1  a file held by another process -> held; that process killed -> free within
       FREED_WITHIN_SECONDS (the operating system frees the lock of a process that dies; on
       Windows after a short delay, which a next start, seconds later, does not meet)
  EC2  another process inside `tempfiles.private_dir`, a file of its open in its folder, when
       this one sweeps the same root -> the sweep removes nothing (0), the other's folder and
       file keep their bytes, and the other's block ends normally, leaving the root empty
  EC3  another process killed inside `private_dir` -> the next sweep removes its folder and
       its lock file (1), and the root is empty
  EC4  another process inside `atomic.write_atomic`, between the write and the rename, when
       this one sweeps the folder -> `sweep_partials` removes nothing (0); the other's write
       then ends and the target holds all of its bytes
  EC5  another process killed in the same place -> the next `sweep_partials` removes its
       partial file (1), and the target was never made

Known limits: the moments between making a private folder and holding its lock, and between
closing a partial file and renaming it, are not reached here: a sweep that lands there is
the helpers' stated limit. The Hebrew and document-structure axes do not apply: the bytes are
fixed.
"""

import subprocess
import sys
import time
from pathlib import Path

from ploni.safety import atomic, locks, tempfiles

ROOT = Path(__file__).resolve().parents[2]
CONTENT = b"what a live run is still working on"
# How long a lock may stay after its process was killed: Windows frees it "after a delay"
# (ploni/safety/locks.py, Known limits); measured on the laptop at about 0.011 s, three runs.
FREED_WITHIN_SECONDS = 5.0

# Holds the file named by the first argument, says so, and waits until it is killed.
HOLDER = """
import sys, time
from ploni.safety import locks
handle = open(sys.argv[1], "r+b")
locks.hold(handle)
print("ready", flush=True)
time.sleep(600)
"""

# Opens a private folder under the root given, writes a file in it and keeps it open, says
# so with the folder's path, and waits for a line; then ends the block.
WORKER = """
import sys
from pathlib import Path
from ploni.safety import tempfiles
with tempfiles.private_dir(Path(sys.argv[1])) as folder:
    with open(folder / "work.bin", "wb") as handle:
        handle.write(sys.argv[2].encode())
        handle.flush()
        print(folder, flush=True)
        sys.stdin.readline()
"""

# Writes the target given with write_atomic, and stops between the write and the rename to say
# so and wait for a line (the fsync of the partial file is that moment).
WRITER = """
import os, sys
from pathlib import Path
from ploni.safety import atomic
real_fsync = os.fsync
def pause(descriptor):
    real_fsync(descriptor)
    print("ready", flush=True)
    sys.stdin.readline()
atomic.os.fsync = pause
atomic.write_atomic(Path(sys.argv[1]), sys.argv[2].encode())
"""


def started(program: str, *arguments: str) -> tuple[subprocess.Popen[str], str]:
    """Start a program text in a fresh interpreter; return it and the first line it printed."""
    child = subprocess.Popen(  # noqa: S603 fixed argv, no shell
        [sys.executable, "-c", program, *arguments], cwd=ROOT, text=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )  # fmt: skip
    assert child.stdout is not None
    return child, child.stdout.readline().strip()


def killed(child: subprocess.Popen[str]) -> None:
    """Kill a child process, as a crash would, and wait for it to be gone."""
    child.kill()
    child.wait(timeout=60)


def freed(path: Path) -> bool:
    """Wait until no one holds the lock of a file, as the next start of a run would; say whether it came."""
    deadline = time.monotonic() + FREED_WITHIN_SECONDS
    while locks.is_held(path):
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True


def finished(child: subprocess.Popen[str]) -> int:
    """Let a waiting child go on, and return its exit code."""
    child.communicate("go\n", timeout=60)
    return child.returncode


def test_ec1_a_lock_of_another_process_and_a_crash(tmp_path: Path) -> None:
    path = tmp_path / "a"
    path.write_bytes(CONTENT)
    child, line = started(HOLDER, str(path))
    try:
        assert line == "ready"
        assert locks.is_held(path) is True
    finally:
        killed(child)
    assert freed(path)


def test_ec2_a_sweep_skips_a_live_run(tmp_path: Path) -> None:
    child, line = started(WORKER, str(tmp_path), CONTENT.decode())
    try:
        folder = Path(line)
        assert folder.parent == tmp_path
        assert tempfiles.sweep(tmp_path) == 0
        assert (folder / "work.bin").read_bytes() == CONTENT
    except BaseException:
        killed(child)
        raise
    assert finished(child) == 0
    assert list(tmp_path.iterdir()) == []


def test_ec3_a_sweep_removes_a_crashed_run(tmp_path: Path) -> None:
    child, line = started(WORKER, str(tmp_path), CONTENT.decode())
    killed(child)
    folder = Path(line)
    assert folder.is_dir()
    assert freed(folder.with_name(folder.name + tempfiles.LOCK_SUFFIX))
    assert tempfiles.sweep(tmp_path) == 1
    assert list(tmp_path.iterdir()) == []


def test_ec4_a_partial_sweep_skips_a_live_write(tmp_path: Path) -> None:
    target = tmp_path / "out.docx"
    child, line = started(WRITER, str(target), CONTENT.decode())
    try:
        assert line == "ready"
        partials = [entry for entry in tmp_path.iterdir() if entry.name.startswith(atomic.PARTIAL_PREFIX)]
        assert len(partials) == 1
        assert atomic.sweep_partials(tmp_path) == 0
        # Its size, not its bytes: on Windows a held file's first byte cannot be read through
        # another handle (ploni/safety/locks.py, Known limits).
        assert partials[0].stat().st_size == len(CONTENT)
    except BaseException:
        killed(child)
        raise
    assert finished(child) == 0
    assert target.read_bytes() == CONTENT
    assert list(tmp_path.iterdir()) == [target]


def test_ec5_a_partial_sweep_removes_a_crashed_write(tmp_path: Path) -> None:
    target = tmp_path / "out.docx"
    child, line = started(WRITER, str(target), CONTENT.decode())
    killed(child)
    assert line == "ready"
    partials = [entry for entry in tmp_path.iterdir() if entry.name.startswith(atomic.PARTIAL_PREFIX)]
    assert len(partials) == 1
    assert freed(partials[0])
    assert atomic.sweep_partials(tmp_path) == 1
    assert list(tmp_path.iterdir()) == []
