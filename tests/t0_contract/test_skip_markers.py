"""The marker scan: no test is skipped, or expected to fail, without an issue link.

Why: PROMOTION.md section 5.1, Class A, "Skip-marker check: `skip` or `xfail` without an issue
link"; section 9: marking a failing test `skip` or `xfail` is how a test is turned off quietly,
and "marker scan requires an issue link" (issue #78). A skip that names an issue stays visible:
the issue says why, and until when.

Test matrix:

Equivalence classes:
  EC1  a skip with an issue link ("issue #12", or a URL ending in /issues/12) on its own lines
                                                                 no line
  EC2  a skip with no link                                       one line, file:line and the name;
       several: in line order, though the tree is walked level by level
  EC3  each form: pytest.skip(), pytest.xfail(), pytest.importorskip(), pytest.mark.skip,
       .skipif, .xfail (called, or bare as a decorator), unittest's skip, skipIf, skipUnless,
       expectedFailure, a test case's skipTest(), and raising unittest.SkipTest or pytest's
       Skipped                                                   each one line without a link
  EC4  a file with no skip                                       no line
  EC5  the repository's tests/                                   no line
  EC6  a skip named by a string: add_marker("skip"), applymarker("xfail"),
       getattr(pytest, "skip")                                   one line without a link

Boundaries:
  B1  a call over several lines, the link on its last line       no line
  B2  the link on the line after the call                        one line: the link belongs to the
                                                                 call's own lines
  B3  a bare decorator `@pytest.mark.xfail`, no arguments        one line
  B4  a form feed, a vertical tab or a Unicode line separator before the skip, the line above it
      holding a link                                             one line: Python does not end a
                                                                 line at them, so neither does the scan

Adversarial:
  A1  the name taken on its own: imported (`from pytest import skip`, `from unittest.case import
      skip`, `from unittest import SkipTest`), or given a name of its own (`skip = pytest.skip`)
      one line, link or not: an alias would hide every later call
  A2  "#" with no number, a number with no "#" ("issue 12"), or "#" and a number that is not
      called an issue ("case #2")                                one line
  A3  a skip inside a string or a comment                        no line: it is not code

Not applicable: the Hebrew and document axes: the input is Python source.
"""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "tests"

# PROMOTION.md section 5.1, "Skip-marker check": the names that skip a test or expect it to fail,
# and the exceptions whose raising skips one (unittest's SkipTest, pytest's Skipped).
SKIPS = frozenset(
    {"skip", "skipif", "xfail", "importorskip", "skipIf", "skipUnless", "expectedFailure", "skipTest", "SkipTest", "Skipped"}
)
# The modules from which such a name may be imported on its own.
SKIP_MODULES = frozenset({"pytest", "unittest", "unittest.case", "_pytest.outcomes", "_pytest.mark"})
# The calls that take a mark: pytest's add_marker and applymarker, as an object or by its name.
MARKING = frozenset({"add_marker", "applymarker"})
# The calls that take a skip by its name as text: the marking calls, and getattr.
BY_NAME = MARKING | {"getattr"}
ISSUE_LINK = re.compile(r"\bissue #\d+\b|/issues/\d+\b", re.IGNORECASE)
# Where Python ends a line (the language reference, "Physical lines"); str.splitlines() also
# ends one at a form feed, a vertical tab and Unicode separators, which would shift the count.
LINE_END = re.compile(r"\r\n|\r|\n")


def called_name(call: ast.Call) -> str:
    """Return the name a call is made by: `f` for f(), `g` for x.g(), "" for anything else.

    Why: a skip named by text is known by the call that takes it (add_marker, getattr).

    Contract: reads the function's own name only, not what it is bound to.

    Known limits: any function or method of that name, on any object, is taken for the real
    one (a test's own `add_marker`, too); that errs on the strict side.
    """
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return call.func.id if isinstance(call.func, ast.Name) else ""


