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
                                folder steps back one block at a time
  EC6  the root                 made when it is missing, with the folders above it
  EC7  a read-only file, and a read-only folder with files in it    removed
  EC8  what is written over     every regular file holds only zeros, at its full length, at
                                the moment it is removed
  EC9  a file with a second name outside the folder (a hard link)    the name inside is
                                removed; the bytes, which the outside name still shows, are
                                kept; so too when the file is read-only
  EC10 a link to a file outside the folder (a symbolic link)    the link is removed; the file
                                outside is neither removed nor written over

sweep. Equivalence classes:
  EC11 folders left under the root    removed, overwritten like any other; their number is returned
  EC12 other entries of the root      a folder with another name, a file with the prefix: left alone
  EC13 a root that does not exist, an empty root    0

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
  E3  a file cannot be written over but can be removed    no error: it is gone

Adversarial:
  A1  a file name in Hebrew, with spaces, and a very long one
  A2  the block removes its own folder before it ends    no error

The Hebrew axes of the test-matrix skill apply to names and content of files (A1, and the
canary). The document-structure axes do not apply: no document is handled.
"""

import os
import stat
import sys
import tempfile
from pathlib import Path

import pytest

from ploni.safety import tempfiles

TEXT = "יעקב כהן / John Smith"


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
    sizes = {"empty": 0, "one": 1, "text": len(TEXT.encode("utf-8")), "large": 3 * tempfiles.CHUNK + 1}
    with tempfiles.private_dir(tmp_path) as folder:
        (folder / "deep").mkdir()
        for name, size in sizes.items():
            data = (TEXT.encode("utf-8") * (size // 20 + 1))[:size]
            (folder / "deep" / name).write_bytes(data)
        (folder / "deep" / "text").chmod(stat.S_IREAD)
    assert {name: len(data) for name, data in seen_at_removal.items()} == sizes
    assert all(set(data) <= {0} for data in seen_at_removal.values())


def test_ec9_a_file_with_a_second_name_outside_keeps_its_bytes(tmp_path: Path) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside.txt"
    outside.write_text(TEXT, encoding="utf-8")
    with tempfiles.private_dir(root) as folder:
        os.link(outside, folder / "same-file.txt")
    assert list(root.iterdir()) == []
    assert outside.read_text(encoding="utf-8") == TEXT


def test_ec9_a_read_only_file_with_a_second_name_outside_is_removed_and_keeps_its_bytes(tmp_path: Path) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside.txt"
    outside.write_text(TEXT, encoding="utf-8")
    outside.chmod(stat.S_IREAD)
    with tempfiles.private_dir(root) as folder:
        os.link(outside, folder / "same-file.txt")
    assert list(root.iterdir()) == []
    assert outside.read_text(encoding="utf-8") == TEXT


def test_ec10_a_link_to_a_file_outside_is_removed_and_the_file_is_untouched(tmp_path: Path) -> None:
    root, outside = tmp_path / "root", tmp_path / "outside"
    outside.mkdir()
    (outside / "kept.txt").write_text(TEXT, encoding="utf-8")
    with tempfiles.private_dir(root) as folder:
        try:
            (folder / "link.txt").symlink_to(outside / "kept.txt")
            (folder / "linked-folder").symlink_to(outside, target_is_directory=True)
        except OSError:
            # Windows gives the right to make a symbolic link only to some accounts (issue #90).
            pytest.skip("this account may not make a symbolic link; see issue #90")
    assert list(root.iterdir()) == []
    assert (outside / "kept.txt").read_text(encoding="utf-8") == TEXT


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
        for name in ("חוזה שכירות - יעקב כהן.docx", "two words.txt", "n" * 120 + ".txt"):
            (folder / name).write_text(TEXT, encoding="utf-8")
    assert list(tmp_path.iterdir()) == []


def test_a2_a_block_that_removes_its_own_folder(tmp_path: Path) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        folder.rmdir()
    assert list(tmp_path.iterdir()) == []
