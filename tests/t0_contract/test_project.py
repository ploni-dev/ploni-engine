"""The project section of pyproject.toml: the installed `ploni` command, built by one pinned tool.

Why: `build-plan.md` Phase 0, Gate: "`ploni selftest` prints the model inventory and "offline
OK"". Until a project section exists only `python -m ploni selftest` works. Achia decided on
2026-11-20 to build it as asked: "Add a project section to pyproject.toml with a `ploni`
command, so `ploni selftest` works as the Phase 0 gate words it (today only `python -m ploni
selftest` works). Adds one build tool, setuptools, pinned with its hash." These tests pin what
that answer allows and no more.

Test matrix:

Equivalence classes:
  EC1  the command: one script, `ploni`, that calls `ploni.__main__:main`, which exists
  EC2  the build tool: setuptools alone, pinned to one version, the same version pinned and
       hashed in requirements-dev.txt
  EC3  what is installed: the `ploni` package and its sub-packages only, not tests/,
       scripts/, eval/ or experiments/
  EC4  the product's dependencies: none, as requirements.txt holds none
  EC5  the Python version: 3.13 (build-plan.md Phase 0)

Not applicable: boundaries, the Hebrew axes and the document axes of the test-matrix skill:
the input is one fixed configuration file.

Known limits:
  - The tests read the file; they do not build or install the package. The installed command
    was run by hand on the laptop, and its output is in the PR that added this file.
"""

import importlib
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
# The one build tool of Achia's answer of 2026-11-20.
BUILD_TOOL = "setuptools"


def test_ec1_the_ploni_command() -> None:
    assert PROJECT["project"]["scripts"] == {"ploni": "ploni.__main__:main"}
    module, _, name = PROJECT["project"]["scripts"]["ploni"].partition(":")
    assert callable(getattr(importlib.import_module(module), name))


def test_ec2_one_build_tool_pinned_as_in_requirements_dev() -> None:
    build = PROJECT["build-system"]
    assert build["build-backend"] == "setuptools.build_meta"
    [requirement] = build["requires"]
    name, _, version = requirement.partition("==")
    assert name == BUILD_TOOL and re.fullmatch(r"[0-9]+(\.[0-9]+)*", version)
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    assert re.search(rf"^{BUILD_TOOL}=={re.escape(version)} \\\n    --hash=sha256:[0-9a-f]{{64}}", dev, re.MULTILINE)


def test_ec3_only_the_ploni_package_is_installed() -> None:
    assert PROJECT["tool"]["setuptools"]["packages"]["find"] == {"include": ["ploni", "ploni.*"]}


def test_ec4_no_dependency() -> None:
    assert PROJECT["project"]["dependencies"] == []


def test_ec5_python_3_13() -> None:
    assert PROJECT["project"]["requires-python"] == ">=3.13"
