"""The command line of Ploni.

Why: Phase 0 asks for a program that installs, imports and runs, with the command names of
the plan in place, and a `selftest` that shows which models are on the machine and that
nothing of Ploni loaded network code (build-plan.md Phase 0, Deliverable and Gate).

Contract: `ploni <command>` once installed (pyproject.toml), or `python -m ploni <command>`.
`selftest` prints one line per model revision under
the models folder, and one per name folder that holds files outside a revision folder, then "offline OK", and exits 0; or a line that names the networking
modules that are loaded, and exits 1. Each other command writes one line on the error
stream that says it is not built yet, and exits 2. No command, or an unknown one, is a usage
error (exit 2). An error that no code caught ends any command with one line and exit 4, and
Ctrl+C with one line and exit 130 (`main`).

Known limits:
- "offline" means: after every module of `ploni/` is imported in this process (by the list
  of imports at the top of this file, which a test holds to the modules on disk), none of the
  modules of the no-network list (NETWORK, the list of `pyproject.toml`) is loaded. It does
  not watch the network, and it does not see a module loaded later, by code a command runs.
  `_socket` and `_ssl`, the C modules under every network call, are not on the list yet: a
  module that imports them directly is not seen. They come with the PR of the longer
  no-network list (build-plan.md Phase 0, "Four stricter rules").
- The models folder is `models/` beside `ploni/`, the place of a development checkout. An
  installed program will have another; that comes with Phase 13.
- The inventory lists what is on disk; whether each model is in `docs/THIRD_PARTY.md` is the
  check of issue #28.
"""

import argparse
import io
import sys
from pathlib import Path
from typing import TextIO

# Every module of ploni/, imported by name so that `network_modules_loaded` sees what each one
# loads. A computed import is refused under ploni/ (tests/t8_privacy/test_imports.py), so the
# list is written out; a test holds it to the modules on disk.
from ploni import errors, types  # noqa: F401
from ploni.detect import base  # noqa: F401 imported so that selftest sees what it loads
from ploni.detect.deterministic import company_number, credit_card, iban, israeli_id  # noqa: F401 imported so that selftest sees what it loads
from ploni.safety import atomic, locks, logging, tempfiles  # noqa: F401

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
# A command stopped by an error no code caught: a code of its own, apart from selftest's 1 ("not
# offline") and the 2 of a stub or a usage error, so that a caller can tell a failure (issue #213).
# Not 3: on Windows a native crash that raises a C signal exits 3 too (measured in the review of
# 58bdd1b with faulthandler._sigsegv()).
FAILED = 4
# A command stopped by Ctrl+C: 128 + 2 (SIGINT), the code the shells give a program so stopped.
INTERRUPTED = 130


def inventory(models: Path) -> list[str]:
    """List the models on disk, one line per revision folder.

    Why: the first thing `selftest` shows, so that the person running it sees which models
    the program would load.

    Contract: one line per folder `models/<name>/<revision>/`, as "name revision N files B
    bytes", counting every file below it; and one line per name folder that holds files
    directly, as "name: N files outside a revision folder, B bytes". Sorted by name, a name's
    revisions before its loose files. A file at the top of the models folder is left out. A
    missing or empty models folder gives one line that says so.

    Known limits: a folder it cannot read counts as empty, with no warning; a link to a
    folder is followed and counted.
    """
    lines = []
    for name in sorted(path for path in models.glob("*") if path.is_dir()):
        for revision in sorted(path for path in name.glob("*") if path.is_dir()):
            files = [path for path in revision.rglob("*") if path.is_file()]
            lines.append(f"{name.name} {revision.name} {len(files)} files {sum(path.stat().st_size for path in files)} bytes")
        loose = [path for path in name.glob("*") if path.is_file()]
        if loose:
            lines.append(f"{name.name}: {len(loose)} files outside a revision folder, {sum(path.stat().st_size for path in loose)} bytes")
    return lines or [f"no models in {models}"]


def network_modules_loaded() -> list[str]:
    """Return the networking modules that are loaded in this process.

    Why: `CLAUDE.md`, Hard constraints: "No networking imports anywhere under ploni/". The lint
    rule and the T8 scan read the source; this shows it in the running program.

    Contract: every module of `ploni/` is imported when this module is (the imports at its
    top). Returns, sorted, each loaded module that is one of NETWORK or below one of them.

    Known limits: `_socket` and `_ssl` are not on the list yet (the module docstring).
    """
    return sorted(name for name in sys.modules if name in NETWORK or name.split(".")[0] in NETWORK)


