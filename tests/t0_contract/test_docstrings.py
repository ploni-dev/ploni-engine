"""The docstring check: every module, class and public function of ploni/ has its parts.

Why: `PROCESS.md` section 5.3 makes the presence of a docstring a test, not a style preference:
every module, class and public function has one with a `Why:` section, and a public function's
also has a `Contract:` section (issue #20; PR #16 added the Contract part). Presence only:
whether the reason is real is a review judgment, which no check can make.

Test matrix:

Equivalence classes:
  EC1  a module, a class and a public function with every part    no line
  EC2  a module, a class, a public function with no docstring     one line each, with the line
  EC3  a docstring with no `Why:`                                 one line
  EC4  a public function with `Why:` and no `Contract:`           one line; a class and a module
                                                                  need no Contract
  EC5  a private function, a dunder method, a nested function, a member of a private class
                                                                  not judged
  EC6  a public method of a public class, an async function, a class inside a public class
                                                                  judged as a function or class
  EC8  a private class                judged: "every class" (PROCESS.md section 5.3); its
                                      members are not
  EC9  a class or function under a top-level `if`, `try` (body, handler, else, finally),
       `try` with `except*`, or `with`                         judged as if at the top
  EC7  the repository: every file under ploni/ and scripts/, sub-packages too    no line

Boundaries:
  B1  an empty file                   one line: a module with no docstring
  B2  the name in another case ("the why: is", "CONTRACT:"), or with no colon after it    not a
      section
  B3  the section after another on one line ("Why: see the class. Contract: ...", as in
      `ploni/safety/logging.py`), and an indented section line    counted

Adversarial:
  A1  a string that is not the first statement looks like a docstring and is not one
  A2  a docstring in Hebrew with the two section names in it    found

Not applicable: the Hebrew axes of the test-matrix skill and the document axes, as the input is
Python source; A2 is the one case where Hebrew text could matter.

Known limits:
  - Only ploni/ and scripts/ (SCOPE). tests/ and experiments/ are not judged: Achia chose
    "Product + scripts" on 2026-11-19, asked which folders the check should judge, with the
    counts of that day (ploni/ 0 gaps, scripts/ 1, tests/ 559, experiments/ 746).
  - A section name in a sentence ("see Why: below") counts as the section.
  - "Public" is by name: no leading underscore. A name exported by `__all__` that begins with
    one is not judged; there is none today.
  - A property setter and each `@overload` stub count as functions of their own, so they need
    a docstring, though Python shows only the getter's and the implementation's. Neither shape
    is in ploni/ today.
  - What and Known limits (CLAUDE.md, "Docstrings") are not checked: the What is the first line,
    which every docstring has, and Known limits is not asked for by PROCESS.md section 5.3.
"""

import ast
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# The folders judged: Achia's answer of 2026-11-19, "Product + scripts" (Known limits).
SCOPE = ("ploni", "scripts")


def has_section(docstring: str, name: str) -> bool:
    """Say whether a docstring holds the section's name, capitalised as written, and a colon.

    Presence only, as PROCESS.md section 5.3 asks: a section may begin a line or follow another
    on the same line.
    """
    return f"{name}:" in docstring


def missing(node: ast.AST, contract: bool) -> list[str]:
    """Name the parts a module, class or function's docstring lacks."""
    docstring = ast.get_docstring(node)  # type: ignore[arg-type]
    if docstring is None:
        return ["no docstring"]
    parts = ["Why"] + (["Contract"] if contract else [])
    return [f"no {part}:" for part in parts if not has_section(docstring, part)]


def judged(body: list[ast.stmt], prefix: str = "") -> list[tuple[str, ast.AST, bool]]:
    """List the classes and public functions of a body, with whether each needs a Contract.

    A block (`if`, `try`, `with`) is looked into as if its statements stood in the body; the
    members of a private class are not judged.
    """
    found: list[tuple[str, ast.AST, bool]] = []
    for node in body:
        if isinstance(node, ast.ClassDef):
            found.append((prefix + node.name, node, False))
            if not node.name.startswith("_"):
                found.extend(judged(node.body, f"{prefix}{node.name}."))
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and not node.name.startswith("_"):
            found.append((prefix + node.name, node, True))
        elif isinstance(node, ast.If | ast.Try | ast.With):
            handlers = [handler.body for handler in getattr(node, "handlers", [])]
            blocks = [node.body, *handlers, getattr(node, "orelse", []), getattr(node, "finalbody", [])]
            found.extend(judged([statement for block in blocks for statement in block], prefix))
    return found


def problems(source: str, name: str) -> list[str]:
    """Return one line per missing part in a module's source: name, line, what is missing."""
    tree = ast.parse(source)
    lines = [f"{name}:1 module: {part}" for part in missing(tree, contract=False)]
    for qualified, node, contract in judged(tree.body):
        lines.extend(f"{name}:{node.lineno} {qualified}: {part}" for part in missing(node, contract))  # type: ignore[attr-defined]
    return lines


