"""Write a file whole or not at all: the only sanctioned way to write an artifact.

Why: an export that stops half-way must not leave half a document where the user expects
the whole one (ADR-0005: "a crash leaves either a complete artifact or none"; build-plan.md
journey S12). The bytes are written to a partial file beside the target, flushed to disk,
and then put in the target's place in one step.

Contract: `write_atomic` leaves the target holding either its old bytes (or no file) or all
of the new ones. When it fails before the rename it tries to remove its partial file, and
the first error passes through. A crash that kills the process before the rename leaves the
partial file behind: `sweep_partials` removes such files from a folder, and leaves the partial
file of a write that is still running, which holds it (`ploni.safety.locks`, issue #212). It must be called
when a run starts, before any export; no caller exists yet (the exporter, Phase 9).

Known limits:
- One file is made whole. A set of files, and the mapping beside them, is not written as
  one: the order and the clean-up of a set are the exporter's (journey S12).
- The partial file is in the target's folder, because a rename is one step only within one
  volume. Until it is swept after a crash it holds the bytes of the artifact. On Windows the
  leading dot of its name does not hide it.
- A partial file is removed, not written over. What it held is no more sensitive than the
  artifact it was meant to become, which is written in plain to the same folder.
- A partial file that cannot be removed after a failure (on Windows, one that another
  program holds open) stays for `sweep_partials`; the first error still passes through.
- An OSError after the rename, from the folder flush on POSIX, means the target already
  holds all the new bytes.
- On Windows the folder itself is not flushed after the rename: the system has no call for
  it. A power cut right after the rename can lose the rename, never half of the bytes.
- The partial file's name is 32 characters longer than the target's. A name that fits the
  file system but not with that tail raises an OSError (FileNotFoundError on Windows,
  although the folder exists), and the target is as it was.
- A target that is a symbolic link is replaced by a plain file with the new bytes; what the
  link pointed to is not changed.
- On Windows a target that is read-only, a folder, or open in another program gives
  PermissionError and is left as it was. On POSIX a read-only target is replaced, as a
  rename does.
- Two writers of one target at once: on Windows some writes fail with PermissionError; the
  target always holds the whole of one of them.
- The new file does not keep the old one's permissions: it gets the default of a new file
  in that folder (on POSIX, 0o666 less the umask).
- A stop that lands after the partial file is made and before the write begins, such as
  Ctrl+C, can leave it, as a crash does. A stop later than that removes it.
"""

import os
import secrets
from contextlib import suppress
from pathlib import Path
from typing import BinaryIO

from ploni.safety import locks

# How the name of every partial file begins. `sweep_partials` removes entries with this
# beginning and nothing else; the leading dot hides them in a POSIX listing.
PARTIAL_PREFIX = ".ploni-partial-"
# Random bytes in a partial file's name (16 hex characters), so that two writers of one
# target do not draw the same name. On Windows two such writers still collide at the rename
# (see Known limits).
NAME_BYTES = 8


def _open_partial(path: Path) -> BinaryIO:
    """Create a partial file for writing; fail if one by that name is there.

    Contract: raises FileExistsError when the name is taken. The one place where the file is
    opened, so that a test can make the write fail.
    """
    return open(path, "xb")


def _sync_folder(folder: Path) -> None:
    """Flush a folder's entries to disk, where the system allows it (not on Windows)."""
    if os.name == "nt":
        return
    descriptor = os.open(folder, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_atomic(path: Path, data: bytes) -> None:
    """Write bytes to a file so that it holds either all of them or what it held before.

    Why: see the module docstring.

    Contract: `path` is the target. The bytes go to a new partial file in the same folder,
    are flushed to disk, and the partial file then replaces the target. On any error before
    the rename, also one that is not an Exception, the partial file is removed if it can be
    and the first error passes through. FileExistsError when the random name of the partial
    file is taken: the file that has the name is left as it is. FileNotFoundError when the
    folder does not exist. An OSError after the rename (the folder flush on POSIX) means the
    target already holds all the new bytes.

    Known limits: see the module docstring.
    """
    partial = path.with_name(f"{PARTIAL_PREFIX}{path.name}.{secrets.token_hex(NAME_BYTES)}")
    # Opened before the try: a name that is taken raises here, and the file that has it is
    # another writer's, which must not be removed.
    handle = _open_partial(partial)
    try:
        with handle:
            # Held while it is written, so that another run's sweep leaves it (issue #212).
            locks.hold(handle)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            locks.release(handle)
        os.replace(partial, path)
    except BaseException:
        # A clean-up that fails must not hide why the write failed; the sweep gets the file.
        with suppress(OSError):
            partial.unlink()
        raise
    _sync_folder(path.parent)


def sweep_partials(folder: Path) -> int:
    """Remove the partial files that a crash left in a folder.

    Why: a process killed between the write and the rename cannot clean up after itself;
    the next run does it.

    Contract: removes the entries directly in `folder` whose names begin with PARTIAL_PREFIX
    and that are not folders, but for a partial file that a live write holds
    (`ploni.safety.locks`, issue #212); returns how many. A symbolic link with the prefix is
    removed itself, without looking at what it points to, which is not touched. Every such entry is tried; when one cannot be
    removed, the first error is raised after the others were tried. A folder that does not
    exist gives 0.

    Known limits:
    - Deeper folders are not looked at. A Windows junction with the prefix is left: it counts
      as a folder.
    - A partial file made by a writer that has not yet held it, or that it has just given
      back before the rename, is taken for a crashed one's in that moment: on POSIX the
      write then fails at the rename, the target as it was; on Windows the open file cannot
      be removed and the sweep raises.
    - An OSError from `locks.is_held` (a partial file that cannot be opened for reading)
      counts as one that cannot be removed: the first such error is raised at the end.
    """
    if not folder.is_dir():
        return 0
    removed = 0
    first: OSError | None = None
    for entry in os.scandir(folder):
        if entry.name.startswith(PARTIAL_PREFIX) and not entry.is_dir(follow_symlinks=False):
            try:
                if not entry.is_symlink() and locks.is_held(Path(entry.path)):
                    continue
                os.unlink(entry.path)
            except OSError as error:
                first = first or error
                continue
            removed += 1
    if first is not None:
        raise first
    return removed
