"""Test matrix for ploni/__main__.py: the command line of Phase 0, with `selftest` and nine stubs.

The command run as a program of its own is tests/t4_integration/test_cli.py.

main. Equivalence classes:
  EC1  each of the nine stubs (scan, analyze, review, export, verify, restore, rehydrate,
       report, usage)                exit code 2; one line on the error stream that names the
                                     command and says it is not built yet; nothing on the output
  EC2  no command, or an unknown one    exit code 2 (argparse's usage error)
  EC3  selftest                      what `selftest` returns

inventory. Equivalence classes:
  EC4  models/<name>/<revision>/ with files    one line per revision: name, revision, number
                                     of files, bytes; sorted
  EC5  a name folder with no revision folder, a file at the top    left out
Boundaries:
  B1  no models folder               one line that says so
  B2  an empty models folder         one line that says so

network_modules_loaded. Equivalence classes:
  EC6  after every module of ploni/ is imported, in this process    no networking module is
                                     loaded
  EC7  a networking module loaded (one of the list, and a submodule of one)    named
  EC8  the list                      the same names as the no-network list of pyproject.toml

selftest. Equivalence classes:
  EC9  nothing loaded                the inventory, then "offline OK"; 0
  EC10 a networking module loaded    the inventory, then a line that names it; 1
"""

import io
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
    assert cli.network_modules_loaded() == []


def test_ec7_a_networking_module_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "socket", sys.modules.get("socket", object()))
    monkeypatch.setitem(sys.modules, "urllib.request", object())
    loaded = cli.network_modules_loaded()
    assert "socket" in loaded and "urllib.request" in loaded


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
