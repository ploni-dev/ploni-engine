"""Bad PR 1 of the Phase 0 closing test: a networking import under ploni/.

Why: issue #30. This file must be refused by CI and never merge.
"""

import requests

__all__ = ["requests"]
