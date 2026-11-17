"""Make the list of given names for E5's `list` step from the files of a public project.

Why: the `list` step marks a word because it is on a list of names. A list made from the
name banks of the corpora would hold exactly the names that were planted, and measure
nothing. So the list comes from outside: the given-name tables of the project
`alumag/hebrew-names` (MIT), fetched at a pinned commit by `scripts/download_e5_models.py`
(PREREGISTRATION.md, "Steps that are no model").

Contract: `python -I names_list.py --folder F --out FILE [--top N]`. F holds the ten
`dist.<group>.<gender>.first` files. Writes the names, one per line, sorted. With `--top`
only the N most common names of each file are taken.

Known limits: the tables are of the project's making; where its counts come from is not
stated in its files. A name of two words is taken apart into its words.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# The tables are UTF-16 with a byte order mark; a line is name, count, share, running share, rank.
ENCODING = "utf-16"
# A word of one letter is never taken as a name.
MIN_LETTERS = 2


def names_of(table: str, top: int | None) -> set[str]:
    """Return the names of one table.

    Why: the tables are ordered by how common a name is, so the same function gives the
    whole list and its shorter form.

    Contract: `table` is the text of one file; a line is the name, then tab-separated
    numbers, most common first. With `top`, only the first `top` lines that hold a name.
    Each word of a name of several words is a name. A word is kept when it is at least
    MIN_LETTERS long after quote marks at its two ends are taken off.
    """
    found: set[str] = set()
    lines = [line.split("\t")[0].strip() for line in table.splitlines()]
    for name in [line for line in lines if line][:top]:
        found |= {word.strip("'\"") for word in name.split()}
    return {word for word in found if len(word) >= MIN_LETTERS}


def build(folder: Path, top: int | None) -> list[str]:
    """Return the sorted names of every given-name table in a folder.

    Why: a name is on the list whichever table holds it; the step does not ask who a
    name belongs to.

    Contract: reads every file of `folder` whose name ends in `.first`. Raises
    FileNotFoundError when there is none: an empty list would turn the step off unseen.
    """
    files = sorted(folder.glob("*.first"))
    if not files:
        raise FileNotFoundError(f"no given-name table in {folder.name}")
    names: set[str] = set()
    for path in files:
        names |= names_of(path.read_text(encoding=ENCODING), top)
    return sorted(names)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--top", type=int)
    arguments = parser.parse_args()
    listed = build(arguments.folder, arguments.top)
    arguments.out.write_text("\n".join(listed) + "\n", encoding="utf-8")
    print(f"{len(listed)} names written")
