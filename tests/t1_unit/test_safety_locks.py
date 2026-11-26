"""Test matrix for ploni/safety/locks.py: a lock that marks a file as in use by a live run.

Why: the start-up sweeps remove what crashed runs left, and must not remove what a live run
still uses (issue #212). Achia chose on 2026-11-26 "Each run locks its own (Recommended)":
each run holds a lock on its own temp folder and on each half-written file while it works,
the operating system frees the lock if the run crashes, and the sweeps skip what is still
locked (issue #212, issuecomment-7188059248). A sweep takes the lock of what it removes and
keeps it while it removes, so that a run cannot begin to use it in between (the review of
b7390ae, finding 1). These cases run in one process, through two handles of one file; the
cases across processes, a crash among them, are tests/t4_integration/test_safety_locks.py.

hold. Equivalence classes:
  EC1  a file opened for writing, held -> another handle cannot take it
  EC2  the holding handle closed -> another handle takes it
  EC3  a file held by another handle, held again -> OSError, and the first keeps it
  EC4  the owner writes, reads and flushes through the held handle -> as without the lock
  EC9  a handle not at position 0 -> ValueError, and nothing is held
take. Equivalence classes:
  EC5  a file no one holds -> an open handle that holds it; the file's bytes unchanged
  EC6  a missing file -> made, empty, for its owner only on POSIX, and held
  EC7  a file another handle holds -> None, and the other keeps it
  EC8  a file opened for reading only by someone who does not hold it -> taken
again (issue #212, the four retries). Equivalence classes:
  EC10 an action that succeeds -> its value, no pause
  EC11 an action that fails with an error named, then succeeds -> its value, one pause of
       PAUSE_SECONDS between the tries
  EC12 an action that fails with an error named every time -> that error after ATTEMPTS tries,
       ATTEMPTS - 1 pauses
  EC13 an action that fails with an error not named -> that error at once, no pause
Boundaries:
  B1  an empty file, held and taken -> the same as a file with bytes
  B2  a file whose name is Hebrew -> the same
Error paths:
  E1  take of a folder -> OSError (not FileNotFoundError), nothing changed

Known limits: two handles of one process stand in for two processes here; that a lock of
another process counts, and that a crash frees it, is the integration suite. The document-
structure and Hebrew text axes do not apply beyond B2: no document text is read.
"""

import os
import stat
from pathlib import Path
from typing import BinaryIO

import pytest

from ploni.safety import locks
from tests.locking import held


def held_file(path: Path, data: bytes = b"") -> BinaryIO:
    """Create a file with the bytes given and hold it; return the open handle, which the case closes."""
    path.write_bytes(data)
    handle = open(path, "r+b")
    locks.hold(handle)
    return handle


def test_ec1_a_held_file_cannot_be_taken(tmp_path: Path) -> None:
    handle = held_file(tmp_path / "a", b"bytes")
    try:
        assert locks.take(tmp_path / "a") is None
    finally:
        handle.close()


def test_ec2_closing_the_handle_frees_it(tmp_path: Path) -> None:
    handle = held_file(tmp_path / "a", b"bytes")
    handle.close()
    assert held(tmp_path / "a") is False


def test_ec3_a_held_file_cannot_be_held_twice(tmp_path: Path) -> None:
    first = held_file(tmp_path / "a", b"bytes")
    try:
        with open(tmp_path / "a", "r+b") as second, pytest.raises(OSError):
            locks.hold(second)
        assert held(tmp_path / "a") is True
    finally:
        first.close()


def test_ec4_the_owner_writes_through_the_held_handle(tmp_path: Path) -> None:
    path = tmp_path / "a"
    with open(path, "xb") as handle:
        locks.hold(handle)
        handle.write(b"written by the owner")
        handle.flush()
    assert path.read_bytes() == b"written by the owner"


