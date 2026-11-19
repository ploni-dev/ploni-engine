"""Tests of scripts/check_changed_paths.py: a PR that changes code changes no baselines and no CI workflow.

Why: `PROMOTION.md` section 5.1, the rows "Baselines not changed in a code PR" and "CI
workflows not edited by a code PR"; `CLAUDE.md`, "Code changes and baseline or gate changes
never share a PR"; bad PR 7 of the closing test of Phase 0 (`PROMOTION.md` section 10, issue
#30). Issue #78. What counts as code is Achia's answer of 2026-11-19, "New workflow file
(Recommended)", whose text said: "'Code' means any .py file anywhere in the repo."

Test matrix:

Equivalence classes (problems):
  EC1  code only                                    no line
  EC2  eval/baselines.json only                     no line
  EC3  a CI workflow only                           no line
  EC4  code and eval/baselines.json                 one line, naming the baselines
  EC5  code and two CI workflows                    one line per workflow
  EC6  code, the baselines and a workflow           a line each, sorted by path
  EC7  the baselines and a workflow, no code        no line: not this rule
  EC8  documents only (.md)                         no line

Equivalence classes (is_code):
  EC9  a .py file at the root, in ploni/, tests/, scripts/, experiments/ and eval/    code
  EC10 Markdown, JSON, YAML, TOML, a Makefile, a requirements file    not code

Boundaries:
  B1  no changed path                               no line
  B2  `eval/baselines.json.bak`, `x/eval/baselines.json`, `eval/baselines.jsonl`,
      `eval/Baselines.json`                         not the baselines
  B3  `.github/workflows.yml`, `.github/actions/a/action.yml`, `github/workflows/x.yml`,
      `docs/.github/workflows/x.yml` (GitHub reads workflows at the root only)
                                                    not a CI workflow
  B4  `.github/workflows/sub/x.yml`, a workflow with a `.yaml` end, and a file there that
      is not YAML                                   a CI workflow: everything in that folder
  B5  `x.py.txt`, `py`, `x.pyc`                     not code
  B6  a file named `.py`                            code
  B7  the same path given twice                     one line, not two

Error paths (main):
  E1  no argument, one argument, three              exit 2, a usage line on the error stream
  E2  a revision git does not know                  CalledProcessError (the module suite)

Adversarial:
  A1  `x.PY` and `x.Py`                             code: on Windows Python imports `x.PY`
                                                    as the module `x`
  A2  a Hebrew path, `ploni/שם.py`, with a workflow  code, one line
  A3  a path with a space and one with a line break  read whole (the module suite)
  A4  a .py file renamed to .txt, with a workflow   code: the old name counts (the module suite)
  A5  a deleted .py file, with the baselines        code (the module suite)

Not applicable: the document axes; the Hebrew axes of the test-matrix skill other than A2,
as the input is a list of paths judged by their ends and folders only.

Known limits:
  - `.github/actions/` (composite actions a workflow may call) is not watched; none exists.
  - A gate value outside `eval/baselines.json` is not watched: today the limits in
    `pyproject.toml` (`max-complexity`, `max-statements`), later a `config.py` of Phase 3.
"""

import pytest

from scripts import check_changed_paths as check

BASELINES = "eval/baselines.json"
FAST = ".github/workflows/fast.yml"
BODY = ".github/workflows/pr-body.yml"


def test_ec1_code_only() -> None:
    assert check.problems(["ploni/types.py", "tests/t1_unit/test_x.py"]) == []


def test_ec2_baselines_only() -> None:
    assert check.problems([BASELINES]) == []


def test_ec3_a_workflow_only() -> None:
    assert check.problems([FAST]) == []


def test_ec4_code_and_the_baselines() -> None:
    assert check.problems(["ploni/types.py", BASELINES]) == [f"baselines changed in a code PR: {BASELINES}"]


def test_ec5_code_and_two_workflows() -> None:
    assert check.problems([FAST, "scripts/check.py", BODY]) == [
        f"CI workflow changed in a code PR: {FAST}",
        f"CI workflow changed in a code PR: {BODY}",
    ]


def test_ec6_code_the_baselines_and_a_workflow() -> None:
    assert check.problems([FAST, BASELINES, "ploni/x.py"]) == [
        f"CI workflow changed in a code PR: {FAST}",
        f"baselines changed in a code PR: {BASELINES}",
    ]


def test_ec7_the_baselines_and_a_workflow_without_code() -> None:
    assert check.problems([BASELINES, FAST]) == []


def test_ec8_documents_only() -> None:
    assert check.problems(["docs/STATUS.md", "README.md"]) == []


@pytest.mark.parametrize(
    "path",
    ["x.py", "ploni/types.py", "tests/t1_unit/test_x.py", "scripts/check.py", "experiments/e6/run.py", "eval/score.py"],
)
def test_ec9_python_files_are_code(path: str) -> None:
    assert check.is_code(path)


@pytest.mark.parametrize(
    "path",
    ["docs/STATUS.md", BASELINES, FAST, "pyproject.toml", "Makefile", "requirements-dev.txt"],
)
def test_ec10_other_files_are_not_code(path: str) -> None:
    assert not check.is_code(path)


def test_b1_no_changed_path() -> None:
    assert check.problems([]) == []


@pytest.mark.parametrize(
    "path", ["eval/baselines.json.bak", "x/eval/baselines.json", "eval/baselines.jsonl", "eval/Baselines.json"]
)
def test_b2_near_the_baselines_is_not_the_baselines(path: str) -> None:
    assert check.problems(["ploni/x.py", path]) == []


@pytest.mark.parametrize(
    "path", [".github/workflows.yml", ".github/actions/a/action.yml", "github/workflows/x.yml", "docs/.github/workflows/x.yml"]
)
def test_b3_near_the_workflows_is_not_a_workflow(path: str) -> None:
    assert check.problems(["ploni/x.py", path]) == []


@pytest.mark.parametrize("path", [".github/workflows/sub/x.yml", ".github/workflows/x.yaml", ".github/workflows/README.md"])
def test_b4_everything_in_the_workflows_folder(path: str) -> None:
    assert check.problems(["ploni/x.py", path]) == [f"CI workflow changed in a code PR: {path}"]


@pytest.mark.parametrize("path", ["x.py.txt", "py", "x.pyc"])
def test_b5_near_a_python_end_is_not_code(path: str) -> None:
    assert not check.is_code(path)


def test_b6_a_file_named_dot_py_is_code() -> None:
    assert check.is_code(".py")


def test_b7_a_path_given_twice_is_named_once() -> None:
    assert check.problems(["ploni/x.py", BASELINES, BASELINES]) == [f"baselines changed in a code PR: {BASELINES}"]


@pytest.mark.parametrize("argv", [[], ["HEAD^1"], ["a", "b", "c"]])
def test_e1_main_needs_two_revisions(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main(argv) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("usage: ")


@pytest.mark.parametrize("path", ["x.PY", "ploni/x.Py"])
def test_a1_an_upper_case_end_is_code(path: str) -> None:
    assert check.is_code(path)


def test_a2_a_hebrew_path() -> None:
    assert check.problems(["ploni/שם.py", FAST]) == [f"CI workflow changed in a code PR: {FAST}"]
# scratch: a .py change for the red case of #119
