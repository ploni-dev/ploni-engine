"""Read every import of a package folder, for the tests that judge imports.

Why: three rules of the project are rules about imports: the layering (`PROCESS.md` section
5.2), no networking import under ploni/, and nothing under ploni/ imports eval/ (`CLAUDE.md`,
Hard constraints). A lint rule on top-level imports misses an import inside a function, so the
tests read every import of every file themselves, here, in one place.

Contract: `project_imports` reads a folder, `imported` one source text; `not_allowed`
judges imports against a table of allowed layers, and `from_packages` against a list of
packages that must not be imported. Module names are absolute and dotted; an import whose
name cannot be read is given as UNREADABLE in place of a name.

Known limits: source text handed to `exec` or `eval` is not read, and neither is code that
reaches the import system some other way (`pkgutil`, `runpy`, a loader object).
`from a import b` is given as `a` and as `a.b`, because `b` may be a module; a caller that
counts imports counts such a statement twice.
"""

import ast
from collections.abc import Collection, Iterable, Mapping
from importlib.util import resolve_name
from pathlib import Path
from typing import NamedTuple


# What Python imports as source on Windows (importlib.machinery.SOURCE_SUFFIXES there). Elsewhere
# it imports .py only; reading .pyw there too is the stricter side.
SOURCE_SUFFIXES = (".py", ".pyw")

# The functions that import a module named by their first argument: importlib.import_module
# and the built-in __import__. A call is known when it names the function by one of these
# names, on any receiver (importlib.__import__, tools.import_module).
IMPORT_CALLS = ("import_module", "__import__")

# What `imported` gives in place of a module name when a call of such a function names its
# module by anything but a string literal, and where such a function is named without being
# called. It is no dotted name, so no rule takes it for one.
UNREADABLE = "<unreadable>"


class Import(NamedTuple):
    """One module that one file may import.

    Why: a finding has to name the file and the line, and a rule has to know who imports.

    Contract: `file` is the path below the root given to `project_imports`, with forward
    slashes on every system; `line` is the first line of the import statement, or of the
    call or the mention that stands for one, counted from 1; `importer` is an absolute
    dotted name, and so is `module`, unless it is UNREADABLE.

    Known limits: `module` may name something that is no module, the `b` of `from a import b`.
    """

    file: str
    line: int
    importer: str
    module: str


def imported(source: str | bytes, importer: str, is_package: bool = False) -> list[tuple[int, str]]:
    """Return every module that the source may import, with the line of the statement.

    Why: the rules are about what a file can load, wherever in the file the import stands,
    so the whole syntax tree is walked and not only its top level.

    Contract:
        Args: source, the text of one Python file, or its bytes, which may carry a coding
            line or a byte order mark; importer, the dotted name of the module the source
            is; is_package, True when the source is the `__init__.py` of that name.
        Returns: (line, module) pairs sorted by line, then by name. `from a import b` gives
            `a` and `a.b`; `from a import *` gives `a`. A relative import is resolved
            against the importer. A call of `import_module` or `__import__` is given like
            an import statement when its name is a string literal, and as UNREADABLE when
            it is anything else. A relative name in a call is resolved against the
            importer's package when the call gives the bare name `__package__`, against
            the package the call gives when that is a string literal, and is UNREADABLE
            otherwise; so is a call of `__import__` with a level other than 0, and a call
            that spreads arguments with `*` or `**`. A place that names one of the two functions without calling it
            there is UNREADABLE too, see `_mentions`. The same import twice is given
            twice.
        Raises: SyntaxError when the source is not Python. ImportError when a relative
            import leaves the top package, or the importer has no package.

    Known limits: see the module docstring. A call is known by the name of the function
    alone, so a method of the project's own that is called `import_module` is read as one,
    and a string that is exactly one of the two names is read as a mention of it. What
    still gets past: a function name that is built when the program runs
    (`getattr(importlib, "import_" + "module")`), and a file that gives `__package__`
    another value before it calls `import_module(".x", __package__)`.
    """
    package = importer if is_package else importer.rpartition(".")[0]
    tree = ast.parse(source)
    found = [(line, UNREADABLE) for line in _mentions(tree)]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = resolve_name("." * node.level + (node.module or ""), package)
            found.append((node.lineno, base))
            found += [(node.lineno, f"{base}.{alias.name}") for alias in node.names if alias.name != "*"]
        elif isinstance(node, ast.Call) and (module := _called(node, package)) is not None:
            found.append((node.lineno, module))
    return sorted(found)


def _argument(node: ast.Call, position: int, keyword: str) -> ast.expr | None:
    """Return the argument of a call that stands at a position or is given by a keyword."""
    if len(node.args) > position:
        return node.args[position]
    return next((given.value for given in node.keywords if given.arg == keyword), None)