def selftest(models: Path, out: TextIO) -> int:
    """Write the selftest report; return its exit code.

    Why: the gate of Phase 0 ("`ploni selftest` prints the model inventory and "offline OK"").

    Contract: the lines of `inventory`, then "offline OK" and 0, or "not offline: <names> is
    loaded" and 1.

    Known limits: what "offline" means is in the module docstring.
    """
    for line in inventory(models):
        out.write(line + "\n")
    loaded = network_modules_loaded()
    if loaded:
        out.write(f"not offline: {', '.join(loaded)} is loaded\n")
        return 1
    out.write("offline OK\n")
    return 0


def error_name(error: BaseException) -> str:
    """Return the name of an error's type, or `<value>` when it is no plain name of code.

    Why: `main` writes the name of an error no code caught, and must write one line with no
    document text in it. A class made at run time can have any name: a line break in it would
    start a second line, a metaclass can answer with any text or raise, and a name set to a
    subclass of str can format itself as any text.

    Contract: the type's own name, read past its metaclass as the log filter reads it
    (`type.__dict__["__name__"]`), when it is exactly a str of ASCII that is a Python
    identifier; otherwise `<value>`. Raises nothing.

    Known limits: an identifier taken from a document as a class name (`Jacob`) is written, as
    the log filter writes names of code (its Known limits).
    """
    name = type.__dict__["__name__"].__get__(type(error))
    return name if type(name) is str and name.isascii() and name.isidentifier() else "<value>"


def main(argv: list[str] | None = None) -> int:
    """Run one command; return its exit code.

    Why: the one entry point of the command line, so that a test can call it, and the function
    the installed `ploni` command calls (pyproject.toml).

    Contract: `argv` without the program name; None, as the installed command calls it, reads
    the arguments of the process (argparse's own default). Raises SystemExit(2) for no command, an
    unknown one, or an argument a command does not take, and SystemExit(0) for `--help`, as
    argparse does. The output stream writes a character it cannot encode as an escape, so
    that a Hebrew folder name does not stop `selftest` on a console of another code page.
    Effects on the process: first of all, before the arguments are read, the log filter of
    `ploni.safety.logging` is installed on the error stream, so every log record from then
    on, a library's too, is written by it, within the filter's Known limits: a record logged
    while ploni/ is imported, before `main` runs, is not, nor one of a library that adds a
    handler of its own later (issue #211). An error that a command raises and no code catches
    stops the command with FAILED and one line on the error stream, "ploni <command>: failed:
    <name>", the name as `error_name` gives it: the error's message, which may quote a
    document, is not written, nor its traceback (issue #213). Ctrl+C during a command stops it
    with INTERRUPTED and the line "ploni <command>: interrupted", also while an error was being
    handled, whose message Python would otherwise print with the interrupt's.

    Known limits: a stub and a usage error both exit 2. An argument argparse does not know,
    such as a file name, is repeated on the error stream: that is argparse writing, not a log
    record, and the filter does not see it. An exit raised inside a command passes through: its
    number is the exit code, and a text given to it is printed: a command must not call
    `sys.exit` with a text, and nothing checks that. Ctrl+C before the arguments are read is not caught.
    """
    logging.install(sys.stderr)
    parser = argparse.ArgumentParser(prog="ploni", description=__doc__.splitlines()[0] if __doc__ else None)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("selftest", *STUBS):
        commands.add_parser(name)
    command = parser.parse_args(argv).command
    try:
        if command == "selftest":
            if isinstance(sys.stdout, io.TextIOWrapper):
                sys.stdout.reconfigure(errors="backslashreplace")
            return selftest(MODELS, sys.stdout)
        sys.stderr.write(f"ploni {command}: not built yet\n")
        return NOT_BUILT
    except KeyboardInterrupt:
        sys.stderr.write(f"ploni {command}: interrupted\n")
        return INTERRUPTED
    except Exception as error:  # noqa: BLE001 the program's last catch: an error's message may quote a document, so only its type is written (issue #213)
        sys.stderr.write(f"ploni {command}: failed: {error_name(error)}\n")
        return FAILED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
