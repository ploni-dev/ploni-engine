"""Module suite for ploni/__main__.py: the command line run as a program of its own.

Why: pytest itself loads modules, so only a fresh interpreter shows whether importing Ploni
and running `selftest` pulls in a networking module (build-plan.md Phase 0, Gate: "`ploni
selftest` prints the model inventory and "offline OK"").

Matrix (`python -m ploni ...` started in the repository):
  M1  selftest                   exit 0; the last line is "offline OK"; the lines before it
                                 are the inventory of models/
  M2  a stub                     exit 2; nothing on the output; one line on the error stream
  M3  no command                 exit 2; a usage line on the error stream
  M4  the installed `ploni selftest`: the project installed as pyproject.toml says, offline,
      into a fresh environment that sees the packages of this one (setuptools among them, as
      requirements-dev.txt holds it)      exit 0; the last line is "offline OK"

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import os
import subprocess
import sys
import sysconfig
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# The seconds a program of these tests may take: an install into a fresh environment takes the
# longest, about ten on the laptop.
TIMEOUT_SECONDS = 120


def started(*command: str) -> subprocess.CompletedProcess[str]:
    """Run one program in the repository and return how it ended."""
    return subprocess.run([*command], cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)  # noqa: S603 fixed argv, no shell


def run(*argv: str) -> subprocess.CompletedProcess[str]:
    """Run `python -m ploni` with these arguments in the repository."""
    return started(sys.executable, "-m", "ploni", *argv)


def test_m1_selftest() -> None:
    done = run("selftest")
    lines = done.stdout.splitlines()
    assert done.returncode == 0, done.stdout + done.stderr
    assert lines[-1] == "offline OK"
    assert all(line.endswith(" bytes") or line.startswith("no models in ") for line in lines[:-1])


def test_m2_a_stub() -> None:
    done = run("scan")
    assert (done.returncode, done.stdout) == (2, "") and done.stderr.count("\n") == 1


def test_m3_no_command() -> None:
    done = run()
    assert done.returncode == 2 and "usage" in done.stderr


def test_m4_the_installed_command(tmp_path: Path) -> None:
    environment = tmp_path / "env"
    venv.create(environment, with_pip=False)
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    site = Path(started(str(python), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])").stdout.strip())
    (site / "outer.pth").write_text(sysconfig.get_paths()["purelib"] + "\n", encoding="utf-8")
    install = started(str(python), "-m", "pip", "install", "-q", "--no-index", "--no-build-isolation", "--no-deps", "-e", str(ROOT))
    assert install.returncode == 0, install.stdout + install.stderr
    done = started(str(scripts / ("ploni.exe" if os.name == "nt" else "ploni")), "selftest")
    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.splitlines()[-1] == "offline OK"
