"""Test matrix for tests/conftest.py: on GitHub, a failed test names its test and line, never its values.

Why: Achia, 2026-11-27, issue #32, "Hide them on GitHub (Recommended)": "On GitHub, a failing test
shows one short line (which test, which line) and not the values. On the laptop, nothing changes:
full detail." Each case runs pytest in this process on a small test file of its own, which fails
on an invented number, and reads only whether the number appears in what pytest printed.

Test matrix:
  EC1 GITHUB_ACTIONS "true": an assert on the number (a parametrized test, its id a word), a
      fixture that raises with it, a test that prints it and fails, pytest.fail with it, and one
      passing test             exit 1; the number nowhere in the output; each failed test named
                               on a FAILED or ERROR line; the assert's file and line printed
  EC2 GITHUB_ACTIONS not set   the output as with no conftest at all, the number in it
  EC3 GITHUB_ACTIONS "false", "1", "", "TRUE"    the same: only "true" hides
  EC4 a test file that fails to import, with the number in its error, beside a passing one,
      under "true"             exit 2, the error still an error; the number nowhere; the file
                               named on an ERROR line
  EC5 this repository's own test run               tests/conftest.py is one of its plugins
"""

import importlib
import re
import sys
from pathlib import Path

import pytest

# An invented number, made here; any digits would do, none is written in this file.
NUMBER = "".join(str((i * 7 + 4) % 10) for i in range(9))
ON_GITHUB = "GITHUB_ACTIONS"
FAILING = '''
import pytest

NUMBER = "".join(str((i * 7 + 4) % 10) for i in range(9))


@pytest.mark.parametrize("number", [NUMBER], ids=["invented"])
def test_assert(number):
    assert number == "0"


@pytest.fixture
def broken():
    raise ValueError("cannot use " + NUMBER)


def test_setup(broken):
    pass


def test_printed():
    print("the number", NUMBER)
    assert False


def test_failed():
    pytest.fail("refused " + NUMBER)


def test_passes():
    assert NUMBER
'''
# The line of FAILING that holds the assert on the number, counted from 1.
ASSERT_LINE = FAILING.splitlines().index('    assert number == "0"') + 1
BROKEN = 'NUMBER = "".join(str((i * 7 + 4) % 10) for i in range(9))\nraise ValueError("no import of " + NUMBER)\n'
TIMING = re.compile(r" in [0-9.]+s")
# The modules of the small test files, as pytest's importlib mode names them.
SMALL_FILES = ("test_fail", "test_ok")


def drop_imported() -> None:
    """Forget the modules of the small test files, so that the next run imports them again."""
    for name in SMALL_FILES:
        sys.modules.pop(name, None)


def run(tmp_path: Path, capsys: pytest.CaptureFixture[str], source: str, with_conftest: bool, value: str | None) -> tuple[int, str]:
    """Run pytest in this process on the test files of tmp_path, GITHUB_ACTIONS set to `value` (None: unset) for that run only; return its exit code and output.

    The variable is put back before this returns, so that the report of the test calling this is
    made as the outer run's own setting says. The modules the run imports are dropped from
    sys.modules before and after it: pytest names them by their file alone, so a later run would
    otherwise get an earlier run's module, and a file that fails to import would not fail again.
    """
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    path = tmp_path / "test_fail.py"
    path.write_text(source, encoding="utf-8")
    plugins = [importlib.import_module("tests.conftest")] if with_conftest else []
    args = ["-q", "-p", "no:cacheprovider", "--import-mode=importlib", "--rootdir", str(tmp_path), "."]
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(tmp_path)
        if value is None:
            patch.delenv(ON_GITHUB, raising=False)
        else:
            patch.setenv(ON_GITHUB, value)
        drop_imported()
        code = pytest.main(args, plugins=plugins)
        drop_imported()
    out, err = capsys.readouterr()
    return int(code), TIMING.sub("", out + err)


def test_ec1_on_github_the_values_are_hidden(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, output = run(tmp_path, capsys, FAILING, with_conftest=True, value="true")
    assert code == 1
    assert NUMBER not in output
    named = {line.split(" ")[1] for line in output.splitlines() if line.startswith(("FAILED ", "ERROR "))}
    assert named == {f"test_fail.py::{name}" for name in ("test_assert[invented]", "test_setup", "test_printed", "test_failed")}
    assert f"test_fail.py:{ASSERT_LINE}: " in output


def test_ec2_on_the_laptop_nothing_changes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with_it = run(tmp_path, capsys, FAILING, with_conftest=True, value=None)
    without = run(tmp_path, capsys, FAILING, with_conftest=False, value=None)
    assert with_it == without
    assert NUMBER in with_it[1]


@pytest.mark.parametrize("value", ["false", "1", "", "TRUE"])
def test_ec3_only_true_hides(tmp_path: Path, capsys: pytest.CaptureFixture[str], value: str) -> None:
    assert run(tmp_path, capsys, FAILING, True, value) == run(tmp_path, capsys, FAILING, False, value)


def test_ec4_a_file_that_fails_to_import(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    pass\n", encoding="utf-8")
    code, output = run(tmp_path, capsys, BROKEN, with_conftest=True, value="true")
    assert code == 2
    assert NUMBER not in output
    assert "ERROR test_fail.py" in output



def test_ec5_this_repository_loads_it(pytestconfig: pytest.Config) -> None:
    files = {Path(getattr(plugin, "__file__", "") or "").resolve() for plugin in pytestconfig.pluginmanager.get_plugins()}
    assert Path(__file__).resolve().parents[1] / "conftest.py" in files
