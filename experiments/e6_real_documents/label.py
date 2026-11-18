"""Make the answer key of E6: worksheets for the labellers, their labels side by side, the freeze.

Why: no script knows where the names of a real decision are. Two labellers mark every
document alone, a third pass settles where they differ, and the key is frozen by its hashes
before any detector is run (PREREGISTRATION.md, "The answer key"). This script does the
parts of that which need no reading, and checks the third pass against its own rule.

Contract: `python -I label.py COMMAND --corpus DIR [--a A] [--b B]`.
`worksheets` writes `DIR/worksheets/<id>.txt` for every document of both piles.
`check --a FOLDER` says, per document, how many labels its file in FOLDER holds or which
lines do not fit the text. `compare --a A --b B` reads the two labellers' folders, writes
`DIR/compare/<id>.tsv` with every difference and every place to look at, and prints counts
per document. `freeze --a A --b B` checks every file of `DIR/key` against the two labellers
and the lists, and writes the hashes to `key_sha256.tsv` beside this script; it refuses
when that file is already there. Only counts, ids and line numbers are printed; every file
with text stays in DIR.

Known limits: a name that neither labeller marked, that stands after no title and shares
no word with a label, is in no list here. `freeze` checks where the key's labels stand and
of which kind they are, not which person each is given to. It cannot tell where one name
ends and the next begins: a listed word wrongly added as a name of its own, or a listed
word or a label of one labeller wrongly joined to the name before it, passes.
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
# E1's list of titles for this cross-check held three that the list of E5's `titles` step
# lacks (review of PR #99, finding 4). They are looked for here only: the step under test
# keeps its own list. The forms behind ל are spelled out, because `layers.is_trigger` takes
# the article off only for words of its own.
MORE_TITLES = frozenset({"הנשיא", "הנשיאה", "כב'", "לנשיא", "לנשיאה", "ולנשיא", "ולנשיאה"})


def _kinds(gold: list) -> dict[Place, str]:
    """Return the kind of every label by its place; a name that is not counted has the kind `not_counted`."""
    return {(item.paragraph, item.start, item.end): next(iter(item.classes)) if item.counted else real.NOT_COUNTED for item in gold}


def _shares(place: tuple, others: list) -> bool:
    """Say whether a place shares a character with one of the others; each begins with paragraph, start, end."""
    return any(place[0] == other[0] and place[1] < other[2] and other[1] < place[2] for other in others)


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


def person_splits(a: list, b: list) -> list[tuple[int, int, int, str, str]]:
    """List the places where the two labellers do not divide the names among the same people.

    Why: the row `lonely` counts people who are named once, from the person keys of the
    answer key. Two labellers can mark the same places and still see one person where the
    other sees two; by place and kind that is no difference.

    Contract: looks at the places both label as counted. Returns, in reading order,
    `(paragraph, start, end, person in a, person in b)` for every place of a person of
    one labeller whose places the other gives to more than one person. The keys
    themselves need not be the same in the two files.
    """
    first = {(item.paragraph, item.start, item.end): item.person for item in a if item.counted}
    second = {(item.paragraph, item.start, item.end): item.person for item in b if item.counted}
    shared = sorted(set(first) & set(second))

    def split(mine: dict, theirs: dict) -> set:
        groups: dict[str, set[str]] = {}
        for place in shared:
            groups.setdefault(mine[place], set()).add(theirs[place])
        return {place for place in shared if len(groups[mine[place]]) > 1}

    flagged = split(first, second) | split(second, first)
    return [(*place, first[place], second[place]) for place in shared if place in flagged]


def _name_words(gold: list) -> set[str]:
    """Return the words of the labelled names that can lead to another mention.

    Contract: every Hebrew word inside a label's own text, so that a name labelled
    behind attached letters gives its bare form. Left out, as in E5's `carry`: name
    particles, initials, words of one letter and the trigger words.
    """
    found = {text for item in gold for _, _, text in layers.words(item.name)}
    triggers = layers.TITLE_TRIGGERS | layers.GROUP_TRIGGERS
    return {
        word for word in found
        if len(word) >= 2 and word not in layers.NAME_PARTICLES and not layers.INITIAL.fullmatch(word) and not layers.is_trigger(word, triggers)
    }  # fmt: skip


def _after_more_titles(paragraphs: list[str]) -> list[Place]:
    """Return the word right after each title of MORE_TITLES, as `layers.after_triggers` does for its own.

    Contract: the word after the title, with nothing but white space between, and the
    word after that when the first is an initial or a name particle (`הנשיא א' ברק`), so
    that every word of the name is a listed place.
    """
    found = []
    for index, paragraph in enumerate(paragraphs):
        tokens = layers.words(paragraph)
        for position, title in enumerate(tokens[:-1]):
            first = tokens[position + 1]
            if not layers.is_trigger(title[2], MORE_TITLES) or paragraph[title[1] : first[0]].strip():
                continue
            found.append((index, first[0], first[1]))
            joins = first[2] in layers.NAME_PARTICLES or layers.INITIAL.fullmatch(first[2])
            if joins and position + 2 < len(tokens) and not paragraph[first[1] : tokens[position + 2][0]].strip():
                found.append((index, tokens[position + 2][0], tokens[position + 2][1]))
    return found


def places(paragraphs: list[str], gold: list) -> list[tuple[int, int, int, str]]:
    """List the places that may hold a name no label marks.

    Why: a reader misses a name most easily where it stands a second time. E1 looked at
    the same two lists; here they are made from the labels and from no detector's output.

    Contract: `gold` are the labels of one document, of either labeller, counted or not.
    Returns, in reading order, `(paragraph, start, end, why)` for every Hebrew word that
    shares no character with a label and that is a word of a labelled name, bare or
    behind attached letters (`carry`: the words of the labels' own text, looked for by
    E5's `layers.from_list`), or stands right after a title or a group word (`title`:
    E5's `layers.after_triggers`, and the titles of MORE_TITLES).

    Known limits: these are the places E5's `carry` and `titles` steps reach, and three
    titles more. A missed name anywhere else is not listed (PREREGISTRATION.md, "What
    the key cannot be trusted for").
    """
    spans = [(item.paragraph, item.start, item.end) for item in gold]
    found = dict.fromkeys([*layers.after_triggers(paragraphs, spans, titles=True), *_after_more_titles(paragraphs)], "title")
    found.update(dict.fromkeys(layers.from_list(paragraphs, spans, _name_words(gold)), "carry"))
    return sorted((*place, why) for place, why in found.items() if not _shares(place, spans))


def key_faults(paragraphs: list[str], a: list, b: list, key: list) -> tuple[int, int]:
    """Count the labels of a key that break the rule of the third pass.

    Why: the third pass decides the differences and the listed places and "adds nothing
    of its own" (PREREGISTRATION.md, "How the two are put together"). That is checked
    here, by a script, before the key is frozen.

    Contract: returns two counts that are both 0 for a key made by the rule. The first
    counts the labels of the key that the third pass had no ground for. A label of
    the key that covers no label both labellers have needs to share a character with
    a label of either labeller or with a listed place (`places`): it may then hold the
    whole name, which is often longer than the one word a list gives. A label of the
    key that covers a label both have is held word by word: every run of characters
    between spaces in it, with a letter in it, must share a character with a label of
    either labeller or with a listed place; a hyphen that stands by itself is no such
    run. The
    second: places that both labellers label with the same kind and that the key does
    not keep. Such a label is kept when one label of the key, of that kind, covers all
    of it and covers no other label that both have. So the key may make it longer by
    a listed word (an initial before a surname, a second surname), and may not drop
    it, cut it, give it another kind or join it with another.

    Known limits: a label of the key at a listed place, or at a label only one
    labeller has, can reach as far as the third pass wrote it. And the check cannot
    tell where one name ends and the next begins. A
    listed word that belongs to the name before it can be added as a label of its
    own; and a listed word, or a label only one labeller has, can be joined to the
    name before it though it is another person's. It looks at places and kinds, not
    at person keys.
    """
    first, second, final = _kinds(a), _kinds(b), _kinds(key)
    allowed = [*first, *second, *places(paragraphs, [*a, *b])]
    agreed = {place: kind for place, kind in first.items() if second.get(place) == kind}

    def covers(outer: Place, inner: Place) -> bool:
        return outer[0] == inner[0] and outer[1] <= inner[1] and inner[2] <= outer[2]

    def strange(place: Place) -> bool:
        if not any(covers(place, more) for more in agreed):
            return not _shares(place, allowed)
        index, start, end = place
        text = paragraphs[index][start:end]
        parts = [(index, start + low, start + high) for low, high in real.runs(text) if any(character.isalpha() for character in text[low:high])]
        return any(not _shares(part, allowed) for part in parts)

    def kept(place: Place, kind: str) -> bool:
        return any(kind == other_kind and covers(other, place) and sum(covers(other, more) for more in agreed) == 1 for other, other_kind in final.items())

    outside = sum(strange(place) for place in final)
    changed = sum(not kept(place, kind) for place, kind in agreed.items())
    return outside, changed


def run_span(paragraph: str, start: int, end: int) -> tuple[int, int]:
    """Return the numbers of the first and the last run that a place touches.

    Why: the third pass writes a label by run numbers, so the compare file gives them
    as the worksheet does.
    """
    touched = [number for number, (low, high) in enumerate(real.runs(paragraph)) if low < end and start < high]
    return touched[0], touched[-1]


def write_worksheets(corpus_dir: Path) -> int:
    """Write the worksheet of every document of both piles and return how many were written.

    Why: the labellers read the worksheets and nothing else, so that every place they
    name is a place in the text the detectors get.
    """
    folder = corpus_dir / "worksheets"
    folder.mkdir(exist_ok=True)
    for doc_id in real.ids():
        (folder / f"{doc_id}.txt").write_text(real.worksheet(real.read_document(corpus_dir, doc_id)), encoding="utf-8", newline="\n")
    return len(real.ids())


def check(corpus_dir: Path, folder: Path) -> dict[str, str]:
    """Say, per document, whether its label file in a folder fits the text.

    Why: a labeller runs this on their own folder and mends the lines it names, before
    the two are put side by side.

    Contract: returns, for every document of both piles, `<n> labels`, or the message of
    the error its file gives: the bad lines by number, or that there is no file. No file
    stops the others from being checked.
    """
    found = {}
    for doc_id in real.ids():
        try:
            found[doc_id] = f"{len(real.read_labels(folder, doc_id, real.read_document(corpus_dir, doc_id)))} labels"
        except (real.LabelError, real.CorpusError) as error:
            found[doc_id] = str(error)
    return found


def compare(corpus_dir: Path, a_dir: Path, b_dir: Path) -> dict[str, dict[str, int]]:
    """Put the two labellers side by side, document by document.

    Why: what the third pass has to decide is written to one file per document, and the
    counts say how far the two agree.

    Contract: writes `compare/<id>.tsv` in the corpus folder: a header, then a line per
    difference (`why` is `differ`, with each labeller's kind), per place where the two
    divide the names among people in another way (`person`, with each labeller's key)
    and per place to look at (`carry` or `title`), each with its paragraph, its first
    and last run and its text, written with one space where the text has other white
    space, as a label is. Returns per document: the labels of `a` and of `b`,
    `same` and `either` as `agreement` counts them, and the numbers of differences, of
    person places and of places to look at. Raises as `real.read_document` and
    `real.read_labels` do.
    """
    folder = corpus_dir / "compare"
    folder.mkdir(exist_ok=True)
    counts = {}
    for doc_id in real.ids():
        paragraphs = real.read_document(corpus_dir, doc_id)
        a, b = (real.read_labels(labels, doc_id, paragraphs) for labels in (a_dir, b_dir))
        differ, persons, look = differences(a, b), person_splits(a, b), places(paragraphs, [*a, *b])
        rows = [(*row, "differ") for row in differ] + [(*row, "person") for row in persons] + [(*place, "", "", why) for *place, why in look]
        lines = ["paragraph\tfirst\tlast\ttext\ta\tb\twhy"]
        for paragraph, start, end, first, second, why in sorted(rows):
            low, high = run_span(paragraphs[paragraph], start, end)
            text = " ".join(paragraphs[paragraph][start:end].split())
            lines.append(f"{paragraph}\t{low}\t{high}\t{text}\t{first}\t{second}\t{why}")
        (folder / f"{doc_id}.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        same, either = agreement(a, b)
        counts[doc_id] = {"a": len(a), "b": len(b), "same": same, "either": either, "differ": len(differ), "persons": len(persons), "places": len(look)}
    return counts


def freeze(corpus_dir: Path, a_dir: Path, b_dir: Path) -> list[str]:
    """Return a line with the id and the SHA-256 of every key file, for a key made by the rule.

    Why: the hashes are committed before any detector is run, so a key that was changed
    after a number was seen is refused (PREREGISTRATION.md, "Frozen"). A key that cannot
    be scored, or that the third pass did not make by its rule, must not get that far.

    Contract: for every document of both piles, `key/<id>.tsv` is read like any label
    file and held against the two labellers' files by `key_faults`. Raises
    `real.CorpusError`, naming each document with its two counts, when a count is not 0,
    and as `real.read_document` and `real.read_labels` do.
    """
    lines, faults = [], []
    for doc_id in real.ids():
        paragraphs = real.read_document(corpus_dir, doc_id)
        a, b, key = (real.read_labels(folder, doc_id, paragraphs) for folder in (a_dir, b_dir, corpus_dir / "key"))
        outside, changed = key_faults(paragraphs, a, b, key)
        if outside or changed:
            faults.append(f"{doc_id}: {outside} label(s) of the key in no labeller's file and at no listed place, {changed} label(s) both labellers have missing or changed")
        lines.append(f"{doc_id}\t{hashlib.sha256((corpus_dir / 'key' / f'{doc_id}.tsv').read_bytes()).hexdigest()}")
    if faults:
        raise real.CorpusError("; ".join(faults))
    return lines


def main(arguments: argparse.Namespace) -> None:
    """Run one of the four commands and print counts, ids and line numbers only.

    Why: the commands are run by hand, between the passes of the readers.

    Contract: `arguments` has `command`, `corpus`, `a` and `b`. `freeze` writes
    `real.FROZEN`, and raises ValueError when that file is already there: a key is
    frozen once, and a second freeze would take a key that was changed after a run.
    """
    if arguments.command == "worksheets":
        print(f"worksheets written: {write_worksheets(arguments.corpus)}")
    elif arguments.command == "check":
        for doc_id, result in check(arguments.corpus, arguments.a).items():
            print(doc_id, result)
    elif arguments.command == "compare":
        counts = compare(arguments.corpus, arguments.a, arguments.b)
        for doc_id, row in counts.items():
            print(doc_id, *(f"{name} {value}" for name, value in row.items()))
        same, either = (sum(row[name] for row in counts.values()) for name in ("same", "either"))
        print(f"counted names both mark at the same place: {same} of {either}" + (f" = {same * 100 / either:.2f}%" if either else ""))
    else:
        if real.FROZEN.exists():
            raise ValueError(f"{real.FROZEN.name} is already there: a key is frozen once")
        lines = freeze(arguments.corpus, arguments.a, arguments.b)
        real.FROZEN.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print(f"key files frozen: {len(lines)}, written to {real.FROZEN.name}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("worksheets", "check", "compare", "freeze"))
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--a", type=Path)
    parser.add_argument("--b", type=Path)
    parsed = parser.parse_args()
    if parsed.command != "worksheets" and not parsed.a:
        parser.error(f"{parsed.command} needs --a")
    if parsed.command in ("compare", "freeze") and not parsed.b:
        parser.error(f"{parsed.command} needs --a and --b")
    main(parsed)
