"""Test matrix for tests/sizes.py: whether this run is the full suite.

Equivalence classes:
  EC1  the variable not set                         not full
  EC2  the variable set to "1"                      full
  EC3  any other value ("0", "true", "yes", "", " 1")   not full: only "1" turns it on, so that
                                                    no other spelling widens a run by accident
EC4  the full count of an invariant              5,000 (CLAUDE.md, Tests)
"""

import pytest

from tests import sizes


def test_ec1_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(sizes.FULL_SUITE, raising=False)
    assert sizes.full() is False


def test_ec2_set_to_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(sizes.FULL_SUITE, "1")
    assert sizes.full() is True


@pytest.mark.parametrize("value", ["0", "true", "yes", "", " 1"])
def test_ec3_any_other_value(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv(sizes.FULL_SUITE, value)
    assert sizes.full() is False


def test_ec4_the_full_count_of_an_invariant() -> None:
    assert sizes.INVARIANT_FULL == 5000
