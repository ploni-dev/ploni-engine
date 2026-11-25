"""Tests of tests/workflow_lines.py: the reader of a workflow's code lines that the pin tests compare.

Each case edits a copy of a real workflow in tmp_path and reads it again: an edit that changes
what GitHub runs must give other lines than the file as merged, or refuse to read; a comment or
a blank line must give the same lines.

Equivalence classes:
  W1 a comment line, a blank line of spaces, a trailing comment, the whole file in CRLF: the
     same lines as the merged file
  W2 a code line changed or added (a top-level `env:` in front of the file's first line, a
     checkout of another ref, a job BASH_ENV, a step added in front of the changed-paths step,
     written `- run :`, a push trigger, PR_BODY moved from the waiver step to the job): other
     lines
  W3 a character outside ASCII anywhere, in a code line or a comment: ValueError
  W4 a control character other than tab and the line ends (each of 0x00 to 0x1f but tab, line
     feed and carriage return, and DEL), in a comment or in a code line: ValueError; a tab
     inside a comment and CRLF line ends are none (issue #239: a NUL in a comment leaves the
     code lines as they are, and by the runner's YAML library the file is then no workflow at
     all)
  W5 the file is a symbolic link to a workflow: ValueError (issue #239: the reader would follow
     the link and read another file than the one GitHub runs)
Boundaries:
  B1 a tab before a trailing comment: other lines (YAML reads it as a comment; the reader
     keeps the tab, so a pin fails closed)
  B2 the file's first line: a code line put in front of it shows (W2), a Hebrew comment put
     in front of it is refused (W3). pr-checks.yml opens with comment lines, so a reader that
     skips the top of a file would otherwise pass
  B3 the file's last line: a trailing comment on it is cut (W1), a tab before a comment on it
     shows (B1), U+0085 and U+00A0 on it are refused (A2, A3)
  B4 the kind of line. On changed-paths.yml, which these cases edited until the cut of #209,
     one line was the last line, a step line and a run line at once; pr-checks.yml has no
     such line. So the trailing comment stands on every line of the last step (W1); A2 and
     A3 move the last step's run line to the end of the file and stand on it, and A2 stands
     on a step line too; the tab before a comment stands on the last line, on a run line and
     on a step line (B1)
Adversarial (the reviews of #164, pass 2, and #166, pass 1): characters that end a line or a
comment for GitHub's parser and not for Python's split, or count as whitespace for Python only:
  A1 U+2028 inside a comment, then `if: false`
  A2 U+0085 inside a trailing comment of the run line that ends the file (B4), and of a step
     line, then `continue-on-error: true`
  A3 U+00A0 before `#|| true` at the end of the run line that ends the file (B4)
Hebrew and document axes: do not apply; the input is a workflow file. A Hebrew word in a comment
is outside ASCII, so it is refused (W3).
"""

from pathlib import Path

import pytest

from tests.workflow_lines import code_lines

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
# Pieces of pr-checks.yml. `edited` asserts that each text it replaces is in the file exactly
# once; STEP_IF and WAIVER_ENV are replaced only inside a longer text (with RUN, with
# WAIVER_RUN), and JOB_ENV is text a case adds.
# Until the cut of #209 the cases edited copies of two of the six small check workflows, which
# leave with it.
STEP_IF = "      - if: ${{ !cancelled() }}\n"
RUN = "        run: python scripts/check_changed_paths.py HEAD^1 HEAD\n"
FETCH_DEPTH = "          fetch-depth: 0\n"
TIMEOUT = "    timeout-minutes: 5\n"
WAIVER_RUN = "        run: python -m scripts.check_waiver HEAD^1 HEAD\n"
WAIVER_ENV = "        env:\n          PR_BODY: ${{ github.event.pull_request.body }}\n"
JOB_ENV = "    env:\n      PR_BODY: ${{ github.event.pull_request.body }}\n"
# The waiver step ends the file; its last line is the file's last line.
LAST_STEP = STEP_IF + WAIVER_RUN + WAIVER_ENV
# Read from the file, so that a reworded first comment of the workflow does not break a case
# (unless its whole text also ends another line). Read at import: without pr-checks.yml this
# file is not collected, which is red too.
FIRST = (WORKFLOWS / "pr-checks.yml").read_text(encoding="utf-8").split("\n", 1)[0] + "\n"
# Every control character the reader refuses: both ends of the range and all between.
CONTROLS = [chr(code) for code in range(0x20) if code not in (0x09, 0x0A, 0x0D)] + ["\x7f"]


