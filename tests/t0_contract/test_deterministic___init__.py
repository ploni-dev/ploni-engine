"""The package file of ploni/detect/deterministic/: its docstring and no code.

Why: importing one deterministic detector imports its package first, and the package will hold
some fifteen of them (build-plan.md section 4.7). A package file that holds no code loads none
of them, as ploni/detect/__init__.py holds none; a detector that reuses another's helpers
imports that module itself (the company number detector imports the Israeli ID detector's,
issue #33). The docstring itself is judged by tests/t0_contract/test_docstrings.py.

Test matrix:
  EC1  the file holds one statement, its docstring
"""

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[2] / "ploni" / "detect" / "deterministic" / "__init__.py"


def test_ec1_the_package_file_holds_its_docstring_only() -> None:
    tree = ast.parse(PACKAGE.read_text(encoding="utf-8"))
    assert len(tree.body) == 1
    assert ast.get_docstring(tree) is not None
