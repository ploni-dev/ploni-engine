"""Tests of scripts/check_commit_order.py: the failing tests of a module come before it, in a commit of their own.

Why: `PROMOTION.md` section 5.2, the row "Test written before implementation": "the first
commit touching `tests/.../test_X.py` must precede the first commit touching the module `X`
implements ... The failing tests are a commit of their own, with no implementation in it. This
covers every PR that changes code under `ploni/`, `eval/` or `scripts/`." Issue #175, one of the
four robots Achia chose on 2026-11-20 ("Yes, all four (Recommended)").

Test matrix:

Equivalence classes (problems):
  EC1  a test file for X in one commit, X in a later one              no line
  EC2  X first, its test file in a later commit                       one line: no test before
  EC3  X and its test file in one commit, nothing before              one line: no test before
                                                                      (that commit is X's first,
                                                                      not a test commit before it)
  EC4  a test commit first, then a commit touching X and its test again    no line: a later commit
                                                                      may change both (the review
                                                                      of #194, finding 1)
  EC5  X in two commits, its test file between them                   one line: the first counts
  EC6  a test file for another module only                            one line
  EC7  no module touched (docs, tests, a workflow, experiments/)      no line
  EC8  two modules, both refused; six, given in reverse order        lines sorted by module
  EC9  a module of each folder: ploni/, eval/, scripts/               each needs its test
  EC10 X deleted, no test anywhere                                    no line
  EC11 X deleted together with its test file in one commit            no line: a deleted module
                                                                      needs no test
  EC12 X deleted, then added again, no test                           one line: it is there at the end
  EC13 X added, then deleted later, no test                           no line
  EC14 status T (a type change) counts as touching                    one line
  EC19 a test commit of X, before X's first, that also changes module Y    a line for X naming Y,
                                                                      and Y's own no-test line
  EC20 two test commits before X's first, one with code in it         one line: that commit
  EC21 a test commit of X that deletes a module                       one line: a deletion is a
                                                                      change of code (Claude's
                                                                      choice: it only narrows)
  EC22 X's test file deleted in a commit before X's first             no line: a deleted test file
                                                                      counts as touched (Claude's
                                                                      choice 5: it does less than
                                                                      the row asks)
  EC23 a test commit of X with code in it, X deleted at the end       no line: a deleted module
                                                                      needs no test

Equivalence classes (mixed, on its own):
  EC24 test files only; test files and documents; code with a test file of another module only
                                                                      ""
  EC25 a test file of X and two modules, given in reverse             the line, both named, sorted

Equivalence classes (is_module):
  EC15 a .py file under ploni/ (any depth), eval/, scripts/           a module
  EC16 a .py file under tests/, experiments/, docs/, the root; a .sh under scripts/   not

Equivalence classes (is_test_for):
  EC17 each tail of X's path joined by `_`: test_atomic.py, test_safety_atomic.py,
       test_ploni_safety_atomic.py, at any depth under tests/       a test file for X
  EC18 the six modules that have no test file named for them today (issue #175): a test
       file named by the rule counts (test___init__.py, test_ploni___init__.py,
       test___main__.py, test_errors.py, test_download_e1_model.py); the file that tests them
       today under another name (tests/t1_unit/test_cli.py for ploni/__main__.py) does not.
       The narrowest rule: no exemption (Known limits of the script).

Boundaries:
  B1  no commit                                                       no line
  B2  one commit, X only                                              one line
  B3  a commit touching nothing (empty)                               no effect
  B4  the test file in the commit just before X's first               no line
  B5  `tests/test_atomic.py` directly under tests/                    a test file
  B6  a module at the top of its folder (`scripts/a.py`): tails test_a.py, test_scripts_a.py

Error paths (main):
  E1  no argument, one, three                                         exit 2, a usage line
  E2  a revision git does not know                                    CalledProcessError (the
                                                                      module suite)

Adversarial:
  A1  near a tail but not one: test_ploni_atomic.py (a part skipped), test_tomic.py,
      test_afety_atomic.py, test_atomic.txt, test_atomic.py.bak, atomic_test.py,
      test_Atomic.py                                                  not a test file for X
  A2  a test-named file outside tests/: ploni/test_atomic.py, experiments/e1/tests/test_atomic.py,
      docs/tests/test_atomic.py                                       not a test file (the first
                                                                      is itself a module)
  A3  near a module folder: ploni2/a.py, evaluation/a.py, docs/ploni/a.py, scripts.py   not a module
  A4  `scripts/X.PY`: a module, as Python imports it on Windows; its test test_X.py
  A5  a Hebrew module, ploni/שם.py, with tests/t1_unit/test_שם.py first    no line; without it,
      one line with the name whole
  A6  two modules with the same tail (ploni/a/x.py, scripts/x.py) share test_x.py    one test
      commit covers both (Known limits)
  A7  a merge commit of main into the branch (its second parent on the base)    left out; a
      merge of another branch, whose second parent the base does not hold    one line naming it
      (the module suite: merges are read from git only)

Not applicable: the document axes; the Hebrew axes of the test-matrix skill other than A5, as
the input is a list of paths compared by their parts.
"""

