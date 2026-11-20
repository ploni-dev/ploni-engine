"""Whether this run is the full suite, and how many cases an invariant gets in it.

Why: `CLAUDE.md`, Tests: "invariants 500 generated cases, 5,000 at phase close". The fast suite
keeps the counts its property tests have; the full suite (`PROCESS.md` section 5.1: on a
`run-full` label, on phase-close PRs and nightly) runs them at 5,000 or more. The full workflow
sets FULL_SUITE to "1"; nothing else does.

Contract: `full()` is True exactly when the environment variable FULL_SUITE holds "1". A
property test reads it when its module is imported, so the variable is set before pytest starts.

Known limits: a run started by hand is full only when the variable is set by hand too:
`PLONI_FULL_SUITE=1 python -m pytest tests` (in PowerShell, `$env:PLONI_FULL_SUITE = "1"` first).
"""

import os

FULL_SUITE = "PLONI_FULL_SUITE"
# CLAUDE.md, Tests: an invariant at phase close.
INVARIANT_FULL = 5000


def full() -> bool:
    """Say whether this run is the full suite."""
    return os.environ.get(FULL_SUITE) == "1"
