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
  E4  the error is not an Exception (KeyboardInterrupt, SystemExit), at the write and at the
       rename                         the partial file is removed all the same
  E5  the clean-up fails (the partial file cannot be removed)    the first error passes through,
                                      not the clean-up's; the partial file stays for the sweep
  E6  the folder flush after the rename fails (POSIX)    the error passes through, and the
                                      target already holds all the new bytes
  E7  the target is a folder          an OSError; the folder is as it was; no partial file
  E8  the name is too long for its partial file (the partial name is 32 characters longer): a
       name of 230 characters, under the limit of one name (255) and over it with the tail; where
       the target itself cannot be made (a path limit of 260), a name sized to a path of 259
                                      an OSError; the target is as it was; no partial file
Adversarial:
  A1  the target's name holds Hebrew letters and spaces
  A2  a file that already has the partial file's name: a write does not reuse or remove it
  A3  the random name of the partial file is taken (two writers drew the same)    FileExistsError;
       the file that has that name is neither written over nor removed (found by a hand mutant)
Durability:
  EC7 the bytes are flushed to disk before the rename: at the moment of os.fsync the partial
       file holds all of them, and os.replace comes after
  EC8 _sync_folder: on POSIX a descriptor of the folder is flushed and closed; on Windows nothing
       is opened
  EC13 _sync_folder where os.name says "posix", on any system (the calls to the system faked):
       the folder is opened, flushed and closed, in that order. Kills `os.name >= "nt"` on
       Windows too (issue #189, the review of PR #203, finding 3)
  EC12 write_atomic flushes the target's folder, after the rename
  EC9 the random part of the partial name is 16 hex characters
Targets:
  EC10 a target that is a symbolic link    the link is replaced by a file with the new bytes; what
       it pointed to is not changed (skipped where links cannot be made)

sweep_partials. Equivalence classes:
  EC4  partial files left in the folder by a crash    removed; their number is returned
  EC5  other files, a folder with the prefix, a file with the prefix in a deeper folder,
       `.ploni-notes`, a name with the prefix not at its start    left; `.ploni-partial` with no
       tail is removed (it begins with the prefix)
  EC11 a symbolic link with the prefix, to a file and to a folder outside    the link is removed,
       what it points to is not (skipped where links cannot be made)
  E9  two partial files that cannot be removed, with two kinds of OSError    every other partial
       file is still removed, then the first error is raised, not the last
  EC6  a folder that does not exist, an empty folder, a path that is a file    0
  EC12 a partial file that a live write holds (issue #212): the sweep runs between the write
       and the rename    left, not counted, and a dead partial file after it is removed; the
       write ends and the target holds all its bytes
  EC13 a sweep that takes the partial file before the writer holds it (the review of b7390ae,
       finding 1)    the write fails with OSError before it writes; the target keeps its bytes
"""

import os
from pathlib import Path

import pytest

from ploni.safety import atomic, locks

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

    def fileno(self) -> int:
        # The partial file is held through its descriptor (issue #212).
        return int(self.handle.fileno())

    def tell(self) -> int:
        # The partial file is held from position 0 (issue #212).
        return int(self.handle.tell())


def test_e1_the_write_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "out.docx"
    target.write_bytes(b"old")
    real_open = atomic._open_partial
    monkeypatch.setattr(atomic, "_open_partial", lambda path: Broken(real_open(path)))
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
    (tmp_path / "a file").write_bytes(b"x")
    assert atomic.sweep_partials(tmp_path / "a file") == 0


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


@pytest.mark.parametrize("stop", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("where", ["write", "replace"])
def test_e4_a_stop_that_is_not_an_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stop: type[BaseException], where: str) -> None:
    def halt(*_: object) -> None:
        raise stop

    if where == "replace":
        monkeypatch.setattr(atomic.os, "replace", halt)
    else:
        monkeypatch.setattr(atomic.os, "fsync", halt)
    with pytest.raises(stop):
        atomic.write_atomic(tmp_path / "out.docx", TEXT)
    assert os.listdir(tmp_path) == []


def test_e5_a_failed_clean_up_keeps_the_first_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def crash(source: object, destination: object) -> None:
        raise OSError(28, "No space left on device")

    def locked(self: Path, missing_ok: bool = False) -> None:
        raise PermissionError(13, "held by another program")

    monkeypatch.setattr(atomic.os, "replace", crash)
    monkeypatch.setattr(Path, "unlink", locked)
    with pytest.raises(OSError, match="No space"):
        atomic.write_atomic(tmp_path / "out.docx", TEXT)
    monkeypatch.undo()
    assert len([name for name in os.listdir(tmp_path) if name.startswith(atomic.PARTIAL_PREFIX)]) == 1


def test_e6_a_failed_folder_flush_after_the_rename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(folder: Path) -> None:
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(atomic, "_sync_folder", broken)
    with pytest.raises(OSError, match="Input/output"):
        atomic.write_atomic(tmp_path / "out.docx", TEXT)
    assert (tmp_path / "out.docx").read_bytes() == TEXT and leftovers(tmp_path, "out.docx") == []


def test_e7_a_target_that_is_a_folder(tmp_path: Path) -> None:
    (tmp_path / "out.docx").mkdir()
    (tmp_path / "out.docx" / "inside").write_bytes(b"x")
    with pytest.raises(OSError):
        atomic.write_atomic(tmp_path / "out.docx", TEXT)
    assert os.listdir(tmp_path / "out.docx") == ["inside"] and leftovers(tmp_path, "out.docx") == []


def test_e8_a_name_too_long_for_its_partial_file(tmp_path: Path) -> None:
    # The name fits; the partial name, 32 characters longer, does not: 230 characters breaks the
    # limit of one name (255 on ext4 and NTFS). Where the whole path is the tighter limit (Windows
    # without long paths), the name is sized to a path of 259 characters instead.
    name = "n" * 225 + ".docx"
    try:
        (tmp_path / name).write_bytes(b"old")
    except OSError:
        length = 259 - len(str(tmp_path)) - 1
        if length < 20:
            pytest.skip("the temp folder's path leaves no room for the test, issue #115")
        name = "n" * (length - 5) + ".docx"
        try:
            (tmp_path / name).write_bytes(b"old")
        except OSError:
            pytest.skip("this file system refuses a name of this length, issue #115")
    with pytest.raises(OSError):
        atomic.write_atomic(tmp_path / name, TEXT)
    assert (tmp_path / name).read_bytes() == b"old" and leftovers(tmp_path, name) == []


def test_ec7_all_bytes_are_on_disk_at_the_flush(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sizes: list[int] = []
    real_fsync = atomic.os.fsync
    monkeypatch.setattr(atomic.os, "fsync", lambda descriptor: (sizes.append(os.fstat(descriptor).st_size), real_fsync(descriptor))[1])
    atomic.write_atomic(tmp_path / "out.docx", TEXT)
    assert sizes[0] == len(TEXT)


def test_ec8_sync_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[object] = []
    descriptors: list[int] = []
    flushed: list[int] = []
    closed: list[int] = []
    real_open, real_close = atomic.os.open, atomic.os.close
    monkeypatch.setattr(atomic.os, "open", lambda path, flags: (opened.append(path), descriptors.append(real_open(path, flags)), descriptors[-1])[2])
    monkeypatch.setattr(atomic.os, "fsync", flushed.append)
    monkeypatch.setattr(atomic.os, "close", lambda descriptor: (closed.append(descriptor), real_close(descriptor))[1])
    atomic._sync_folder(tmp_path)
    if os.name == "nt":
        assert (opened, flushed, closed) == ([], [], [])
    else:
        assert opened == [tmp_path] and flushed == descriptors and closed == descriptors


# Any number stands for the descriptor: the calls that would use it are faked.
FAKE_DESCRIPTOR = 7


def test_ec13_sync_folder_flushes_the_folder_where_the_system_is_posix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(atomic.os, "name", "posix")
    monkeypatch.setattr(atomic.os, "open", lambda path, flags: (calls.append(("open", path)), FAKE_DESCRIPTOR)[1])
    monkeypatch.setattr(atomic.os, "fsync", lambda descriptor: calls.append(("fsync", descriptor)))
    monkeypatch.setattr(atomic.os, "close", lambda descriptor: calls.append(("close", descriptor)))
    atomic._sync_folder(tmp_path)
    assert calls == [("open", tmp_path), ("fsync", FAKE_DESCRIPTOR), ("close", FAKE_DESCRIPTOR)]


def test_ec9_the_random_part_of_the_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    names: list[str] = []
    real_replace = atomic.os.replace
    monkeypatch.setattr(atomic.os, "replace", lambda source, target: (names.append(Path(source).name), real_replace(source, target))[1])
    atomic.write_atomic(tmp_path / "out.docx", TEXT)
    tail = names[0].removeprefix(f"{atomic.PARTIAL_PREFIX}out.docx.")
    assert len(tail) == 16 and all(character in "0123456789abcdef" for character in tail)


def make_link(link: Path, target: Path, folder: bool = False) -> None:
    """Make a symbolic link, or skip the test where the system does not let this user make one."""
    try:
        link.symlink_to(target, target_is_directory=folder)
    except OSError:
        pytest.skip("symbolic links cannot be made here, issue #115")


def test_ec10_a_target_that_is_a_link(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "real.docx").write_bytes(b"old")
    folder = tmp_path / "out"
    folder.mkdir()
    make_link(folder / "out.docx", outside / "real.docx")
    atomic.write_atomic(folder / "out.docx", TEXT)
    assert not (folder / "out.docx").is_symlink() and (folder / "out.docx").read_bytes() == TEXT
    assert (outside / "real.docx").read_bytes() == b"old"


def test_ec5_names_that_only_look_like_a_partial_file(tmp_path: Path) -> None:
    for name in (".ploni-notes", "x.ploni-partial-y", ".ploni", ".ploni-partialX"):
        (tmp_path / name).write_bytes(b"keep")
    (tmp_path / atomic.PARTIAL_PREFIX).write_bytes(b"part")
    assert atomic.sweep_partials(tmp_path) == 1
    assert sorted(os.listdir(tmp_path)) == sorted([".ploni-notes", "x.ploni-partial-y", ".ploni", ".ploni-partialX"])


def test_ec11_a_link_with_the_prefix(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    (outside / "folder").mkdir(parents=True)
    (outside / "file").write_bytes(b"keep")
    folder = tmp_path / "out"
    folder.mkdir()
    make_link(folder / f"{atomic.PARTIAL_PREFIX}to-file", outside / "file")
    make_link(folder / f"{atomic.PARTIAL_PREFIX}to-folder", outside / "folder", folder=True)
    assert atomic.sweep_partials(folder) == 2
    assert os.listdir(folder) == [] and (outside / "file").read_bytes() == b"keep" and (outside / "folder").is_dir()


def test_e9_the_sweep_tries_every_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("a", "b", "c"):
        (tmp_path / f"{atomic.PARTIAL_PREFIX}{name}").write_bytes(b"part")
    real_unlink = atomic.os.unlink

    order = sorted(entry.name for entry in os.scandir(tmp_path))
    errors = {order[0]: PermissionError(32, "in use"), order[1]: FileNotFoundError(2, "gone meanwhile")}

    def unlink(path: str) -> None:
        name = Path(path).name
        if name in errors:
            raise errors[name]
        real_unlink(path)

    monkeypatch.setattr(atomic.os, "unlink", unlink)
    with pytest.raises(OSError) as caught:
        atomic.sweep_partials(tmp_path)
    scanned_first = next(name for name in (entry.name for entry in os.scandir(tmp_path)) if name in errors)
    assert caught.value is errors[scanned_first]
    assert sorted(os.listdir(tmp_path)) == sorted(errors)


def test_ec12_the_folder_of_the_target_is_flushed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    flushed: list[Path] = []
    monkeypatch.setattr(atomic, "_sync_folder", flushed.append)
    atomic.write_atomic(tmp_path / "out.docx", TEXT)
    assert flushed == [tmp_path] and (tmp_path / "out.docx").read_bytes() == TEXT


def test_ec12_sweep_partials_leaves_the_partial_file_of_a_live_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[int] = []
    real_fsync = os.fsync

    def sweep_while_writing(descriptor: int) -> None:
        real_fsync(descriptor)
        seen.append(atomic.sweep_partials(tmp_path))

    monkeypatch.setattr(atomic.os, "fsync", sweep_while_writing)
    atomic.write_atomic(tmp_path / "out.docx", TEXT)
    assert seen[0] == 0  # the partial file's fsync; POSIX also flushes the folder after the rename
    assert (tmp_path / "out.docx").read_bytes() == TEXT
    assert os.listdir(tmp_path) == ["out.docx"]


def test_ec12_sweep_partials_goes_on_past_a_live_write_to_a_dead_partial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dead = tmp_path / f"{atomic.PARTIAL_PREFIX}zzz.docx.0000000000000000"
    dead.write_bytes(b"left by a crash")
    seen: list[int] = []
    real_fsync = os.fsync

    def sweep_while_writing(descriptor: int) -> None:
        real_fsync(descriptor)
        seen.append(atomic.sweep_partials(tmp_path))

    monkeypatch.setattr(atomic.os, "fsync", sweep_while_writing)
    atomic.write_atomic(tmp_path / "out.docx", TEXT)
    assert seen[0] == 1  # the dead partial file, not the live one
    assert not dead.exists()
    assert (tmp_path / "out.docx").read_bytes() == TEXT


def test_ec13_a_sweep_that_takes_the_partial_file_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "out.docx"
    target.write_bytes(b"old")
    real_open = atomic._open_partial
    taken: list[object] = []

    def opened_then_taken(path: Path) -> object:
        handle = real_open(path)
        taken.append(locks.take(path))
        return handle

    monkeypatch.setattr(atomic, "_open_partial", opened_then_taken)
    try:
        with pytest.raises(OSError):
            atomic.write_atomic(target, TEXT)
    finally:
        for handle in taken:
            if handle is not None:
                handle.close()
    assert target.read_bytes() == b"old"
