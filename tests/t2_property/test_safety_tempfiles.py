"""The invariant of ploni/safety/tempfiles.py over generated trees: whatever a block makes, nothing is left.

Why: the unit tests and the canary try the trees someone thought of. `PROCESS.md` section 4.3
asks for a test over generated input for any invariant that can be stated over it, and this
module has one.

The invariant, for every tree a block can make inside its private folder:
  - after the block the root holds nothing;
  - at the moment a file of the folder's own is removed it holds only zeros, at its full length;
  - a folder outside, which the tree links to in every way this system has, is as it was:
    every byte, and the read-only mark of its read-only file.

Generated input: TREES are 500 trees from a seeded generator. A tree is 1 to 6 entries, each
one of: a file in the folder or up to three folders deep, with a name in Hebrew, in Latin
letters or with spaces, of 0 to 3,000 bytes, read-only or not; an empty folder, read-only or
not; a second name for an earlier file, inside the folder; a second name, inside, for a file
outside; a symbolic link to a file or a folder outside; on Windows a junction to a folder
outside. One test runs all 500, so that the cost of the file system is paid once.

Not covered: a file that is open when the block ends, which the unit tests and the canary
cover for both kinds of system.
"""

import os
import random
import stat
import sys
from pathlib import Path

import pytest

from ploni.safety import tempfiles
from tests.sizes import INVARIANT_FULL, full

if sys.platform == "win32":
    import _winapi

# CLAUDE.md, Tests: an invariant is held over 500 generated cases.
TREES = INVARIANT_FULL if full() else 500
TEXT = "יעקב כהן / John Smith ".encode()
NAMES = ("page", "חוזה שכירות", "two words", "a.b.c", "יעקב-כהן", "x")
KINDS = ["file", "file", "file", "folder", "second name", "name of an outside file", "link to a file", "link to a folder"]
if sys.platform == "win32":
    KINDS.append("junction")


def outside_tree(base: Path) -> Path:
    """Make a folder that is not the helper's: a file, a read-only file, and a file one folder deeper."""
    outside = base / "outside"
    (outside / "sub").mkdir(parents=True)
    (outside / "kept.txt").write_bytes(TEXT)
    (outside / "sub" / "deep.txt").write_bytes(TEXT)
    (outside / "locked.txt").write_bytes(TEXT)
    (outside / "locked.txt").chmod(stat.S_IREAD)
    return outside


def untouched(outside: Path) -> bool:
    """Say whether the outside folder is as `outside_tree` made it."""
    files = [outside / "kept.txt", outside / "sub" / "deep.txt", outside / "locked.txt"]
    same = all(file.read_bytes() == TEXT for file in files)
    return same and not os.access(outside / "locked.txt", os.W_OK) and sorted(path.name for path in outside.iterdir()) == ["kept.txt", "locked.txt", "sub"]


def entry(kind: str, at: Path, own: list[Path], outside: Path, rng: random.Random) -> None:
    """Make one entry of a kind at a path; a file of the folder's own is added to `own`."""
    if kind == "file":
        at.write_bytes((TEXT * 140)[: rng.choice([0, 1, 22, 3000])])
        own.append(at)
    elif kind == "folder":
        at.mkdir()
    elif kind == "second name" and own:
        os.link(rng.choice(own), at)
        own.append(at)
    elif kind == "name of an outside file":
        os.link(outside / "kept.txt", at)
    elif kind == "link to a file":
        at.symlink_to(outside / rng.choice(["kept.txt", "locked.txt", "missing.txt"]))
    elif kind == "link to a folder":
        at.symlink_to(outside / rng.choice(["sub", ""]), target_is_directory=True)
    elif kind == "junction":
        _winapi.CreateJunction(str(outside / rng.choice(["sub", ""])), str(at))


def build(folder: Path, outside: Path, rng: random.Random, made: set[str]) -> list[Path]:
    """Make one generated tree inside the folder and return the files that are the folder's own.

    Every kind of entry that was really made is added to `made`.
    """
    own: list[Path] = []
    for number in range(rng.randint(1, 6)):
        where = folder.joinpath(*[f"d{rng.randint(0, 2)}" for _ in range(rng.randint(0, 3))])
        where.mkdir(parents=True, exist_ok=True)
        at = where / f"{rng.choice(NAMES)} {number}"
        kind = rng.choice(KINDS)
        entry(kind, at, own, outside, rng)
        if at.is_symlink() or at.is_junction() or at.exists():
            made.add(kind)
        # A read-only mark on a second name of an outside file would mark that file too.
        if kind in ("file", "folder", "second name") and at.exists() and rng.random() < 0.3:
            at.chmod(stat.S_IREAD | (stat.S_IEXEC if at.is_dir() else 0))
    return own


def test_whatever_tree_a_block_makes_nothing_is_left_and_nothing_outside_is_touched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rng = random.Random("ploni-safety-tempfiles")  # noqa: S311 seeded on purpose, so the trees are the same on every run
    root, outside = tmp_path / "root", outside_tree(tmp_path)
    still_text: list[str] = []
    real = tempfiles.shutil.rmtree

    def recording(folder: Path, **options: object) -> None:
        for path, size in sizes.items():
            data = path.read_bytes()
            if any(data) or len(data) != size:
                still_text.append(str(path))
        real(folder, **options)

    monkeypatch.setattr(tempfiles.shutil, "rmtree", recording)
    failed = []
    made: set[str] = set()
    for number in range(TREES):
        with tempfiles.private_dir(root) as folder:
            expected = build(folder, outside, rng, made)
            sizes = {path: path.stat().st_size for path in expected}
        if list(root.iterdir()) or not untouched(outside):
            failed.append(number)
    assert failed == []
    assert still_text == []
    # Without this, a generator that never made a link would let the invariant pass for nothing.
    assert made == set(KINDS)


def test_the_sample_is_over_500() -> None:
    # CLAUDE.md, Tests: an invariant is held over 500 generated cases, 5,000 at phase close.
    assert TREES == (INVARIANT_FULL if full() else 500)
