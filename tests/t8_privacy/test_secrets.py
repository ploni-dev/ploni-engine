"""No secret is committed: every tracked file is searched for the shapes of keys and tokens.

Why: `PROCESS.md` section 2: "No secrets. There are none in v1 by design, and a pre-commit scan
keeps it that way"; section 5.1 puts a secret scan in the fast suite, and `PROMOTION.md` section
5.1 lists "No secrets committed: the secret scan" among the Class A checks (issue #78). A key in
the repository is a key on GitHub and in every clone, and taking it out of the history is far
harder than keeping it out.

The rule: no tracked file holds a match of PATTERNS: a cloud or service key by its own prefix
(AWS, GitHub, Slack, Google, an `sk-` key, Hugging Face), a private key block, or a quoted value
of twelve or more characters given to a name that says key, secret, password or token.

Test matrix:

Equivalence classes:
  EC1  each kind of PATTERNS, 5 fake values each, made at run time    found, with its kind and line
  EC2  text with no secret: code, prose, Hebrew, hashes of git commits and models   no line
  EC3  the files the scan reads: every tracked file, binary ones decoded leniently
  EC4  the repository                                                  no line

Boundaries:
  B1  one character short of each prefix pattern's length              not found
  B2  the generic rule: an 11-character value, a value read from the environment, an empty
      value                                                            not found
  B3  a key at the start and the end of a file, and on the last line with no line break   found

Adversarial:
  A1  a key inside a longer word or a URL                              found
  A2  a key in a binary file (bytes around it that are not UTF-8)      found
  A3  a GitHub key of the fine-grained form (`github_pat_`)           found
  A4  two keys of one kind in a text, and keys of two kinds out of the order of PATTERNS
                                                                       each found, by line

Sample size (CLAUDE.md, Tests: detectors 40 positive and 40 negative): EC1 and A1 give 45
positive cases, EC2, B1 and B2 give 43 negative ones.

Not applicable: the Hebrew axes of the test-matrix skill but one (EC2 holds Hebrew text, so that
the scan is shown not to break on it), and the document axes: no document is handled.

Known limits:
  - Shapes only. A secret with no known prefix, given to a name that does not say what it is,
    or split, encoded or encrypted, is not found.
  - Tracked files only: what git lists (the index, so a file added for the next commit is read).
    An ignored file, and the history of the repository, are not read.
  - The fake values of this file are made at run time, so that the file itself holds none.
"""

import hashlib
import re
import shutil
import string
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# The shapes of the keys of the services a developer of this project is likely to hold, each by
# the prefix and length its provider documents, and the header of a private key file.
PATTERNS = {
    "aws": r"AKIA[0-9A-Z]{16}",
    "github": r"gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,}",
    "private key": r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----",
    "slack": r"xox[baprs]-[A-Za-z0-9-]{10,}",
    "google": r"AIza[0-9A-Za-z_-]{35}",
    "sk": r"\bsk-[A-Za-z0-9_-]{20,}",
    "hugging face": r"\bhf_[A-Za-z0-9]{30,}",
    "assigned": r"(?i)(?:api[_-]?key|secret|passw(?:or)?d|token)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]",
}


COMPILED = {kind: re.compile(pattern) for kind, pattern in PATTERNS.items()}
# git from PATH, as a full path, as in CI; the seconds a git command may take.
GIT = shutil.which("git") or "git"
GIT_TIMEOUT_SECONDS = 60


def _git(*args: str) -> bytes:
    """Run one git command and return what it printed."""
    return subprocess.run(  # noqa: S603 fixed argv, no shell
        [GIT, *args], capture_output=True, check=True, timeout=GIT_TIMEOUT_SECONDS
    ).stdout


def secrets_in(text: str) -> list[str]:
    """Name each match of PATTERNS in a text, as "<line>: <kind>", in order.

    Why: the rule of this file, apart from where the text comes from.

    Contract: a line is counted from 1; a match that spans lines (none of PATTERNS does) is
    named at its first line. Each match is named once, with its kind, and no part of the
    value, so that a failing test does not print the secret.
    """
    found = [
        (text.count("\n", 0, match.start()) + 1, kind)
        for kind, pattern in COMPILED.items()
        for match in pattern.finditer(text)
    ]
    return [f"{line}: {kind}" for line, kind in sorted(found)]


def tracked(root: Path) -> list[Path]:
    """Return the files git lists for a repository, in order.

    Why: the scan reads what would be pushed, not what lies ignored in the folder.

    Contract: the paths git's index holds, as paths under `root`, in git's order (sorted by
    path). Raises subprocess.CalledProcessError when `root` is no git repository.
    """
    listed = _git("-C", str(root), "ls-files", "-z").decode("utf-8").split("\0")
    return [root / name for name in listed if name]


def _fake(prefix: str, alphabet: str, length: int, seed: int) -> str:
    """Return a value of a key's shape, made from a seed, so that this file holds none."""
    drawn = hashlib.shake_256(f"{prefix}{alphabet}{seed}".encode()).digest(length)
    return prefix + "".join(alphabet[byte % len(alphabet)] for byte in drawn)


