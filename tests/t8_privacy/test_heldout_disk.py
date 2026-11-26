"""Nothing of the held-out batch reaches a disk, a log or the output of a failing test.

Why: Achia chose on 2026-11-26 that the batch is "Made fresh each run": "Each time the score
runs, the documents are made in memory and thrown away. No list of ID or card numbers sits in
any file" (issue 283). `CLAUDE.md`, Hard constraints: "No document text in logs or temp files."
A cache file, a temp file or a debug dump of the key would undo that answer without any other
test noticing; and so would a failing test, whose output pytest fills with what its assertion
compared, read by the session that writes the detectors and kept in the public CI log (review 1
of the branch, finding 1).

Test matrix:
  D1  every way of opening a file for writing raises while the batch is built (builtins.open,
      io.open, os.open, and os.mkdir), so a write anywhere fails the test; the batch is built
      all the same, and the key replayed against itself matches it whole
  D2  the temp folder (tempfile's, and TMP, TEMP and TMPDIR, pointed at a fresh empty folder)
      and the working folder (a fresh empty one) are empty before and after
  D3  the repository's files, names and sizes, are the same before and after
  D4  a broken build (every key span moved by one, no Hebrew marks) makes the generator's own
      tests fail, run in a child pytest at -vv; their output holds no planted text of 4 code
      points or more (but a run of underscores, which is how pytest draws its own rules), and
      pytest's failure lines are in it (the positive control)
  D5  the check that the checker works: a write made inside the guard of D1 is caught

Known limits: a write made by another process, or through a C extension that does not call
these functions, is not seen; the batch's code imports neither. The real temp folder of the
machine is not listed, as other programs write to it at any time: D1 is what covers it. D4
shows what the tests print when they fail in the two ways it breaks, not in every way.
"""

import builtins
import io
import os
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from eval.heldout.generator import SEED, build

ROOT = Path(__file__).resolve().parents[2]
SKIPPED = (".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache")
# The generator's own tests, run broken by D4.
GENERATOR_TESTS = (
    "tests/t1_unit/test_heldout_generator.py",
    "tests/t2_property/test_heldout_generator.py",
    "tests/t4_integration/test_heldout_generator.py",
)
# A pytest plugin that breaks the build: every key span one code point to the right, and the
# Hebrew marks never drawn.
BROKEN = '''
import dataclasses
import eval.heldout.generator as generator

_real = generator._document


def _broken(rng, index, planned):
    text, key, near = _real(rng, index, planned)
    return text, [dataclasses.replace(item, start=item.start + 1, end=item.end + 1) for item in key], near


generator._document = _broken
generator.HEBREW_MARK_TABLE = str.maketrans({})
'''
# The child pytest is given this long; it took about five seconds on the laptop.
CHILD_TIMEOUT_SECONDS = 300
SHORTEST_LEAK = 4


class WriteAttempt(AssertionError):
    """A write was attempted while the guard was on."""


@contextmanager
def no_writes(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Make every way of writing a file raise WriteAttempt inside the block; reading still works."""
    real_open, real_os_open = builtins.open, os.open

    def guarded_open(file: object, mode: str = "r", *args: object, **kwargs: object) -> object:
        if any(flag in mode for flag in "wax+"):
            raise WriteAttempt(f"open for writing, mode {mode}")
        return real_open(file, mode, *args, **kwargs)

    def guarded_os_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND):
            raise WriteAttempt("os.open for writing")
        return real_os_open(path, flags, *args, **kwargs)

    def refused(*args: object, **kwargs: object) -> None:
        raise WriteAttempt("a folder made")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", guarded_open)
        patch.setattr(io, "open", guarded_open)
        patch.setattr(os, "open", guarded_os_open)
        patch.setattr(os, "mkdir", refused)
        yield


def files_of(root: Path) -> set[tuple[str, int]]:
    """The files under root, by path below it and size, the caches and .git left out."""
    found = set()
    for folder, names, files in os.walk(root):
        names[:] = [name for name in names if name not in SKIPPED]
        found |= {(os.path.relpath(os.path.join(folder, name), root), os.path.getsize(os.path.join(folder, name))) for name in files}
    return found


def test_d1_d2_d3_nothing_is_written(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    temp, work = tmp_path / "temp", tmp_path / "work"
    temp.mkdir()
    work.mkdir()
    for name in ("TMP", "TEMP", "TMPDIR"):
        monkeypatch.setenv(name, str(temp))
    monkeypatch.setattr(tempfile, "tempdir", str(temp))
    monkeypatch.chdir(work)
    repository = files_of(ROOT)
    with no_writes(monkeypatch):
        batch = build(SEED)
        replayed = {(item.doc, item.start, item.end, item.type) for item in batch.key if batch.documents[item.doc][item.start : item.end] == item.text}
    assert len(replayed) == len(batch.key)
    assert (list(temp.iterdir()), list(work.iterdir())) == ([], [])
    same = files_of(ROOT) == repository
    assert same


def test_d4_a_failing_test_prints_no_planted_text(tmp_path: Path) -> None:
    (tmp_path / "broken_batch.py").write_text(BROKEN, encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    env |= {"PYTHONPATH": os.pathsep.join((str(tmp_path), str(ROOT))), "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    command = [sys.executable, "-m", "pytest", "-vv", "-p", "no:cacheprovider", "-p", "broken_batch", *GENERATOR_TESTS]
    done = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=CHILD_TIMEOUT_SECONDS, check=False)  # noqa: S603 fixed argv, no shell
    output = (done.stdout + done.stderr).decode("utf-8", errors="replace")
    clean = build(SEED)
    # A run of underscores tells nothing and is how pytest draws its own rules, so it is left out.
    telling = [item for item in clean.key + clean.near_misses if len(item.text) >= SHORTEST_LEAK and item.text.strip("_")]
    leaked = [index for index, item in enumerate(telling) if item.text in output]
    controls = (done.returncode, "FAILED" in output, "AssertionError" in output or "assert" in output)
    assert controls == (1, True, True)
    assert leaked == []


def test_d5_a_write_inside_the_guard_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with no_writes(monkeypatch):
        with pytest.raises(WriteAttempt):
            (tmp_path / "x.txt").write_text("x", encoding="utf-8")
        with pytest.raises(WriteAttempt):
            tempfile.mkstemp(dir=tmp_path)
        with pytest.raises(WriteAttempt):
            (tmp_path / "folder").mkdir()
        assert Path(__file__).read_text(encoding="utf-8").startswith('"""')
    assert list(tmp_path.iterdir()) == []