def marks(tree: ast.AST) -> set[int]:
    """Return the ids of the nodes that stand where pytest or unittest takes a mark as it is.

    Why: a skip that is not called is a mark only in these places; anywhere else it is given a
    name of its own, or passed on, and every later use of it could skip with no link.

    Contract: the places are a decorator; the value of a `marks=` keyword, or an element of a
    list or tuple given there; and an argument, by position or by keyword, of a call in
    MARKING. Ids are those of the nodes of `tree`, as `id()` gives them.
    """
    placed: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            placed |= {id(decorator) for decorator in node.decorator_list}
        elif isinstance(node, ast.Call):
            given = [keyword.value for keyword in node.keywords if keyword.arg == "marks"]
            if called_name(node) in MARKING:
                given += [*node.args, *(keyword.value for keyword in node.keywords)]
            for value in given:
                placed.add(id(value))
                if isinstance(value, ast.List | ast.Tuple):
                    placed |= {id(element) for element in value.elts}
    return placed


def unlinked(source: str, name: str = "<source>") -> list[str]:
    """Return "name:line skip-name" for each skip in `source` with no issue link on its lines.

    Why: the scan itself, apart from the folder it is run on, so that each form can be tested
    on source made for it.

    Contract: a skip is an attribute that ends in one of SKIPS (`pytest.skip`,
    `pytest.mark.xfail`, `unittest.SkipTest`, `self.skipTest`), judged on the lines of the call
    it is the function of, or on its own lines where it is not called and stands as a mark
    (`marks`); a string equal to one of SKIPS given to a call in BY_NAME, by position or by
    keyword, judged on that call's lines; and, link or not, such an attribute anywhere else
    (given a name, put in a tuple or a dict, passed on), or such a name imported from one of
    SKIP_MODULES, since each hides every later use. A link is "issue #" and digits, in any
    case, or "/issues/" and digits. Lines are counted from 1, as Python counts them. Raises
    SyntaxError when `source` is not Python.

    Known limits: a link is not checked to name an issue that exists, or one still open. Only
    the source given is read: the run of EC5 reads `tests/`, so a `conftest.py` at the root of
    the repository would not be read (none exists). A skip reached any other way is not seen:
    a name held in a variable, `exec`, a module imported by `importlib`, a hook that skips by
    its return value. A function of the test's own that calls a skip, the link on that call,
    and is then called with no link, is not told apart from a helper that skips where the
    machine cannot make the case (`make_link` of test_safety_atomic.py).
    """
    lines = LINE_END.split(source)
    tree = ast.parse(source)
    called = {id(node.func): node for node in ast.walk(tree) if isinstance(node, ast.Call)}
    placed = marks(tree)
    judged: list[tuple[ast.expr, str]] = []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in SKIPS:
            if id(node) in called or id(node) in placed:
                judged.append((called.get(id(node), node), node.attr))
            else:
                found.append((node.lineno, node.attr))
        elif isinstance(node, ast.Call) and called_name(node) in BY_NAME:
            given = [*node.args, *(keyword.value for keyword in node.keywords)]
            judged += [(node, arg.value) for arg in given if isinstance(arg, ast.Constant) and arg.value in SKIPS]
        elif isinstance(node, ast.ImportFrom) and node.module in SKIP_MODULES:
            found += [(node.lineno, alias.name) for alias in node.names if alias.name in SKIPS]
    for span, skip in judged:
        if not ISSUE_LINK.search("\n".join(lines[span.lineno - 1 : span.end_lineno])):
            found.append((span.lineno, skip))
    return [f"{name}:{line} {skip}" for line, skip in sorted(found)]


def test_marks() -> None:
    tree = ast.parse("@d\ndef f(): pass\np(1, marks=[m], other=o)\ni.add_marker(a, append=b)\nx = y")
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and id(node) in marks(tree)}
    assert names == {"d", "m", "a", "b"}


def test_called_name() -> None:
    calls = [ast.parse(text).body[0].value for text in ("f()", "x.g()", "f()()")]  # type: ignore[attr-defined]
    assert [called_name(call) for call in calls] == ["f", "g", ""]


def test_ec1_with_a_link() -> None:
    assert unlinked('pytest.skip("no network here, issue #12")') == []
    assert unlinked('pytest.skip("see https://github.com/o/r/issues/12")') == []
    assert unlinked('pytest.skip("no network")  # issue #12') == []
    assert unlinked('pytest.skip("no network, Issue #12")') == []


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
        'raise unittest.SkipTest("x")': "SkipTest",
        'raise _pytest.outcomes.Skipped("x")': "Skipped",
    }
    assert {source: unlinked(source) for source in forms} == {source: [f"<source>:1 {skip}"] for source, skip in forms.items()}
    assert unlinked('raise unittest.SkipTest("x, issue #12")') == []


