"""Make the answer key of E6: worksheets for the labellers, their labels side by side, the freeze.

Why: no script knows where the names of a real decision are. Two labellers mark every
document alone, a third pass settles where they differ, and the key is frozen by its hashes
before any detector is run (PREREGISTRATION.md, "The answer key"). This script does the
parts of that which need no reading.

Contract: `python -I label.py worksheets --corpus DIR` writes `DIR/worksheets/<id>.txt`
for every document of both piles. `python -I label.py compare --corpus DIR --a A --b B`
reads the two labellers' folders, writes `DIR/compare/<id>.tsv` with every difference and
every place to look at, and prints counts per document. `python -I label.py freeze
--corpus DIR` checks every file of `DIR/key` and writes their hashes to `key_sha256.tsv`
beside this script. Only counts and ids are printed; every file with text stays in DIR.

Known limits: a name that neither labeller marked, that stands after no title and shares
no word with a label, is in no list here.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]  # `python -I` drops the script folder

import real

import layers

Place = tuple[int, int, int]


def _kinds(gold: list) -> dict[Place, str]:
    """Return the kind of every label by its place; a name that is not counted has the kind `not_counted`."""
    return {(item.paragraph, item.start, item.end): next(iter(item.classes)) if item.counted else real.NOT_COUNTED for item in gold}


def differences(a: list, b: list) -> list[tuple[int, int, int, str, str]]:
    """List where two labellers differ.

    Why: the third pass decides exactly these, so nothing the two agree on is opened again.

    Contract: `a` and `b` are the labels of one document. Returns, in reading order,
    `(paragraph, start, end, kind in a, kind in b)` for every place that only one of them
    labels, the missing side being "", and for every place both label with another kind.
    Two labels that overlap without being the same place are two entries.
    """
    first, second = _kinds(a), _kinds(b)
    return [(*place, first.get(place, ""), second.get(place, "")) for place in sorted(set(first) | set(second)) if first.get(place) != second.get(place)]


def agreement(a: list, b: list) -> tuple[int, int]:
    """Count how far two labellers agree on what is counted.

    Why: PREREGISTRATION.md, prediction 10: a key from two readers who often differ is weak.

    Contract: returns `(same, either)`: the counted names both mark at the same place,
    and the counted names that at least one marks. A place one of them marks as not
    counted is not shared.
    """
    first = {place for place, kind in _kinds(a).items() if kind != real.NOT_COUNTED}
    second = {place for place, kind in _kinds(b).items() if kind != real.NOT_COUNTED}
    return len(first & second), len(first | second)


def places(paragraphs: list[str], gold: list) -> list[tuple[int, int, int, str]]:
    """List the places that may hold a name no label marks.

    Why: a reader misses a name most easily where it stands a second time. E1 looked at
    the same two lists; here they are made from the labels and from no detector's output.

    Contract: `gold` are the labels of one document, of either labeller, counted or not.
    Returns, in reading order, `(paragraph, start, end, why)` for every Hebrew word that
    shares no character with a label and that is a word of a labelled name, also behind
    attached letters (`carry`, by E5's `layers.propagate`), or stands right after a title
    or a group word (`title`, by E5's `layers.after_triggers`).
    """
    spans = [(item.paragraph, item.start, item.end) for item in gold]
    found = dict.fromkeys(layers.after_triggers(paragraphs, spans, titles=True), "title")
    found.update(dict.fromkeys(layers.propagate(paragraphs, spans), "carry"))
    free = [place for place in found if not any(place[0] == index and place[1] < end and start < place[2] for index, start, end in spans)]
    return sorted((*place, found[place]) for place in free)


def run_span(paragraph: str, start: int, end: int) -> tuple[int, int]:
    """Return the numbers of the first and the last run that a place touches, as the worksheet numbers them."""
    touched = [number for number, (low, high) in enumerate(real.runs(paragraph)) if low < end and start < high]
    return touched[0], touched[-1]


def write_worksheets(corpus_dir: Path) -> int:
    """Write the worksheet of every document of both piles and return how many were written."""
    folder = corpus_dir / "worksheets"
    folder.mkdir(exist_ok=True)
    for doc_id in real.ids():
        (folder / f"{doc_id}.txt").write_text(real.worksheet(real.read_document(corpus_dir, doc_id)), encoding="utf-8", newline="\n")
    return len(real.ids())


def compare(corpus_dir: Path, a_dir: Path, b_dir: Path) -> dict[str, dict[str, int]]:
    """Put the two labellers side by side, document by document.

    Why: what the third pass has to decide is written to one file per document, and the
    counts say how far the two agree.

    Contract: writes `compare/<id>.tsv` in the corpus folder: a header, then a line per
    difference (`why` is `differ`, with each labeller's kind) and per place to look at
    (`why` is `carry` or `title`), each with its paragraph, its first and last run and
    its text. Returns per document: the labels of `a` and of `b`, `same` and `either` as
    `agreement` counts them, and the numbers of differences and of places. Raises as
    `real.read_document` and `real.read_labels` do.
    """
    folder = corpus_dir / "compare"
    folder.mkdir(exist_ok=True)
    counts = {}
    for doc_id in real.ids():
        paragraphs = real.read_document(corpus_dir, doc_id)
        a, b = (real.read_labels(labels, doc_id, paragraphs) for labels in (a_dir, b_dir))
        differ = differences(a, b)
        look = places(paragraphs, [*a, *b])
        rows = [(*place, first, second, "differ") for *place, first, second in differ] + [(*place, "", "", why) for *place, why in look]
        lines = ["paragraph\tfirst\tlast\ttext\ta\tb\twhy"]
        for paragraph, start, end, first, second, why in sorted(rows):
            low, high = run_span(paragraphs[paragraph], start, end)
            lines.append(f"{paragraph}\t{low}\t{high}\t{paragraphs[paragraph][start:end]}\t{first}\t{second}\t{why}")
        (folder / f"{doc_id}.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        same, either = agreement(a, b)
        counts[doc_id] = {"a": len(a), "b": len(b), "same": same, "either": either, "differ": len(differ), "places": len(look)}
    return counts


def freeze(corpus_dir: Path) -> list[str]:
    """Return a line with the id and the SHA-256 of every key file.

    Why: the hashes are committed before any detector is run, so a key that was changed
    after a number was seen is refused (PREREGISTRATION.md, "Frozen").

    Contract: for every document of both piles, `key/<id>.tsv` is read and checked like
    any label file, so a key that cannot be scored is not frozen. Raises as
    `real.read_document` and `real.read_labels` do.
    """
    lines = []
    for doc_id in real.ids():
        real.read_labels(corpus_dir / "key", doc_id, real.read_document(corpus_dir, doc_id))
        lines.append(f"{doc_id}\t{hashlib.sha256((corpus_dir / 'key' / f'{doc_id}.tsv').read_bytes()).hexdigest()}")
    return lines


def main(arguments: argparse.Namespace) -> None:
    """Run one of the three commands and print counts only."""
    if arguments.command == "worksheets":
        print(f"worksheets written: {write_worksheets(arguments.corpus)}")
    elif arguments.command == "compare":
        counts = compare(arguments.corpus, arguments.a, arguments.b)
        for doc_id, row in counts.items():
            print(doc_id, *(f"{name} {value}" for name, value in row.items()))
        same, either = (sum(row[name] for row in counts.values()) for name in ("same", "either"))
        print(f"counted names both mark at the same place: {same} of {either}" + (f" = {same * 100 / either:.2f}%" if either else ""))
    else:
        lines = freeze(arguments.corpus)
        real.FROZEN.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print(f"key files frozen: {len(lines)}, written to {real.FROZEN.name}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("worksheets", "compare", "freeze"))
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--a", type=Path)
    parser.add_argument("--b", type=Path)
    parsed = parser.parse_args()
    if parsed.command == "compare" and not (parsed.a and parsed.b):
        parser.error("compare needs --a and --b")
    main(parsed)
