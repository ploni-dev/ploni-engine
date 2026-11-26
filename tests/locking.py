"""Ask whether another handle holds the lock of a file; age partial files; for the tests of the lock helper's callers.

Why: the product's helper takes a lock and keeps it (`ploni.safety.locks.take`); a test only
asks whether a file is held, and must not leave a file it did not find.

Contract: `aged(folder)` sets the last change of every partial file in a folder (not a link)
to 2 * YOUNG_SECONDS ago, as a crashed run's file is at the next start, so that
`sweep_partials` looks at it (Achia, 2026-11-26, "Skip young files (Recommended)", #212).
`held(path)` is False for a file that does not exist; otherwise it takes the lock
for a moment, gives it back, and says whether it could not. Raises OSError as `take` does,
for a path that cannot be opened (a folder).

Known limits: taking the lock for a moment makes a `hold` by someone else in that moment
fail; the tests that call this do not race it.
"""

import os
import time
from pathlib import Path

from ploni.safety import atomic, locks


def aged(folder: Path) -> None:
    """Make every partial file in a folder older than YOUNG_SECONDS, as a crashed run's is at the next start."""
    then = time.time() - 2 * atomic.YOUNG_SECONDS
    for entry in folder.iterdir():
        if entry.name.startswith(atomic.PARTIAL_PREFIX) and not entry.is_symlink():
            os.utime(entry, (then, then))


def held(path: Path) -> bool:
    """Say whether another handle holds the lock of an existing file."""
    if not path.exists():
        return False
    handle = locks.take(path)
    if handle is None:
        return True
    handle.close()
    return False
