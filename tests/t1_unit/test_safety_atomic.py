"""Test matrix for ploni/safety/atomic.py: an artifact is written whole or not at all.

The crash in a process of its own, killed between the write and the rename, is
tests/t4_integration/test_safety_atomic.py.

write_atomic. Equivalence classes:
  EC1  a new file                      the file holds exactly the bytes; nothing else is left in
                                       the folder
  EC2  a file that is already there    replaced by the new bytes, whole
  EC3  bytes of Hebrew text, encoded   the same bytes back
Boundaries:
  B1  no bytes                         an empty file
  B2  a large write (8 MiB)            whole
Error paths (a crash simulated in the process):
  E1  the write fails part-way         the old file is as it was; no partial file is left; the
                                       error passes through
  E2  the rename fails (a crash between the write and the rename)    the old file is as it was,
                                       or there is still no file; no partial file is left; the
                                       error passes through
  E3  the folder does not exist        FileNotFoundError; nothing is made
  E4  the error is not an Exception (KeyboardInterrupt)    the partial file is removed all the same
Adversarial:
  A1  the target's name holds Hebrew letters and spaces
  A2  a file that already has the partial file's name: a write does not reuse or remove it
  A3  the random name of the partial file is taken (two writers drew the same)    FileExistsError;
       the file that has that name is neither written over nor removed (found by a hand mutant)
  EC7 the bytes are flushed to disk before the rename (os.fsync on the partial file, then os.replace)

sweep_partials. Equivalence classes:
  EC4  partial files left in the folder by a crash    removed; their number is returned
  EC5  other files, a folder with the prefix, a file with the prefix in a deeper folder    left
  EC6  a folder that does not exist, an empty folder    0
"""

import os
from pathlib import Path

import pytest

from ploni.safety import atomic

TEXT = "ישראל ישראלי, ת.ז. 123456782".encode()


def leftovers(folder: Path, keep: str) -> list[str]:
    """Return the names in a folder other than the target's."""
    return sorted(name for name in os.listdir(folder) if name != keep)


def test_ec1_a_new_file(tmp_path: Path) -> None:
    target = tmp_path / "out.docx"
    atomic.write_atomic(target, TEXT)
    assert target.read_bytes() == TEXT
    assert leftovers(tmp_path, "out.docx") == []


def test_ec2_ec3_a_file_that_is_there_is_replaced(tmp_path: Path) -> None:
    target = tmp_path / "out.docx"
    target.write_bytes(b"old " * 100)
    atomic.write_atomic(target, TEXT)
    assert target.read_bytes() == TEXT and leftovers(tmp_path, "out.docx") == []


def test_b1_b2_no_bytes_and_many(tmp_path: Path) -> None:
    empty, large = tmp_path / "e", tmp_path / "l"
    atomic.write_atomic(empty, b"")
    atomic.write_atomic(large, b"x" * (8 * 1024 * 1024))
    assert empty.read_bytes() == b"" and large.stat().st_size == 8 * 1024 * 1024


class Broken:
    """A file object that writes some bytes, then fails, as a full disk would."""

    def __init__(self, handle: object) -> None:
        self.handle = handle

    def __enter__(self) -> "Broken":
        return self

    def __exit__(self, *_: object) -> None:
        self.handle.close()  # type: ignore[attr-defined]

    def write(self, data: bytes) -> int:
        self.handle.write(data[:10])  # type: ignore[attr-defined]
        raise OSError(28, "No space left on device")


def test_e1_the_write_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "out.docx"
    target.write_bytes(b"old")
    real_open = atomic.open_partial
    monkeypatch.setattr(atomic, "open_partial", lambda path: Broken(real_open(path)))
    with pytest.raises(OSError, match="No space"):
        atomic.write_atomic(target, TEXT)
    assert target.read_bytes() == b"old" and leftovers(tmp_path, "out.docx") == []


