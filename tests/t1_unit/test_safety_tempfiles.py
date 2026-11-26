"""Test matrix for ploni/safety/tempfiles.py, the only way product code gets a temp folder.

The canary test, which writes one string into temp files in every way and then searches the
disk for it, is tests/t8_privacy/test_temp_canary.py. The module used by a program of its own
is tests/t4_integration/test_safety_tempfiles.py.

private_dir. Equivalence classes:
  EC1  inside the block         a new, empty folder under the root, its name beginning with the
                                prefix; on a POSIX system only its owner can open it
  EC2  after the block          the folder is gone, with the files and folders made in it
  EC3  the block ends in error  the folder is gone all the same, and the error passes through
  EC4  the process's temp folder    inside the block it is the private folder, so that the
                                standard tempfile calls land there; after the block, also one
                                that ended in error, it is what it was before
  EC5  a block inside a block   two folders side by side under the root; the process's temp
                                folder steps back one block at a time. Blocks that overlap and
                                end in the order they began: the folder handed out is that of
                                the newest block still open, and at the end what it was before
  EC6  the root                 made when it is missing, with the folders above it
  EC7  a read-only file, and a read-only folder with files in it    removed
  EC8  what is written over     every regular file holds only zeros, at its full length, at
                                the moment it is removed
  EC9  a file with a second name outside the folder (a hard link)    the name inside is
                                removed; the bytes, which the outside name still shows, are
                                kept; so too when the file is read-only
  EC10 a link to a file or a folder outside the folder: a symbolic link, and on Windows a
                                junction, also one folder deeper, also to a read-only file and
                                to nothing    the link is removed; nothing behind it is removed,
                                written over or made writable

sweep. Equivalence classes:
  EC11 folders left under the root    removed, overwritten like any other; their number is returned
  EC12 other entries of the root      a folder with another name, a file with the prefix, a link
                                with the prefix, a folder with the prefix one level deeper: left alone
  EC13 a root that does not exist, an empty root    0
  EC14 a folder of a block that is still open (its lock beside it held, issue #212)    left,
      not counted, and the sweep goes on to the folders after it; the block still ends as before
  EC15 a folder that a killed run left with its lock file beside it, not held    the folder and
      its lock file are removed, counted once
private_dir and the lock (issue #212). Equivalence classes:
  EC16 inside the block the lock file `<folder>.lock` stands beside the folder in the root and
       is held; the folder itself is still empty; after the block both are gone, also when the
       block ends with NotRemoved
The race of a run's start (the review of b7390ae, finding 1). Equivalence classes:
  EC17 the sweep holds a folder's lock while it removes the folder
  EC18 a run whose lock file a sweep already made (it holds it while it removes the folder)
       -> FileExistsError at the start, before the block runs; the folder is not left
  EC19 a run whose folder a sweep removed before the run held its lock -> FileNotFoundError at
       the start, before the block runs
  EC20 a lock path that cannot be opened (a folder in its place) -> the sweep goes on to the
       folders after it, and raises that OSError at the end
  EC21 a lock file with no folder, not held -> removed by the sweep, not counted
       (also when it comes after a lock file that a run holds, which stays)
  EC22 a symbolic link named like a lone lock file, to a file outside and to nothing -> left;
       nothing outside is made or changed
  EC23 a symbolic link in the place of a dead folder's lock file, to a file outside and to
       nothing -> not followed: the link and the folder are removed, nothing outside is made or
       changed (the review of 5d1ee74, finding 14)
  EC24 an unheld lock file beside a live folder (a run between its "xb" open and its hold),
       met by the lone-lock pass alone -> left
  EC25 a held lock file with no folder (a block between its folder's removal and its close)
       -> left, and the sweep raises nothing

Boundaries:
  B1  a block that makes nothing
  B2  an empty file; a file of one byte; a file one byte longer than three chunks
  B3  folders nested ten deep

Error paths:
  E1  the folder cannot be removed    NotRemoved, which names the private folder and neither a
                                file in it nor the path above it, and carries no cause; from
                                the block and from sweep; also when the removal fails without
                                an error; and for real, with a file that a program still holds
                                open, which Windows does not remove and a POSIX system does
  E2  the root is a file              the error of making the folder passes through (OSError)
  E3  a file cannot be written over but can be removed    no error: it is gone. One file that
      cannot be opened, and one entry that cannot be made writable, do not stop the others

Adversarial:
  A1  a file name in Hebrew, with spaces, and a very long one
  A2  the block removes its own folder before it ends    no error

From the second review:
  A3  the block puts a link to a folder outside in the place of its own folder, a symbolic
      link or a junction    nothing behind it is touched; NotRemoved, also when the link
      leads to nothing
  A4  a file system that gives every file the number 0    every file is still written over,
      and a file with a name outside still keeps its bytes
  A5  the removal is interrupted while files are being written over    the folder is gone
      all the same, and the interrupt passes through
  A6  a file and a folder with no permission bit at all    written over, removed
  A7  one file whose facts cannot be read    the others are written over
  A8  blocks in two threads    a `tempfile` call lands in the newest open block, whichever
      thread makes it; every change of the process's temp folder is made under the lock
  EC6 on Windows too: the root that the helper makes does not take its access list from
      the folder above it

From the survivors of the Cosmic Ray trial of #188 (issue #189):
  B4  a file with 257 names, all inside the folder: one more than the largest whole number
      that CPython keeps a single object of, so the count of names and the link count are
      two objects that are equal    written over under every name

The Hebrew axes of the test-matrix skill apply to names and content of files (A1, and the
canary). The document-structure axes do not apply: no document is handled.
"""

import os
import stat
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

if sys.platform == "win32":
    import _winapi

import pytest

from ploni.safety import locks, tempfiles
from tests.locking import held

