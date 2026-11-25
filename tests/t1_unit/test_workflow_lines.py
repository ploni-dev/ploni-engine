"""Tests of tests/workflow_lines.py: the reader of a workflow's code lines that the pin tests compare.

Each case edits a copy of a real workflow in tmp_path and reads it again: an edit that changes
what GitHub runs must give other lines than the file as merged, or refuse to read; a comment or
a blank line must give the same lines.

Equivalence classes:
  W1 a comment line, a blank line of spaces, a trailing comment, the whole file in CRLF: the
     same lines as the merged file
  W2 a code line changed or added (a checkout of another ref, a job BASH_ENV, a second step
     written `- run :`, a push trigger, PR_BODY moved from the run step to the job): other lines
  W3 a character outside ASCII anywhere, in a code line or a comment: ValueError
  W4 a control character other than tab and the line ends (NUL, SOH, vertical tab, form feed,
     escape, DEL), in a comment or in a code line: ValueError; a tab inside a comment and CRLF
     line ends are none (issue #239: a NUL in a comment leaves the code lines as they are, and
     by the runner's YAML library the file is then no workflow at all)
  W5 the file is a symbolic link to a workflow: ValueError (issue #239: the reader would follow
     the link and read another file than the one GitHub runs)
Boundaries:
  B1 a tab before a trailing comment: other lines (YAML reads it as a comment; the reader
     keeps the tab, so a pin fails closed)
Adversarial (the reviews of #164, pass 2, and #166, pass 1): characters that end a line or a
comment for GitHub's parser and not for Python's split, or count as whitespace for Python only:
  A1 U+2028 inside a comment, then `if: false`
  A2 U+0085 inside a trailing comment of the run line, then `continue-on-error: true`
  A3 U+00A0 before `#|| true` at the end of the run line
Hebrew and document axes: do not apply; the input is a workflow file. A Hebrew word in a comment
is outside ASCII, so it is refused (W3).
"""

from pathlib import Path

import pytest

from tests.workflow_lines import code_lines

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
RUN = "      - run: python scripts/check_changed_paths.py HEAD^1 HEAD\n"
CHECKOUT = "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1\n"
TIMEOUT = "    timeout-minutes: 2\n"
WAIVER_RUN = "      - run: python -m scripts.check_waiver HEAD^1 HEAD\n"
WAIVER_ENV = (
    "        env:\n"
    "          # The body reaches the script only through the environment, never inside a shell command.\n"
    "          PR_BODY: ${{ github.event.pull_request.body }}\n"
)
JOB_ENV = "    env:\n      PR_BODY: ${{ github.event.pull_request.body }}\n"
# pr-checks.yml, for the classes added with issue #239: the six small workflows are on their way out.
JOB_TIMEOUT = "    timeout-minutes: 5\n"


def edited(tmp_path: Path, workflow: str, *pairs: tuple[str, str], crlf: bool = False) -> tuple[list[str], Path]:
    text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    path = tmp_path / workflow
    path.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    return code_lines(WORKFLOWS / workflow), path


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("name: changed-paths\n", "# a comment line\nname: changed-paths\n"),
        (TIMEOUT, TIMEOUT + "      \n"),
        (RUN, RUN.rstrip("\n") + "  # a trailing comment\n"),
        (TIMEOUT, TIMEOUT),
    ],
    ids=["comment-line", "blank-line-of-spaces", "trailing-comment", "unchanged"],
)
def test_w1_the_same_lines(tmp_path: Path, old: str, new: str) -> None:
    merged, path = edited(tmp_path, "changed-paths.yml", (old, new))
    assert code_lines(path) == merged


def test_w1_crlf(tmp_path: Path) -> None:
    merged, path = edited(tmp_path, "changed-paths.yml", (TIMEOUT, TIMEOUT), crlf=True)
    assert code_lines(path) == merged


@pytest.mark.parametrize(
    ("workflow", "pairs"),
    [
        ("changed-paths.yml", [(CHECKOUT, CHECKOUT + "        with:\n          ref: main\n")]),
        ("changed-paths.yml", [(TIMEOUT, TIMEOUT + "    env:\n      BASH_ENV: /tmp/off\n")]),
        ("changed-paths.yml", [(RUN, "      - run : sed -i s/1/0/ scripts/check_changed_paths.py\n" + RUN)]),
        ("changed-paths.yml", [("  pull_request:\n", "  push:\n  pull_request:\n")]),
        ("waiver.yml", [(WAIVER_RUN + WAIVER_ENV, WAIVER_RUN), (TIMEOUT, TIMEOUT + JOB_ENV)]),
        ("changed-paths.yml", [(RUN, RUN.rstrip("\n") + "\t# a comment after a tab\n")]),
    ],
    ids=["checkout-ref", "bash-env", "second-run-step", "push-trigger", "pr-body-off-the-run-step", "b1-tab"],
)
def test_w2_other_lines(tmp_path: Path, workflow: str, pairs: list[tuple[str, str]]) -> None:
    merged, path = edited(tmp_path, workflow, *pairs)
    assert code_lines(path) != merged


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (TIMEOUT, TIMEOUT + "    # note     if: false\n"),
        (RUN, RUN.rstrip("\n") + " # x\u0085        continue-on-error: true\n"),
        (RUN, RUN.rstrip("\n") + " #|| true\n"),
        ("name: changed-paths\n", "# יעקב\nname: changed-paths\n"),
    ],
    ids=["a1-line-separator", "a2-next-line", "a3-no-break-space", "w3-hebrew-in-a-comment"],
)
def test_w3_outside_ascii(tmp_path: Path, old: str, new: str) -> None:
    _, path = edited(tmp_path, "changed-paths.yml", (old, new))
    with pytest.raises(ValueError, match="outside ASCII"):
        code_lines(path)


@pytest.mark.parametrize("where", ["comment", "code"])
@pytest.mark.parametrize("character", ["\x00", "\x01", "\x0b", "\x0c", "\x1b", "\x7f"], ids=["nul", "soh", "vertical-tab", "form-feed", "escape", "del"])
def test_w4_a_control_character(tmp_path: Path, character: str, where: str) -> None:
    new = JOB_TIMEOUT + f"    # note{character}\n" if where == "comment" else JOB_TIMEOUT.rstrip("\n") + f"{character}\n"
    _, path = edited(tmp_path, "pr-checks.yml", (JOB_TIMEOUT, new))
    with pytest.raises(ValueError, match="a control character"):
        code_lines(path)


def test_w4_a_tab_in_a_comment_and_crlf_are_none(tmp_path: Path) -> None:
    merged, path = edited(tmp_path, "pr-checks.yml", (JOB_TIMEOUT, JOB_TIMEOUT + "    #\tnote\n"), crlf=True)
    assert code_lines(path) == merged


def test_w5_a_symbolic_link(tmp_path: Path) -> None:
    merged, path = edited(tmp_path, "pr-checks.yml")
    assert code_lines(path) == merged
    link = tmp_path / "link.yml"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="a symbolic link"):
        code_lines(link)
