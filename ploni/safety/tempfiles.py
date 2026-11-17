"""A private temp folder that is gone when the work is over: the only sanctioned way to get one.

Why: a temp file that holds document text and survives, after an error or a crash, is one of
the loudest ways this product could leak (ADR-0005; `CLAUDE.md`, Hard constraints: "No
document text in logs or temp files"). So temp files live in one folder that only this user
can open, exist only while a block of code runs, and are written over before they are
removed; what a crashed run left behind is removed when the next one starts.

Contract: `private_dir` gives a new folder for the length of a `with` block. `sweep` removes
what earlier runs left under the same root. `NotRemoved` is raised when a folder cannot be
removed. No file outside the folder is written over or removed: a link, of any kind, is
never followed, also when it stands in the place of the private folder itself. One thing
outside can change, the read-only mark of a file that has a name inside too (below).

Known limits:
- All of this holds while nothing else changes the folder during the removal. Code that
  swaps a folder for a link between the moment the module looks and the moment it removes
  is not guarded against: on Windows the standard removal has no such guard either.
- What is written over is the main content of a file that is still in the folder when the
  block ends, on a disk that writes in place. Not reached: a file its maker deleted inside
  the block; the name of a file; an alternate data stream of a file on NTFS; a file that
  NTFS keeps compressed; any copy of the bytes that a solid-state disk or a file system
  that writes changed blocks elsewhere still holds. Full-disk encryption is what covers
  those.
- A file that has a name outside the folder too (a hard link) is not written over: its
  bytes are not this folder's alone. The name inside is removed.
- A file that cannot be opened for writing is removed without being written over, and no
  error says so: a `tempfile.TemporaryFile` that is still open on Windows, for one.
- Inside the block the temp folder that the `tempfile` module hands out is the private
  one, for the whole process, so that a library that asks `tempfile` for a file gets one
  there. Code that found the temp folder before the block began, native code that asks
  the system, and a process started from inside the block are not redirected: the
  variables TEMP, TMP and TMPDIR are not changed.
- With several blocks open at once, in threads, a `tempfile` call lands in the folder of
  the block that was entered last and is still open, whichever thread makes it. So a file
  that one thread made through `tempfile` goes when that newest block ends, also when
  the thread that made it still uses it.
- A file that other code holds open with a plain `open` when the block ends is written
  over but cannot be removed on Windows. The block then ends with `NotRemoved`, and
  `sweep` removes the file on the next start.
- A read-only file that has a second name outside the folder is made writable there too:
  the mark belongs to the file, not to the name.
"""

import os
import shutil
import stat
import tempfile
import threading
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

# How the name of every folder made here begins. `sweep` removes folders with this beginning
# and nothing else.
PREFIX = "ploni-"

# Zeros are written in pieces of this size, so that a large file needs no large buffer.
CHUNK = 1024 * 1024

# Only the owner may read, write and list the folders made here.
OWNER_ONLY = 0o700

# The folders of the blocks that are open, oldest first, behind the temp folder that the
# process had before the first of them. Empty when no block is open.
_OPEN: list[str | None] = []
_LOCK = threading.Lock()


class NotRemoved(OSError):
    """A temp folder is still there after the attempt to remove it.

    Why: a folder that stays may hold document text, so this must not pass in silence.

    Contract: the message names the private folder, whose name is random, and nothing
    else: the name of a file in it may come from a document, and the path above it
    holds the user's name.

    Known limits: what stopped the removal is not carried. When the block itself ended
    with an error, that error is this one's context.
    """


def _is_link(path: Path) -> bool:
    """Say whether a path is a link of any kind: a symbolic link, or a junction on Windows."""
    return path.is_symlink() or path.is_junction()


def _walk(folder: Path) -> Iterator[tuple[Path, list[str], list[str]]]:
    """Walk the folders under a folder as `os.walk` does, never through a link.

    `os.walk` does not follow a symbolic link but does walk into a junction, the folder
    link of Windows, which needs no special right to make. What lies behind a link is
    outside the folder, so a link to a folder is neither listed nor entered.
    """
    for directory, folders, names in os.walk(folder):
        here = Path(directory)
        folders[:] = [name for name in folders if not _is_link(here / name)]
        yield here, folders, names


def _unlock(folder: Path) -> None:
    """Make everything in a folder writable, the folder itself included.

    A read-only file cannot be written over anywhere, and cannot be removed on Windows; the
    entries of a read-only folder cannot be removed on a POSIX system. A link is left as it
    is: its target lies outside. An entry that resists is passed over, so that one such
    entry does not leave the others locked.
    """
    with suppress(OSError):
        folder.chmod(folder.stat().st_mode | OWNER_ONLY)
    for directory, folders, names in _walk(folder):
        for entry in (directory / name for name in folders + names):
            with suppress(OSError):
                if not _is_link(entry):
                    mode = entry.lstat().st_mode
                    # A file is opened for reading and writing to be written over, so it needs both.
                    entry.chmod(mode | (OWNER_ONLY if stat.S_ISDIR(mode) else stat.S_IREAD | stat.S_IWRITE))