@pytest.mark.parametrize("existing", [True, False])
def test_e2_a_crash_between_the_write_and_the_rename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bool) -> None:
    target = tmp_path / "out.docx"
    if existing:
        target.write_bytes(b"old")

    def crash(source: object, destination: object) -> None:
        raise OSError("crash between the write and the rename")

    monkeypatch.setattr(atomic.os, "replace", crash)
    with pytest.raises(OSError, match="crash"):
        atomic.write_atomic(target, TEXT)
    assert (target.read_bytes() == b"old") if existing else not target.exists()
    assert leftovers(tmp_path, "out.docx") == []


def test_e3_the_folder_does_not_exist(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        atomic.write_atomic(tmp_path / "missing" / "out.docx", TEXT)
    assert os.listdir(tmp_path) == []


def test_e4_an_interrupt_removes_the_partial_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def interrupt(source: object, destination: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(atomic.os, "replace", interrupt)
    with pytest.raises(KeyboardInterrupt):
        atomic.write_atomic(tmp_path / "out.docx", TEXT)
    assert os.listdir(tmp_path) == []


def test_a1_a_hebrew_name_with_spaces(tmp_path: Path) -> None:
    target = tmp_path / "חוזה שכירות.docx"
    atomic.write_atomic(target, TEXT)
    assert target.read_bytes() == TEXT and leftovers(tmp_path, target.name) == []


def test_a2_a_file_that_already_has_a_partial_name(tmp_path: Path) -> None:
    stray = tmp_path / f"{atomic.PARTIAL_PREFIX}out.docx.0000000000000000"
    stray.write_bytes(b"left by a crash")
    atomic.write_atomic(tmp_path / "out.docx", TEXT)
    assert stray.read_bytes() == b"left by a crash"


def test_ec4_ec5_sweep_partials(tmp_path: Path) -> None:
    for name in ("a.docx.1", "b.txt.2"):
        (tmp_path / f"{atomic.PARTIAL_PREFIX}{name}").write_bytes(b"part")
    (tmp_path / "keep.docx").write_bytes(b"keep")
    (tmp_path / f"{atomic.PARTIAL_PREFIX}folder").mkdir()
    deeper = tmp_path / "sub"
    deeper.mkdir()
    (deeper / f"{atomic.PARTIAL_PREFIX}c.1").write_bytes(b"part")
    assert atomic.sweep_partials(tmp_path) == 2
    assert sorted(os.listdir(tmp_path)) == sorted([f"{atomic.PARTIAL_PREFIX}folder", "keep.docx", "sub"])
    assert os.listdir(deeper) == [f"{atomic.PARTIAL_PREFIX}c.1"]


def test_ec6_sweep_partials_of_nothing(tmp_path: Path) -> None:
    assert atomic.sweep_partials(tmp_path / "missing") == 0
    assert atomic.sweep_partials(tmp_path) == 0


def test_a3_a_taken_partial_name_is_neither_written_nor_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(atomic.secrets, "token_hex", lambda _: "0" * 16)
    taken = tmp_path / f"{atomic.PARTIAL_PREFIX}out.docx.{'0' * 16}"
    taken.write_bytes(b"another writer's bytes")
    with pytest.raises(FileExistsError):
        atomic.write_atomic(tmp_path / "out.docx", TEXT)
    assert taken.read_bytes() == b"another writer's bytes" and not (tmp_path / "out.docx").exists()


def test_ec7_flushed_before_the_rename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    real_fsync, real_replace = atomic.os.fsync, atomic.os.replace
    monkeypatch.setattr(atomic.os, "fsync", lambda descriptor: (calls.append("fsync"), real_fsync(descriptor))[1])
    monkeypatch.setattr(atomic.os, "replace", lambda source, target: (calls.append("replace"), real_replace(source, target))[1])
    atomic.write_atomic(tmp_path / "out.docx", TEXT)
    assert calls[:2] == ["fsync", "replace"]
