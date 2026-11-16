"""A test that fails on purpose, for the merge gate's own test (PROMOTION.md sections 10 and 11).

Why: the gate must refuse a PR whose check is red. This file makes the check red. The PR that
holds it targets a scratch branch and must never merge.
"""


def test_this_pr_must_never_merge() -> None:
    raise AssertionError("the merge gate's own test: this check is red on purpose")
