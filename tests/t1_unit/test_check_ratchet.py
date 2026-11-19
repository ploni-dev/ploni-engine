"""Tests of scripts/check_ratchet.py: a PR lowers no test count without an override, and adds no unbudgeted suppression.

Why: `PROMOTION.md` section 6, the ratchet: "Test functions per test file" and "Assertions per
test file" may not decrease; "A decrease fails the build with the exact counter and the
delta"; an override line is accepted "only when the line is present and the PR touches no
file under `ploni/`". `PROCESS.md` section 4.5: a ceiling counter for `noqa` and `type: ignore`
lines in `.ratchet.json`, "a number that may not rise". Bad PR 6 of the closing test of Phase 0
(`PROMOTION.md` section 10): a test file with one test function deleted, with no override line.
Issue #78. Two answers of Achia's of 2026-11-19: "Count main and the PR (Recommended)" (CI
counts on main and on the PR; `.ratchet.json` keeps one number, the ceiling, which a PR raises
in that file when it adds a suppression), and "Tests now, rest when real (Recommended)" (test
functions, assertions and the ceiling now; fixtures, baselines, detectors and journeys each in
a PR of its own when the first one exists).

Test matrix:

Equivalence classes (problems):
  EC1  no test file changed                          no line
  EC2  a test function added                         no line
  EC3  one test function deleted, no override        one line, with the counter and the delta
  EC4  the same, with a matching override, no ploni/ path    no line
  EC5  a matching override, and the PR changes ploni/    the refusal and the decrease
  EC6  assertions fewer, test functions the same     one line for assertions
  EC7  a test file deleted                           a line per counter, down to 0
  EC8  a new test file                               no line
  EC9  suppressions over the ceiling                 one line; equal or under: none
  EC10 no ceiling in .ratchet.json, or a ceiling that is not a whole number, or no valid JSON,
       or JSON that is not an object                 one line

Error paths (main):
  E1  wrong argument count                           exit 2, a usage line

Equivalence classes (the parts):
  EC11 count(): test functions at module level, in a class, async; the names pytest collects
       ("test", "test_x", "testing"); a helper is not counted; asserts anywhere in the file
  EC12 overrides(): a line read whole; in backquotes; spaces; Hebrew in the reason
  EC13 is_test_file(): tests/**/test_*.py only

Boundaries:
  B1  an override with the wrong delta (-2 for -1)    the decrease, and "names no decrease"
  B2  two decreases of the same delta in one file     two override lines needed
  B3  an override for a file with no decrease         "names no decrease"
  B4  an override line that cannot be read (no reason, "+1", no number)    "not read"
  B5  conftest.py and a helper under tests/          not test files
  B6  source that does not parse                     SyntaxError (main fails, red)

Adversarial:
  A1  an override inside a quoted block ("> ratchet-override: ...")    not read: a line
      starts with the token, nothing else
  A2  "ploni_x/a.py" is not under ploni/; "ploni/a.py" is
  A3  a test function renamed: one gone, one new, the count the same    no line (the known
      limit: functions are counted, not named)

Not applicable: the document axes; the Hebrew axes other than A2's reason (EC12), as the
inputs are Python source, paths, a PR body read for one token, and a JSON file.

Known limits:
  - Functions are counted, not named, and parametrized cases are not counted: a renamed test
    and a shorter parameter list are not seen. Assertions catch part of the second.
"""

import pytest

from scripts import check_ratchet as check
from scripts.check_ratchet import Counts

FILE = "tests/t1_unit/test_a.py"
RATCHET = '{"suppressions_ceiling": 10}'


def problems(body: str, before: dict[str, Counts], after: dict[str, Counts], paths: list[str] | None = None, suppressions: int = 10, ratchet: str = RATCHET) -> list[str]:
    """Run problems() with the changed paths defaulting to the counted files."""
    changed = sorted(set(before) | set(after)) if paths is None else paths
    return check.problems(body, changed, before, after, suppressions, ratchet)


def test_ec1_no_test_file() -> None:
    assert problems("", {}, {}, paths=["ploni/a.py", "docs/a.md"]) == []


def test_ec2_a_test_added() -> None:
    assert problems("", {FILE: Counts(2, 3)}, {FILE: Counts(3, 4)}) == []


def test_ec3_one_test_deleted() -> None:
    assert problems("", {FILE: Counts(2, 3)}, {FILE: Counts(1, 3)}) == [f"{FILE}: test functions 2 -> 1 (-1)"]


def test_ec4_with_an_override() -> None:
    body = f"ratchet-override: {FILE}  -1  merged two cases into one\n"
    assert problems(body, {FILE: Counts(2, 3)}, {FILE: Counts(1, 3)}) == []


def test_ec5_an_override_and_ploni() -> None:
    body = f"ratchet-override: {FILE} -1 merged\n"
    found = problems(body, {FILE: Counts(2, 3)}, {FILE: Counts(1, 3)}, paths=[FILE, "ploni/a.py"])
    assert found == [
        "ratchet-override refused: the PR changes files under ploni/",
        f"{FILE}: test functions 2 -> 1 (-1)",
    ]


def test_ec6_fewer_assertions() -> None:
    assert problems("", {FILE: Counts(2, 5)}, {FILE: Counts(2, 3)}) == [f"{FILE}: assertions 5 -> 3 (-2)"]


