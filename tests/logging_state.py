"""Put the logging state of the process back after a test that installs a handler.

Why: `ploni.safety.logging.install` changes process-wide state: the handlers and level of the
root logger, the handlers of every named logger, and where warnings go. A test that leaves
that behind changes what the next test, and pytest itself, sees.

Contract: `restored` is a context manager. What it restores on leaving: the root logger's
handlers and level, the handlers and the propagate flag of every logger that existed on
entering, and the function that shows warnings.

Known limits: a logger first made inside the block keeps what the block gave it.
"""

import logging
import warnings
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def restored() -> Iterator[None]:
    """Run a block, then put the logging state back as it was on entering."""
    root = logging.getLogger()
    named = {
        name: (list(logger.handlers), logger.propagate)
        for name, logger in logging.root.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
    }
    handlers, level, show = list(root.handlers), root.level, warnings.showwarning
    try:
        yield
    finally:
        logging.captureWarnings(False)
        warnings.showwarning = show
        root.handlers[:] = handlers
        root.setLevel(level)
        for name, (kept, propagate) in named.items():
            logger = logging.getLogger(name)
            logger.handlers[:] = kept
            logger.propagate = propagate
