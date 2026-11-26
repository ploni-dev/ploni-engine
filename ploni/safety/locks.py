"""A lock on an open file that says a live run is using what it guards.

Why: the start-up sweeps remove what crashed runs left, and must not remove what a run that
is still working uses (issue #212: a second process's sweep wrote zeros over a live run's
open temp file). Achia chose on 2026-11-26 "Each run locks its own (Recommended)": each run
holds a lock on its own temp folder and on each half-written file while it works; the
operating system frees the lock if the run crashes; the sweeps skip what is still locked
(issue #212, issuecomment-7188059248).

Contract: `again` tries an action again, a few times with a short pause, when it fails with
an error that two runs meeting can cause; the safety helpers use it where they meet another run
(Achia, 2026-11-26, "All four (Recommended)", #212, issuecomment-7191184897). `hold` takes the
lock on an open file and keeps it until that file is closed or its
process ends, however it ends. `take` opens a file, made when it is missing, and takes its
lock, or gives None when another handle holds it: `tempfiles.sweep` keeps what it takes while
it removes the folder, so that no run can begin to use it in between (the review of b7390ae,
finding 1); `atomic.sweep_partials` gives it back before it removes the file.
The lock is the operating system's: on Windows a lock of the file's byte 0
(`msvcrt.locking`), elsewhere `fcntl.flock`. Two handles of one file in one process count as
two holders, as two processes do.

Known limits:
- A lock is advisory: it stops code that asks for it, these helpers, and nothing else. A
  program that does not ask reads and writes the file as before (on Windows, byte 0 of a
  held file cannot be read or written through another handle).
- On a network share the lock may not reach other machines; a product folder on the local
  disk is assumed.
- Microsoft's page on LockFile says that when a process ends, or closes a file, that holds
  locks, "the time it takes for the operating system to unlock these locks depends upon
  available system resources", and advises unlocking before the close. Measured on the
  laptop: a handle closed by its own process was free at once in 2,000 of 2,000 tries, and
  the lock of a killed process was free within 1.28 ms in 30 kills (the review of b7390ae;
  0.011 s in 3 earlier tries). A slow free costs a sweep that skips a dead entry once, or a
  `hold` or `take` that fails with OSError or None; no data is lost.
"""

import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO

# Who may open a lock file that `take` makes: its owner, as the private folders (tempfiles).
OWNER_READ_WRITE = 0o600
# How often, and after how long a pause, `again` tries an action that met another run: "each
# wait a few hundredths of a second and try again, a few times" (Achia, 2026-11-26, "All four
# (Recommended)", #212). At most four pauses, 0.08 s in all, against the moment in which a start
# can lose the race, measured at a median of 1.0 ms and at most 9.6 ms (the review of b7390ae).
ATTEMPTS = 5
PAUSE_SECONDS = 0.02

if sys.platform == "win32":
    import msvcrt

    def _lock(handle: BinaryIO) -> None:
        """Lock the byte at the handle's position, 0 for every caller here, or raise OSError at once."""
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

else:
    import fcntl

    def _lock(handle: BinaryIO) -> None:
        """Lock the open file for this handle, or raise OSError at once."""
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def hold(handle: BinaryIO) -> None:
    """Take the lock of an open file, for as long as the file stays open.

    Why: a run marks what it is working on, so that another run's sweep leaves it alone.

    Contract:
        Args: handle, a file opened in binary mode by this process, for reading or writing,
            at position 0, as a file just opened is.
        Returns: nothing. The lock is gone when the handle is closed or the process ends.
        Raises: ValueError when the handle is not at position 0 (on Windows the lock is of
            the byte at the position, and `take` asks for byte 0), before anything is locked;
            OSError when another handle, of this process or another, holds the lock.

    Known limits: see the module docstring.
    """
    if handle.tell() != 0:
        raise ValueError("a file is held from position 0")
    _lock(handle)


def take(path: Path) -> BinaryIO | None:
    """Open a file and take its lock; None when another handle holds it.

    Why: a sweep must keep the lock of what it removes until it is removed. A question that
    gives the lock back at once leaves a moment in which a starting run takes it and begins,
    and the sweep then removes what that run is writing (the review of b7390ae, finding 1).

    Contract:
        Args: path, a file; made, empty, when it is missing (for its owner only on POSIX;
            Windows keeps only the read-only bit of a mode). A link is followed: a caller
            that must not follow one looks first, as `tempfiles.sweep` does.
        Returns: the open handle, holding the lock, which the caller closes; or None, the
            file left as it was, when another handle holds the lock.
        Raises: OSError when the file cannot be opened for reading and writing (a folder in
            its place, for one).

    Known limits: see the module docstring. A file that `take` made stays when the caller
    does not remove it.
    """
    handle = os.fdopen(os.open(path, os.O_RDWR | os.O_CREAT, OWNER_READ_WRITE), "r+b")
    try:
        _lock(handle)
    except OSError:
        handle.close()
        return None
    return handle


def again[T](action: Callable[[], T], errors: tuple[type[BaseException], ...]) -> T:
    """Run an action; when it fails with one of the errors given, pause and run it again, a few times.

    Why: two runs that meet in one folder can refuse each other for a moment (a file the other
    has open, a lock it holds); a few hundredths of a second later the moment is over (#212).

    Contract:
        Args: action, called with no arguments; errors, the kinds that are tried again.
        Returns: what the action returns, from the first try that succeeds.
        Raises: an error of another kind at once; one of the kinds given, the last, when
            ATTEMPTS tries have failed, after ATTEMPTS - 1 pauses of PAUSE_SECONDS.

    Known limits: an action that is not safe to run twice must not be given; the callers give
    a rename, a removal, a take, a start that leaves nothing when it fails, and a write that
    makes a new partial file each try.
    """
    for _ in range(ATTEMPTS - 1):
        try:
            return action()
        except errors:
            time.sleep(PAUSE_SECONDS)
    return action()