def test_ec7_a_test_file_deleted() -> None:
    assert problems("", {FILE: Counts(2, 5)}, {FILE: Counts(0, 0)}) == [
        f"{FILE}: test functions 2 -> 0 (-2)",
        f"{FILE}: assertions 5 -> 0 (-5)",
    ]


def test_ec8_a_new_test_file() -> None:
    assert problems("", {}, {FILE: Counts(2, 5)}) == []


@pytest.mark.parametrize(("suppressions", "lines"), [(11, ["suppressions 11, ceiling 10 in .ratchet.json: raise suppressions_ceiling in the PR that adds one"]), (10, []), (3, [])])
def test_ec9_the_ceiling(suppressions: int, lines: list[str]) -> None:
    assert problems("", {}, {}, paths=[], suppressions=suppressions) == lines


@pytest.mark.parametrize("ratchet", ["{}", '{"suppressions_ceiling": "10"}', '{"suppressions_ceiling": 1.5}', "not json", '{"suppressions_ceiling": true}', "[10]"])
def test_ec10_no_readable_ceiling(ratchet: str) -> None:
    assert problems("", {}, {}, paths=[], ratchet=ratchet) == [".ratchet.json has no whole-number suppressions_ceiling"]


SOURCE = '''
import pytest

def helper():
    assert True

def test():
    assert 1

def test_x():
    assert 1
    assert 2

def testing():
    pass

async def test_async():
    assert 3

class TestThing:
    def test_method(self):
        for _ in range(2):
            assert 4
'''


def test_ec11_count() -> None:
    assert check.count(SOURCE) == Counts(test_functions=5, assertions=6)


@pytest.mark.parametrize(
    ("line", "read"),
    [
        (f"ratchet-override: {FILE} -3 merged duplicate separator cases", (FILE, 3)),
        (f"`ratchet-override: {FILE}  -3  merged`", (FILE, 3)),
        (f"  ratchet-override:   {FILE} -12 איחוד מקרים כפולים", (FILE, 12)),
    ],
)
def test_ec12_overrides(line: str, read: tuple[str, int]) -> None:
    assert check.overrides(f"text\n{line}\nmore") == ([read], [])


@pytest.mark.parametrize(
    ("path", "is_test"),
    [(FILE, True), ("tests/t4_integration/test_b.py", True), ("tests/test_c.py", True), ("tests/conftest.py", False), ("tests/project_imports.py", False), ("ploni/test_d.py", False), ("tests/t1_unit/test_e.txt", False)],
)
def test_ec13_is_test_file(path: str, is_test: bool) -> None:
    assert check.is_test_file(path) is is_test


def test_b1_the_wrong_delta() -> None:
    body = f"ratchet-override: {FILE} -2 merged\n"
    assert problems(body, {FILE: Counts(2, 3)}, {FILE: Counts(1, 3)}) == [
        f"ratchet-override names no decrease: {FILE} -2",
        f"{FILE}: test functions 2 -> 1 (-1)",
    ]


def test_b2_two_decreases_of_one_delta() -> None:
    one = f"ratchet-override: {FILE} -1 merged\n"
    assert problems(one, {FILE: Counts(2, 3)}, {FILE: Counts(1, 2)}) == [f"{FILE}: assertions 3 -> 2 (-1)"]
    assert problems(one + one, {FILE: Counts(2, 3)}, {FILE: Counts(1, 2)}) == []


def test_b3_an_override_with_no_decrease() -> None:
    body = "ratchet-override: tests/t1_unit/test_z.py -1 merged\n"
    assert problems(body, {}, {}, paths=[]) == ["ratchet-override names no decrease: tests/t1_unit/test_z.py -1"]


@pytest.mark.parametrize("line", [f"ratchet-override: {FILE} -1", f"ratchet-override: {FILE} +1 more", f"ratchet-override: {FILE} merged", "ratchet-override:"])
def test_b4_a_line_not_read(line: str) -> None:
    assert check.overrides(line) == ([], [line])
    assert problems(line, {}, {}, paths=[]) == [f"ratchet-override line not read: {line}"]


def test_b6_source_that_does_not_parse() -> None:
    with pytest.raises(SyntaxError):
        check.count("def test(:\n")


@pytest.mark.parametrize("argv", [[], ["HEAD^1"], ["a", "b", "c"]])
def test_e1_main_needs_two_revisions(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert check.main(argv, {}) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert err.startswith("usage: ")


def test_a1_an_override_in_a_quote() -> None:
    body = f"> ratchet-override: {FILE} -1 merged\n"
    assert check.overrides(body) == ([], [])
    assert problems(body, {FILE: Counts(2, 3)}, {FILE: Counts(1, 3)}) == [f"{FILE}: test functions 2 -> 1 (-1)"]


@pytest.mark.parametrize(("other", "refused"), [("ploni_x/a.py", False), ("ploni/a.py", True), ("docs/ploni/a.md", False)])
def test_a2_what_is_under_ploni(other: str, refused: bool) -> None:
    body = f"ratchet-override: {FILE} -1 merged\n"
    found = problems(body, {FILE: Counts(2, 3)}, {FILE: Counts(1, 3)}, paths=[FILE, other])
    assert (found != []) is refused


def test_a3_a_renamed_test_is_not_seen() -> None:
    before = "def test_a():\n    assert 1\n"
    after = "def test_b():\n    assert 1\n"
    assert problems("", {FILE: check.count(before)}, {FILE: check.count(after)}) == []
