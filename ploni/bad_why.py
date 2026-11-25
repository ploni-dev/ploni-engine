"""Bad PR 4 of the Phase 0 closing test: a public function whose docstring has no Why section.

Why: issue #30. This file must be refused by CI and never merge.
"""


def doubled(number: int) -> int:
    """Return the number times two.

    Contract: an int in, an int out.
    """
    return number * 2