def _called(node: ast.Call, package: str) -> str | None:
    """Return the module that a call imports: None when the call is of no import function.

    A name that is a string literal and not relative is the module. A relative name is
    resolved as `import_module` resolves it: against the importer's own package when the
    call gives the bare name `__package__`, against the package the call gives when that is
    a string literal. Any other name, and a relative name with any other package or none,
    gives UNREADABLE. So does a call of `__import__` whose fifth argument, `level`, is
    anything but the number 0: a level makes the name relative to a package that the call
    takes from a mapping, which cannot be read. And so does a call that spreads arguments
    with `*` or `**`: they can carry a level or a package that is not written out.
    """
    function = node.func
    name = function.id if isinstance(function, ast.Name) else getattr(function, "attr", None)
    if name not in IMPORT_CALLS:
        return None
    given = _argument(node, 0, "name")
    spread = any(isinstance(item, ast.Starred) for item in node.args) or any(item.arg is None for item in node.keywords)
    if spread or not (isinstance(given, ast.Constant) and isinstance(given.value, str)):
        return UNREADABLE
    level = _argument(node, 4, "level")
    if level is not None and not (isinstance(level, ast.Constant) and level.value == 0):
        return UNREADABLE
    if not given.value.startswith("."):
        return given.value
    anchor = _argument(node, 1, "package")
    if isinstance(anchor, ast.Name) and anchor.id == "__package__":
        return resolve_name(given.value, package)
    if isinstance(anchor, ast.Constant) and isinstance(anchor.value, str):
        return resolve_name(given.value, anchor.value)
    return UNREADABLE


def _named(node: ast.AST) -> str | None:
    """Return what a node names when it is read: a name, an attribute, or a string's own text."""
    if isinstance(node, (ast.Name, ast.Attribute)) and isinstance(node.ctx, ast.Load):
        return node.id if isinstance(node, ast.Name) else node.attr
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _mentions(tree: ast.AST) -> list[int]:
    """Return the line of every place that names an import function without calling it there.

    Such a place hands the function on: it is assigned to another name, passed to `map` or
    `partial`, fetched by its name as a string with `getattr` or from `__builtins__`, or
    imported `as` another name. The call that follows cannot be told from any other call,
    so the place that names the function is what is given.
    """
    called = {id(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            renamed = (alias for alias in node.names if alias.asname not in (None, alias.name))
            lines += [node.lineno for alias in renamed if alias.name in IMPORT_CALLS]
        elif id(node) not in called and _named(node) in IMPORT_CALLS:
            lines.append(node.lineno)
    return lines


def project_imports(root: Path, package: str) -> list[Import]:
    """Return every import of every Python file under root/package.

    Why: a rule about imports holds only when no file is left out, so the folder is walked
    and no list of modules is kept by hand.

    Contract:
        Args: root, the folder that holds the package folder; package, the name of that
            folder, which is also the first part of every importer's name.
        Returns: the imports, ordered by file path and then by line. Only `.py` and `.pyw`
            files are read, with the suffix in any case of letters. No package folder gives
            an empty list.
        Raises: SyntaxError or ImportError as `imported` does, with the file named first in
            the message; OSError when a file cannot be read.

    Known limits: a file that Python would never import (a stray script in the folder) is
    read like any other.
    """
    found = []
    files = (file for file in (root / package).rglob("*") if file.suffix.lower() in SOURCE_SUFFIXES)
    for path in sorted(file.relative_to(root).as_posix() for file in files):
        parts = path.rpartition(".")[0].split("/")
        is_package = parts[-1] == "__init__"
        importer = ".".join(parts[:-1] if is_package else parts)
        try:
            lines = imported((root / path).read_bytes(), importer, is_package)
        except (SyntaxError, ImportError) as error:
            raise type(error)(f"{path}: {error}") from error
        found += [Import(path, line, importer, module) for line, module in lines]
    return found


def _layer(module: str) -> str:
    """Return the first two parts of a dotted name: the layer of `ploni.detect.fusion` is `ploni.detect`."""
    return ".".join(module.split(".")[:2])


def not_allowed(imports: Iterable[Import], table: Mapping[str, Collection[str]]) -> list[str]:
    """Return one line for every import that the table does not allow.

    Why: the table lists what a layer may import, so anything else inside the project is a
    finding, also a layer that was added after the table was written.

    Contract:
        Args: imports, as `project_imports` returns them; table, layer name to the layers
            it may import, each name two dotted parts such as `ploni.detect`.
        Returns: lines of the form `file:line: A may not import B`, in the order of the
            imports, each line once. An import is judged when the importer's layer has a
            row and the module lies in a layer of the same top package. Its own layer is
            always allowed.
        Raises: nothing.

    Known limits: an importer whose layer has no row is not judged. The bare top package
    (`import ploni`) is not judged, so attribute access after it is not seen. `from ploni
    import NAME` is judged as the layer `ploni.NAME`, also when NAME is no module.
    """
    found = []
    for item in imports:
        source, target = _layer(item.importer), _layer(item.module)
        inside = "." in target and target.split(".")[0] == source.split(".")[0]
        if source in table and inside and target != source and target not in table[source]:
            found.append(f"{item.file}:{item.line}: {source} may not import {target}")
    return list(dict.fromkeys(found))


def from_packages(imports: Iterable[Import], packages: Collection[str]) -> list[str]:
    """Return one line for every import whose top package is one of those given.

    Why: two rules of the project name packages that product code must never load, the
    networking modules and `eval/`. A module below such a package loads the package too, so
    the top name is what is compared.

    Contract:
        Args: imports, as `project_imports` returns them; packages, top-level names such as
            `socket`. UNREADABLE may be one of them, and then an import whose name could
            not be read is reported as well.
        Returns: lines of the form `file:line: imports NAME`, NAME being the top package,
            in the order of the imports, each line once.
        Raises: nothing.

    Known limits: only the first part of a module's name is compared. A project module
    with the name of such a package (`ploni.socket`) is not reported, and rightly so. A
    package that another package hands on under its own name is not reported either:
    `from logging.handlers import socket` binds the real `socket` module.
    """
    found = [
        f"{item.file}:{item.line}: imports {top}"
        for item in imports
        if (top := item.module.split(".")[0]) in packages
    ]
    return list(dict.fromkeys(found))