TEXT = "יעקב כהן / John Smith"
# The kinds of link to a folder that this system has. A junction is the folder link of Windows and needs no
# special right there; no other system has one, so there the case does not exist.
FOLDER_LINKS = ["symlink", "junction"] if sys.platform == "win32" else ["symlink"]


def test_ec1_inside_the_block_there_is_a_new_empty_folder_under_the_root(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        assert folder.is_dir()
        assert folder.parent == tmp_path
        assert folder.name.startswith(tempfiles.PREFIX)
        assert list(folder.iterdir()) == []
        if sys.platform != "win32":
            assert stat.S_IMODE(folder.stat().st_mode) == 0o700


def test_ec2_after_the_block_the_folder_and_all_in_it_are_gone(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        (folder / "a.txt").write_text(TEXT, encoding="utf-8")
        (folder / "inner" / "deeper").mkdir(parents=True)
        (folder / "inner" / "deeper" / "b.bin").write_bytes(TEXT.encode("utf-16"))
    assert not folder.exists()
    assert list(tmp_path.iterdir()) == []


def test_ec3_a_block_that_ends_in_error_leaves_nothing_and_passes_the_error_on(tmp_path: Path) -> None:
    with pytest.raises(KeyError, match="the block's own"), tempfiles.private_dir(tmp_path) as folder:
        (folder / "a.txt").write_text(TEXT, encoding="utf-8")
        raise KeyError("the block's own")
    assert list(tmp_path.iterdir()) == []


def test_ec4_the_standard_tempfile_calls_land_in_the_private_folder(tmp_path: Path) -> None:
    before = tempfile.gettempdir()
    with tempfiles.private_dir(tmp_path) as folder:
        assert Path(tempfile.gettempdir()) == folder
        handle, name = tempfile.mkstemp()
        os.close(handle)
        made = [Path(name), Path(tempfile.mkdtemp())]
        with tempfile.NamedTemporaryFile(delete=False) as kept:
            kept.write(TEXT.encode("utf-8"))
        made.append(Path(kept.name))
        assert all(path.parent == folder for path in made)
    assert tempfile.gettempdir() == before
    assert not any(path.exists() for path in made)


def test_ec4_the_temp_folder_of_the_process_is_put_back_after_an_error_too(tmp_path: Path) -> None:
    before = tempfile.gettempdir()
    with pytest.raises(KeyError), tempfiles.private_dir(tmp_path):
        raise KeyError
    assert tempfile.gettempdir() == before


def test_ec5_a_block_inside_a_block(tmp_path: Path) -> None:
    before = tempfile.gettempdir()
    with tempfiles.private_dir(tmp_path) as outer:
        with tempfiles.private_dir(tmp_path) as inner:
            assert inner.parent == outer.parent == tmp_path
            assert inner != outer
            assert Path(tempfile.gettempdir()) == inner
        assert not inner.exists()
        assert outer.is_dir()
        assert Path(tempfile.gettempdir()) == outer
    assert tempfile.gettempdir() == before
    assert list(tmp_path.iterdir()) == []


def test_ec6_a_missing_root_is_made_with_the_folders_above_it(tmp_path: Path) -> None:
    root = tmp_path / "not" / "there" / "yet"
    with tempfiles.private_dir(root) as folder:
        assert folder.parent == root
    assert root.is_dir()
    assert list(root.iterdir()) == []


def test_ec7_a_read_only_file_is_removed(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        locked = folder / "locked.txt"
        locked.write_text(TEXT, encoding="utf-8")
        locked.chmod(stat.S_IREAD)
    assert list(tmp_path.iterdir()) == []


def test_ec7_a_read_only_folder_is_removed_with_what_is_in_it(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        (folder / "locked" / "deeper").mkdir(parents=True)
        (folder / "locked" / "deeper" / "page.txt").write_text(TEXT, encoding="utf-8")
        (folder / "locked" / "deeper").chmod(stat.S_IREAD | stat.S_IEXEC)
        (folder / "locked").chmod(stat.S_IREAD | stat.S_IEXEC)
    assert list(tmp_path.iterdir()) == []


def test_a6_a_folder_and_a_file_with_no_permission_bit_at_all(tmp_path: Path, seen_at_removal: dict[str, bytes]) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        (folder / "closed" / "deeper").mkdir(parents=True)
        (folder / "closed" / "deeper" / "page.txt").write_text(TEXT, encoding="utf-8")
        (folder / "closed" / "deeper" / "page.txt").chmod(0)
        (folder / "closed" / "deeper").chmod(0)
        (folder / "closed").chmod(0)
    assert list(tmp_path.iterdir()) == []
    assert set(seen_at_removal["page.txt"]) == {0}


@pytest.fixture
def seen_at_removal(monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    """Record the bytes of every file of a folder at the moment the module starts to remove it."""
    seen: dict[str, bytes] = {}
    real = tempfiles.shutil.rmtree

    def recording(folder: Path, **options: object) -> None:
        for path in Path(folder).rglob("*"):
            if path.is_file() and not path.is_symlink():
                seen[path.name] = path.read_bytes()
        real(folder, **options)

    monkeypatch.setattr(tempfiles.shutil, "rmtree", recording)
    return seen


def test_ec8_every_file_holds_only_zeros_when_it_is_removed(tmp_path: Path, seen_at_removal: dict[str, bytes]) -> None:
    size = len(TEXT.encode("utf-8"))
    with tempfiles.private_dir(tmp_path) as folder:
        (folder / "deep" / "deeper").mkdir(parents=True)
        for path in ("top", "deep/middle", "deep/deeper/bottom", "deep/locked"):
            (folder / path).write_text(TEXT, encoding="utf-8")
        (folder / "deep" / "locked").chmod(stat.S_IREAD)
        os.link(folder / "top", folder / "deep" / "second-name")
    names = {"top", "middle", "bottom", "locked", "second-name"}
    assert {name: len(data) for name, data in seen_at_removal.items()} == dict.fromkeys(names, size)
    assert all(set(data) == {0} for data in seen_at_removal.values())


def test_b2_an_empty_file_one_byte_and_one_byte_more_than_three_chunks(tmp_path: Path, seen_at_removal: dict[str, bytes]) -> None:
    sizes = {"empty": 0, "one": 1, "large": 3 * tempfiles.CHUNK + 1}
    with tempfiles.private_dir(tmp_path) as folder:
        for name, size in sizes.items():
            (folder / name).write_bytes((TEXT.encode("utf-8") * (size // 20 + 1))[:size])
    assert {name: len(data) for name, data in seen_at_removal.items()} == sizes
    assert all(set(data) <= {0} for data in seen_at_removal.values())


# CPython keeps one object of each whole number below this (Include/internal/pycore_global_objects.h line 20 of
# 3.13.5, _PY_NSMALLPOSINTS 257): from it up, a count and a link count that are equal are two objects.
NAMES_PAST_THE_SMALL_NUMBERS = 257


def test_b4_a_file_with_257_names_inside_is_written_over(tmp_path: Path, seen_at_removal: dict[str, bytes]) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        (folder / "name-0").write_text(TEXT, encoding="utf-8")
        for number in range(1, NAMES_PAST_THE_SMALL_NUMBERS):
            os.link(folder / "name-0", folder / f"name-{number}")
        assert (folder / "name-0").stat().st_nlink == NAMES_PAST_THE_SMALL_NUMBERS
    assert list(tmp_path.iterdir()) == []
    assert len(seen_at_removal) == NAMES_PAST_THE_SMALL_NUMBERS
    assert all(set(data) == {0} for data in seen_at_removal.values())


def test_ec8_every_file_is_flushed_to_the_disk_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    synced = []
    real = os.fsync
    monkeypatch.setattr(tempfiles.os, "fsync", lambda handle: (synced.append(handle), real(handle))[1])
    with tempfiles.private_dir(tmp_path) as folder:
        for name in ("one", "two", "three"):
            (folder / name).write_text(TEXT, encoding="utf-8")
    assert len(synced) == 3


def test_e3_one_file_that_cannot_be_opened_does_not_stop_the_others(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, seen_at_removal: dict[str, bytes]
) -> None:
    real = Path.open

    def opening(self: Path, *arguments: object, **options: object) -> object:
        # Only the opening for writing fails, as for a file that another handle holds; reading it stays possible.
        if self.name == "b-held.txt" and "+" in str(arguments[:1]):
            raise PermissionError(13, "The process cannot access the file")
        return real(self, *arguments, **options)

    with tempfiles.private_dir(tmp_path) as folder:
        for name in ("a-first.txt", "b-held.txt", "c-last.txt"):
            (folder / name).write_text(TEXT, encoding="utf-8")
        (folder / "d-dir").mkdir()
        (folder / "d-dir" / "inner.txt").write_text(TEXT, encoding="utf-8")
        monkeypatch.setattr(Path, "open", opening)
    monkeypatch.setattr(Path, "open", real)
    assert list(tmp_path.iterdir()) == []
    zeroed = {name for name, data in seen_at_removal.items() if set(data) == {0}}
    assert zeroed == {"a-first.txt", "c-last.txt", "inner.txt"}
    assert seen_at_removal["b-held.txt"] == TEXT.encode("utf-8")


def test_e3_one_entry_that_cannot_be_made_writable_does_not_stop_the_others(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, seen_at_removal: dict[str, bytes]
) -> None:
    real = Path.chmod

    def changing(self: Path, mode: int, **options: object) -> None:
        if self.name == "a-stubborn.txt":
            raise PermissionError(13, "Access is denied")
        real(self, mode, **options)

    with tempfiles.private_dir(tmp_path) as folder:
        for name in ("a-stubborn.txt", "b-locked.txt"):
            (folder / name).write_text(TEXT, encoding="utf-8")
        (folder / "b-locked.txt").chmod(stat.S_IREAD)
        monkeypatch.setattr(Path, "chmod", changing)
    monkeypatch.setattr(Path, "chmod", real)
    assert list(tmp_path.iterdir()) == []
    assert set(seen_at_removal["b-locked.txt"]) == {0}


def test_ec9_a_file_with_a_second_name_outside_keeps_its_bytes(tmp_path: Path) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside.txt"
    outside.write_text(TEXT, encoding="utf-8")
    mode = stat.S_IMODE(outside.stat().st_mode)
    with tempfiles.private_dir(root) as folder:
        os.link(outside, folder / "same-file.txt")
    assert list(root.iterdir()) == []
    assert outside.read_text(encoding="utf-8") == TEXT
    # A file that was writable keeps every bit of its mode: the group's and the others' too.
    assert stat.S_IMODE(outside.stat().st_mode) == mode


def test_ec9_a_read_only_file_with_a_second_name_outside_is_removed_and_keeps_its_bytes(tmp_path: Path) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside.txt"
    outside.write_text(TEXT, encoding="utf-8")
    outside.chmod(stat.S_IREAD)
    with tempfiles.private_dir(root) as folder:
        os.link(outside, folder / "same-file.txt")
    assert list(root.iterdir()) == []
    assert outside.read_text(encoding="utf-8") == TEXT


def link(at: Path, target: Path, kind: str) -> None:
    """Make a link of one kind at a path: a symbolic link, or a junction, the folder link of Windows."""
    if kind == "junction":
        _winapi.CreateJunction(str(target), str(at))
    else:
        at.symlink_to(target, target_is_directory=target.is_dir())


def outside_tree(base: Path) -> Path:
    """Make a folder that is not the helper's, with a file, a read-only file and a file one folder deeper."""
    outside = base / "outside"
    (outside / "sub").mkdir(parents=True)
    (outside / "kept.txt").write_text(TEXT, encoding="utf-8")
    (outside / "sub" / "deep.txt").write_text(TEXT, encoding="utf-8")
    (outside / "locked.txt").write_text(TEXT, encoding="utf-8")
    (outside / "locked.txt").chmod(stat.S_IREAD)
    return outside


def untouched(outside: Path) -> bool:
    """Say whether the outside folder is as `outside_tree` made it: every byte, and the read-only mark."""
    files = [outside / "kept.txt", outside / "sub" / "deep.txt", outside / "locked.txt"]
    same = all(file.read_text(encoding="utf-8") == TEXT for file in files)
    return same and not os.access(outside / "locked.txt", os.W_OK) and os.access(outside / "kept.txt", os.W_OK)


@pytest.mark.parametrize("kind", FOLDER_LINKS)
def test_ec10_a_link_to_a_folder_outside_is_removed_and_nothing_behind_it_is_touched(tmp_path: Path, kind: str) -> None:
    root, outside = tmp_path / "root", outside_tree(tmp_path)
    with tempfiles.private_dir(root) as folder:
        (folder / "inner").mkdir()
        link(folder / "linked-folder", outside, kind)
        link(folder / "inner" / "deeper-link", outside / "sub", kind)
        (folder / "own.txt").write_text(TEXT, encoding="utf-8")
    assert list(root.iterdir()) == []
    assert untouched(outside)


def test_ec10_a_link_to_a_file_outside_is_removed_and_the_file_is_untouched(tmp_path: Path) -> None:
    root, outside = tmp_path / "root", outside_tree(tmp_path)
    with tempfiles.private_dir(root) as folder:
        link(folder / "link.txt", outside / "kept.txt", "symlink")
        link(folder / "locked-link.txt", outside / "locked.txt", "symlink")
        link(folder / "nowhere.txt", outside / "missing.txt", "symlink")
    assert list(root.iterdir()) == []
    assert untouched(outside)


@pytest.mark.parametrize("kind", FOLDER_LINKS)
def test_ec12_sweep_leaves_a_link_with_the_prefix_and_what_lies_behind_it(tmp_path: Path, kind: str) -> None:
    root, outside = tmp_path / "root", outside_tree(tmp_path)
    leftover(root, "real")
    link(root / f"{tempfiles.PREFIX}linked", outside, kind)
    assert tempfiles.sweep(root) == 1
    assert [path.name for path in root.iterdir()] == [f"{tempfiles.PREFIX}linked"]
    assert untouched(outside)


def leftover(root: Path, name: str) -> Path:
    """Make a folder under root as a killed run would have left it, with a file in it."""
    folder = root / f"{tempfiles.PREFIX}{name}"
    (folder / "inner").mkdir(parents=True)
    (folder / "inner" / "page.txt").write_text(TEXT, encoding="utf-8")
    return folder


def test_ec11_sweep_removes_what_earlier_runs_left_and_counts_it(
    tmp_path: Path, seen_at_removal: dict[str, bytes]
) -> None:
    leftover(tmp_path, "one")
    leftover(tmp_path, "two")
    assert tempfiles.sweep(tmp_path) == 2
    assert list(tmp_path.iterdir()) == []
    assert seen_at_removal == {"page.txt": bytes(len(TEXT.encode("utf-8")))}


def test_ec12_sweep_leaves_other_entries_of_the_root_alone(tmp_path: Path) -> None:
    leftover(tmp_path, "one")
    (tmp_path / "other-folder").mkdir()
    (tmp_path / "other-folder" / "keep.txt").write_text(TEXT, encoding="utf-8")
    (tmp_path / f"{tempfiles.PREFIX}a-file").write_text(TEXT, encoding="utf-8")
    assert tempfiles.sweep(tmp_path) == 1
    assert sorted(path.name for path in tmp_path.iterdir()) == ["other-folder", f"{tempfiles.PREFIX}a-file"]
    assert (tmp_path / "other-folder" / "keep.txt").read_text(encoding="utf-8") == TEXT


def test_ec13_sweep_of_a_missing_root_and_of_an_empty_one(tmp_path: Path) -> None:
    assert tempfiles.sweep(tmp_path / "missing") == 0
    assert tempfiles.sweep(tmp_path) == 0
    assert not (tmp_path / "missing").exists()


def test_ec12_sweep_leaves_a_folder_with_the_prefix_that_is_not_directly_under_the_root(tmp_path: Path) -> None:
    leftover(tmp_path / "other-folder", "nested")
    assert tempfiles.sweep(tmp_path) == 0
    assert (tmp_path / "other-folder" / f"{tempfiles.PREFIX}nested" / "inner" / "page.txt").read_text(encoding="utf-8") == TEXT


def test_ec3_a_block_that_is_interrupted_leaves_nothing(tmp_path: Path) -> None:
    before = tempfile.gettempdir()
    for ending in (KeyboardInterrupt, SystemExit, GeneratorExit):
        with pytest.raises(ending), tempfiles.private_dir(tmp_path) as folder:
            (folder / "a.txt").write_text(TEXT, encoding="utf-8")
            raise ending
        assert list(tmp_path.iterdir()) == []
        assert tempfile.gettempdir() == before


def test_ec5_blocks_that_overlap_and_end_in_the_order_they_began(tmp_path: Path) -> None:
    before = tempfile.gettempdir()
    first, second, third = (tempfiles.private_dir(tmp_path) for _ in range(3))
    one = first.__enter__()
    two = second.__enter__()
    assert Path(tempfile.gettempdir()) == two
    first.__exit__(None, None, None)
    assert not one.exists()
    assert Path(tempfile.gettempdir()) == two
    handle, name = tempfile.mkstemp()
    os.close(handle)
    assert Path(name).parent == two
    three = third.__enter__()
    assert Path(tempfile.gettempdir()) == three
    second.__exit__(None, None, None)
    assert Path(tempfile.gettempdir()) == three
    third.__exit__(None, None, None)
    assert tempfile.gettempdir() == before
    assert list(tmp_path.iterdir()) == []


def test_ec5_three_blocks_that_end_out_of_order_hand_out_the_newest_that_is_still_open(tmp_path: Path) -> None:
    before = tempfile.gettempdir()
    first, second, third = (tempfiles.private_dir(tmp_path) for _ in range(3))
    first.__enter__()
    two = second.__enter__()
    third.__enter__()
    third.__exit__(None, None, None)
    assert Path(tempfile.gettempdir()) == two
    first.__exit__(None, None, None)
    assert Path(tempfile.gettempdir()) == two
    second.__exit__(None, None, None)
    assert tempfile.gettempdir() == before
    assert list(tmp_path.iterdir()) == []


def test_ec4_a_temp_folder_that_other_code_chose_is_put_back_each_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    chosen, later, root = tmp_path / "chosen", tmp_path / "later", tmp_path / "root"
    chosen.mkdir()
    later.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(chosen))
    with tempfiles.private_dir(root) as folder:
        assert tempfile.tempdir == str(folder)
    assert tempfile.tempdir == str(chosen)
    tempfile.tempdir = str(later)
    with tempfiles.private_dir(root) as folder:
        assert tempfile.tempdir == str(folder)
    assert tempfile.tempdir == str(later)


def access_list(folder: Path) -> bytes:
    """Return what the Windows tool icacls prints for a folder: who may do what with it."""
    tool = Path(os.environ["SystemRoot"]) / "System32" / "icacls.exe"
    # Read as bytes: the tool writes in the console's code page, and a path with Hebrew letters would not decode.
    return subprocess.run([str(tool), str(folder)], capture_output=True, check=True).stdout  # noqa: S603 a fixed system tool, on a folder the test made


def test_ec6_a_root_that_the_helper_makes_is_for_its_owner_only(tmp_path: Path) -> None:
    root = tmp_path / "made"
    with tempfiles.private_dir(root):
        if sys.platform != "win32":
            assert stat.S_IMODE(root.stat().st_mode) == 0o700
        else:
            # Windows has no mode. A folder made for its owner only gets an access list of its own; one made
            # in the usual way takes the list of the folder above it, and icacls marks such an entry with (I).
            plain = tmp_path / "plain"
            plain.mkdir()
            assert b"(I)" in access_list(plain)
            assert b"(I)" not in access_list(root)
    assert root.is_dir()


def test_ec7_the_private_folder_itself_read_only_is_removed(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        (folder / "page.txt").write_text(TEXT, encoding="utf-8")
        # No bit at all: with the read and list bits left, adding the write bit alone would be enough.
        folder.chmod(0)
    assert list(tmp_path.iterdir()) == []


def test_b1_a_block_that_makes_nothing(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path):
        pass
    assert list(tmp_path.iterdir()) == []


def test_b3_folders_nested_ten_deep(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        deep = folder.joinpath(*[f"level{number}" for number in range(10)])
        deep.mkdir(parents=True)
        (deep / "page.txt").write_text(TEXT, encoding="utf-8")
    assert list(tmp_path.iterdir()) == []


@pytest.fixture
def stuck(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the module's removal fail as it does for a file that another program holds open."""

    def failing(folder: Path, **options: object) -> None:
        raise PermissionError(13, "The process cannot access the file", str(Path(folder) / "client-name.docx"))

    monkeypatch.setattr(tempfiles.shutil, "rmtree", failing)


def test_e1_a_folder_that_cannot_be_removed_is_an_error_that_names_no_file(tmp_path: Path, stuck: None) -> None:
    with pytest.raises(tempfiles.NotRemoved) as raised, tempfiles.private_dir(tmp_path) as folder:
        (folder / "client-name.docx").write_text(TEXT, encoding="utf-8")
    assert folder.name in str(raised.value)
    assert "client-name" not in str(raised.value)
    assert str(tmp_path) not in str(raised.value)
    assert raised.value.__context__ is None
    assert raised.value.__cause__ is None
    assert isinstance(raised.value, OSError)
    assert folder.exists()


def test_e1_a_removal_that_fails_without_an_error_is_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tempfiles.shutil, "rmtree", lambda folder, **options: None)
    with pytest.raises(tempfiles.NotRemoved) as raised, tempfiles.private_dir(tmp_path) as folder:
        (folder / "page.txt").write_text(TEXT, encoding="utf-8")
    assert folder.name in str(raised.value)


def test_e1_a_file_that_is_still_open_when_the_block_ends(tmp_path: Path) -> None:
    # Windows does not remove a file that a program holds open; a POSIX system does.
    if sys.platform == "win32":
        with pytest.raises(tempfiles.NotRemoved), tempfiles.private_dir(tmp_path) as folder:
            held = (folder / "held.txt").open("w", encoding="utf-8")
            held.write(TEXT)
            held.flush()
        held.close()
        assert tempfiles.sweep(tmp_path) == 1
    else:
        with tempfiles.private_dir(tmp_path) as folder:
            held = (folder / "held.txt").open("w", encoding="utf-8")
            held.write(TEXT)
        held.close()
    assert list(tmp_path.iterdir()) == []


def test_e1_sweep_says_so_when_a_folder_cannot_be_removed(tmp_path: Path, stuck: None) -> None:
    folder = leftover(tmp_path, "one")
    with pytest.raises(tempfiles.NotRemoved, match=folder.name):
        tempfiles.sweep(tmp_path)


def test_e1_sweep_tries_every_folder_before_it_says_that_one_could_not_be_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tempfiles.shutil.rmtree

    def failing_for_one(folder: Path, **options: object) -> None:
        if Path(folder).name.endswith("b-stuck"):
            raise PermissionError(13, "The process cannot access the file")
        real(folder, **options)

    for name in ("a-first", "b-stuck", "c-stuck-too-b-stuck", "d-last"):
        leftover(tmp_path, name)
    monkeypatch.setattr(tempfiles.shutil, "rmtree", failing_for_one)
    with pytest.raises(tempfiles.NotRemoved, match=f"{tempfiles.PREFIX}b-stuck could not"):
        tempfiles.sweep(tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == [f"{tempfiles.PREFIX}b-stuck", f"{tempfiles.PREFIX}c-stuck-too-b-stuck"]


def test_e1_an_error_of_the_block_is_the_context_of_the_removal_error(tmp_path: Path, stuck: None) -> None:
    with pytest.raises(tempfiles.NotRemoved) as raised, tempfiles.private_dir(tmp_path):
        raise KeyError("the block's own")
    assert isinstance(raised.value.__context__, KeyError)


def test_e1_the_temp_folder_of_the_process_is_put_back_when_removal_fails(tmp_path: Path, stuck: None) -> None:
    before = tempfile.gettempdir()
    with pytest.raises(tempfiles.NotRemoved), tempfiles.private_dir(tmp_path):
        pass
    assert tempfile.gettempdir() == before


def test_e2_a_root_that_is_a_file(tmp_path: Path) -> None:
    root = tmp_path / "a-file"
    root.write_text("x", encoding="utf-8")
    with pytest.raises(OSError), tempfiles.private_dir(root):
        pass
    assert root.read_text(encoding="utf-8") == "x"


def test_e3_a_file_that_cannot_be_written_over_is_still_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(handle: int) -> None:
        raise OSError("the disk said no")

    monkeypatch.setattr(tempfiles.os, "fsync", failing)
    with tempfiles.private_dir(tmp_path) as folder:
        (folder / "page.txt").write_text(TEXT, encoding="utf-8")
    assert list(tmp_path.iterdir()) == []


def test_a1_file_names_in_hebrew_with_spaces_and_a_long_one(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        # 60 letters: long for a name, and short enough that a deep temp folder stays under the 260 of Windows.
        for name in ("חוזה שכירות - יעקב כהן.docx", "two words.txt", "n" * 60 + ".txt"):
            (folder / name).write_text(TEXT, encoding="utf-8")
    assert list(tmp_path.iterdir()) == []


def test_a2_a_block_that_removes_its_own_folder(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        folder.rmdir()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", FOLDER_LINKS)
def test_a3_a_link_in_the_place_of_the_private_folder_itself_is_not_gone_through(tmp_path: Path, kind: str) -> None:
    root, outside = tmp_path / "root", outside_tree(tmp_path)
    with pytest.raises(tempfiles.NotRemoved), tempfiles.private_dir(root) as folder:
        folder.rmdir()
        link(folder, outside, kind)
    assert untouched(outside)
    assert [path.name for path in root.iterdir()] == [folder.name]
    # sweep leaves a link alone, so the next start does not go through it either.
    assert tempfiles.sweep(root) == 0
    assert untouched(outside)


@pytest.mark.parametrize("kind", FOLDER_LINKS)
def test_a3_a_link_to_nothing_in_the_place_of_the_private_folder_is_an_error_too(tmp_path: Path, kind: str) -> None:
    root, target = tmp_path / "root", tmp_path / "short-lived"
    target.mkdir()
    with pytest.raises(tempfiles.NotRemoved), tempfiles.private_dir(root) as folder:
        folder.rmdir()
        link(folder, target, kind)
        target.rmdir()
    assert [path.name for path in root.iterdir()] == [folder.name]


def test_a4_without_file_numbers_a_file_with_a_name_outside_keeps_its_bytes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real = Path.lstat

    def unnumbered(self: Path) -> os.stat_result:
        facts = list(real(self))
        facts[1] = 0  # st_ino
        return os.stat_result(facts)

    root, outside = tmp_path / "root", tmp_path / "outside.txt"
    outside.write_text(TEXT, encoding="utf-8")
    with tempfiles.private_dir(root) as folder:
        os.link(outside, folder / "same-file.txt")
        monkeypatch.setattr(Path, "lstat", unnumbered)
    monkeypatch.setattr(Path, "lstat", real)
    assert list(root.iterdir()) == []
    assert outside.read_text(encoding="utf-8") == TEXT


def test_a4_a_file_system_that_numbers_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, seen_at_removal: dict[str, bytes]) -> None:
    real = Path.lstat

    def unnumbered(self: Path) -> os.stat_result:
        facts = list(real(self))
        facts[1] = 0  # st_ino
        return os.stat_result(facts)

    with tempfiles.private_dir(tmp_path) as folder:
        for name in ("a.txt", "b.txt", "c.txt"):
            (folder / name).write_text(TEXT, encoding="utf-8")
        monkeypatch.setattr(Path, "lstat", unnumbered)
    monkeypatch.setattr(Path, "lstat", real)
    assert {name: set(data) for name, data in seen_at_removal.items()} == dict.fromkeys(("a.txt", "b.txt", "c.txt"), {0})


def test_a5_a_removal_that_is_interrupted_still_removes_the_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def interrupted(handle: int) -> None:
        calls.append(handle)
        if len(calls) == 2:
            raise KeyboardInterrupt

    monkeypatch.setattr(tempfiles.os, "fsync", interrupted)
    with pytest.raises(KeyboardInterrupt), tempfiles.private_dir(tmp_path) as folder:
        for name in ("a.txt", "b.txt", "c.txt", "d.txt"):
            (folder / name).write_text(TEXT, encoding="utf-8")
    assert len(calls) == 2
    assert list(tmp_path.iterdir()) == []


def test_a7_one_file_whose_facts_cannot_be_read_does_not_stop_the_others(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    names = ("a-first.txt", "b-odd.txt", "c-last.txt")
    seen: dict[str, bytes] = {}
    real, remove = Path.lstat, tempfiles.shutil.rmtree

    def failing_for_one(self: Path) -> os.stat_result:
        if self.name == "b-odd.txt":
            raise PermissionError(13, "Access is denied")
        return real(self)

    def recording(folder: Path, **options: object) -> None:
        # Read by name with the built-in open: the recorder of the other tests asks for the facts of each file.
        for name in names:
            with open(os.path.join(folder, name), "rb") as handle:
                seen[name] = handle.read()
        remove(folder, **options)

    monkeypatch.setattr(tempfiles.shutil, "rmtree", recording)
    with tempfiles.private_dir(tmp_path) as folder:
        for name in names:
            (folder / name).write_text(TEXT, encoding="utf-8")
        monkeypatch.setattr(Path, "lstat", failing_for_one)
    monkeypatch.setattr(Path, "lstat", real)
    assert list(tmp_path.iterdir()) == []
    assert set(seen["a-first.txt"]) == {0}
    assert set(seen["c-last.txt"]) == {0}
    assert seen["b-odd.txt"] == TEXT.encode("utf-8")


def test_a8_blocks_in_two_threads_hand_out_the_newest_open_folder_to_both(tmp_path: Path) -> None:
    before = tempfile.gettempdir()
    second_open, first_may_go, seen = threading.Event(), threading.Event(), {}

    def second() -> None:
        with tempfiles.private_dir(tmp_path) as folder:
            seen["second folder"] = folder
            second_open.set()
            first_may_go.wait(timeout=30)

    with tempfiles.private_dir(tmp_path) as first:
        worker = threading.Thread(target=second)
        worker.start()
        assert second_open.wait(timeout=30)
        # The first thread asks while the second thread's block is the newest that is open.
        seen["asked by the first thread"] = Path(tempfile.gettempdir())
        first_may_go.set()
        worker.join(timeout=30)
        assert not worker.is_alive()
        seen["after the second ended"] = Path(tempfile.gettempdir())
    assert seen["asked by the first thread"] == seen["second folder"]
    assert seen["after the second ended"] == first
    assert tempfile.gettempdir() == before
    assert list(tmp_path.iterdir()) == []


def test_a8_the_temp_folder_of_the_process_is_changed_only_under_the_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The lock the module really uses is a lock; the watcher below stands in for it only to see when it is held.
    assert isinstance(tempfiles._LOCK, type(threading.Lock()))
    held, changes = [], []

    class Watched:
        """A lock that says whether it is held."""

        def __enter__(self) -> None:
            held.append(True)

        def __exit__(self, *details: object) -> None:
            held.pop()

    class Watching(list[object]):
        """A list that writes down whether the lock was held at each change."""

        def append(self, item: object) -> None:
            changes.append(("list", bool(held)))
            super().append(item)

        def remove(self, item: object) -> None:
            changes.append(("list", bool(held)))
            super().remove(item)

        def clear(self) -> None:
            changes.append(("list", bool(held)))
            super().clear()

    class WatchedTempfile:
        """The tempfile module, writing down whether the lock was held each time its temp folder is set."""

        def __getattr__(self, name: str) -> object:
            return getattr(tempfile, name)

        def __setattr__(self, name: str, value: object) -> None:
            changes.append((name, bool(held)))
            setattr(tempfile, name, value)

    before = tempfile.tempdir
    monkeypatch.setattr(tempfiles, "_LOCK", Watched())
    monkeypatch.setattr(tempfiles, "_OPEN", Watching())
    monkeypatch.setattr(tempfiles, "tempfile", WatchedTempfile())
    with tempfiles.private_dir(tmp_path), tempfiles.private_dir(tmp_path):
        pass
    # Two blocks: three additions to the list, two removals and one emptying; the temp folder set four times.
    assert changes.count(("list", True)) == 6
    assert changes.count(("tempdir", True)) == 4
    assert len(changes) == 10
    assert held == []
    assert tempfile.tempdir == before


def test_ec14_sweep_leaves_the_folder_of_a_block_that_is_still_open(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        (folder / "work.txt").write_text(TEXT, encoding="utf-8")
        assert tempfiles.sweep(tmp_path) == 0
        assert (folder / "work.txt").read_text(encoding="utf-8") == TEXT
    assert list(tmp_path.iterdir()) == []


def test_ec15_sweep_removes_a_killed_run_and_its_lock_file(tmp_path: Path) -> None:
    folder = leftover(tmp_path, "killed")
    lock = folder.with_name(folder.name + tempfiles.LOCK_SUFFIX)
    lock.write_bytes(b"")
    assert tempfiles.sweep(tmp_path) == 1
    assert list(tmp_path.iterdir()) == []


def test_ec16_the_lock_file_beside_the_folder(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        lock = folder.with_name(folder.name + tempfiles.LOCK_SUFFIX)
        assert lock.is_file()
        assert held(lock) is True
        assert list(folder.iterdir()) == []
    assert list(tmp_path.iterdir()) == []


def test_ec16_the_lock_file_goes_when_the_block_ends_with_not_removed(tmp_path: Path, stuck: None) -> None:
    with pytest.raises(tempfiles.NotRemoved), tempfiles.private_dir(tmp_path) as folder:
        pass
    assert not folder.with_name(folder.name + tempfiles.LOCK_SUFFIX).exists()


def test_ec14_sweep_goes_on_past_a_live_folder_to_a_dead_one(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        dead = leftover(tmp_path, "zzz-dead")
        assert tempfiles.sweep(tmp_path) == 1
        assert not dead.exists()
        assert folder.is_dir()


def test_ec17_the_sweep_holds_the_lock_while_it_removes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    folder = leftover(tmp_path, "dead")
    seen: list[bool] = []
    real_remove = tempfiles._remove

    def remove_and_look(path: Path) -> None:
        seen.append(held(path.with_name(path.name + tempfiles.LOCK_SUFFIX)))
        real_remove(path)

    monkeypatch.setattr(tempfiles, "_remove", remove_and_look)
    assert tempfiles.sweep(tmp_path) == 1
    assert seen == [True]
    assert not folder.exists()


def test_ec18_a_run_whose_lock_file_a_sweep_made(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_mkdtemp = tempfile.mkdtemp
    ran: list[bool] = []

    def made_and_taken(*arguments: object, **keywords: object) -> str:
        name = real_mkdtemp(*arguments, **keywords)
        Path(name + tempfiles.LOCK_SUFFIX).write_bytes(b"")
        return name

    monkeypatch.setattr(tempfiles.tempfile, "mkdtemp", made_and_taken)
    with pytest.raises(FileExistsError), tempfiles.private_dir(tmp_path):
        ran.append(True)
    assert ran == []
    assert [entry.is_dir() for entry in tmp_path.iterdir()] == [False]


def test_ec19_a_run_whose_folder_a_sweep_removed_before_the_hold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_hold = locks.hold
    ran: list[bool] = []

    def removed_then_held(handle: object) -> None:
        for folder in tmp_path.iterdir():
            if folder.is_dir():
                folder.rmdir()
        real_hold(handle)

    monkeypatch.setattr(tempfiles.locks, "hold", removed_then_held)
    with pytest.raises(FileNotFoundError), tempfiles.private_dir(tmp_path):
        ran.append(True)
    assert ran == []


def test_ec20_a_lock_path_that_cannot_be_opened_does_not_stop_the_sweep(tmp_path: Path) -> None:
    first = leftover(tmp_path, "a")
    (tmp_path / f"{first.name}{tempfiles.LOCK_SUFFIX}").mkdir()
    later = leftover(tmp_path, "b")
    with pytest.raises(OSError) as raised:
        tempfiles.sweep(tmp_path)
    assert not isinstance(raised.value, tempfiles.NotRemoved)
    assert not later.exists()
    assert first.is_dir()


def test_ec21_a_lock_file_with_no_folder_is_removed(tmp_path: Path) -> None:
    (tmp_path / f"{tempfiles.PREFIX}gone{tempfiles.LOCK_SUFFIX}").write_bytes(b"")
    assert tempfiles.sweep(tmp_path) == 0
    assert list(tmp_path.iterdir()) == []


def test_ec21_the_sweep_goes_on_past_a_held_lock_file_to_a_lone_one(tmp_path: Path) -> None:
    lone = tmp_path / f"{tempfiles.PREFIX}zzzz-gone{tempfiles.LOCK_SUFFIX}"
    lone.write_bytes(b"")
    with tempfiles.private_dir(tmp_path) as folder:
        assert tempfiles.sweep(tmp_path) == 0
        assert not lone.exists()
        assert held(folder.with_name(folder.name + tempfiles.LOCK_SUFFIX)) is True


@pytest.mark.parametrize("target_exists", [True, False])
def test_ec22_a_link_named_like_a_lone_lock_file_is_left(tmp_path: Path, target_exists: bool) -> None:
    root, outside = tmp_path / "root", outside_tree(tmp_path)
    root.mkdir()
    target = outside / ("kept.txt" if target_exists else "made-by-no-one.txt")
    at = root / f"{tempfiles.PREFIX}gone{tempfiles.LOCK_SUFFIX}"
    link(at, target, "symlink")
    assert tempfiles.sweep(root) == 0
    assert at.is_symlink()
    assert target.exists() is target_exists
    assert untouched(outside)


@pytest.mark.parametrize("target_exists", [True, False])
def test_ec23_a_link_in_the_place_of_a_dead_folders_lock_file(tmp_path: Path, target_exists: bool) -> None:
    root, outside = tmp_path / "root", outside_tree(tmp_path)
    root.mkdir()
    folder = leftover(root, "dead")
    target = outside / ("kept.txt" if target_exists else "made-by-no-one.txt")
    link(folder.with_name(folder.name + tempfiles.LOCK_SUFFIX), target, "symlink")
    assert tempfiles.sweep(root) == 1
    assert list(root.iterdir()) == []
    assert target.exists() is target_exists
    assert untouched(outside)


def test_ec24_a_lone_lock_pass_leaves_an_unheld_lock_file_beside_a_live_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The state of a run between its "xb" open and its hold; _sweep_one is set aside so that the
    # lone-lock pass alone meets it.
    folder = tmp_path / f"{tempfiles.PREFIX}starting"
    folder.mkdir()
    lock = folder.with_name(folder.name + tempfiles.LOCK_SUFFIX)
    lock.write_bytes(b"")
    monkeypatch.setattr(tempfiles, "_sweep_one", lambda folder: 0)
    assert tempfiles.sweep(tmp_path) == 0
    assert lock.exists()


def test_ec25_a_held_lock_file_with_no_folder_is_left(tmp_path: Path) -> None:
    # The state of a block between its folder's removal and the close of its lock file.
    lock = tmp_path / f"{tempfiles.PREFIX}ending{tempfiles.LOCK_SUFFIX}"
    lock.write_bytes(b"")
    with open(lock, "r+b") as handle:
        locks.hold(handle)
        assert tempfiles.sweep(tmp_path) == 0
        assert lock.exists()
