"""Invariants of scripts/check_ratchet.py over every combination of counts, overrides and ploni/.

Why: `CLAUDE.md`, Tests: an invariant is held over 500 generated cases. The rule of
`PROMOTION.md` section 6 is short enough to state whole, so each case's answer comes from it.

Invariants:
  I1  problems() is empty exactly when the decreases and the override lines match one to one
      by delta, and no override line stands in a PR that changes ploni/.
  I2  every decrease that is not covered is named, with its counter and its delta.

Sample: test functions and assertions before and after, each 0 to 2 (81 pairs of counts),
times four sets of override lines, times whether the PR changes ploni/: 648 cases.

Known limits: one file per case; several files are covered by the unit tests.
"""

from itertools import product

from scripts import check_ratchet as check
from scripts.check_ratchet import Counts

FILE = "tests/t1_unit/test_a.py"
LEVELS = range(3)
OVERRIDES = [[], [1], [2], [1, 2]]
CASES = list(product(LEVELS, LEVELS, LEVELS, LEVELS, range(len(OVERRIDES)), [False, True]))


def run(case: tuple[int, int, int, int, int, bool]) -> tuple[list[str], list[tuple[str, int]]]:
    """Return the problems of a case and the decreases it holds, as (counter, delta)."""
    tf_before, as_before, tf_after, as_after, which, ploni = case
    body = "".join(f"ratchet-override: {FILE} -{delta} reason\n" for delta in OVERRIDES[which])
    paths = [FILE, "ploni/a.py"] if ploni else [FILE]
    found = check.problems(body, paths, {FILE: Counts(tf_before, as_before)}, {FILE: Counts(tf_after, as_after)}, 0, '{"suppressions_ceiling": 0}')
    drops = [(name, before - after) for name, before, after in (("test functions", tf_before, tf_after), ("assertions", as_before, as_after)) if after < before]
    return found, drops


def test_the_sample_is_over_500() -> None:
    assert len(CASES) == 648


def test_i1_empty_exactly_when_every_decrease_is_covered() -> None:
    for case in CASES:
        found, drops = run(case)
        lines = list(OVERRIDES[case[4]])
        # Refused overrides are a problem only when there is an override line to refuse.
        covered = sorted(delta for _, delta in drops) == sorted(lines) and not (case[5] and lines)
        assert (found == []) is covered, case


def test_i2_an_uncovered_decrease_is_named() -> None:
    for case in CASES:
        found, drops = run(case)
        if case[5] or not OVERRIDES[case[4]]:
            for name, delta in drops:
                assert any(line.startswith(f"{FILE}: {name} ") and line.endswith(f"(-{delta})") for line in found), case
