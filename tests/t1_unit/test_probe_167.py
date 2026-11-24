"""A probe of issue #167, never merged: one test that fails only at full size.

Why: after a failed night the nightly check runs the full suite on a PR. This test passes in the
fast suite and fails at full size, so that check must turn this PR red.
"""

from tests.sizes import full


def test_probe_fails_only_at_full_size() -> None:
    assert not full()
