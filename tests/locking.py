"""Ask whether another handle holds the lock of a file, for the tests of the lock helper's callers.

Why: the product's helper takes a lock and keeps it (`ploni.safety.locks.take`); a test only
asks whether a file is held, and must not leave a file it did not find.

Contract: `held(path)` is False for a file that does not exist; otherwise it takes the lock
for a moment, gives it back, and says whether it could not. Raises OSError as `take` does,
for a path that cannot be opened (a folder).

Known limits: taking the lock for a moment makes a `hold` by someone else in that moment
fail; the tests that call this do not race it.
"""

from pathlib import Path

from ploni.safety import locks


def held(path: Path) -> bool:
    """Say whether another handle holds the lock of an existing file."""
    if not path.exists():
        return False
    handle = locks.take(path)
    if handle is None:
        return True
    handle.close()
    return False
