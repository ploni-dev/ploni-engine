"""The temp-file canary: a string given as document text must not stay in a temp file.

Why: `CLAUDE.md`, Hard constraints: "No document text in logs or temp files." A temp file
that survives, after an error or a crash, is one of the loudest ways this product could leak
(ADR-0005). The canary is a string that stands for document text. It is written into temp
files in every way that code under `ploni.safety.tempfiles.private_dir` can write one, the
block ends in every way a block can end, and then every byte of every file under the temp
root is searched for it. It is one of the four tests the merge gate needs in order to work
(`PROMOTION.md` section 11).

Test matrix (every case writes the canary, ends the block, then searches the whole root):

How the canary is written (WAYS):
  W1  a text file in UTF-8                  W2  a text file in UTF-16 and one in cp1255
  W3  a file in folders nested three deep   W4  the canary as the name of a file and of a folder
  W5  a file opened by tempfile.mkstemp     W6  tempfile.NamedTemporaryFile(delete=False)
  W7  tempfile.mkdtemp, a file inside       W8  tempfile.TemporaryDirectory that is never closed
  W9  a read-only file                      W10 a file written in pieces through two handles
  W11 a tempfile.TemporaryFile that is still open when the block ends, with files beside it
  W12 a file with two names inside the folder
How the block ends (ENDINGS):
  N1  normally       N2  with an error      N3  the process is killed inside the block, and
                                                the next start calls sweep
For N3 the canary is first looked for and found: that is the positive control. It shows that
the search finds the canary in a temp file when it is there, and that the kill left it.

After the block the search covers every file under the root, by content in four encodings
and by name, and the root holds no entry at all.

Known limits:
  - No pipeline exists yet, so the canary is written by the test and not by `analyze` and
    `apply`. Every phase that adds a stage that writes a temp file adds a run of that stage
    over a document that holds the canary (`build-plan.md` section 7, T8).
  - A temp file made outside `private_dir`, by code that does not use the helper, is not seen
    by this test. Inside a block even a plain `tempfile` call lands in the private folder.
  - That the bytes are gone from the disk itself, and not only from the file system, is not
    tested and on a solid-state disk not promised (see the module's docstring).

The document-structure axes of the test-matrix skill do not apply: no document is handled.
"""

import os
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import pytest

from ploni.safety import tempfiles

ROOT = Path(__file__).resolve().parents[2]
HEBREW, LATIN, DIGITS = "קנרית־יעקב", "Canary-Jacob", "7301946"
CANARY = f"{HEBREW} {LATIN} {DIGITS}"
PARTS = (HEBREW, LATIN, DIGITS)
ENCODINGS = ("utf-8", "utf-16-le", "utf-16-be", "cp1255")


def text_files(folder: Path) -> None:
    """W1 and W2: the canary in a text file, in three encodings."""
    (folder / "utf8.txt").write_text(CANARY, encoding="utf-8")
    (folder / "utf16.txt").write_text(CANARY, encoding="utf-16")
    (folder / "cp1255.txt").write_text(CANARY, encoding="cp1255")


def nested(folder: Path) -> None:
    """W3: the canary three folders deep."""
    deep = folder / "a" / "b" / "c"
    deep.mkdir(parents=True)
    (deep / "page.txt").write_text(f"before {CANARY} after", encoding="utf-8")


def as_names(folder: Path) -> None:
    """W4: the canary as the name of a folder and of a file in it."""
    named = folder / CANARY
    named.mkdir()
    (named / f"{CANARY}.txt").write_text("nothing of note", encoding="utf-8")


def by_mkstemp(folder: Path) -> None:
    """W5: a file from tempfile.mkstemp, which knows nothing of the helper."""
    handle, _ = tempfile.mkstemp(suffix=".tmp")
    os.write(handle, CANARY.encode("utf-8"))
    os.close(handle)


