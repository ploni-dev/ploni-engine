"""Write a file whole or not at all: the only sanctioned way to write an artifact.

Why: an export that stops half-way must not leave half a document where the user expects
the whole one (ADR-0005: "a crash leaves either a complete artifact or none"; build-plan.md
journey S12). The bytes are written to a partial file beside the target, flushed to disk,
and then put in the target's place in one step.

Contract: `write_atomic` leaves the target holding either its old bytes (or no file) or all
of the new ones. When it fails it removes its partial file and the error passes through.
A crash that kills the process before the rename leaves the partial file behind:
`sweep_partials` removes such files from a folder, and is called when the next run starts.

Known limits:
- The partial file is in the target's folder, because a rename is one step only within one
  volume. Until it is swept after a crash it holds the bytes of the artifact.
- A partial file is removed, not written over. What it held is no more sensitive than the
  artifact it was meant to become, which is written in plain to the same folder.
- On Windows the folder itself is not flushed after the rename: the system has no call for
  it. A power cut right after the rename can lose the rename, never half of the bytes.
- On Windows the rename fails when another program holds the target open; the error
  passes through and the target is as it was.
"""

import os
import secrets
from contextlib import suppress
from pathlib import Path
from typing import BinaryIO

# How the name of every partial file begins. `sweep_partials` removes files with this
# beginning and nothing else; the leading dot hides them in a POSIX listing.
PARTIAL_PREFIX = ".ploni-partial-"
# Random bytes in a partial file's name, so that two writers of one target never share it.
NAME_BYTES = 8


def open_partial(path: Path) -> BinaryIO:
    """Create a partial file for writing; fail if one by that name is there.

    Why: the one place where the file is opened, so that a test can make the write fail.
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

    Contract: `path` is the target; its folder must exist (FileNotFoundError otherwise).
    The bytes go to a new partial file in the same folder, are flushed to disk, and the
    partial file then replaces the target. On any error, also one that is not an
    Exception, the partial file is removed and the error passes through.
    """
    partial = path.with_name(f"{PARTIAL_PREFIX}{path.name}.{secrets.token_hex(NAME_BYTES)}")
    try:
        with open_partial(partial) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(partial, path)
    except BaseException:
        with suppress(FileNotFoundError):
            partial.unlink()
        raise
    _sync_folder(path.parent)


def sweep_partials(folder: Path) -> int:
    """Remove the partial files that a crash left in a folder, and return how many.

    Why: a process killed between the write and the rename cannot clean up after itself;
    the next run does it.

    Contract: removes the files directly in `folder` whose names begin with PARTIAL_PREFIX;
    not folders, not deeper files. A folder that does not exist gives 0. A link with the
    prefix is removed itself; what it points to is not touched.
    """
    if not folder.is_dir():
        return 0
    removed = 0
    for entry in os.scandir(folder):
        if entry.name.startswith(PARTIAL_PREFIX) and not entry.is_dir(follow_symlinks=False):
            os.unlink(entry.path)
            removed += 1
    return removed