def edited(tmp_path: Path, workflow: str, *pairs: tuple[str, str], crlf: bool = False) -> tuple[list[str], Path]:
    text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    # Not the workflow's own name: a reader that keeps a rule for one file name only must fail.
    path = tmp_path / "copy.yml"
    path.write_bytes((text.replace("\n", "\r\n") if crlf else text).encode("utf-8"))
    return code_lines(WORKFLOWS / workflow), path


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("name: pr-checks\n", "# a comment line\nname: pr-checks\n"),
        (TIMEOUT, TIMEOUT + "      \n"),
        (LAST_STEP, "".join(line + "  # a trailing comment\n" for line in LAST_STEP.splitlines())),
        (TIMEOUT, TIMEOUT),
    ],
    ids=["comment-line", "blank-line-of-spaces", "trailing-comment", "unchanged"],
)
def test_w1_the_same_lines(tmp_path: Path, old: str, new: str) -> None:
    merged, path = edited(tmp_path, "pr-checks.yml", (old, new))
    assert code_lines(path) == merged


def test_w1_crlf(tmp_path: Path) -> None:
    merged, path = edited(tmp_path, "pr-checks.yml", (TIMEOUT, TIMEOUT), crlf=True)
    assert code_lines(path) == merged


@pytest.mark.parametrize(
    "pairs",
    [
        [(FIRST, "env: {BASH_ENV: /tmp/off}\n" + FIRST)],
        [(FETCH_DEPTH, FETCH_DEPTH + "          ref: other\n")],
        [(TIMEOUT, TIMEOUT + "    env:\n      BASH_ENV: /tmp/off\n")],
        [(STEP_IF + RUN, "      - run : sed -i s/1/0/ scripts/check_changed_paths.py\n" + STEP_IF + RUN)],
        [("  pull_request:\n", "  push:\n  pull_request:\n")],
        [(WAIVER_RUN + WAIVER_ENV, WAIVER_RUN), (TIMEOUT, TIMEOUT + JOB_ENV)],
        # The file's last line: a reader that drops the end of the file must fail here.
        [(WAIVER_RUN + WAIVER_ENV, (WAIVER_RUN + WAIVER_ENV).rstrip("\n") + "\t# a comment after a tab\n")],
        [(RUN, RUN.rstrip("\n") + "\t# a comment after a tab\n")],
        [(STEP_IF + RUN, STEP_IF.rstrip("\n") + "\t# a comment after a tab\n" + RUN)],
    ],
    ids=["first-line", "checkout-ref", "bash-env", "second-run-step", "push-trigger", "pr-body-off-the-run-step", "b1-tab", "b1-tab-on-a-run-line", "b1-tab-on-a-step-line"],
)
def test_w2_other_lines(tmp_path: Path, pairs: list[tuple[str, str]]) -> None:
    merged, path = edited(tmp_path, "pr-checks.yml", *pairs)
    assert code_lines(path) != merged


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (TIMEOUT, TIMEOUT + "    # note     if: false\n"),
        (LAST_STEP, STEP_IF + WAIVER_ENV + WAIVER_RUN.rstrip("\n") + " # x\u0085        continue-on-error: true\n"),
        (LAST_STEP, STEP_IF + WAIVER_ENV + WAIVER_RUN.rstrip("\n") + " #|| true\n"),
        (STEP_IF + RUN, STEP_IF.rstrip("\n") + " # x\u0085        continue-on-error: true\n" + RUN),
        (FIRST, "# יעקב\n" + FIRST),
    ],
    ids=["a1-line-separator", "a2-next-line", "a3-no-break-space", "a2-on-a-step-line", "w3-hebrew-in-a-comment"],
)
def test_w3_outside_ascii(tmp_path: Path, old: str, new: str) -> None:
    _, path = edited(tmp_path, "pr-checks.yml", (old, new))
    with pytest.raises(ValueError, match="outside ASCII"):
        code_lines(path)


@pytest.mark.parametrize("where", ["comment", "code"])
@pytest.mark.parametrize("character", CONTROLS, ids=[f"0x{ord(character):02x}" for character in CONTROLS])
def test_w4_a_control_character(tmp_path: Path, character: str, where: str) -> None:
    new = TIMEOUT + f"    # note{character}\n" if where == "comment" else TIMEOUT.rstrip("\n") + f"{character}\n"
    _, path = edited(tmp_path, "pr-checks.yml", (TIMEOUT, new))
    with pytest.raises(ValueError, match="a control character"):
        code_lines(path)


def test_w4_a_tab_in_a_comment_and_crlf_are_none(tmp_path: Path) -> None:
    merged, path = edited(tmp_path, "pr-checks.yml", (TIMEOUT, TIMEOUT + "    #\tnote\n"), crlf=True)
    assert code_lines(path) == merged


def test_w5_a_symbolic_link(tmp_path: Path) -> None:
    merged, path = edited(tmp_path, "pr-checks.yml")
    assert code_lines(path) == merged
    link = tmp_path / "link.yml"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="a symbolic link"):
        code_lines(link)
