"""The package file of ploni/detect/: its docstring and no code.

Why: importing one detector imports its package first, and a detector of Phase 3 loads a
model. A package file that holds no code loads nothing, as ploni/safety/__init__.py holds
none. The docstring itself is judged by tests/t0_contract/test_docstrings.py.

Test matrix:
  EC1  the file holds one statement, its docstring
"""

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "ploni" / "detect" / "__init__.py"


def test_ec1_the_package_file_holds_its_docstring_only() -> None:
    tree = ast.parse(PACKAGE.read_text(encoding="utf-8"))
    assert len(tree.body) == 1
    assert ast.get_docstring(tree) is not None
