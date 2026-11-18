"""The command line of Ploni: `selftest`, and stubs for the commands later phases build.

Why: Phase 0 asks for a program that installs, imports and runs, with the command names of
the plan in place, and a `selftest` that shows which models are on the machine and that
nothing of Ploni loaded network code (build-plan.md Phase 0, Deliverable and Gate).

Contract: `python -m ploni <command>`. `selftest` prints one line per model revision under
the models folder, then "offline OK", and exits 0; or a line that names the networking
modules that are loaded, and exits 1. Each other command writes one line on the error
stream that says it is not built yet, and exits 2. No command, or an unknown one, is a usage
error (exit 2).

Known limits:
- "offline" means: after every module of `ploni/` is imported in this process (by the list
  of imports at the top of this file, which a test holds to the modules on disk), none of the
  modules of the no-network list (NETWORK, the list of `pyproject.toml`) is loaded. It does
  not watch the network, and it does not see a module loaded later, by code a command runs.
- The command is `python -m ploni`, not `ploni`: an installed `ploni` command needs an entry
  in `pyproject.toml`, which comes with issue #17.
- The models folder is `models/` beside `ploni/`, the place of a development checkout. An
  installed program will have another; that comes with Phase 13.
- The inventory lists what is on disk; whether each model is in `docs/THIRD_PARTY.md` is the
  check of issue #28.
"""

import argparse
import sys
from pathlib import Path
from typing import TextIO

# Every module of ploni/, imported by name so that `network_modules_loaded` sees what each one
# loads. A computed import is refused under ploni/ (tests/t8_privacy/test_imports.py), so the
# list is written out; a test holds it to the modules on disk.
from ploni.safety import logging, tempfiles  # noqa: F401

# The models folder of a development checkout (see Known limits).
MODELS = Path(__file__).resolve().parents[1] / "models"
# The no-network list of pyproject.toml, `banned-module-level-imports`; a test holds the two equal.
NETWORK = (
    "aiohttp", "ftplib", "http", "httpx", "imaplib", "poplib", "requests", "smtplib", "socket", "socketserver",
    "ssl", "telnetlib", "urllib", "urllib3", "websockets", "xmlrpc",
)  # fmt: skip
# build-plan.md Phase 0, Deliverable: the commands other than selftest, each built by a later phase.
STUBS = ("scan", "analyze", "review", "export", "verify", "restore", "rehydrate", "report", "usage")
NOT_BUILT = 2


def inventory(models: Path) -> list[str]:
    """List the model revisions on disk, one line each: name, revision, files, bytes.

    Why: the first thing `selftest` shows, so that the person running it sees which models
    the program would load.

    Contract: one line per folder `models/<name>/<revision>/`, sorted, counting every file
    below it. A name folder with no revision folder, and a file at the top, are left out.
    A missing or empty models folder gives one line that says so.
    """
    lines = []
    if models.is_dir():
        for revision in sorted(path for path in models.glob("*/*") if path.is_dir()):
            files = [path for path in revision.rglob("*") if path.is_file()]
            lines.append(f"{revision.parent.name} {revision.name} {len(files)} files {sum(path.stat().st_size for path in files)} bytes")
    return lines or [f"no models in {models}"]


def network_modules_loaded() -> list[str]:
    """Return the networking modules that are loaded in this process.

    Why: `CLAUDE.md`, Hard constraints: "No networking imports anywhere under ploni/". The lint
    rule and the T8 scan read the source; this shows it in the running program.

    Contract: every module of `ploni/` is imported when this module is (the imports at its
    top). Returns, sorted, each loaded module that is one of NETWORK or below one of them.
    """
    return sorted(name for name in sys.modules if name in NETWORK or name.split(".")[0] in NETWORK)


def selftest(models: Path, out: TextIO) -> int:
    """Print the inventory and whether Ploni is offline; return the exit code.

    Why: the gate of Phase 0 ("`ploni selftest` prints the model inventory and "offline OK"").

    Contract: the lines of `inventory`, then "offline OK" and 0, or "not offline: <names> is
    loaded" and 1.
    """
    for line in inventory(models):
        out.write(line + "\n")
    loaded = network_modules_loaded()
    if loaded:
        out.write(f"not offline: {', '.join(loaded)} is loaded\n")
        return 1
    out.write("offline OK\n")
    return 0


def main(argv: list[str]) -> int:
    """Run one command and return its exit code.

    Why: the one entry point of the command line, so that a test can call it.

    Contract: `argv` without the program name. Raises SystemExit(2) for no command or an
    unknown one, as argparse does.
    """
    parser = argparse.ArgumentParser(prog="ploni", description=__doc__.splitlines()[0] if __doc__ else None)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("selftest", *STUBS):
        commands.add_parser(name)
    command = parser.parse_args(argv).command
    if command == "selftest":
        return selftest(MODELS, sys.stdout)
    sys.stderr.write(f"ploni {command}: not built yet\n")
    return NOT_BUILT


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
