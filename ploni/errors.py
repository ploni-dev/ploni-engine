"""The errors that Ploni's public functions raise.

Why: a caller of the public API catches Ploni's own failures by one base class, and the one
failure the plan names, an export before every must-resolve item is resolved, by its own
(build-plan.md section 4.1: `apply()` "raises NotApprovedError if any ReviewItem is
unresolved"; journey S7 of section 7).

Contract: `PloniError` is the base of every error raised on purpose by Ploni. A message never
holds document text (`CLAUDE.md`, Hard constraints): it names ids, counts and kinds.

Known limits: only the error the plan names exists. Others are added by the phase that first
raises them.
"""


class PloniError(Exception):
    """The base of every error Ploni raises on purpose."""


class NotApprovedError(PloniError):
    """An export was asked for while a must-resolve review item is still open."""
