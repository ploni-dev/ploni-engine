"""A lock on an open file that says a live run is using what it guards.

Why: the start-up sweeps remove what crashed runs left, and must not remove what a run that
is still working uses (issue #212: a second process's sweep wrote zeros over a live run's
open temp file). Achia chose on 2026-11-26 "Each run locks its own (Recommended)": each run
holds a lock on its own temp folder and on each half-written file while it works; the
operating system frees the lock if the run crashes; the sweeps skip what is still locked
(issue #212, issuecomment-7188059248).

Contract: `hold` takes the lock on an open file and keeps it until that file is closed or its
process ends, however it ends. `is_held` says whether anyone holds the
lock of a file, by trying to take it for a moment. The lock is the operating system's: on Windows a lock of
the file's first byte (`msvcrt.locking`), elsewhere `fcntl.flock`. Two handles of one file
in one process count as two holders, as two processes do.

Known limits:
- A lock is advisory: it stops code that asks for it, these helpers, and nothing else. A
  program that does not ask reads and writes the file as before (on Windows, the first byte
  of a held file cannot be read or written through another handle).
- `is_held` takes the lock for a moment when it is free: a `hold` by someone else in that
  moment fails with OSError. Only the sweeps call `is_held`, at a run's start.
- On a network share the lock may not reach other machines; a product folder on the local
  disk is assumed.
- Windows frees the lock of a process that ended "after a delay" that "depends upon
  available system resources" (the documentation of LockFile); measured on the laptop at
  about 0.011 s after the process was gone. A sweep in that moment leaves what it guards, for
  the next start. A handle closed by its own process frees its lock at once (measured: an
  explicit unlock before the close changed no case, under mutation testing).
"""

import sys
from pathlib import Path
from typing import BinaryIO

if sys.platform == "win32":
    import msvcrt

    def _lock(handle: BinaryIO) -> None:
        """Lock the first byte of the open file for this handle, or raise OSError at once."""
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
            at position 0, as a file just opened is (on Windows the lock is of the byte at
            the handle's position, and `is_held` asks for byte 0).
        Returns: nothing. The lock is gone when the handle is closed or the process ends.
        Raises: OSError when another handle, of this process or another, holds the lock.

    Known limits: see the module docstring.
    """
    _lock(handle)


def is_held(path: Path) -> bool:
    """Say whether anyone holds the lock of a file.

    Why: a sweep removes what is not held and leaves what is.

    Contract:
        Args: path, a file.
        Returns: True when another handle holds the lock; False when no one does, and for a
            file that does not exist. The file's bytes are not changed, and it is left free.
        Raises: OSError other than FileNotFoundError when the file cannot be opened for
            reading (a folder, for one).

    Known limits: see the module docstring.
    """
    try:
        handle = open(path, "rb")
    except FileNotFoundError:
        return False
    with handle:
        try:
            _lock(handle)
        except OSError:
            return True
    return False
