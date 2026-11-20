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
