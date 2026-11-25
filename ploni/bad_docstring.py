"""Bad PR 3 of the Phase 0 closing test: a public function with no docstring.

Why: issue #30. This file must be refused by CI and never merge.
"""


def doubled(number: int) -> int:
    return number * 2
