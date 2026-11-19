"""The marker scan: no test is skipped, or expected to fail, without an issue link.

Why: PROMOTION.md section 5.1, Class A, "Skip-marker check: `skip` or `xfail` without an issue
link"; section 9: marking a failing test `skip` or `xfail` is how a test is turned off quietly,
and "marker scan requires an issue link" (issue #78). A skip that names an issue stays visible:
the issue says why, and until when.

Test matrix:

Equivalence classes:
  EC1  a skip with an issue link ("#12", or a URL ending in /issues/12) on its own lines
                                                                 no line
  EC2  a skip with no link                                       one line, file:line and the name;
       several: in line order, though the tree is walked level by level
  EC3  each form: pytest.skip(), pytest.xfail(), pytest.importorskip(), pytest.mark.skip,
       .skipif, .xfail (called, or bare as a decorator), unittest's skip, skipIf, skipUnless,
       expectedFailure, and a test case's skipTest()            each one line without a link
  EC4  a file with no skip                                       no line
  EC5  the repository's tests/                                   no line

Boundaries:
  B1  a call over several lines, the link on its last line       no line
  B2  the link on the line after the call                        one line: the link belongs to the
                                                                 call's own lines
  B3  a bare decorator `@pytest.mark.xfail`, no arguments        one line

Adversarial:
  A1  the name imported on its own (`from pytest import skip`, `from unittest import skip`)
      one line: an alias would hide every later call
  A2  "#" with no number, or a number with no "#" ("issue 12")    one line
  A3  a skip inside a string or a comment                        no line: it is not code

Not applicable: the Hebrew and document axes: the input is Python source.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"

# PROMOTION.md section 5.1, "Skip-marker check": the names that skip a test or expect it to fail.
SKIPS = frozenset({"skip", "skipif", "xfail", "importorskip", "skipIf", "skipUnless", "expectedFailure", "skipTest"})
# The modules from which such a name may be imported on its own.
SKIP_MODULES = frozenset({"pytest", "unittest", "_pytest.outcomes", "_pytest.mark"})
ISSUE_LINK = re.compile(r"#\d+\b|/issues/\d+\b")


def unlinked(source: str, name: str = "<source>") -> list[str]:
    """Return "name:line skip-name" for each skip in `source` with no issue link on its lines.

    Why: the scan itself, apart from the folder it is run on, so that each form can be tested
    on source made for it.

    Contract: a skip is an attribute that ends in one of SKIPS (`pytest.skip`,
    `pytest.mark.xfail`, `unittest.skip`, `self.skipTest`), judged on the lines of the call it
    is the function of, or on its own line where it is not called; and a `from` import of such
    a name from one of SKIP_MODULES. A link is "#" and digits, or "/issues/" and digits.
    Lines are counted from 1. Raises SyntaxError when `source` is not Python.
    """
    lines = source.splitlines()
    tree = ast.parse(source)
    called = {id(node.func): node for node in ast.walk(tree) if isinstance(node, ast.Call)}
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in SKIPS:
            span = called.get(id(node), node)
            text = "\n".join(lines[span.lineno - 1 : span.end_lineno])
            if not ISSUE_LINK.search(text):
                found.append((span.lineno, node.attr))
        elif isinstance(node, ast.ImportFrom) and node.module in SKIP_MODULES:
            found += [(node.lineno, alias.name) for alias in node.names if alias.name in SKIPS]
    return [f"{name}:{line} {skip}" for line, skip in sorted(found)]


def test_ec1_with_a_link() -> None:
    assert unlinked('pytest.skip("no network here, #12")') == []
    assert unlinked('pytest.skip("see https://github.com/o/r/issues/12")') == []
    assert unlinked('pytest.skip("no network")  # #12') == []


def test_ec2_without_a_link() -> None:
    assert unlinked('import pytest\n\npytest.skip("no network")', "t.py") == ["t.py:3 skip"]
    # The tree is walked level by level, so the call on line 3 is met before the one inside f.
    assert unlinked('def f():\n    pytest.skip("a")\npytest.xfail("b")') == ["<source>:2 skip", "<source>:3 xfail"]


def test_ec3_each_form() -> None:
    forms = {
        'pytest.skip("x")': "skip",
        'pytest.xfail("x")': "xfail",
        'pytest.importorskip("x")': "importorskip",
        '@pytest.mark.skip(reason="x")\ndef test(): pass': "skip",
        '@pytest.mark.skipif(True, reason="x")\ndef test(): pass': "skipif",
        '@pytest.mark.xfail(strict=True)\ndef test(): pass': "xfail",
        'pytestmark = pytest.mark.skip(reason="x")': "skip",
        '@unittest.skip("x")\ndef test(): pass': "skip",
        '@unittest.skipIf(True, "x")\ndef test(): pass': "skipIf",
        '@unittest.skipUnless(True, "x")\ndef test(): pass': "skipUnless",
        "@unittest.expectedFailure\ndef test(): pass": "expectedFailure",
        'self.skipTest("x")': "skipTest",
    }
    assert {source: unlinked(source) for source in forms} == {source: [f"<source>:1 {skip}"] for source, skip in forms.items()}


def test_ec4_no_skip() -> None:
    assert unlinked("def test():\n    assert skip_count() == 0\n") == []


def test_ec5_the_repository() -> None:
    files = sorted(TESTS.rglob("*.py"), key=lambda path: path.as_posix())
    found = [line for path in files for line in unlinked(path.read_text(encoding="utf-8"), path.relative_to(ROOT).as_posix())]
    assert found == []


def test_b1_a_call_over_several_lines() -> None:
    assert unlinked('pytest.skip(\n    "no network",\n    # #12\n)') == []


def test_b2_the_link_on_the_next_line() -> None:
    assert unlinked('pytest.skip("no network")\n# #12') == ["<source>:1 skip"]


def test_b3_a_bare_decorator() -> None:
    assert unlinked("@pytest.mark.xfail\ndef test(): pass") == ["<source>:1 xfail"]


def test_a1_imported_on_its_own() -> None:
    assert unlinked("from pytest import skip, raises") == ["<source>:1 skip"]
    assert unlinked("from unittest import skipIf as maybe") == ["<source>:1 skipIf"]
    assert unlinked("from pytest import raises") == []


def test_a2_not_a_link() -> None:
    assert unlinked('pytest.skip("see issue 12")') == ["<source>:1 skip"]
    assert unlinked('pytest.skip("see #")') == ["<source>:1 skip"]


def test_a3_in_a_string_or_a_comment() -> None:
    assert unlinked('text = "pytest.skip(no link)"  # pytest.mark.xfail') == []
