"""Bad PR 2 of the Phase 0 closing test: detect/ importing write/.

Why: issue #30. This file must be refused by CI and never merge.
"""

import ploni.write

__all__ = ["ploni"]
