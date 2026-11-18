"""The errors that Ploni's public API raises on purpose.

Why: a caller of the public API catches Ploni's own failures by one base class, and the one
failure the plan names, an export before every must-resolve item is resolved, by its own
(build-plan.md section 4.1: `apply()` "raises NotApprovedError if any ReviewItem is
unresolved"; journey S7 of section 7).

Contract: `PloniError` is the base of the errors that the public API raises on purpose. A
message never holds document text (`CLAUDE.md`, Hard constraints): it names ids, counts and
kinds.

Known limits: only the error the plan names exists; others are added by the phase that
first raises them. Not every error is a `PloniError`: `safety.tempfiles.NotRemoved` is an
`OSError`, and the safety helpers raise `TypeError` or `ValueError` when they are misused.
"""


class PloniError(Exception):
    """The base of the errors that the public API raises on purpose.

    Why: one class to catch Ploni's own failures by, apart from errors of the system.

    Contract: an Exception; its message names ids, counts and kinds, never document text.
    """


class NotApprovedError(PloniError):
    """An export was asked for while a must-resolve review item is still open.

    Why: the user's review is the product's last line of defence; an export must not go
    around it (build-plan.md section 4.1, journey S7).

    Contract: raised by the export before anything is written; the message names the
    open items by id.
    """
