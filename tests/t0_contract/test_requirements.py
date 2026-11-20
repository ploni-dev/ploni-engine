"""Every dependency is pinned: each requirements file names exact versions, each with its hashes.

Why: `CLAUDE.md`, Hard constraints: "Pin every dependency version"; `PROMOTION.md` section 5.1
lists "Every dependency pinned: requirements parse test" among the Class A checks (issue #78),
and `PROCESS.md` section 12 item 8 asks for "Hashes in every requirements file, the ones under
`experiments/` included, and installs with `--require-hashes`". A version that floats installs
something no one reviewed; a file without hashes installs whatever the index serves today.

The rule: in every tracked file named `requirements*.txt`, each requirement is `name==version`,
with optional extras, spaces around `==` and an environment marker, and at least one
`--hash=sha256:` of 64 hex digits among its words. The only other lines are `-r` of another
requirements file that exists, `--require-hashes` and `--only-binary :all:`, each alone on its
line. No other option (`-e`, an index URL, `-f`), no URL or path as a requirement, no wildcard
version. Comments are cut as pip cuts them; lines are joined much as pip joins them (Known
limits).

Test matrix:

Equivalence classes:
  EC1  a pinned, hashed requirement: one hash, several, with a marker, over continued lines   no line
  EC2  a version that floats: none, `>=`, `~=`, `!=`, `<`, `==1.*`, `===`    a line
  EC3  a pinned requirement with no hash, or a hash that is not sha256 of 64 hex digits   a line
  EC4  a line that installs from elsewhere: `-e`, a URL, a path, `--index-url`,
       `--extra-index-url`, `-f`, `--trusted-host`, one of them after a stricter option,
       `--only-binary :none:`, a hash with more glued to it                 a line
  EC5  `-r` of a requirements file that exists; of one that does not, of a file the rule does
       not read, `-r` followed by more, `-e` of a requirements file      no line; a line each
  EC6  comments, blank lines, Windows line ends                            no line
  EC7  the repository: every tracked requirements file                      no line
  EC8  a continued line at the end of a file, with and without a last line break   a line
  EC9  a comment after a tab that holds the only hash                       a line
  EC10 an inline comment after a hashed requirement                         no line
  EC11 a marker with no space, extras, spaces around `==`, `--require-hashes`,
       `--only-binary :all:` in both forms                                 no line

Boundaries:
  B1  a hash of 63 and of 65 hex digits                                     a line
  B2  a hash given on the requirement's own line, and on the next only      both pinned

Adversarial:
  A1  `--hash` with no value, and a hash with upper-case hex                 a line
  A2  a hash on a comment line under a requirement                          a line
  A3  a hash inside a marker string                                         a line
  A4  a continued requirement with its hash on a comment line               a line

And for the parts on their own: `_logical` names each logical line at its first line; a problem
never prints a hash in full; `requirement_files` reads `requirements*.txt` in any folder, not
`constraints.txt`, `*.in`, `*.orig` or other names.

Not applicable: the Hebrew axes and the document axes of the test-matrix skill: the input is
a requirements file.

Known limits:
  - The hashes are read, not checked against the files they name: that is what an install with
    `--require-hashes` does. The hashes under `experiments/` are PyPI's for the pinned versions,
    read from its metadata on 2026-11-20; no install with them has been run since.
  - Only files named `requirements*.txt` are read, and `-r` may name only such a file, so that
    every file an install reads is read here. `pyproject.toml` declares no dependency yet; when
    it does, this check is widened in the same PR.
  - A line broken inside a word is joined here with a space, so it is refused where pip would
    join it with nothing; a backslash followed by white space continues the line here, where pip
    stops on it. Both differences refuse, or leave pip to fail; neither lets a line through.
  - Refused though pip would take them, as none of this repository's files needs them: an
    option line other than `-r`, `--require-hashes` and `--only-binary :all:`.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# The file names the rule reads (the usual names; pip itself reads any file it is given).
NAME = re.compile(r"requirements[^/]*\.txt")
# git from PATH, as a full path, as in CI; the seconds a git command may take.
GIT = shutil.which("git") or "git"
GIT_TIMEOUT_SECONDS = 60


def _git(*args: str) -> bytes:
    """Return what one git command printed."""
    return subprocess.run(  # noqa: S603 fixed argv, no shell
        [GIT, *args], capture_output=True, check=True, timeout=GIT_TIMEOUT_SECONDS
    ).stdout


# A requirement pinned to one version: a name with optional extras, `==`, a version with no
# wildcard, and an optional environment marker (PEP 508); then the options pip reads after it.
PINNED = re.compile(
    r"(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[A-Za-z0-9,._ -]+\])?\s*==\s*(?P<version>[A-Za-z0-9._+!-]+)"
    r"(?:\s*;(?P<marker>.*?))?(?:\s+(?P<options>--.*))?"
)
# One hash option: sha256, 64 lower-case hex digits, as pip writes and reads it.
HASH_OPTION = re.compile(r"--hash=sha256:[0-9a-f]{64}")
INCLUDE = re.compile(r"-r\s+(?P<path>\S+)")
# The option lines that only make an install stricter: hashes required, wheels only.
STRICTER = re.compile(r"--require-hashes|--only-binary(?:=|\s+):all:")
# A comment, as pip cuts it: `#` at the start of a line or after white space (pip's COMMENT_RE).
COMMENT = re.compile(r"(^|\s+)#.*$")
# How much of a line a problem prints, so that a hash on it is never printed in full.
SHOWN = 30


def _logical(text: str) -> list[tuple[int, str]]:
    """Return the logical lines of a requirements file, each with the number of its first line.

    A line that ends in a backslash goes on with the next, as pip reads it; a comment, a blank
    line and the end of a line are dropped.
    """
    found: list[tuple[int, str]] = []
    start, parts = 0, []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = COMMENT.sub("", raw).strip()
        if not parts:
            start = number
        parts.append(line.removesuffix("\\").strip())
        if not line.endswith("\\"):
            found.append((start, " ".join(part for part in parts if part)))
            parts = []
    if parts:
        found.append((start, " ".join(part for part in parts if part)))
    return [(number, line) for number, line in found if line]


def _judge(line: str, folder: Path) -> str | None:
    """Say what is wrong with one logical line of a requirements file, or None."""
    if STRICTER.fullmatch(line):
        return None
    if include := INCLUDE.fullmatch(line):
        target = folder / include["path"]
        if not NAME.fullmatch(target.name):
            return f"{line[:SHOWN]}: not a requirements file the rule reads"
        return None if target.is_file() else f"{line[:SHOWN]}: no such file"
    pinned = PINNED.fullmatch(line)
    if pinned is None:
        return f"{line.split()[0][:SHOWN]}: not pinned to one version"
    if not any(HASH_OPTION.fullmatch(word) for word in line.split()):
        return f"{pinned['name']}: no sha256 hash"
    return None


def problems(text: str, folder: Path) -> list[str]:
    """Name each requirement of a requirements file that is not pinned and hashed, as "<line>: <what>".

    Why: the rule of this file, apart from where the text comes from.

    Contract: `folder` is the folder of the file, against which `-r` paths are read. A logical
    line is named at its first line. Each problem names the requirement or the line, never a
    hash in full.
    """
    return [f"{number}: {why}" for number, line in _logical(text) if (why := _judge(line, folder))]


def requirement_files(root: Path) -> list[Path]:
    """Return the tracked requirements files of a repository, in git's order.

    Why: the rule reads what would be pushed, every requirements file of every folder.

    Contract: the files git's index holds whose name matches NAME. Raises
    subprocess.CalledProcessError when `root` is no git repository.
    """
    listed = _git("-C", str(root), "ls-files", "-z").decode("utf-8").split("\0")
    return [root / name for name in listed if NAME.fullmatch(name.rsplit("/", 1)[-1])]


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
        f"pytest==9.2.0 --hash=sha1:{HASH}\n",
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
        "--require-hashes --index-url https://example.invalid/simple\n",
        "--only-binary :all: -f https://example.invalid\n",
        "--only-binary :none:\n",
        f"x==1 --hash=sha256:{HASH}#x\n",
    ],
)
def test_ec4_a_line_that_installs_from_elsewhere(text: str) -> None:
    assert _lines(text) == [1]


def test_ec5_an_include(tmp_path: Path) -> None:
    (tmp_path / "requirements-base.txt").write_text(f"x==1.0 --hash=sha256:{HASH}\n", encoding="utf-8")
    (tmp_path / "base.txt").write_text("requests\n", encoding="utf-8")
    assert problems("-r requirements-base.txt\n", tmp_path) == []
    assert problems("-r base.txt\n", tmp_path) == ["1: -r base.txt: not a requirements file the rule reads"]
    assert problems("-r pyproject.toml\n", ROOT) == ["1: -r pyproject.toml: not a requirements file the rule reads"]
    assert problems("-e requirements-base.txt\n", tmp_path) == ["1: -e: not pinned to one version"]
    assert problems("-r requirements-base.txt more\n", tmp_path) == ["1: -r: not pinned to one version"]
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
    names = (
        "requirements.txt",
        "requirements-dev.txt",
        "x/requirements.txt",
        "constraints.txt",
        "requirements.in",
        "requirements.txt.orig",
        "notes.txt",
    )
    for name in names:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("\n", encoding="utf-8")
    _git("-C", str(tmp_path), "add", *names)
    found = [path.relative_to(tmp_path).as_posix() for path in requirement_files(tmp_path)]
    assert found == ["requirements-dev.txt", "requirements.txt", "x/requirements.txt"]


def test_ec8_a_continued_line_at_the_end_of_the_file() -> None:
    assert _lines("pytest \\\n") == [1]
    assert _lines("pytest \\") == [1]


def test_ec9_a_comment_after_a_tab_holds_no_hash() -> None:
    assert _lines(f"pytest==9.2.0 --config-settings=a=b\t# --hash=sha256:{HASH}\n") == [1]


def test_ec10_an_inline_comment_after_a_hashed_requirement() -> None:
    assert problems(f"pytest==9.2.0 --hash=sha256:{HASH}  # the test runner\n", ROOT) == []


@pytest.mark.parametrize(
    "text",
    [
        f'x==1;sys_platform=="win32" --hash=sha256:{HASH}\n',
        f"pydantic[email]==2.14.3 --hash=sha256:{HASH}\n",
        f"pytest == 9.2.0 --hash=sha256:{HASH}\n",
        "--require-hashes\n",
        "--only-binary :all:\n",
        "--only-binary=:all:\n",
    ],
)
def test_ec11_markers_extras_spaces_and_the_stricter_options(text: str) -> None:
    assert problems(text, ROOT) == []


def test_a3_a_hash_inside_a_marker_string() -> None:
    assert _lines(f'x==1 ; extra=="--hash=sha256:{HASH}"\n') == [1]


def test_a4_a_continued_requirement_with_its_hash_on_a_comment_line() -> None:
    assert _lines(f"pytest==9.2.0 \\\n# --hash=sha256:{HASH}\n") == [1]


def test_logical_lines_each_at_its_first_line() -> None:
    text = f"# head\n\npytest \\\n    ==9.2.0 \\\n    --hash=sha256:{HASH}\nruff==0.17.5  # why\n"
    assert _logical(text) == [(3, f"pytest ==9.2.0 --hash=sha256:{HASH}"), (6, "ruff==0.17.5")]
    assert problems("x = \\\n  y\n", ROOT) == ["1: x: not pinned to one version"]


def test_a_problem_never_prints_a_hash_in_full() -> None:
    [found] = problems(f"--hash=sha256:{HASH}\n", ROOT)
    assert HASH not in found
