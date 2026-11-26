"""Test matrix for ploni/safety/locks.py: a lock that marks a file as in use by a live run.

Why: the start-up sweeps remove what crashed runs left, and must not remove what a live run
still uses (issue #212). Achia chose on 2026-11-26 "Each run locks its own (Recommended)":
each run holds a lock on its own temp folder and on each half-written file while it works,
the operating system frees the lock if the run crashes, and the sweeps skip what is still
locked (issue #212, issuecomment-7188059248). These cases run in one process, through two
handles of one file; the cases across processes, a crash among them, are
tests/t4_integration/test_safety_locks.py.

hold. Equivalence classes:
  EC1  a file opened for writing, held -> another handle sees it held
  EC2  the holding handle closed -> no longer held
  EC3  a file held by another handle, held again -> OSError, and the first stays held
  EC4  the owner writes, reads and flushes through the held handle -> as without the lock
is_held. Equivalence classes:
  EC5  a file no one holds -> False, and the file is not changed (bytes, size)
  EC6  a missing file -> False
  EC7  after is_held, the file is free: a hold on it succeeds
  EC8  a file opened for reading only, by someone who does not hold it -> no effect on is_held
Boundaries:
  B1  an empty file, held and asked -> the same as a file with bytes
  B2  a file whose name is Hebrew -> the same
Error paths:
  E1  is_held of a folder -> OSError (not FileNotFoundError), nothing changed

Known limits: two handles of one process stand in for two processes here; that a lock of
another process counts, and that a crash frees it, is the integration suite. The document-
structure and Hebrew text axes do not apply beyond B2: no document text is read.
"""

from pathlib import Path
from typing import BinaryIO

import pytest

from ploni.safety import locks


def held_file(path: Path, data: bytes = b"") -> BinaryIO:
    """Create a file with the bytes given and hold it; return the open handle, which the case closes."""
    path.write_bytes(data)
    handle = open(path, "r+b")
    locks.hold(handle)
    return handle


def test_ec1_a_held_file_is_seen_held(tmp_path: Path) -> None:
    handle = held_file(tmp_path / "a", b"bytes")
    try:
        assert locks.is_held(tmp_path / "a") is True
    finally:
        handle.close()


def test_ec2_closing_the_handle_frees_it(tmp_path: Path) -> None:
    handle = held_file(tmp_path / "a", b"bytes")
    handle.close()
    assert locks.is_held(tmp_path / "a") is False


def test_ec3_a_held_file_cannot_be_held_twice(tmp_path: Path) -> None:
    first = held_file(tmp_path / "a", b"bytes")
    try:
        with open(tmp_path / "a", "r+b") as second, pytest.raises(OSError):
            locks.hold(second)
        assert locks.is_held(tmp_path / "a") is True
    finally:
        first.close()


def test_ec4_the_owner_writes_through_the_held_handle(tmp_path: Path) -> None:
    path = tmp_path / "a"
    with open(path, "xb") as handle:
        locks.hold(handle)
        handle.write(b"written by the owner")
        handle.flush()
    assert path.read_bytes() == b"written by the owner"


def test_ec5_a_file_no_one_holds(tmp_path: Path) -> None:
    path = tmp_path / "a"
    path.write_bytes(b"bytes")
    before = path.stat()
    assert locks.is_held(path) is False
    assert path.read_bytes() == b"bytes"
    assert path.stat().st_size == before.st_size


def test_ec6_a_missing_file(tmp_path: Path) -> None:
    assert locks.is_held(tmp_path / "missing") is False


def test_ec7_after_is_held_the_file_is_free(tmp_path: Path) -> None:
    path = tmp_path / "a"
    path.write_bytes(b"bytes")
    assert locks.is_held(path) is False
    with open(path, "r+b") as handle:
        locks.hold(handle)
        assert locks.is_held(path) is True


def test_ec8_a_reader_that_does_not_hold_it(tmp_path: Path) -> None:
    path = tmp_path / "a"
    path.write_bytes(b"bytes")
    with open(path, "rb"):
        assert locks.is_held(path) is False


@pytest.mark.parametrize("name", ["empty", "קובץ-נעול"])
def test_b1_b2_an_empty_file_and_a_hebrew_name(tmp_path: Path, name: str) -> None:
    handle = held_file(tmp_path / name)
    try:
        assert locks.is_held(tmp_path / name) is True
    finally:
        handle.close()
    assert locks.is_held(tmp_path / name) is False


def test_e1_a_folder(tmp_path: Path) -> None:
    (tmp_path / "folder").mkdir()
    with pytest.raises(OSError) as raised:
        locks.is_held(tmp_path / "folder")
    assert not isinstance(raised.value, FileNotFoundError)
    assert (tmp_path / "folder").is_dir()
