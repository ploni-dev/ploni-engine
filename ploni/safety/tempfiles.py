"""The only sanctioned way to get a temp folder: private, and gone when the work is over.

Why: a temp file that holds document text and survives, after an error or a crash, is one of
the loudest ways this product could leak (ADR-0005; `CLAUDE.md`, Hard constraints: "No
document text in logs or temp files"). So temp files live in one folder that only this user
can open, exist only while a block of code runs, and are overwritten before they are
removed; what a crashed run left behind is removed when the next one starts.

Contract: `private_dir` gives a new folder for the length of a `with` block. `sweep` removes
what earlier runs left under the same root. `NotRemoved` is raised when a folder cannot be
removed.

Known limits:
- Overwriting a file does not reach every copy of its bytes on a solid-state disk or on a
  file system that writes changed blocks elsewhere. Full-disk encryption is what covers
  those; the overwrite covers a plain undelete.
- Inside the block the temp folder of the whole process is the private one, so that a
  library that asks `tempfile` for a file gets one there. That is process-wide state: two
  threads that each hold a block share whichever was entered last.
- A process started from inside the block chooses its own temp folder.
- A file that is still open when the block ends cannot be removed on Windows. The block
  then ends with `NotRemoved`, and `sweep` removes the file on the next start.
"""

import os
import shutil
import stat
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

# How the name of every folder made here begins. `sweep` removes folders with this beginning
# and nothing else.
PREFIX = "ploni-"

# Zeros are written in pieces of this size, so that a large file needs no large buffer.
CHUNK = 1024 * 1024


class NotRemoved(OSError):
    """A temp folder is still there after the attempt to remove it.

    Why: a folder that stays may hold document text, so this must not pass in silence.

    Contract: the message names the private folder, whose name is random, and nothing
    else: the name of a file in it may come from a document, and the path above it
    holds the user's name.

    Known limits: what stopped the removal is not carried.
    """


def _unlock(folder: Path) -> None:
    """Make every folder and file under the folder writable.

    A read-only file cannot be written over anywhere, and cannot be removed on Windows; the
    entries of a read-only folder cannot be removed on a POSIX system. A link is left as it
    is: its target lies outside.
    """
    for directory, folders, names in os.walk(folder):
        for name in folders + names:
            entry = Path(directory, name)
            if not entry.is_symlink():
                entry.chmod(stat.S_IRWXU if entry.is_dir() else stat.S_IREAD | stat.S_IWRITE)


def _overwrite(folder: Path) -> None:
    """Write zeros over every regular file under the folder that has no other name elsewhere.

    A link is not followed, so a file outside the folder is never written to, and a file
    that has a second name outside the folder (a hard link) keeps its bytes: they are not
    this folder's alone.
    """
    for directory, _, names in os.walk(folder):
        for name in names:
            file = Path(directory, name)
            info = file.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                continue
            with file.open("r+b") as handle:
                for start in range(0, info.st_size, CHUNK):
                    handle.write(bytes(min(CHUNK, info.st_size - start)))
                handle.flush()
                os.fsync(handle.fileno())


def _remove(folder: Path) -> None:
    """Overwrite and remove one temp folder with everything in it.

    Why: removal is where a leak is closed, so it is one function, used when a block ends
    and when leftovers are swept, and it says so when it fails.

    Contract:
        Args: folder, a folder made by `private_dir`.
        Returns: nothing. The folder is gone.
        Raises: NotRemoved when the folder is still there afterwards, whatever the cause.
            A file that could not be made writable or written over is still removed when
            it can be.

    Known limits: see the module docstring on overwriting and on open files. A read-only
    file that has a second name outside the folder loses its read-only mark there too: the
    mark belongs to the file, not to the name.
    """
    with suppress(OSError):
        try:
            _unlock(folder)
            _overwrite(folder)
        finally:
            shutil.rmtree(folder)
    # Asked of the disk and not of an error: a removal that failed quietly is found too.
    if folder.exists():
        raise NotRemoved(f"the temp folder {folder.name} could not be removed")


@contextmanager
def private_dir(root: Path) -> Iterator[Path]:
    """Give a new, empty folder that exists only for the length of the block.

    Why: code that needs a file on disk for a moment gets it here, in a folder that only
    this user can open and that is gone, overwritten, when the block ends, also when the
    block ends with an error.

    Contract:
        Args: root, the folder that holds the private folders of this product; it is made
            when it is missing.
        Yields: the path of the new folder, under root, its name beginning with PREFIX.
            Inside the block it is also the temp folder of the process, see the module
            docstring.
        Raises: OSError when the folder cannot be made; NotRemoved when it cannot be
            removed at the end. An error of the block itself passes through.

    Known limits: see the module docstring.
    """
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=PREFIX, dir=root))
    before = tempfile.tempdir
    tempfile.tempdir = str(folder)
    try:
        yield folder
    finally:
        tempfile.tempdir = before
        _remove(folder)


def sweep(root: Path) -> int:
    """Remove the temp folders that earlier runs left under root.

    Why: a run that was killed never reached the end of its block, and its folder, with
    whatever was in it, is still on disk. The next start removes it.

    Contract:
        Args: root, the folder given to `private_dir`.
        Returns: how many folders were removed. A root that does not exist gives 0.
            Entries of root whose name does not begin with PREFIX are left alone, and so
            is anything with such a name that is no folder of its own (a file, a link).
        Raises: NotRemoved for the first folder that cannot be removed.

    Known limits: it must not run while another process of this product is at work under
    the same root: that process's folder would be removed under it.
    """
    found = sorted(root.glob(f"{PREFIX}*"))
    left = [folder for folder in found if folder.is_dir() and not folder.is_symlink()]
    for folder in left:
        _remove(folder)
    return len(left)
