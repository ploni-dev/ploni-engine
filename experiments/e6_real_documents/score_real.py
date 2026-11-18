"""Score every method of E5 on one pile of E6's real decisions, against the key made by readers.

Why: E5 found on generated text which way of finding names misses fewest. E6 asks whether
that holds on real decisions (PREREGISTRATION.md). The methods are built and scored by
E5's own code; this script gives it the real documents and counts the rows that make
sense for a key made by readers.

Contract: `python -I score_real.py --corpus DIR --runs-dir R --pile open|closed
[--only METHOD ...] [--key-dir K] [--record FILE] [--lists-to FILE]`. R holds the files
`detect_real.py` wrote, `<detector>.e6-<pile>.json`. Prints one table: a row per method,
best recall first. The key is the frozen one unless `--key-dir` names another folder, which
only the open pile takes, and the table's title says which. `--record` appends a JSON line per method, numbers and
labels only. `--lists-to` writes every name a method did not find and every word it marked
for nothing, with the text around each, to a file that must be outside the repository.
The closed pile is scored only for methods named with `--only`, only once
`results/CHOSEN.md` exists, and only for methods that file names. Nothing of a document is printed.

Known limits: as E5's `evaluate.py`. That the closed pile is scored once is the runner's
to keep; this script cannot count its own runs.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]  # `python -I` drops the script folder

import real

import corpus
import data
import evaluate
import generate
import layers

# PREREGISTRATION.md, "How it is scored": the rows beside the pooled number, in the order they are printed.
ROWS = ("private", "public", "one_word", "prefixed", "alone", "lonely", "no_trigger")
# Words marked for nothing are given per this many Hebrew words of text (PREREGISTRATION.md, "Predictions").
PER_WORDS = 1000
# PREREGISTRATION.md, "What may be fitted on the open pile": the methods fitted after the open
# pile's errors were read. One: E5's two steps in the other order. In `titles, carry` a word that
# only a title gave (the word after `השופט` that is no name) is spread through the document; with
# `carry strong` first, only what the detector found is spread, and the titles add their word last.
FITTED = (evaluate.Method("joint + carry strong, titles", ("joint",), None, True, ("carry_strong", "titles")),)
# How much of the paragraph is written on each side of a word that was marked for nothing.
CONTEXT_CHARACTERS = evaluate.ERROR_CONTEXT_CHARACTERS


def rows_of(document: generate.Document) -> dict[str, set[int]]:
    """Sort the counted names of one document into the rows of the table.

    Why: a pooled number hides where a method fails. These are the kinds of mention that
    can be told from a label and from the text, with no reader's judgement beyond the label.

    Contract: returns, for every name of ROWS, the positions in `document.gold` of the
    counted names in it. `private` and `public` by the label's kind; `one_word` for a
    name with no white space in it; `prefixed` for one behind attached letters; `alone`
    for one that is its whole line; `lonely` for a person named once, as `data.lonely`
    counts; `no_trigger` for a name that E5's `titles` step, run with nothing marked,
    does not touch.
    """
    triggered = layers.after_triggers(document.paragraphs, [], titles=True)
    lonely = data.lonely(document)
    rows: dict[str, set[int]] = {name: set() for name in ROWS}
    for index, gold in enumerate(document.gold):
        if not gold.counted:
            continue
        touched = any(paragraph == gold.paragraph and start < gold.end and gold.start < end for paragraph, start, end in triggered)
        member = {
            "private": "private" in gold.classes, "public": "public" in gold.classes, "one_word": len(gold.name.split()) == 1,
            "prefixed": bool(gold.prefix), "alone": gold.alone, "lonely": index in lonely, "no_trigger": not touched,
        }  # fmt: skip
        for name in ROWS:
            if member[name]:
                rows[name].add(index)
    return rows


def row_counts(documents: list[generate.Document], missed: list) -> dict[str, list[int]]:
    """Count, per row, how many names a method found.

    Why: E5's scorer counts the rows of generated text; a key made by readers has
    rows of its own, counted here from what E5's scorer says was not found.

    Contract: `missed` is what `evaluate.measure` returns under that name: every counted
    name that is not found by E4's strict rule, with its document. Returns `all` and
    every name of ROWS, each as `[found, total]`.
    """
    lost = {(document.doc_id, item.gold) for document, item in missed}
    counts = {name: [0, 0] for name in ("all", *ROWS)}
    for document in documents:
        rows = {"all": {index for index, gold in enumerate(document.gold) if gold.counted}, **rows_of(document)}
        for name, indexes in rows.items():
            counts[name][0] += sum((document.doc_id, document.gold[index]) not in lost for index in indexes)
            counts[name][1] += len(indexes)
    return counts


def check_request(pile: str, only: list[str], key_dir: Path | None = None) -> None:
    """Refuse a request that would score the closed pile for choosing.

    Why: the closed pile judges methods that were already chosen and written down
    (PREREGISTRATION.md, "What is judged on the closed pile").

    Contract: raises ValueError for the closed pile before `real.CHOSEN` exists, when
    no method is named, when a named method does not stand in that file between
    backticks, or when another key than the frozen one is asked for: the closed pile is
    scored once, by the frozen key.
    """
    real.check_closed(pile)
    if pile != real.CLOSED:
        return
    if key_dir is not None:
        raise ValueError("the closed pile is scored by the frozen key only")
    if not only:
        raise ValueError("the closed pile is scored only for methods named with --only")
    chosen = real.CHOSEN.read_text(encoding="utf-8")
    unnamed = [name for name in only if f"`{name}`" not in chosen]
    if unnamed:
        raise ValueError(f"{real.CHOSEN.name} does not name: {', '.join(unnamed)}")


def score(corpus_dir: Path, runs_dir: Path, pile: str, only: list[str], key_dir: Path | None = None) -> tuple[dict, dict, dict, list[generate.Document]]:
    """Score every method on one pile.

    Why: the whole of a scoring run in one function, so that a test can run it on
    made-up files.

    Contract: returns `(results, methods, runs, documents)`. `results` maps a method's
    name to what `evaluate.measure` gave, with `real_rows` added, as `row_counts` counts
    them. The methods are E5's grid without the `list` step, and those of FITTED whose
    detector was run; `only`, when not empty, keeps the methods with those names. The key is the frozen one, or, with `key_dir`,
    the files of that folder without the check. Raises ValueError as `check_request` and
    `evaluate.score_corpora` do, and as `real.load` does.
    """
    check_request(pile, only, key_dir)
    documents = real.load(corpus_dir, pile, key_dir, frozen=key_dir is None)
    name = f"e6-{pile}"
    results, methods, runs, _ = evaluate.score_corpora(runs_dir, {name: documents}, evaluate.NameList(frozenset(), ""), only, FITTED)
    for result in results[name].values():
        result["real_rows"] = row_counts(documents, result["missed"])
    return results[name], methods, runs[name], documents


def extra_places(document: generate.Document, spans: list) -> list[tuple[int, int, int, bool]]:
    """List the Hebrew words a method marked that lie in no name of the key.

    Why: `evaluate.extra_words` counts them; to read them, and to find a name the key
    lacks among them, their places are needed (PREREGISTRATION.md, "What the key cannot
    be trusted for").

    Contract: `spans` are `(paragraph, start, end)`. Returns, in reading order,
    `(paragraph, start, end, title)` for every word that a span overlaps and no name of
    the key does, counted or not; `title` says that the word is a title, a group word or
    an initial, as in `evaluate.extra_words`.
    """
    found = []
    for index, paragraph in enumerate(document.paragraphs):
        here = [(start, end) for where, start, end in spans if where == index]
        gold = [(item.start, item.end) for item in document.gold if item.paragraph == index]
        for start, end, text in layers.words(paragraph):
            marked = any(low < end and start < high for low, high in here)
            if marked and not any(low < end and start < high for low, high in gold):
                title = layers.is_trigger(text, layers.TITLE_TRIGGERS | layers.GROUP_TRIGGERS) or layers.INITIAL.fullmatch(text)
                found.append((index, start, end, bool(title)))
    return found


def _cell(row: list[int]) -> str:
    """Write a count as `found/total`, or a dash when the pile has no such name."""
    return f"{row[0]}/{row[1]}" if row[1] else "-"


def table(title: str, results: dict[str, dict]) -> str:
    """Write the table of one scoring run: a row per method, best recall first.

    Why: the findings note pastes this as printed.

    Contract: columns: the method; strict recall in percent and as a count; each of
    ROWS as a count; the Hebrew words marked outside every name of the key, titles left
    out, then all; the first of those per PER_WORDS Hebrew words of the pile; seconds;
    peak memory in megabytes. Methods with the same number of names found come in E5's
    order: fewer words marked for nothing without titles, then fewer seconds, then the name.
    """
    head = ["method", "recall", "found", *ROWS, "extra words", "with titles", "per 1,000", "seconds", "peak MB"]
    lines = [f"### {title}", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    order = sorted(results, key=lambda name: (-results[name]["real_rows"]["all"][0], results[name]["extra_no_title"], results[name]["seconds"], name))
    for name in order:
        result = results[name]
        found, total = result["real_rows"]["all"]
        cells = [
            name, f"{found * 100 / total:.2f}%" if total else "-", f"{found}/{total}", *(_cell(result["real_rows"][row]) for row in ROWS),
            str(result["extra_no_title"]), str(result["extra"]), f"{result['extra_no_title'] * PER_WORDS / result['words']:.2f}",
            f"{result['seconds']:.0f}", str(result["peak_mb"]),
        ]  # fmt: skip
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def record_lines(pile: str, key: str, results: dict[str, dict], methods: dict, runs: dict[str, dict]) -> list[str]:
    """Write the rows of one table as JSON objects, one per line, for the record file.

    Why: `build-plan.md` section 7 asks every experiment to write its numbers in a form a
    dashboard can read later.

    Contract: each object holds the date, the commit, the experiment `e6`, the pile as
    `dataset`, which key was used, the method with its parts, the model and the hashes
    of every detector in it, and every number of the table. It holds no word of a
    document: the names that were not found are left out.
    """
    lines = []
    for name, result in results.items():
        method = methods[name]
        entry = {
            "date": datetime.date.today().isoformat(), "commit": evaluate.commit(), "experiment": "e6", "dataset": pile, "key": key,
            "method": name, "threshold": method.threshold, "whole_words": method.whole_words, "steps": list(method.steps),
            "detectors": [{"name": detector, "model": runs[detector]["model"], "hashes": runs[detector]["hashes"]} for detector in method.detectors],
            "rows": result["real_rows"],
            **{field: result[field] for field in ("extra", "extra_no_title", "marked", "words", "seconds", "peak_mb")},
        }  # fmt: skip
        lines.append(json.dumps(entry, ensure_ascii=False))
    return lines


def listing(name: str, method: evaluate.Method, documents: list[generate.Document], runs: dict[str, dict], result: dict) -> list[str]:
    """List what one method got wrong, with the text around each place.

    Why: what a method misses and what it marks for nothing say more than how many. The
    lines hold names and sentences of real decisions, so they go to a private file only
    (`write_private`).

    Contract: a first line with the two counts; then a line per counted name that was
    not found, as `evaluate.error_lines` writes it; then a line per word marked outside
    every name of the key, with `title` beside a title, a group word or an initial.
    """
    steps = evaluate.step_table(frozenset())
    extras = []
    for document in documents:
        for paragraph, start, end, title in extra_places(document, evaluate.marked(method, document, runs, steps)):
            text = document.paragraphs[paragraph]
            window = text[max(0, start - CONTEXT_CHARACTERS) : end + CONTEXT_CHARACTERS]
            extras.append(f"  {document.doc_id} ¶{paragraph} extra{' title' if title else ''} [{text[start:end]}] :: {window}")
    return [f"{name}: {len(result['missed'])} not found, {len(extras)} marked for nothing", *evaluate.error_lines(result["missed"]), *extras]


def write_private(path: Path, lines: list[str]) -> None:
    """Write lines that hold text of real decisions to a file outside the repository.

    Why: `CLAUDE.md`, Hard constraints: no real document in the repository, in any form.

    Contract: raises ValueError, and writes nothing, when `path` lies inside the
    repository. Makes the folder when it is missing.
    """
    if corpus.is_inside(path, real.REPOSITORY):
        raise ValueError("a listing holds text of real documents and is never written inside the repository")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(arguments: argparse.Namespace) -> None:
    """Print the table of one scoring run, and write the record lines and the listing when asked.

    Why: the command line of the experiment; a test runs it on made-up files.

    Contract: the record lines are added to the end of the record file, whose folder
    is made when it is missing. The listing goes through `write_private`.
    """
    key = "frozen" if arguments.key_dir is None else arguments.key_dir.name
    results, methods, runs, documents = score(arguments.corpus, arguments.runs_dir, arguments.pile, arguments.only, arguments.key_dir)
    title = "frozen key" if arguments.key_dir is None else f"key of {key}, not the frozen one"
    print(table(f"e6 {arguments.pile}, {title}", results), end="\n\n")
    if arguments.record:
        arguments.record.parent.mkdir(parents=True, exist_ok=True)
        with arguments.record.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(record_lines(arguments.pile, key, results, methods, runs)) + "\n")
    if arguments.lists_to:
        write_private(arguments.lists_to, [line for name, result in results.items() for line in listing(name, methods[name], documents, runs, result)])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--pile", choices=(real.OPEN, real.CLOSED), required=True)
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--key-dir", type=Path)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--lists-to", type=Path)
    main(parser.parse_args())