import pytest

from scripts import check_commit_order as check
from scripts.check_commit_order import Commit

ATOMIC = "ploni/safety/atomic.py"
TEST = "tests/t1_unit/test_safety_atomic.py"
DOCS = "docs/STATUS.md"


def c(sha: str, *paths: str, status: str = "M") -> Commit:
    """Return a commit that gave each path the same status."""
    return Commit(sha, dict.fromkeys(paths, status))


def no_test(module: str, sha: str) -> str:
    """Return the line of a module with no test file touched before its first commit."""
    return f"{module}: no test file for it is touched before its first commit, {sha}"


def mixed(sha: str, module: str, code: str) -> str:
    """Return the line of a test commit of a module, before its first commit, that changes code."""
    return f"{sha}: a test commit of {module} also changes {code}; the failing tests are a commit of their own, with no implementation in it"


def test_ec1_test_first_then_the_module() -> None:
    assert check.problems([c("a1", TEST), c("b2", ATOMIC)]) == []


def test_ec2_the_module_first() -> None:
    assert check.problems([c("a1", ATOMIC), c("b2", TEST)]) == [no_test(ATOMIC, "a1")]


def test_ec3_module_and_test_in_one_commit() -> None:
    assert check.problems([c("a1", ATOMIC, TEST)]) == [no_test(ATOMIC, "a1")]


def test_ec4_a_later_commit_may_change_both() -> None:
    commits = [c("a1", TEST), c("b2", ATOMIC), c("c3", ATOMIC, TEST)]
    assert check.problems(commits) == []


def test_ec5_the_first_commit_of_the_module_counts() -> None:
    commits = [c("a1", ATOMIC), c("b2", TEST), c("c3", ATOMIC)]
    assert check.problems(commits) == [no_test(ATOMIC, "a1")]


def test_ec6_a_test_of_another_module_only() -> None:
    commits = [c("a1", "tests/t1_unit/test_logging.py"), c("b2", ATOMIC)]
    assert check.problems(commits) == [no_test(ATOMIC, "b2")]


def test_ec7_no_module_touched() -> None:
    commits = [c("a1", DOCS, ".github/workflows/fast.yml"), c("b2", TEST, "experiments/e6/run.py", "tests/conftest.py")]
    assert check.problems(commits) == []


def test_ec8_two_modules_sorted() -> None:
    commits = [c("a1", "scripts/check.py"), c("b2", ATOMIC)]
    assert check.problems(commits) == [no_test(ATOMIC, "b2"), no_test("scripts/check.py", "a1")]


def test_ec8_six_modules_sorted() -> None:
    modules = [f"ploni/m{index}.py" for index in range(6)]
    assert check.problems([c("a1", *reversed(modules))]) == [no_test(module, "a1") for module in modules]


@pytest.mark.parametrize(
    ("module", "test"),
    [("ploni/types.py", "tests/t1_unit/test_types.py"), ("eval/score.py", "tests/t1_unit/test_score.py"), ("scripts/check.py", "tests/t4_integration/test_check.py")],
)
def test_ec9_a_module_of_each_folder(module: str, test: str) -> None:
    assert check.problems([c("a1", module)]) == [no_test(module, "a1")]
    assert check.problems([c("a1", test), c("b2", module)]) == []


