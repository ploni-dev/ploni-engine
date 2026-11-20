"""Invariants of scripts/check_changed_paths.py over every set of paths drawn from a labelled pool.

Why: `CLAUDE.md`, Tests: an invariant is held over 500 generated cases. The pool below is
labelled by hand, so the expected answer of each case comes from the labels, not from the
code under test.

Invariants:
  I1  problems() is empty exactly when the set holds no code or nothing protected (the
      baselines or a CI workflow).
  I2  when it is not empty, it names each protected path of the set once, sorted, and
      nothing else.
  I3  the order of the paths does not change the answer.

Sample: every subset of a pool of ten paths, 1,024 cases, each also given in reverse; in the full
suite (tests/sizes.py) one more path of each kind, 13 paths, 8,192 cases.

Known limits: the pool is fixed; a path of a shape that is not in it is covered only by the
unit tests (tests/t1_unit/test_check_changed_paths.py).
"""

from itertools import combinations

from scripts import check_changed_paths as check

from tests.sizes import full

CODE = ["ploni/a.py", "tests/t1_unit/test_b.py", "x.PY", "experiments/e6/run.py"]
PROTECTED = ["eval/baselines.json", ".github/workflows/fast.yml", ".github/workflows/pr-body.yml"]
OTHER = ["docs/STATUS.md", "eval/baselines.json.bak", ".github/actions/a/action.yml"]
if full():
    # One more path of each kind: 13 paths, 8,192 subsets.
    CODE = [*CODE, "ploni/detect/c.py"]
    PROTECTED = [*PROTECTED, ".github/workflows/full.yml"]
    OTHER = [*OTHER, "README.md"]
POOL = CODE + PROTECTED + OTHER
SUBSETS = [list(chosen) for size in range(len(POOL) + 1) for chosen in combinations(POOL, size)]


def named(lines: list[str]) -> list[str]:
    """Return the path each problem line names: the text after its last ': '."""
    return [line.rsplit(": ", 1)[1] for line in lines]


def test_the_sample_is_over_500() -> None:
    assert len(SUBSETS) == (8192 if full() else 1024)


def test_i1_i2_the_answer_follows_the_labels() -> None:
    for paths in SUBSETS:
        protected = sorted(path for path in paths if path in PROTECTED)
        has_code = any(path in CODE for path in paths)
        expected = protected if has_code else []
        assert named(check.problems(paths)) == expected, paths


def test_i3_order_does_not_matter() -> None:
    for paths in SUBSETS:
        assert check.problems(paths) == check.problems(paths[::-1]), paths