def test_ec4_no_skip() -> None:
    assert unlinked("def test():\n    assert skip_count() == 0\n") == []


def test_ec5_the_repository() -> None:
    files = sorted(TESTS.rglob("*.py"), key=lambda path: path.as_posix())
    found = [line for path in files for line in unlinked(path.read_text(encoding="utf-8"), path.relative_to(ROOT).as_posix())]
    assert found == []


def test_ec6_named_by_a_string() -> None:
    assert unlinked('item.add_marker("skip")') == ["<source>:1 skip"]
    assert unlinked('request.node.applymarker("xfail")') == ["<source>:1 xfail"]
    assert unlinked('getattr(pytest, "skip")("x")') == ["<source>:1 skip"]
    assert unlinked('item.add_marker("skip")  # issue #12') == []
    assert unlinked('item.add_marker("slow")') == []
    assert unlinked('item.add_marker(marker="skip")') == ["<source>:1 skip"]
    assert unlinked('request.applymarker(marker="xfail")') == ["<source>:1 xfail"]


def test_b1_a_call_over_several_lines() -> None:
    assert unlinked('pytest.skip(\n    "no network",\n    # issue #12\n)') == []


def test_b2_the_link_on_the_next_line() -> None:
    assert unlinked('pytest.skip("no network")\n# issue #12') == ["<source>:1 skip"]


def test_b3_a_bare_decorator() -> None:
    assert unlinked("@pytest.mark.xfail\ndef test(): pass") == ["<source>:1 xfail"]
    assert unlinked("@pytest.mark.xfail  # issue #12\ndef test(): pass") == []
    assert unlinked("pytest.param(1, marks=pytest.mark.xfail)  # issue #12") == []
    assert unlinked("pytest.param(1, marks=[pytest.mark.xfail])  # issue #12") == []
    assert unlinked("pytest.param(1, marks=[pytest.mark.xfail])") == ["<source>:1 xfail"]
    assert unlinked("item.add_marker(pytest.mark.skip)  # issue #12") == []


def test_b4_a_character_python_does_not_end_a_line_at() -> None:
    for character in ("\x0c", "\x0b", "\u2028"):
        # str.splitlines() would end a line at the character, so that line 2 holds the link.
        source = f'X = 1  # {character} issue #12\npytest.skip("no link")'
        assert unlinked(source) == ["<source>:2 skip"], repr(character)


def test_a1_taken_on_its_own() -> None:
    assert unlinked("from pytest import skip, raises") == ["<source>:1 skip"]
    assert unlinked("from unittest import skipIf as maybe") == ["<source>:1 skipIf"]
    assert unlinked("from unittest.case import skip") == ["<source>:1 skip"]
    assert unlinked("from unittest import SkipTest") == ["<source>:1 SkipTest"]
    assert unlinked("from _pytest.outcomes import Skipped") == ["<source>:1 Skipped"]
    assert unlinked('skip = pytest.skip  # issue #115\nskip("x")') == ["<source>:1 skip"]
    for source in (
        'skip, other = pytest.skip, 1  # issue #115\nskip("x")',
        'skip = pytest.skip if True else None  # issue #115\nskip("x")',
        'skip = functools.partial(pytest.skip)  # issue #115\nskip("x")',
        'S = {"s": pytest.skip}  # issue #115\nS["s"]("x")',
        'def t(skip=pytest.skip):  # issue #115\n    skip("x")',
    ):
        assert unlinked(source) == ["<source>:1 skip"], source
    assert unlinked("from pytest import raises") == []


def test_a2_not_a_link() -> None:
    assert unlinked('pytest.skip("see issue 12")') == ["<source>:1 skip"]
    assert unlinked('pytest.skip("see #")') == ["<source>:1 skip"]
    assert unlinked('pytest.skip("case #2 is broken")') == ["<source>:1 skip"]


def test_a3_in_a_string_or_a_comment() -> None:
    assert unlinked('text = "pytest.skip(no link)"  # pytest.mark.xfail') == []
