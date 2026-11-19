"""Invariants of scripts/check_waiver.py over every combination drawn from labelled pools.

Why: `CLAUDE.md`, Tests: an invariant is held over 500 generated cases. Each ID and each path
below is labelled by hand: whether the ID is in force on each day, and which paths it covers.
The expected answer comes from the labels, not from the code under test.

Invariants:
  I1  a body that cites nothing has no problem, whatever the paths.
  I2  problems() is empty exactly when every cited ID is in force on that day and covers
      every changed path.
  I3  the order of the paths and of the citations does not change the answer.

Sample: every subset of four IDs, times every subset of four paths, times two days: 512
cases, each also with paths and citations reversed.

Known limits: the pools are fixed; other shapes are covered by the unit tests
(tests/t1_unit/test_check_waiver.py), whose fixture files this suite reuses.
"""

from datetime import date
from itertools import combinations

from scripts import check_waiver as check
from tests.t1_unit.test_check_waiver import STATUS, WAIVERS

DAYS = [date(2026, 11, 17), date(2026, 11, 19)]
IDS = ["WAIVER-003", "WAIVER-005", "WAIVER-002", "WAIVER-999"]
PATHS = ["ploni/resolve/a.py", "tests/t2_property/test_projection.py", "ploni/x.py", "docs/a.md"]
# By hand, from the fixture: 003 is in force on both days (Phase 3 is open); 005 expires on
# 2026-11-18; 002 is under Expired; 999 is not in the file.
IN_FORCE = {"WAIVER-003": set(DAYS), "WAIVER-005": {date(2026, 11, 17)}, "WAIVER-002": set(), "WAIVER-999": set()}
COVERS = {
    "WAIVER-003": {"ploni/resolve/a.py", "tests/t2_property/test_projection.py"},
    "WAIVER-005": {"ploni/resolve/a.py", "ploni/x.py"},
    "WAIVER-002": set(),
    "WAIVER-999": set(),
}


def subsets(pool: list[str]) -> list[list[str]]:
    """Return every subset of the pool, in pool order."""
    return [list(chosen) for size in range(len(pool) + 1) for chosen in combinations(pool, size)]


CASES = [(ids, paths, day) for ids in subsets(IDS) for paths in subsets(PATHS) for day in DAYS]


def body(ids: list[str]) -> str:
    """Return a PR body that cites each ID on a line of its own."""
    return "".join(f"waiver: {waiver_id}\n" for waiver_id in ids)


def test_the_sample_is_over_500() -> None:
    assert len(CASES) == 512


def test_i1_no_citation_no_problem() -> None:
    for paths in subsets(PATHS):
        for day in DAYS:
            assert check.problems("", paths, WAIVERS, STATUS, day) == [], paths


def test_i2_the_answer_follows_the_labels() -> None:
    for ids, paths, day in CASES:
        good = all(day in IN_FORCE[waiver_id] and set(paths) <= COVERS[waiver_id] for waiver_id in ids)
        assert (check.problems(body(ids), paths, WAIVERS, STATUS, day) == []) is good, (ids, paths, day)


def test_i3_order_does_not_matter() -> None:
    for ids, paths, day in CASES:
        forward = check.problems(body(ids), paths, WAIVERS, STATUS, day)
        assert forward == check.problems(body(ids[::-1]), paths[::-1], WAIVERS, STATUS, day), (ids, paths, day)