def test_ec9_a_handle_not_at_position_0(tmp_path: Path) -> None:
    path = tmp_path / "a"
    path.write_bytes(b"bytes")
    with open(path, "r+b") as handle:
        handle.seek(3)
        with pytest.raises(ValueError, match="position 0"):
            locks.hold(handle)
        assert held(path) is False


def test_ec5_take_a_file_no_one_holds(tmp_path: Path) -> None:
    path = tmp_path / "a"
    path.write_bytes(b"bytes")
    handle = locks.take(path)
    assert handle is not None
    try:
        assert held(path) is True
    finally:
        handle.close()
    assert path.read_bytes() == b"bytes"
    assert held(path) is False


def test_ec6_take_a_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing"
    handle = locks.take(path)
    assert handle is not None
    try:
        assert path.stat().st_size == 0
        assert held(path) is True
        if os.name != "nt":  # Windows keeps only the read-only bit of a mode
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
    finally:
        handle.close()


def test_ec7_take_a_file_another_holds(tmp_path: Path) -> None:
    handle = held_file(tmp_path / "a", b"bytes")
    try:
        assert locks.take(tmp_path / "a") is None
        assert held(tmp_path / "a") is True
    finally:
        handle.close()


def test_ec8_a_reader_that_does_not_hold_it(tmp_path: Path) -> None:
    path = tmp_path / "a"
    path.write_bytes(b"bytes")
    with open(path, "rb"):
        handle = locks.take(path)
        assert handle is not None
        handle.close()


@pytest.mark.parametrize("name", ["empty", "קובץ-נעול"])
def test_b1_b2_an_empty_file_and_a_hebrew_name(tmp_path: Path, name: str) -> None:
    handle = held_file(tmp_path / name)
    try:
        assert locks.take(tmp_path / name) is None
    finally:
        handle.close()
    assert held(tmp_path / name) is False


def test_e1_a_folder(tmp_path: Path) -> None:
    (tmp_path / "folder").mkdir()
    with pytest.raises(OSError) as raised:
        locks.take(tmp_path / "folder")
    assert not isinstance(raised.value, FileNotFoundError)
    assert (tmp_path / "folder").is_dir()


class Flaky:
    """An action that raises the errors given, one per call, then returns a value."""

    def __init__(self, *errors: BaseException) -> None:
        self.errors = list(errors)
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return "done"


@pytest.fixture
def pauses(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record each pause of `again` in place of sleeping."""
    seen: list[float] = []
    monkeypatch.setattr(locks.time, "sleep", seen.append)
    return seen


def test_ec10_an_action_that_succeeds(pauses: list[float]) -> None:
    action = Flaky()
    assert locks.again(action, (PermissionError,)) == "done"
    assert (action.calls, pauses) == (1, [])


def test_ec11_an_action_that_fails_once(pauses: list[float]) -> None:
    action = Flaky(PermissionError(13, "in use"))
    assert locks.again(action, (PermissionError,)) == "done"
    assert (action.calls, pauses) == (2, [locks.PAUSE_SECONDS])


def test_ec12_an_action_that_always_fails(pauses: list[float]) -> None:
    last = PermissionError(13, "the last")
    action = Flaky(*[PermissionError(13, "in use")] * (locks.ATTEMPTS - 1), last)
    with pytest.raises(PermissionError) as raised:
        locks.again(action, (PermissionError,))
    assert raised.value is last
    assert (action.calls, pauses) == (locks.ATTEMPTS, [locks.PAUSE_SECONDS] * (locks.ATTEMPTS - 1))


def test_ec13_an_error_not_named(pauses: list[float]) -> None:
    action = Flaky(FileNotFoundError(2, "gone"))
    with pytest.raises(FileNotFoundError):
        locks.again(action, (PermissionError,))
    assert (action.calls, pauses) == (1, [])


def test_ec12_the_tries_are_a_few_hundredths_of_a_second() -> None:
    # Achia's option: "waits a few hundredths of a second and tries again, a few times".
    assert 2 <= locks.ATTEMPTS <= 10
    assert 0.01 <= locks.PAUSE_SECONDS <= 0.09