def by_named_temporary_file(folder: Path) -> None:
    """W6: a NamedTemporaryFile that its maker forgot to delete."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as kept:
        kept.write(CANARY)


def by_mkdtemp(folder: Path) -> None:
    """W7: a folder from tempfile.mkdtemp with a file in it."""
    (Path(tempfile.mkdtemp()) / "page.txt").write_text(CANARY, encoding="utf-8")


def by_temporary_directory(folder: Path) -> None:
    """W8: a TemporaryDirectory that is never closed."""
    made = tempfile.TemporaryDirectory()
    (Path(made.name) / "page.txt").write_text(CANARY, encoding="utf-8")
    # Its own clean-up must not run before the block ends, or the helper would have nothing to do.
    made._finalizer.detach()


def read_only(folder: Path) -> None:
    """W9: a file that is read-only when the block ends."""
    locked = folder / "locked.txt"
    locked.write_text(CANARY, encoding="utf-8")
    locked.chmod(stat.S_IREAD)


def in_pieces(folder: Path) -> None:
    """W10: a file written in pieces through two handles."""
    path = folder / "pieces.txt"
    with path.open("wb") as first:
        first.write(CANARY.encode("utf-8")[:10])
    with path.open("ab") as second:
        second.write(CANARY.encode("utf-8")[10:])
        second.write(CANARY.encode("utf-16"))


STILL_OPEN: list[object] = []


def still_open(folder: Path) -> None:
    """W11: a TemporaryFile that nobody closes before the block ends, and files that sort around it."""
    (folder / "a-before.txt").write_text(CANARY, encoding="utf-8")
    held = tempfile.TemporaryFile()
    held.write(CANARY.encode("utf-8"))
    held.flush()
    STILL_OPEN.append(held)
    (folder / "zz-after.txt").write_text(CANARY, encoding="utf-8")
    (folder / "zz-dir").mkdir()
    (folder / "zz-dir" / "inner.txt").write_text(CANARY, encoding="utf-8")


def two_names(folder: Path) -> None:
    """W12: one file under two names, both inside the folder."""
    (folder / "first-name.txt").write_text(CANARY, encoding="utf-8")
    (folder / "inner").mkdir()
    os.link(folder / "first-name.txt", folder / "inner" / "second-name.txt")


WAYS: dict[str, Callable[[Path], None]] = {
    "W1 W2 text files": text_files,
    "W3 nested": nested,
    "W4 names": as_names,
    "W5 mkstemp": by_mkstemp,
    "W6 NamedTemporaryFile": by_named_temporary_file,
    "W7 mkdtemp": by_mkdtemp,
    "W8 TemporaryDirectory": by_temporary_directory,
    "W9 read-only": read_only,
    "W10 pieces": in_pieces,
    "W11 still open": still_open,
    "W12 two names": two_names,
}


def leaks(root: Path) -> list[str]:
    """Return where a part of the canary is found under root: in the bytes of a file or in a name."""
    found = []
    for path in sorted(root.rglob("*")):
        if any(part in path.name for part in PARTS):
            found.append(f"name of {path.relative_to(root).as_posix()}")
        if path.is_file():
            try:
                data = path.read_bytes()
            except OSError:
                # A file that a program holds open for itself alone cannot be read; it cannot be searched.
                continue
            found += [
                f"{part} as {encoding} in {path.relative_to(root).as_posix()}"
                for part in PARTS
                for encoding in ENCODINGS
                if part.encode(encoding) in data
            ]
    return found


@pytest.mark.parametrize("way", WAYS)
def test_n1_the_canary_is_gone_after_a_block_that_ends_normally(tmp_path: Path, way: str) -> None:
    with tempfiles.private_dir(tmp_path) as folder:
        WAYS[way](folder)
        assert leaks(tmp_path) != [], "the way wrote the canary under the root"
    assert leaks(tmp_path) == []
    assert list(tmp_path.iterdir()) == []
    while STILL_OPEN:
        STILL_OPEN.pop().close()


def test_n1_the_canary_is_written_over_before_a_file_goes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # What the search above cannot see: a file that is removed still holding the canary.
    held = []
    real = tempfiles.shutil.rmtree

    def recording(folder: Path, **options: object) -> None:
        held.extend(leaks(Path(folder)))
        real(folder, **options)

    monkeypatch.setattr(tempfiles.shutil, "rmtree", recording)
    for name, way in WAYS.items():
        if name == "W4 names":
            # A name is not written over: a stated limit.
            continue
        with tempfiles.private_dir(tmp_path) as folder:
            way(folder)
    assert held == []
    while STILL_OPEN:
        STILL_OPEN.pop().close()


@pytest.mark.parametrize("way", WAYS)
def test_n2_the_canary_is_gone_after_a_block_that_ends_with_an_error(tmp_path: Path, way: str) -> None:
    with pytest.raises(RuntimeError, match="stopped"), tempfiles.private_dir(tmp_path) as folder:
        WAYS[way](folder)
        raise RuntimeError("stopped")
    assert leaks(tmp_path) == []
    assert list(tmp_path.iterdir()) == []
    while STILL_OPEN:
        STILL_OPEN.pop().close()


KILLED = """
import os, sys
from pathlib import Path
from ploni.safety import tempfiles

root, canary = Path(sys.argv[1]), sys.argv[2]
with tempfiles.private_dir(root) as folder:
    (folder / "page.txt").write_text(canary, encoding="utf-8")
    (folder / "inner").mkdir()
    (folder / "inner" / "utf16.txt").write_text(canary, encoding="utf-16")
    sys.stdout.write(str(sum(map(ord, canary))))
    sys.stdout.flush()
    os._exit(9)
"""


def test_n3_the_canary_a_killed_process_left_is_gone_after_the_next_start_sweeps(tmp_path: Path) -> None:
    command = [sys.executable, "-c", KILLED, str(tmp_path), CANARY]
    ended = subprocess.run(command, cwd=ROOT, capture_output=True, check=False)  # noqa: S603 fixed argv, no shell
    assert ended.returncode == 9, ended.stderr
    # The sum of the canary's code points: the canary reached the program whole.
    assert ended.stdout == str(sum(map(ord, CANARY))).encode("ascii")
    left = leaks(tmp_path)
    assert f"{HEBREW} as utf-8 in " in " ".join(left), left
    assert f"{HEBREW} as utf-16-le in " in " ".join(left), left
    assert tempfiles.sweep(tmp_path) == 1
    assert leaks(tmp_path) == []
    assert list(tmp_path.iterdir()) == []


def test_the_search_finds_the_canary_when_it_is_there(tmp_path: Path) -> None:
    # The check that the checker works: each form a leak could take is found, and nothing else is.
    (tmp_path / "deep").mkdir()
    (tmp_path / "deep" / "utf8.bin").write_bytes(b"\x00\x01" + HEBREW.encode("utf-8") + b"\xff")
    (tmp_path / "utf16be.bin").write_bytes(DIGITS.encode("utf-16-be"))
    (tmp_path / "cp1255.bin").write_bytes(HEBREW.encode("cp1255"))
    (tmp_path / f"report {LATIN}.txt").write_bytes(b"clean")
    (tmp_path / "clean.txt").write_bytes(bytes(100) + "יעקב לוי, Jacob, 73019".encode())
    assert leaks(tmp_path) == [
        f"{HEBREW} as cp1255 in cp1255.bin",
        f"{HEBREW} as utf-8 in deep/utf8.bin",
        f"name of report {LATIN}.txt",
        f"{DIGITS} as utf-16-be in utf16be.bin",
    ]
