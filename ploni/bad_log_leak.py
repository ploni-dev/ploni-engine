"""Bad PR 5b of the Phase 0 closing test: a product line that logs past the filter.

Why: issue #30, finding 2 of the review of 47780be. This file must never merge.
"""

import logging

_LOG = logging.getLogger("ploni.bad_log_leak")
_LOG.propagate = False
_LOG.addHandler(logging.StreamHandler())


def leak(text: str) -> None:
    """Write a text to the log through a handler of its own, past the filter.

    Why: the shape bad PR 5b tests. Contract: any text in, nothing returned.
    """
    _LOG.warning("document text: %s", text)
