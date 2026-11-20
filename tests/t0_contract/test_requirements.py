"""Every dependency is pinned: each requirements file names exact versions, each with its hashes.

Why: `CLAUDE.md`, Hard constraints: "Pin every dependency version"; `PROMOTION.md` section 5.1
lists "Every dependency pinned: requirements parse test" among the Class A checks (issue #78),
and `PROCESS.md` section 12 item 8 asks for "Hashes in every requirements file, the ones under
`experiments/` included, and installs with `--require-hashes`". A version that floats installs
something no one reviewed; a file without hashes installs whatever the index serves today.

The rule: in every tracked file named `requirements*.txt`, each requirement is `name==version`,
with an optional environment marker, and at least one `--hash=sha256:` of 64 hex digits; the
only other line is `-r` of another requirements file that exists. No other option (`-e`, an
index URL, `-f`), no URL or path as a requirement, no wildcard version.

Test matrix:

Equivalence classes:
  EC1  a pinned, hashed requirement: one hash, several, with a marker, over continued lines   no line
  EC2  a version that floats: none, `>=`, `~=`, `!=`, `<`, `==1.*`, `===`    a line
  EC3  a pinned requirement with no hash, or a hash that is not sha256 of 64 hex digits   a line
  EC4  a line that installs from elsewhere: `-e`, a URL, a path, `--index-url`,
       `--extra-index-url`, `-f`, `--trusted-host`                         a line
  EC5  `-r` of a file that exists, and of one that does not                 no line, a line
  EC6  comments, blank lines, Windows line ends                            no line
  EC7  the repository: every tracked requirements file                      no line

Boundaries:
  B1  a hash of 63 and of 65 hex digits                                     a line
  B2  a hash given on the requirement's own line, and on the next only      both pinned

Adversarial:
  A1  `--hash` with no value, and a hash with upper-case hex                 a line
  A2  a requirement split over continued lines with its hash on a comment line   a line

Not applicable: the Hebrew axes and the document axes of the test-matrix skill: the input is
a requirements file.

Known limits:
  - The hashes are read, not checked against the files they name: that is what an install with
    `--require-hashes` does. The hashes under `experiments/` are PyPI's for the pinned versions,
    read from its metadata on 2026-11-20; no install with them has been run since.
  - Only files named `requirements*.txt` are read. `pyproject.toml` declares no dependency yet;
    when it does, this check is widened in the same PR.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# The file names the rule reads (pip's own convention).
NAME = re.compile(r"requirements[^/]*\.txt")
# git from PATH, as a full path, as in CI; the seconds a git command may take.
GIT = shutil.which("git") or "git"
GIT_TIMEOUT_SECONDS = 60


def _git(*args: str) -> bytes:
    """Run one git command and return what it printed."""
    return subprocess.run(  # noqa: S603 fixed argv, no shell
        [GIT, *args], capture_output=True, check=True, timeout=GIT_TIMEOUT_SECONDS
    ).stdout


def problems(text: str, folder: Path) -> list[str]:
    """Name each requirement of a requirements file that is not pinned and hashed, as "<line>: <what>"."""
    return []


def requirement_files(root: Path) -> list[Path]:
    """Return the tracked requirements files of a repository, in git's order."""
    return []


def _lines(text: str) -> list[int]:
    """Return the line numbers `problems` names."""
    return [int(line.split(":")[0]) for line in problems(text, ROOT)]


HASH = "0123456789abcdef" * 4
OTHER = "fedcba9876543210" * 4


@pytest.mark.parametrize(
    "text",
    [
        f"pytest==9.2.0 --hash=sha256:{HASH}\n",
        f"pytest==9.2.0 \\\n    --hash=sha256:{HASH} \\\n    --hash=sha256:{OTHER}\n",
        f'colorama==0.4.6 ; sys_platform == "win32" \\\n    --hash=sha256:{HASH}\n',
        f"ml_dtypes==0.6.0 \\\n    --hash=sha256:{HASH}\n",
        f"zope.interface==7.0.1 --hash=sha256:{HASH}\n",
    ],
)
def test_ec1_pinned_and_hashed(text: str) -> None:
    assert problems(text, ROOT) == []