def _own_files(folder: Path) -> list[tuple[Path, int]]:
    """Return every regular file under the folder all of whose names are inside it, with its size.

    A file that has a name outside the folder too (a hard link) is left out: its bytes are
    not this folder's alone. A file with several names inside is given once. Files are told
    apart by the number the file system gives them; where it gives none, every name is
    taken as a file of its own.
    """
    found: dict[object, tuple[Path, os.stat_result]] = {}
    names: Counter[object] = Counter()
    for directory, _, files in _walk(folder):
        for file in (directory / name for name in files):
            with suppress(OSError):
                info = file.lstat()
                if stat.S_ISREG(info.st_mode):
                    key = (info.st_dev, info.st_ino) if info.st_ino else file
                    names[key] += 1
                    found.setdefault(key, (file, info))
    return [(file, info.st_size) for key, (file, info) in found.items() if names[key] == info.st_nlink]


def _overwrite(folder: Path) -> None:
    """Write zeros over every file that is the folder's own.

    A file that cannot be opened is passed over, so that one such file does not leave the
    others as they were.
    """
    for file, size in _own_files(folder):
        with suppress(OSError), file.open("r+b") as handle:
            for start in range(0, size, CHUNK):
                handle.write(bytes(min(CHUNK, size - start)))
            handle.flush()
            os.fsync(handle.fileno())


def _remove(folder: Path) -> None:
    """Remove one temp folder with everything in it, written over first.

    Why: removal is where a leak is closed, so it is one function, used when a block ends
    and when leftovers are swept, and it says so when it fails.

    Contract:
        Args: folder, a folder made by `private_dir`, or one that `sweep` found.
        Returns: nothing. The folder is gone.
        Raises: NotRemoved when the folder is still there afterwards, whatever the cause.
            A file that could not be made writable or written over is still removed when
            it can be. A link in the place of the folder is not gone through and not
            removed, so it gives NotRemoved. An interrupt while files are being written
            over passes through, after the folder was removed.

    Known limits: see the module docstring on what is written over and on open files.
    """
    try:
        # Looked at here and not only below the folder: a block can put a link in its place.
        if not _is_link(folder):
            _unlock(folder)
            _overwrite(folder)
    finally:
        # Also after an interrupt: files not yet written over must not stay on disk.
        with suppress(OSError):
            shutil.rmtree(folder)
    # Asked of the disk and not of an error: a removal that failed quietly is found too.
    if folder.exists():
        raise NotRemoved(f"the temp folder {folder.name} could not be removed")


@contextmanager
def _as_temp_of_process(folder: Path) -> Iterator[None]:
    """Make a folder the one that `tempfile` hands out, for the length of the block.

    Blocks may overlap and end in any order, in threads. While any block is open the
    folder of the newest open block is the one handed out; when the last one ends, what
    the process had before the first is put back.
    """
    name = str(folder)
    with _LOCK:
        if not _OPEN:
            _OPEN.append(tempfile.tempdir)
        _OPEN.append(name)
        tempfile.tempdir = name
    try:
        yield
    finally:
        with _LOCK:
            _OPEN.remove(name)
            tempfile.tempdir = _OPEN[-1]
            if len(_OPEN) == 1:
                _OPEN.clear()


@contextmanager
def private_dir(root: Path) -> Iterator[Path]:
    """Give a new, empty folder that exists only for the length of the block.

    Why: code that needs a file on disk for a moment gets it here, in a folder that only
    this user can open and that is gone, written over, when the block ends, however the
    block ends.

    Contract:
        Args: root, the folder that holds the private folders of this product; it is made
            when it is missing, for its owner only.
        Yields: the path of the new folder, under root, its name beginning with PREFIX.
            Inside the block it is also the folder that `tempfile` hands out, see the
            module docstring.
        Raises: OSError when the folder cannot be made, and ValueError for a root that
            no path can be (one with a null character); NotRemoved when the folder cannot
            be removed at the end, also in place of an error of the block itself.
            Otherwise an error of the block passes through.

    Known limits: see the module docstring.
    """
    root.mkdir(mode=OWNER_ONLY, parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=PREFIX, dir=root))
    try:
        with _as_temp_of_process(folder):
            yield folder
    finally:
        _remove(folder)


def sweep(root: Path) -> int:
    """Remove the temp folders that earlier runs left under root.

    Why: a run that was killed never reached the end of its block, and its folder, with
    whatever was in it, is still on disk. The next start removes it.

    Contract:
        Args: root, the folder given to `private_dir`.
        Returns: how many folders were removed. A root that does not exist gives 0.
            Only a folder directly under root whose name begins with PREFIX is removed,
            whoever made it; on Windows the beginning is matched in any case of letters.
            A file and a link with such a name are left alone.
        Raises: NotRemoved, after every folder was tried, for the first one that could
            not be removed.

    Known limits: it must not run while another process of this product is at work under
    the same root: that process's folder would be removed under it. A folder that can
    never be removed is tried, and reported, at every start.
    """
    left = [folder for folder in sorted(root.glob(f"{PREFIX}*")) if folder.is_dir() and not _is_link(folder)]
    stuck: list[NotRemoved] = []
    for folder in left:
        try:
            _remove(folder)
        except NotRemoved as error:
            stuck.append(error)
    if stuck:
        raise stuck[0]
    return len(left)
