"""Test matrix for ploni/__main__.py: the command line of Phase 0, with `selftest` and nine stubs.

The command run as a program of its own is tests/t4_integration/test_cli.py.

main. Equivalence classes:
  EC1  each of the nine stubs (scan, analyze, review, export, verify, restore, rehydrate,
       report, usage)                exit code 2; one line on the error stream that names the
                                     command and says it is not built yet; nothing on the output
  EC2  no command, or an unknown one    exit code 2 (argparse's usage error)
  EC3  selftest                      what `selftest` returns
  EC15 no argument list given (the installed `ploni` command calls main so)    the arguments
       of the process, without the program name
  EC16 `--help`                      exit code 0; the output holds the first line of the module's
                                     docstring
  EC17 the command given as a text equal to "selftest" that is another object    selftest runs
  EC18 the module run as a program with `selftest` (`python -m ploni selftest`, in a fresh
       interpreter)                  exit code 0; the last line is "offline OK"; nothing on the
                                     error stream
  EC19 the default models folder     models/ at the top of the checkout
EC16 to EC19 kill the mutants of ploni/__main__.py that survived this file alone on 2026-11-24
(Cosmic Ray 8.9.0, issue #210): the folder, the help text, `is` for `==`, and the two lines that
start the program, which before only tests/t4_integration/test_cli.py reached.

inventory. Equivalence classes:
  EC4  models/<name>/<revision>/ with files    one line per revision: name, revision, number
                                     of files, bytes; sorted
  EC5  a name folder with no revision folder, a file at the top    left out
  EC12 files directly in a name folder, beside or instead of revision folders    one line for the
       name: how many files outside a revision folder, and their bytes
  EC14 a name folder it cannot read    left out, no error; the other folders are listed
  EC13 a Hebrew folder name, written to an output that cannot encode Hebrew (cp1252)    the line
       is written with the letters escaped; no error
Boundaries:
  B1  no models folder               one line that says so
  B2  an empty models folder         one line that says so

network_modules_loaded. Equivalence classes:
  EC6  after every module of ploni/ is imported, in a fresh interpreter    no networking module
                                     is loaded (pytest's own process holds modules other tests load)
  EC7  each module of the list loaded, and a submodule of each    named
  EC8  the list                      the same names as the no-network list of pyproject.toml
  EC11 the imports at the top of __main__    every module of ploni/ on disk but __main__ is among
                                     them, so that selftest sees what each one loads

selftest. Equivalence classes:
  EC9  nothing loaded                the inventory, then "offline OK"; 0
  EC10 a networking module loaded    the inventory, then a line that names it; 1
"""

import io
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

import ploni.__main__ as cli

ROOT = Path(__file__).resolve().parents[2]
STUBS = ["scan", "analyze", "review", "export", "verify", "restore", "rehydrate", "report", "usage"]