UPPER = string.ascii_uppercase + string.digits
MIXED = string.ascii_letters + string.digits
# One maker per kind of PATTERNS: given a seed, a value of that kind.
MAKERS: dict[str, Callable[[int], str]] = {
    "aws": lambda seed: _fake("AK" + "IA", UPPER, 16, seed),
    "github": lambda seed: _fake("gh" + "p_", MIXED, 36, seed),
    "private key": lambda seed: "-----BEGIN " + ("RSA ", "EC ", "OPENSSH ", "", "DSA ")[seed % 5] + "PRIVATE" + " KEY-----",
    "slack": lambda seed: _fake("xo" + "xb-", MIXED + "-", 24, seed),
    "google": lambda seed: _fake("AI" + "za", MIXED + "_-", 35, seed),
    "sk": lambda seed: _fake("s" + "k-ant-", MIXED + "_-", 40, seed),
    "hugging face": lambda seed: _fake("h" + "f_", MIXED, 34, seed),
    "assigned": lambda seed: "api_key = '" + _fake("", MIXED, 20, seed) + "'",
}


@pytest.mark.parametrize("kind", sorted(MAKERS))
@pytest.mark.parametrize("seed", range(5))
def test_ec1_each_kind_is_found(kind: str, seed: int) -> None:
    assert secrets_in(f"x = 1\nvalue = {MAKERS[kind](seed)}\n") == [f"2: {kind}"]


@pytest.mark.parametrize(
    "text",
    [
        "def doubled(number: int) -> int:\n    return number * 2\n",
        "The secret of a good test is that it can fail.\n",
        "שלום עולם, יעקב כהן גר בתל אביב\n",
        "revision = '0123456789abcdef0123456789abcdef01234567'\n",
        "sha256 = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'\n",
        "token_count = 512\n",
        "password = input()\n",
        "Ask for a key, never print it.\n",
    ],
)
def test_ec2_text_with_no_secret(text: str) -> None:
    assert secrets_in(text) == []


def test_ec3_the_files_the_scan_reads(tmp_path: Path) -> None:
    _git("init", "-q", str(tmp_path))
    for name in ("a.py", "docs/b.md", "ignored.txt", "untracked.py"):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("x\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    _git("-C", str(tmp_path), "add", "a.py", "docs/b.md", ".gitignore")
    assert [path.relative_to(tmp_path).as_posix() for path in tracked(tmp_path)] == [".gitignore", "a.py", "docs/b.md"]


def test_ec4_the_repository() -> None:
    files = tracked(ROOT)
    assert len(files) > 100
    found = [
        f"{path.relative_to(ROOT).as_posix()}:{line}"
        for path in files
        if path.is_file()
        for line in secrets_in(path.read_bytes().decode("utf-8", "replace"))
    ]
    assert found == []


# One maker per prefix kind of PATTERNS: given a seed, a value one character short of that kind.
SHORT: dict[str, Callable[[int], str]] = {
    "aws": lambda seed: _fake("AK" + "IA", UPPER, 15, seed),
    "github": lambda seed: _fake("gh" + "p_", MIXED, 35, seed),
    "slack": lambda seed: _fake("xo" + "xb-", MIXED, 9, seed),
    "google": lambda seed: _fake("AI" + "za", MIXED, 34, seed),
    "sk": lambda seed: _fake("s" + "k-", MIXED, 19, seed),
    "hugging face": lambda seed: _fake("h" + "f_", MIXED, 29, seed),
}


@pytest.mark.parametrize("kind", sorted(SHORT))
@pytest.mark.parametrize("seed", range(5))
def test_b1_one_short_of_the_shape(kind: str, seed: int) -> None:
    assert secrets_in(SHORT[kind](seed) + "\n") == []


def test_b1_a_public_key_block() -> None:
    assert secrets_in("-----BEGIN PUBLIC" + " KEY-----\n") == []


@pytest.mark.parametrize(
    "text",
    [
        "api_key = '" + _fake("", MIXED, 11, 2) + "'\n",
        "token = os.environ['PLONI_TOKEN']\n",
        "secret = ''\n",
        "password = None\n",
    ],
)
def test_b2_the_generic_rule_does_not_reach(text: str) -> None:
    assert secrets_in(text) == []


@pytest.mark.parametrize(
    ("text", "found"),
    [
        (MAKERS["aws"](3) + "\nx = 1\n", ["1: aws"]),
        ("x = 1\n" + MAKERS["aws"](3), ["2: aws"]),
        ("x = 1\n\n" + MAKERS["github"](3) + "\n", ["3: github"]),
    ],
)
def test_b3_the_first_and_the_last_line(text: str, found: list[str]) -> None:
    assert secrets_in(text) == found


@pytest.mark.parametrize("kind", ["aws", "github", "google", "hugging face", "slack"])
def test_a1_inside_a_word_or_a_url(kind: str) -> None:
    assert secrets_in(f"see https://example.invalid/?k={MAKERS[kind](9)}&x=1\n") == [f"1: {kind}"]


def test_a2_in_a_binary_file(tmp_path: Path) -> None:
    data = b"\x89PNG\r\n\x1a\n\xff\xfe" + MAKERS["aws"](4).encode() + b"\x00\x81"
    assert secrets_in(data.decode("utf-8", "replace")) == ["3: aws"]


def test_the_patterns_find_each_other_kind_not() -> None:
    for kind, make in MAKERS.items():
        found = {line.split(": ", 1)[1] for line in secrets_in(make(0) + "\n")}
        assert found == {kind}


def test_a3_a_fine_grained_github_key() -> None:
    assert secrets_in(_fake("github" + "_pat_", MIXED + "_", 40, 5) + "\n") == ["1: github"]


def test_a4_two_keys_of_one_kind_and_keys_out_of_order() -> None:
    assert secrets_in(MAKERS["aws"](6) + "\n" + MAKERS["aws"](7) + "\n") == ["1: aws", "2: aws"]
    assert secrets_in(MAKERS["hugging face"](6) + "\n" + MAKERS["aws"](6) + "\n") == ["1: hugging face", "2: aws"]