def test_ec10_a_deleted_module() -> None:
    assert check.problems([c("a1", ATOMIC, status="D")]) == []


def test_ec11_deleted_with_its_test() -> None:
    assert check.problems([c("a1", ATOMIC, TEST, status="D")]) == []


def test_ec12_deleted_then_added_again() -> None:
    commits = [c("a1", ATOMIC, status="D"), c("b2", ATOMIC, status="A")]
    assert check.problems(commits) == [no_test(ATOMIC, "a1")]


def test_ec13_added_then_deleted() -> None:
    commits = [c("a1", ATOMIC, status="A"), c("b2", DOCS), c("c3", ATOMIC, status="D")]
    assert check.problems(commits) == []


def test_ec14_a_type_change_touches() -> None:
    assert check.problems([c("a1", ATOMIC, status="T")]) == [no_test(ATOMIC, "a1")]


@pytest.mark.parametrize("path", ["ploni/types.py", ATOMIC, "ploni/a/b/c.py", "eval/score.py", "scripts/check.py", "ploni/__init__.py"])
def test_ec15_modules(path: str) -> None:
    assert check.is_module(path)


@pytest.mark.parametrize("path", [TEST, "experiments/e6/run.py", "docs/x.py", "x.py", "scripts/run.sh", "eval/baselines.json"])
def test_ec16_not_modules(path: str) -> None:
    assert not check.is_module(path)


@pytest.mark.parametrize(
    "path",
    ["tests/t1_unit/test_atomic.py", "tests/t4_integration/test_safety_atomic.py", "tests/t2_property/test_ploni_safety_atomic.py", "tests/a/b/test_atomic.py"],
)
def test_ec17_each_tail_names_a_test_file(path: str) -> None:
    assert check.is_test_for(path, ATOMIC)


@pytest.mark.parametrize(
    ("module", "test"),
    [
        ("ploni/__init__.py", "tests/t1_unit/test___init__.py"),
        ("ploni/__init__.py", "tests/t1_unit/test_ploni___init__.py"),
        ("ploni/safety/__init__.py", "tests/t1_unit/test_safety___init__.py"),
        ("ploni/__main__.py", "tests/t1_unit/test___main__.py"),
        ("ploni/errors.py", "tests/t1_unit/test_errors.py"),
        ("scripts/download_e1_model.py", "tests/t1_unit/test_download_e1_model.py"),
        ("scripts/download_e5_models.py", "tests/t1_unit/test_scripts_download_e5_models.py"),
    ],
)
def test_ec18_the_six_by_the_rule(module: str, test: str) -> None:
    assert check.is_test_for(test, module)
    assert check.problems([c("a1", test), c("b2", module)]) == []


def test_ec18_main_is_not_tested_by_test_cli() -> None:
    commits = [c("a1", "tests/t1_unit/test_cli.py"), c("b2", "ploni/__main__.py")]
    assert check.problems(commits) == [no_test("ploni/__main__.py", "b2")]


def test_b1_no_commit() -> None:
    assert check.problems([]) == []


def test_b2_one_commit_module_only() -> None:
    assert check.problems([c("a1", "ploni/types.py")]) == [no_test("ploni/types.py", "a1")]


def test_b3_an_empty_commit() -> None:
    assert check.problems([c("a1"), c("b2", TEST), c("c3"), c("d4", ATOMIC), c("e5")]) == []


def test_b4_the_commit_just_before() -> None:
    assert check.problems([c("a1", DOCS), c("b2", TEST), c("c3", ATOMIC)]) == []


def test_b5_directly_under_tests() -> None:
    assert check.is_test_for("tests/test_atomic.py", ATOMIC)


@pytest.mark.parametrize(("test", "expected"), [("tests/test_a.py", True), ("tests/test_scripts_a.py", True), ("tests/test_.py", False)])
def test_b6_a_module_at_the_top_of_its_folder(test: str, expected: bool) -> None:
    assert check.is_test_for(test, "scripts/a.py") is expected