@pytest.mark.parametrize("command", STUBS)
def test_ec1_a_stub(command: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([command]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.count("\n") == 1 and command in captured.err and "not built yet" in captured.err


@pytest.mark.parametrize("argv", [[], ["unknown"]])
def test_ec2_no_command_or_an_unknown_one(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        cli.main(argv)
    assert caught.value.code == 2


def test_ec3_selftest_returns_what_selftest_returns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "MODELS", tmp_path)
    assert cli.main(["selftest"]) == cli.selftest(tmp_path, io.StringIO())


def test_ec16_help_shows_the_first_line_of_the_module_docstring(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        cli.main(["--help"])
    assert caught.value.code == 0
    assert cli.__doc__ is not None
    # argparse wraps the description to the width of the terminal, so the words are compared.
    assert " ".join(cli.__doc__.splitlines()[0].split()) in " ".join(capsys.readouterr().out.split())


def test_ec17_a_command_equal_to_selftest_that_is_another_object(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "MODELS", tmp_path)
    command = "".join(["self", "test"])
    assert command == "selftest" and command is not sys.intern("selftest")
    # What selftest returns depends on what this process has loaded (EC6), so the two are compared.
    assert cli.main([command]) == cli.selftest(tmp_path, io.StringIO()) != cli.NOT_BUILT


def test_ec18_the_module_run_as_a_program() -> None:
    done = subprocess.run([sys.executable, "-m", "ploni", "selftest"], cwd=ROOT, capture_output=True, text=True, timeout=60, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.splitlines()[-1] == "offline OK"
    # Nothing on the error stream: not a traceback, and not a warning Python gives when it compiles the file.
    assert done.stderr == ""


def test_ec19_the_default_models_folder() -> None:
    assert cli.MODELS == ROOT / "models"


def test_ec4_ec5_inventory(tmp_path: Path) -> None:
    (tmp_path / "b" / "rev2").mkdir(parents=True)
    (tmp_path / "b" / "rev2" / "model.safetensors").write_bytes(b"x" * 10)
    (tmp_path / "a" / "rev1" / "onnx").mkdir(parents=True)
    (tmp_path / "a" / "rev1" / "config.json").write_bytes(b"{}")
    (tmp_path / "a" / "rev1" / "onnx" / "model.onnx").write_bytes(b"y" * 5)
    (tmp_path / "empty").mkdir()
    (tmp_path / "README").write_text("x")
    assert cli.inventory(tmp_path) == ["a rev1 2 files 7 bytes", "b rev2 1 files 10 bytes"]


def test_b1_b2_no_models(tmp_path: Path) -> None:
    assert cli.inventory(tmp_path / "missing") == [f"no models in {tmp_path / 'missing'}"]
    assert cli.inventory(tmp_path) == [f"no models in {tmp_path}"]


def test_ec6_no_networking_module_after_ploni_is_imported() -> None:
    program = "import ploni.__main__ as cli; print(cli.network_modules_loaded())"
    done = subprocess.run([sys.executable, "-c", program], cwd=ROOT, capture_output=True, text=True, timeout=60, check=False)  # noqa: S603 fixed argv, no shell
    assert (done.returncode, done.stdout.strip()) == (0, "[]"), done.stderr


@pytest.mark.parametrize("name", cli.NETWORK)
def test_ec7_each_networking_module_is_named(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    monkeypatch.setitem(sys.modules, name, sys.modules.get(name, object()))
    monkeypatch.setitem(sys.modules, f"{name}.sub", object())
    loaded = cli.network_modules_loaded()
    assert name in loaded and f"{name}.sub" in loaded

def test_ec8_the_list_is_the_no_network_list() -> None:
    settings = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert sorted(cli.NETWORK) == sorted(settings["tool"]["ruff"]["lint"]["flake8-tidy-imports"]["banned-module-level-imports"])


def test_ec9_ec10_selftest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "m" / "r").mkdir(parents=True)
    (tmp_path / "m" / "r" / "w").write_bytes(b"1")
    out = io.StringIO()
    monkeypatch.setattr(cli, "network_modules_loaded", lambda: [])
    assert cli.selftest(tmp_path, out) == 0
    assert out.getvalue() == "m r 1 files 1 bytes\noffline OK\n"
    out = io.StringIO()
    monkeypatch.setattr(cli, "network_modules_loaded", lambda: ["socket"])
    assert cli.selftest(tmp_path, out) == 1
    assert out.getvalue() == "m r 1 files 1 bytes\nnot offline: socket is loaded\n"


def test_ec11_every_module_of_ploni_is_imported() -> None:
    on_disk = {
        ".".join(path.relative_to(ROOT).with_suffix("").parts)
        for path in (ROOT / "ploni").rglob("*.py")
        if path.name not in ("__init__.py", "__main__.py")
    }
    imported = {name for name, module in vars(cli).items() if getattr(module, "__name__", "").startswith("ploni.")}
    assert on_disk <= {getattr(vars(cli)[name], "__name__", "") for name in imported}


def test_ec12_files_directly_in_a_name_folder(tmp_path: Path) -> None:
    (tmp_path / "e2_onnx").mkdir()
    (tmp_path / "e2_onnx" / "ner_fp32.onnx").write_bytes(b"x" * 7)
    (tmp_path / "e2_onnx" / "ner_int8.onnx").write_bytes(b"y" * 3)
    (tmp_path / "m" / "rev").mkdir(parents=True)
    (tmp_path / "m" / "rev" / "w").write_bytes(b"z")
    (tmp_path / "m" / "stray.bin").write_bytes(b"s" * 4)
    assert cli.inventory(tmp_path) == [
        "e2_onnx: 2 files outside a revision folder, 10 bytes",
        "m rev 1 files 1 bytes",
        "m: 1 files outside a revision folder, 4 bytes",
    ]


def test_ec13_a_hebrew_name_on_an_output_that_cannot_encode_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "שמות" / "rev1").mkdir(parents=True)
    (tmp_path / "שמות" / "rev1" / "w").write_bytes(b"1")
    raw = io.BytesIO()
    out = io.TextIOWrapper(raw, encoding="cp1252")
    monkeypatch.setattr(cli.sys, "stdout", out)
    monkeypatch.setattr(cli, "MODELS", tmp_path)
    monkeypatch.setattr(cli, "network_modules_loaded", lambda: [])
    assert cli.main(["selftest"]) == 0
    out.flush()
    assert raw.getvalue().decode("cp1252").splitlines() == ["\\u05e9\\u05de\\u05d5\\u05ea rev1 1 files 1 bytes", "offline OK"]


# The full path, so that no other icacls on PATH is run.
ICACLS = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "icacls.exe")


def deny_reading(folder: Path) -> None:
    """Take away the right to list a folder: an ACL entry on Windows, mode 0 on POSIX.

    Skips the test where that cannot be done (root reads every folder).
    """
    if os.name == "nt":
        subprocess.run([ICACLS, str(folder), "/deny", "*S-1-1-0:(RD)"], check=True, capture_output=True)  # noqa: S603  fixed arguments, a test folder
    elif os.geteuid() == 0:
        pytest.skip("root reads every folder, issue #115")
    else:
        folder.chmod(0)


def allow_reading(folder: Path) -> None:
    """Undo deny_reading, so that pytest can remove the folder."""
    if os.name == "nt":
        subprocess.run([ICACLS, str(folder), "/remove:d", "*S-1-1-0"], check=True, capture_output=True)  # noqa: S603  fixed arguments, a test folder
    else:
        folder.chmod(0o700)


def test_ec14_a_name_folder_it_cannot_read(tmp_path: Path) -> None:
    (tmp_path / "locked" / "rev").mkdir(parents=True)
    (tmp_path / "m" / "rev").mkdir(parents=True)
    (tmp_path / "m" / "rev" / "w").write_bytes(b"z")
    deny_reading(tmp_path / "locked")
    try:
        assert cli.inventory(tmp_path) == ["m rev 1 files 1 bytes"]
    finally:
        allow_reading(tmp_path / "locked")


def test_ec15_no_argument_list_reads_the_process_arguments(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli.sys, "argv", ["ploni", "usage"])
    assert cli.main() == cli.NOT_BUILT
    assert capsys.readouterr().err == "ploni usage: not built yet\n"
