"""Fixtures shared by the test tiers."""

import logging
import warnings
from collections.abc import Iterator

import pytest


@pytest.fixture
def logging_restored() -> Iterator[None]:
    """Put the logging state of the process back after a test that installs a handler.

    Why: `ploni.safety.logging.install` changes process-wide state: the handlers and level of
    the root logger, the handlers of every named logger, and where warnings go. A test that
    leaves that behind changes what the next test, and pytest itself, sees.
    """
    root = logging.getLogger()
    named = {
        name: (list(logger.handlers), logger.propagate)
        for name, logger in logging.root.manager.loggerDict.items()
        if isinstance(logger, logging.Logger)
    }
    handlers, level, show = list(root.handlers), root.level, warnings.showwarning
    yield
    logging.captureWarnings(False)
    warnings.showwarning = show
    root.handlers[:] = handlers
    root.setLevel(level)
    for name, (kept, propagate) in named.items():
        logger = logging.getLogger(name)
        logger.handlers[:] = kept
        logger.propagate = propagate