GOOD = '''"""A module.

Why: a reason.
"""


class Box:
    """A box.

    Why: a reason.
    """

    def open(self) -> None:
        """Open it.

        Why: a reason.

        Contract: none.
        """


def run() -> None:
    """Run.

    Why: a reason.

    Contract: none.
    """
'''


def test_ec1_every_part_present() -> None:
    assert problems(GOOD, "m.py") == []


def test_ec2_no_docstring() -> None:
    source = '"""M.\n\nWhy: r.\n"""\n\n\nclass Box:\n    pass\n\n\ndef run():\n    pass\n'
    assert problems(source, "m.py") == ["m.py:7 Box: no docstring", "m.py:11 run: no docstring"]
    assert problems("x = 1\n", "m.py") == ["m.py:1 module: no docstring"]


def test_ec3_no_why() -> None:
    source = '"""A module."""\n\n\nclass Box:\n    """A box."""\n'
    assert problems(source, "m.py") == ["m.py:1 module: no Why:", "m.py:4 Box: no Why:"]


def test_ec4_a_public_function_needs_a_contract() -> None:
    source = GOOD.replace("\n    Contract: none.\n", "\n")
    assert problems(source, "m.py") == ["m.py:22 run: no Contract:"]
    assert problems(GOOD.replace("        Contract: none.\n", ""), "m.py") == ["m.py:13 Box.open: no Contract:"]


def test_ec5_what_is_not_judged() -> None:
    source = textwrap.dedent('''\
        """M.

        Why: r.
        """


        def _private():
            pass


        class _Hidden:
            """H.

            Why: r.
            """

            def shown(self):
                pass


        def run():
            """R.

            Why: r.

            Contract: none.
            """

            def inner():
                pass


        class Box:
            """B.

            Why: r.
            """

            def __init__(self):
                pass
        ''')
    assert problems(source, "m.py") == []


def test_ec6_methods_async_and_inner_classes_are_judged() -> None:
    source = textwrap.dedent('''\
        """M.

        Why: r.
        """


        class Box:
            """B.

            Why: r.
            """

            def open(self):
                """O."""

            class Lid:
                pass


        async def fetch():
            """F.

            Why: r.
            """
        ''')
    assert problems(source, "m.py") == [
        "m.py:13 Box.open: no Why:",
        "m.py:13 Box.open: no Contract:",
        "m.py:16 Box.Lid: no docstring",
        "m.py:20 fetch: no Contract:",
    ]


def test_ec7_the_repository() -> None:
    files = sorted(path for folder in SCOPE for path in (ROOT / folder).rglob("*.py"))
    assert ROOT / "ploni" / "safety" / "atomic.py" in files and ROOT / "scripts" / "guard.py" in files
    found = [line for path in files for line in problems(path.read_text(encoding="utf-8"), path.relative_to(ROOT).as_posix())]
    assert found == []


def test_b1_an_empty_file() -> None:
    assert problems("", "m.py") == ["m.py:1 module: no docstring"]


def test_b2_a_section_name_in_another_case() -> None:
    assert problems('"""M.\n\nthe why: is here.\n"""\n', "m.py") == ["m.py:1 module: no Why:"]
    assert not has_section("WHY: r. CONTRACT: none.", "Contract")
    assert not has_section("Why it exists: a reason.", "Why")


def test_b3_a_section_after_another_and_an_indented_one() -> None:
    assert has_section("What.\n\n    Why: see the class. Contract: one line.", "Contract")
    assert has_section("What.\n\n    Why: a reason.", "Why")


def test_a1_a_string_that_is_not_the_first_statement() -> None:
    assert problems('x = 1\n"""M.\n\nWhy: r.\n"""\n', "m.py") == ["m.py:1 module: no docstring"]


def test_a2_a_docstring_in_hebrew() -> None:
    source = '"""מודול.\n\nWhy: סיבה.\n"""\n\n\ndef run():\n    """הרצה.\n\n    Why: סיבה.\n\n    Contract: אין.\n    """\n'
    assert problems(source, "m.py") == []


def test_ec8_a_private_class_is_judged() -> None:
    source = '"""M.\n\nWhy: r.\n"""\n\n\nclass _Cache:\n    def get(self):\n        pass\n'
    assert problems(source, "m.py") == ["m.py:7 _Cache: no docstring"]


def test_ec9_definitions_under_a_top_level_block() -> None:
    source = textwrap.dedent('''\
        """M.

        Why: r.
        """
        import sys

        if sys.platform == "win32":
            def link():
                pass
        else:
            class Link:
                pass
        try:
            import fast
        except ImportError:
            def slow():
                pass
        else:
            def quick():
                pass
        finally:
            def done():
                pass
        with open("x") as handle:
            def read():
                pass
        try:
            import fast
        except* ImportError:
            def star():
                pass
        ''')
    assert [line.split(": ")[0] for line in problems(source, "m.py")] == [
        "m.py:8 link", "m.py:11 Link", "m.py:16 slow", "m.py:19 quick", "m.py:22 done", "m.py:25 read", "m.py:30 star",
    ]