@pytest.mark.parametrize("argv", [[], ["HEAD^1"], ["a", "b", "c"]])
def test_e1_main_needs_two_revisions(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main(argv) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("usage: ")


@pytest.mark.parametrize(
    "path",
    [
        "tests/t1_unit/test_ploni_atomic.py",
        "tests/t1_unit/test_tomic.py",
        "tests/t1_unit/test_afety_atomic.py",
        "tests/t1_unit/test_atomic.txt",
        "tests/t1_unit/test_atomic.py.bak",
        "tests/t1_unit/atomic_test.py",
        "tests/t1_unit/test_Atomic.py",
    ],
)
def test_a1_near_a_tail_is_not_a_test_file(path: str) -> None:
    assert not check.is_test_for(path, ATOMIC)


@pytest.mark.parametrize("path", ["ploni/test_atomic.py", "experiments/e1/tests/test_atomic.py", "docs/tests/test_atomic.py"])
def test_a2_outside_tests_is_not_a_test_file(path: str) -> None:
    assert not check.is_test_for(path, ATOMIC)
    assert no_test(ATOMIC, "b2") in check.problems([c("a1", path), c("b2", ATOMIC)])


@pytest.mark.parametrize("path", ["ploni2/a.py", "evaluation/a.py", "docs/ploni/a.py", "scripts.py", "Ploni/a.py"])
def test_a3_near_a_module_folder(path: str) -> None:
    assert not check.is_module(path)


def test_a4_an_upper_case_end() -> None:
    assert check.is_module("scripts/X.PY")
    assert check.problems([c("a1", "tests/test_X.py"), c("b2", "scripts/X.PY")]) == []


def test_a5_a_hebrew_module() -> None:
    module = "ploni/שם.py"
    assert check.problems([c("a1", "tests/t1_unit/test_שם.py"), c("b2", module)]) == []
    assert check.problems([c("a1", module)]) == [no_test(module, "a1")]


def test_a6_one_tail_two_modules() -> None:
    commits = [c("a1", "tests/t1_unit/test_x.py"), c("b2", "ploni/a/x.py", "scripts/x.py")]
    assert check.problems(commits) == []


def test_ec19_a_test_commit_with_another_module() -> None:
    commits = [c("a1", TEST, "ploni/types.py"), c("b2", ATOMIC)]
    assert check.problems(commits) == [mixed("a1", ATOMIC, "ploni/types.py"), no_test("ploni/types.py", "a1")]


def test_ec20_one_of_two_test_commits_with_code() -> None:
    commits = [c("a1", TEST, "tests/t1_unit/test_check.py"), c("b2", TEST, "scripts/check.py"), c("c3", ATOMIC)]
    assert check.problems(commits) == [mixed("b2", ATOMIC, "scripts/check.py")]


def test_ec21_a_test_commit_that_deletes_a_module() -> None:
    commits = [Commit("a1", {TEST: "M", "ploni/types.py": "D"}), c("b2", ATOMIC)]
    assert check.problems(commits) == [mixed("a1", ATOMIC, "ploni/types.py")]


def test_ec22_a_test_file_deleted_before_the_module() -> None:
    assert check.problems([c("a1", TEST, status="D"), c("b2", ATOMIC)]) == []


def test_ec23_a_mixed_test_commit_of_a_module_deleted_at_the_end() -> None:
    commits = [c("a1", TEST, "ploni/types.py"), c("b2", ATOMIC, status="D"), c("c3", "tests/t1_unit/test_types.py")]
    assert check.problems(commits) == [no_test("ploni/types.py", "a1")]


@pytest.mark.parametrize(
    "paths",
    [(TEST, "tests/t4_integration/test_atomic.py"), (TEST, DOCS), ("tests/t1_unit/test_types.py", "ploni/types.py")],
    ids=["tests", "tests-and-docs", "another-module-test"],
)
def test_ec24_mixed_without_code_or_without_a_test_of_x(paths: tuple[str, ...]) -> None:
    assert check.mixed(c("a1", *paths), ATOMIC) == ""


def test_ec25_mixed_names_the_code_sorted() -> None:
    commit = c("0123456789abcdef", "scripts/check.py", TEST, "eval/score.py")
    assert check.mixed(commit, ATOMIC) == mixed("0123456789ab", ATOMIC, "eval/score.py, scripts/check.py")
