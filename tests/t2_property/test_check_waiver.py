"""Invariants of scripts/check_waiver.py over every combination drawn from labelled pools.

Why: `CLAUDE.md`, Tests: an invariant is held over 500 generated cases. Each ID and each path
below is labelled by hand: whether the ID is in force on each day, and which paths it covers.
The expected answer comes from the labels, not from the code under test.

Invariants:
  I1  a body that cites nothing has no problem, whatever the paths.
  I2  problems() is empty exactly when every cited ID is in force on that day and covers
      every changed path.
  I3  the order of the paths and of the citations does not change the answer.

Sample (in the full suite, tests/sizes.py: five IDs, six paths, three days, 6,144; I1 over 27
bodies that cite nothing, 6,912): every subset of four IDs, times every subset of four paths, times two days: 512
cases, each also with paths and citations reversed.

Known limits: the pools are fixed; other shapes are covered by the unit tests
(tests/t1_unit/test_check_waiver.py), whose fixture files this suite reuses.
"""

from datetime import date
from itertools import combinations

from scripts import check_waiver as check
from tests.sizes import INVARIANT_FULL, full
from tests.t1_unit.test_check_waiver import STATUS, WAIVERS

DAYS = [date(2026, 11, 17), date(2026, 11, 19)]
IDS = ["WAIVER-003", "WAIVER-005", "WAIVER-002", "WAIVER-999"]
PATHS = ["ploni/resolve/a.py", "tests/t2_property/test_projection.py", "ploni/x.py", "docs/a.md"]
if full():
    # A third day, a waiver with a file pattern and a date, two more paths: 32 * 64 * 3 = 6,144.
    DAYS = [*DAYS, date(2026, 11, 20)]
    IDS = [*IDS, "WAIVER-004"]
    PATHS = [*PATHS, "ploni/resolve/b/c.py", "README.md"]
# By hand, from the fixture: 003 is in force on every day (Phase 3 is open); 005 expires on
# 2026-11-18; 004 on 2026-11-19, in force on that day; 002 is under Expired; 999 is not in the file.
IN_FORCE = {
    "WAIVER-003": set(DAYS),
    "WAIVER-005": {date(2026, 11, 17)},
    "WAIVER-004": {date(2026, 11, 17), date(2026, 11, 19)},
    "WAIVER-002": set(),
    "WAIVER-999": set(),
}
# By hand, from the scopes: 003 "tests/t2_property/test_projection.py, ploni/resolve/"; 005
# "ploni/"; 004 "ploni/*.py", one folder deep only.
COVERS = {
    "WAIVER-003": {"ploni/resolve/a.py", "tests/t2_property/test_projection.py", "ploni/resolve/b/c.py"},
    "WAIVER-005": {"ploni/resolve/a.py", "ploni/x.py", "ploni/resolve/b/c.py"},
    "WAIVER-004": {"ploni/x.py"},
    "WAIVER-002": set(),
    "WAIVER-999": set(),
}


# Bodies that cite no waiver: the empty body only, in the fast suite. In the full suite also the
# seven shapes of the unit test's A7 that hold the token and its colon where no citation stands,
# each with five IDs that give a line whenever they are read as cited (999 absent, 002 expired,
# 006 no scope, 007 an unreadable expiry, 008 a closed phase): 36 * 64 * 3 = 6,912 cases for I1.
NOT_CITATIONS = (
    "> waiver: {id}",
    "> > waiver: {id}",
    "PROMOTION.md says a PR carries `waiver: {id}` in its body.",
    "see waiver: {id}",
    "בקשה waiver: {id}",
    "waiver:\n{id}",
    "> - waiver: {id}",
)
MISREAD_IDS = ("WAIVER-999", "WAIVER-002", "WAIVER-006", "WAIVER-007", "WAIVER-008")
BODIES = [""]
if full():
    BODIES += [shape.format(id=waiver_id) for shape in NOT_CITATIONS for waiver_id in MISREAD_IDS]


def subsets(pool: list[str]) -> list[list[str]]:
    """Return every subset of the pool, in pool order."""
    return [list(chosen) for size in range(len(pool) + 1) for chosen in combinations(pool, size)]


CASES = [(ids, paths, day) for ids in subsets(IDS) for paths in subsets(PATHS) for day in DAYS]


def body(ids: list[str]) -> str:
    """Return a PR body that cites each ID on a line of its own."""
    return "".join(f"waiver: {waiver_id}\n" for waiver_id in ids)


def test_the_sample_is_over_500() -> None:
    assert len(CASES) == (6144 if full() else 512)
    assert len(BODIES) * len(subsets(PATHS)) * len(DAYS) >= (INVARIANT_FULL if full() else 32)
    assert all(check.cited(body) == [] for body in BODIES)


def test_i1_no_citation_no_problem() -> None:
    for body in BODIES:
        for paths in subsets(PATHS):
            for day in DAYS:
                assert check.problems(body, paths, WAIVERS, STATUS, day) == [], (body, paths)


def test_i2_the_answer_follows_the_labels() -> None:
    for ids, paths, day in CASES:
        good = all(day in IN_FORCE[waiver_id] and set(paths) <= COVERS[waiver_id] for waiver_id in ids)
        assert (check.problems(body(ids), paths, WAIVERS, STATUS, day) == []) is good, (ids, paths, day)


def test_i3_order_does_not_matter() -> None:
    for ids, paths, day in CASES:
        forward = check.problems(body(ids), paths, WAIVERS, STATUS, day)
        assert forward == check.problems(body(ids[::-1]), paths[::-1], WAIVERS, STATUS, day), (ids, paths, day)