@pytest.mark.parametrize("spec", ["pytest", "pytest>=9", "pytest~=9.2", "pytest!=9.1", "pytest<10", "pytest==9.*", "pytest===9.2.0"])
def test_ec2_a_version_that_floats(spec: str) -> None:
    assert _lines(f"# tools\n{spec} --hash=sha256:{HASH}\n") == [2]


@pytest.mark.parametrize(
    "text",
    [
        "pytest==9.2.0\n",
        "pytest==9.2.0 --hash=md5:0123456789abcdef0123456789abcdef\n",
        f"pytest==9.2.0 --hash=sha512:{HASH}{HASH}\n",
    ],
)
def test_ec3_no_hash_or_a_hash_of_another_kind(text: str) -> None:
    assert _lines(text) == [1]


@pytest.mark.parametrize(
    "text",
    [
        "-e .\n",
        f"git+https://example.invalid/repo.git#egg=x --hash=sha256:{HASH}\n",
        f"https://example.invalid/x-1.0.tar.gz --hash=sha256:{HASH}\n",
        f"./vendor/x-1.0.tar.gz --hash=sha256:{HASH}\n",
        "--index-url https://example.invalid/simple\n",
        "--extra-index-url https://example.invalid/simple\n",
        "-f https://example.invalid/wheels\n",
        "--trusted-host example.invalid\n",
    ],
)
def test_ec4_a_line_that_installs_from_elsewhere(text: str) -> None:
    assert _lines(text) == [1]


def test_ec5_an_include(tmp_path: Path) -> None:
    (tmp_path / "base.txt").write_text(f"x==1.0 --hash=sha256:{HASH}\n", encoding="utf-8")
    assert problems("-r base.txt\n", tmp_path) == []
    assert problems("-r ../missing/requirements.txt\n", tmp_path) == ["1: -r ../missing/requirements.txt: no such file"]


def test_ec6_comments_blank_lines_and_windows_line_ends() -> None:
    text = f"# a comment\r\n\r\npytest==9.2.0 \\\r\n    --hash=sha256:{HASH}\r\n   # indented comment\r\n"
    assert problems(text, ROOT) == []


def test_ec7_the_repository() -> None:
    files = requirement_files(ROOT)
    assert {path.relative_to(ROOT).as_posix() for path in files} >= {
        "requirements.txt",
        "requirements-dev.txt",
        "experiments/e1_hebrew_recall/requirements.txt",
    }
    found = [
        f"{path.relative_to(ROOT).as_posix()}:{line}"
        for path in files
        for line in problems(path.read_text(encoding="utf-8"), path.parent)
    ]
    assert found == []


@pytest.mark.parametrize("digits", [63, 65])
def test_b1_a_hash_of_the_wrong_length(digits: int) -> None:
    assert _lines(f"pytest==9.2.0 --hash=sha256:{(HASH * 2)[:digits]}\n") == [1]


def test_b2_a_hash_on_the_line_or_on_the_next() -> None:
    assert problems(f"pytest==9.2.0 --hash=sha256:{HASH}\n", ROOT) == []
    assert problems(f"pytest==9.2.0 \\\n--hash=sha256:{HASH}\n", ROOT) == []


@pytest.mark.parametrize("text", ["pytest==9.2.0 --hash\n", f"pytest==9.2.0 --hash=sha256:{HASH.upper()}\n"])
def test_a1_a_hash_with_no_value_or_upper_case(text: str) -> None:
    assert _lines(text) == [1]


def test_a2_a_hash_on_a_comment_line() -> None:
    assert _lines(f"pytest==9.2.0\n# --hash=sha256:{HASH}\n") == [1]


def test_the_file_names_read(tmp_path: Path) -> None:
    _git("init", "-q", str(tmp_path))
    names = ("requirements.txt", "requirements-dev.txt", "x/requirements.txt", "constraints.txt", "requirements.in", "notes.txt")
    for name in names:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("\n", encoding="utf-8")
    _git("-C", str(tmp_path), "add", *names)
    found = [path.relative_to(tmp_path).as_posix() for path in requirement_files(tmp_path)]
    assert found == ["requirements-dev.txt", "requirements.txt", "x/requirements.txt"]
