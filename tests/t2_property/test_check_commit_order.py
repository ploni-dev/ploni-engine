"""Invariants of scripts/check_commit_order.py over every short commit sequence drawn from a labelled pool.

Why: `CLAUDE.md`, Tests: an invariant is held over 500 generated cases. The pool below is
labelled by hand (which file is a module, which is a test file for which module), so the
expected answer of each case comes from the labels and the words of `PROMOTION.md` section
5.2, not from the code under test.

Invariants:
  I1  for each module the sequence touches, in module order: one line when no commit before
      its first touches its test file, and one line for each commit that touches both; nothing
      else.
  I2  a commit that touches no module and no test file, added at the front and at the end,
      does not change the answer.

Sample: every sequence of one to three commits, each touching any subset of a pool of four
files (two modules, a test file for each), 4,368 cases; in the full suite (tests/sizes.py)
sequences of up to four commits, 69,904 cases.

Known limits: the pool is fixed and every change is a modification; deletions, the name rule
and the folders are covered by the unit tests (tests/t1_unit/test_check_commit_order.py).
"""

from collections.abc import Iterator
from itertools import combinations, product

from scripts import check_commit_order as check
from scripts.check_commit_order import Commit
from tests.sizes import full

TESTS = {"ploni/a.py": "tests/t1_unit/test_a.py", "scripts/b.py": "tests/t4_integration/test_scripts_b.py"}
POOL = [*TESTS, *TESTS.values()]
SUBSETS = [chosen for size in range(len(POOL) + 1) for chosen in combinations(POOL, size)]
LONGEST = 4 if full() else 3


def sequences() -> Iterator[list[Commit]]:
    """Yield every sequence of one to LONGEST commits over the pool, one at a time to keep memory low."""
    for length in range(1, LONGEST + 1):
        for picked in product(SUBSETS, repeat=length):
            yield [Commit(f"c{index}", dict.fromkeys(chosen, "M")) for index, chosen in enumerate(picked)]


def expected(commits: list[Commit]) -> list[str]:
    """Return the lines the labels and the row's words give for a sequence."""
    lines = []
    for module in sorted(TESTS):
        touching = [index for index, commit in enumerate(commits) if module in commit.changes]
        if not touching:
            continue
        test = TESTS[module]
        if not any(test in commit.changes for commit in commits[: touching[0]]):
            lines.append(f"{module}: no test file for it is touched before its first commit, c{touching[0]}")
        lines += [
            f"c{index}: touches {module} and its test file {test}; the failing tests are a commit of their own"
            for index in touching
            if test in commits[index].changes
        ]
    return lines


def test_the_sample_is_over_500() -> None:
    assert sum(1 for _ in sequences()) == (69904 if full() else 4368)


def test_i1_the_answer_follows_the_labels() -> None:
    for commits in sequences():
        assert check.problems(commits) == expected(commits), commits


def test_i2_a_commit_of_other_files_changes_nothing() -> None:
    for commits in sequences():
        other = Commit("docs", {"docs/STATUS.md": "M"})
        assert check.problems([other, *commits, other]) == check.problems(commits), commits
