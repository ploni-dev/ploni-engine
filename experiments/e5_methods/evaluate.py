"""Score every method of E5 against the planted names, from the files `detect.py` wrote.

Why: the question of E5 is which way of finding names misses fewest, and what each one
costs in words marked for nothing, in time and in memory (PREREGISTRATION.md). A method is a
detector, or several, with steps stacked on what they found; this script tries them all and
loads no model.

Contract: `python -I evaluate.py --runs-dir R --datasets NAME [NAME ...] [--names-list F]
[--only METHOD ...] [--record FILE] [--list-errors METHOD]`. R holds files named
`<detector>.<dataset>.json`. Prints one table per corpus, and one for all of them together
when there are several: a row per method, best recall first. With `--record` every row is
also appended to a file, one JSON object per line. With `--list-errors` every mention that
one method missed is printed with the text around it, which is allowed because every
sentence and every name is generated.

Known limits: recall is E4's strict rule, by characters. A word marked for nothing is
counted by Hebrew words; a word in Latin letters is not looked at.
"""

from __future__ import annotations

import argparse
import datetime
import itertools
import json
import re
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "e4_planted_names")]

import generate
import score

import data
import layers

Span = tuple[int, int, int]
# PREREGISTRATION.md, "The methods": the chances at which a token is taken as a person.
THRESHOLDS = (0.5, 0.3, 0.1, 0.03)
# Every stack of steps that is tried on a detector, by the name it has in the tables.
STACKS = {
    "group": ("group",),
    "titles": ("titles",),
    "carry": ("carry",),
    "carry strong": ("carry_strong",),
    "list": ("list",),
    "titles, carry": ("titles", "carry"),
    "titles, carry strong": ("titles", "carry_strong"),
    "titles, list, carry": ("titles", "list", "carry"),
}
# The stack that is also tried on every threshold and on every union of detectors.
MAIN_STACK = "titles, carry"
# The rows of a table beside the pooled recall, in the order they are printed.
WEAK_ROWS = ("group", "given_ordinary", "given_also_word", "prefixed", "alone", "lonely", "arabic", "translit")
SPACE_WORD = re.compile(r"\S+")
# How much of the paragraph is printed on each side of a mention that was not found.
ERROR_CONTEXT_CHARACTERS = 60


class Marked(NamedTuple):
    """A span in the form E4's scorer reads: a place and the label of a person."""

    paragraph: int
    start: int
    end: int
    label: str = score.PERSON_LABEL


class Method(NamedTuple):
    """One way of finding names.

    Contract: `detectors` are names of runs; what they found is put together. `threshold`
    None takes the tokens each model itself labels as a person; a number takes every token
    whose chance is at least that. `whole_words` widens every span to the words it touches.
    `steps` are keys of the step table, applied in order, each on what is marked so far.
    """

    name: str
    detectors: tuple[str, ...]
    threshold: float | None
    whole_words: bool
    steps: tuple[str, ...]


def chosen(rows: list[list], threshold: float | None) -> list[Span]:
    """Return the tokens of one document that count as a person.

    Contract: a row is `[paragraph, start, end, chance, chosen]` as `detect.py` writes it.
    """
    return [(row[0], row[1], row[2]) for row in rows if (row[4] if threshold is None else row[3] >= threshold)]


def whole_words(paragraphs: list[str], spans: list[Span]) -> list[Span]:
    """Widen every span to the whole of each word it touches.

    Why: a model that works on pieces of words can mark half a name. The product replaces
    words, so half a word marked is the word marked.

    Contract: a word is a run of characters with no white space. One span per word that a
    span overlaps; a word is returned once.
    """
    found = set()
    for index, paragraph in enumerate(paragraphs):
        here = [(start, end) for where, start, end in spans if where == index]
        for match in SPACE_WORD.finditer(paragraph):
            if any(start < match.end() and match.start() < end for start, end in here):
                found.add((index, match.start(), match.end()))
    return sorted(found)


def step_table(names: frozenset[str]) -> dict[str, Callable[[list[str], list[Span]], list[Span]]]:
    """Return every step by its key: a function from what is marked to what it adds."""
    return {
        "group": lambda paragraphs, spans: layers.after_triggers(paragraphs, spans),
        "titles": lambda paragraphs, spans: layers.after_triggers(paragraphs, spans, titles=True),
        "carry": lambda paragraphs, spans: layers.propagate(paragraphs, spans),
        "carry_strong": lambda paragraphs, spans: layers.propagate(paragraphs, spans, strong=True),
        "list": lambda paragraphs, spans: layers.from_list(paragraphs, spans, names),
    }


def marked(method: Method, document: generate.Document, runs: dict[str, dict], steps: dict) -> list[Span]:
    """Return everything one method marks in one document."""
    spans = sorted({span for name in method.detectors for span in chosen(runs[name]["tokens"][document.doc_id], method.threshold)})
    if method.whole_words:
        spans = whole_words(document.paragraphs, spans)
    for key in method.steps:
        spans = spans + steps[key](document.paragraphs, spans)
    return spans


def grid(detectors: list[str], with_chance: set[str], has_list: bool) -> list[Method]:
    """Build every method that is tried, from the detectors that were run.

    Contract: per detector: as the model gives it; with whole words; with whole words and
    each stack of STACKS; and, for a detector whose file holds chances, each threshold with
    whole words, alone and with MAIN_STACK. Then every union of two detectors, and of all
    of them when there are more than two, with whole words, alone and with MAIN_STACK. A
    stack with the list step is left out when no list was given.
    """
    stacks = {name: steps for name, steps in STACKS.items() if has_list or "list" not in steps}
    methods = []
    for detector in detectors:
        methods.append(Method(detector, (detector,), None, False, ()))
        methods.append(Method(f"{detector} + whole words", (detector,), None, True, ()))
        methods += [Method(f"{detector} + {name}", (detector,), None, True, steps) for name, steps in stacks.items()]
        for threshold in THRESHOLDS if detector in with_chance else ():
            methods.append(Method(f"{detector} at {threshold}", (detector,), threshold, True, ()))
            methods.append(Method(f"{detector} at {threshold} + {MAIN_STACK}", (detector,), threshold, True, STACKS[MAIN_STACK]))
    unions = list(itertools.combinations(detectors, 2)) + ([tuple(detectors)] if len(detectors) > 2 else [])
    for union in unions:
        methods.append(Method(" or ".join(union), union, None, True, ()))
        methods.append(Method(f"{' or '.join(union)} + {MAIN_STACK}", union, None, True, STACKS[MAIN_STACK]))
    return methods


def extra_words(document: generate.Document, spans: list[Span]) -> tuple[int, int, int]:
    """Count the Hebrew words a method marked that lie in no planted name.

    Contract: returns `(extra, extra that is no title, marked)`. A word is marked when a
    span overlaps it. It is extra when no gold span overlaps it, counted or not. A title, a
    group word and an initial are extra, and are left out of the second number: hiding
    `מר` with the name it stands before is no error for the reader.
    """
    extra = plain = total = 0
    for index, paragraph in enumerate(document.paragraphs):
        here = [(start, end) for where, start, end in spans if where == index]
        gold = [(item.start, item.end) for item in document.gold if item.paragraph == index]
        for start, end, text in layers.words(paragraph):
            if not any(low < end and start < high for low, high in here):
                continue
            total += 1
            if not any(low < end and start < high for low, high in gold):
                extra += 1
                title = layers.is_trigger(text, layers.TITLE_TRIGGERS | layers.GROUP_TRIGGERS) or layers.INITIAL.fullmatch(text)
                plain += not title
    return extra, plain, total


def rows_of(document: generate.Document, outcomes: list[score.Outcome]) -> dict[str, list[score.Outcome]]:
    """Sort the outcomes of one document into the rows of the table.

    Contract: `all`, the document's kind, and each of WEAK_ROWS that applies: E4's rows by
    their names, the name classes `arabic` and `translit`, and `lonely` as `data.lonely`
    defines it.
    """
    lonely = {document.gold[index] for index in data.lonely(document)}
    rows: dict[str, list[score.Outcome]] = {"all": list(outcomes), document.kind: list(outcomes)}
    for item in outcomes:
        names = set(generate.buckets_of(item.gold)) | set(item.gold.classes) | ({"lonely"} if item.gold in lonely else set())
        for name in names & set(WEAK_ROWS):
            rows.setdefault(name, []).append(item)
    return rows


def measure(method: Method, documents: list[generate.Document], runs: dict[str, dict], steps: dict) -> dict:
    """Score one method over one corpus.

    Contract: returns `rows`, mapping a row's name to `[found, total]`; `extra`,
    `extra_no_title` and `marked`, counts of Hebrew words as in `extra_words`; `words`, the
    Hebrew words of the corpus; `seconds`, the detectors' time for the corpus plus the time
    the steps took here; `peak_mb`, the largest of the detectors'; and `missed`, every
    outcome that is not `found`, with its document.
    """
    counts: dict[str, list[int]] = {}
    extra = plain = total = words = 0
    missed = []
    started = time.perf_counter()
    for document in documents:
        spans = marked(method, document, runs, steps)
        outcomes = score.score_document(document, [Marked(*span) for span in spans])
        for name, items in rows_of(document, outcomes).items():
            row = counts.setdefault(name, [0, 0])
            row[0] += sum(item.verdict == "found" for item in items)
            row[1] += len(items)
        missed += [(document, item) for item in outcomes if item.verdict != "found"]
        more = extra_words(document, spans)
        extra, plain, total = extra + more[0], plain + more[1], total + more[2]
        words += sum(len(layers.words(paragraph)) for paragraph in document.paragraphs)
    seconds = time.perf_counter() - started + sum(runs[name]["seconds"] for name in method.detectors)
    return {
        "rows": counts, "extra": extra, "extra_no_title": plain, "marked": total, "words": words,
        "seconds": round(seconds, 1), "peak_mb": max(runs[name]["peak_mb"] for name in method.detectors), "missed": missed,
    }  # fmt: skip


def pooled(results: list[dict]) -> dict:
    """Add up the results of one method over several corpora.

    Contract: counts are summed, seconds are summed, memory is the largest, and the missed
    mentions are put one after the other.
    """
    rows: dict[str, list[int]] = {}
    for result in results:
        for name, (found, total) in result["rows"].items():
            row = rows.setdefault(name, [0, 0])
            row[0], row[1] = row[0] + found, row[1] + total
    summed = {key: sum(result[key] for result in results) for key in ("extra", "extra_no_title", "marked", "words")}
    return {
        "rows": rows, **summed, "seconds": round(sum(result["seconds"] for result in results), 1),
        "peak_mb": max(result["peak_mb"] for result in results), "missed": [item for result in results for item in result["missed"]],
    }  # fmt: skip


def _cell(row: list[int] | None) -> str:
    """Write a count as `found/total`, or a dash when the corpus has no such mention."""
    return f"{row[0]}/{row[1]}" if row else "-"


def table(title: str, results: dict[str, dict]) -> str:
    """Write one table: a row per method, best recall first.

    Contract: columns: the method; strict recall in percent and as a count; each of
    WEAK_ROWS as a count; the Hebrew words marked outside every planted name, titles left
    out, then all; the share of marked words that lie in a planted name; seconds; peak
    memory in megabytes. Methods with the same recall come in order of fewer extra words.
    """
    head = ["method", "recall", "found", *WEAK_ROWS, "extra words", "with titles", "marked in a name", "seconds", "peak MB"]
    lines = [f"### {title}", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    order = sorted(results, key=lambda name: (-results[name]["rows"]["all"][0], results[name]["extra_no_title"], name))
    for name in order:
        result = results[name]
        found, total = result["rows"]["all"]
        share = f"{(result['marked'] - result['extra']) * 100 / result['marked']:.1f}%" if result["marked"] else "-"
        cells = [
            name, f"{found * 100 / total:.2f}%", f"{found}/{total}", *(_cell(result["rows"].get(row)) for row in WEAK_ROWS),
            str(result["extra_no_title"]), str(result["extra"]), share, f"{result['seconds']:.0f}", str(result["peak_mb"]),
        ]  # fmt: skip
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def error_lines(missed: list) -> list[str]:
    """List the mentions one method did not find, with the text around each."""
    lines = []
    for document, item in missed:
        gold = item.gold
        text = document.paragraphs[gold.paragraph]
        window = text[max(0, gold.start - ERROR_CONTEXT_CHARACTERS) : gold.end + ERROR_CONTEXT_CHARACTERS]
        lines.append(f"  {document.doc_id} {document.template} ¶{gold.paragraph} {item.verdict} {gold.form} [{gold.prefix}{gold.name}] :: {window}")
    return lines


def commit() -> str:
    """Return the commit of the checkout this script runs in, or `unknown` outside one."""
    done = subprocess.run(["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True, check=False)  # noqa: S607 git is found on the path, as everywhere in this repository
    return done.stdout.strip() or "unknown"


def record_lines(dataset: str, results: dict[str, dict], methods: dict[str, Method], runs: dict[str, dict]) -> list[str]:
    """Write the rows of one table as JSON objects, one per line, for the record file.

    Contract: each object holds the date, the commit, the corpus, the method with its
    parts, the model and the hashes of every detector in it, and every number of the
    table. The missed mentions are not written.
    """
    lines = []
    for name, result in results.items():
        method = methods[name]
        entry = {
            "date": datetime.date.today().isoformat(), "commit": commit(), "experiment": "e5", "dataset": dataset,
            "method": name, "threshold": method.threshold, "whole_words": method.whole_words, "steps": list(method.steps),
            "detectors": [{"name": key, "model": runs[key]["model"], "hashes": runs[key]["hashes"]} for key in method.detectors],
            **{key: value for key, value in result.items() if key != "missed"},
        }  # fmt: skip
        lines.append(json.dumps(entry, ensure_ascii=False))
    return lines


def load_runs(runs_dir: Path, dataset: str) -> dict[str, dict]:
    """Read every detector's file for one corpus, by the detector's name."""
    return {
        path.name.removesuffix(f".{dataset}.json"): json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(runs_dir.glob(f"*.{dataset}.json"))
    }


def evaluate(runs_dir: Path, datasets: list[str], names: frozenset[str], only: list[str]) -> tuple[dict, dict, dict]:
    """Score every method on every corpus asked for.

    Contract: returns `(results, methods, runs)`. `results` maps a corpus to a method's
    name to what `measure` gave; with several corpora it also has `all`, from `pooled`.
    Only detectors that were run on every corpus asked for take part. `only`, when not
    empty, keeps the methods with those names; a name that no method has raises KeyError.
    """
    runs = {dataset: load_runs(runs_dir, dataset) for dataset in datasets}
    detectors = sorted(set.intersection(*(set(found) for found in runs.values())))
    first = runs[datasets[0]]
    with_chance = {name for name in detectors if any(row[3] < 1 for rows in first[name]["tokens"].values() for row in rows)}
    methods = {method.name: method for method in grid(detectors, with_chance, bool(names))}
    if only:
        methods = {name: methods[name] for name in only}
    steps = step_table(names)
    results: dict[str, dict[str, dict]] = {}
    for dataset in datasets:
        documents = data.load(dataset)
        results[dataset] = {name: measure(method, documents, runs[dataset], steps) for name, method in methods.items()}
    if len(datasets) > 1:
        results["all"] = {name: pooled([results[dataset][name] for dataset in datasets]) for name in methods}
    return results, methods, first


def main(arguments: argparse.Namespace) -> None:
    """Print the tables, and write the record and the errors when asked."""
    names = frozenset(arguments.names_list.read_text(encoding="utf-8").split()) if arguments.names_list else frozenset()
    results, methods, runs = evaluate(arguments.runs_dir, arguments.datasets, names, arguments.only)
    for dataset, found in results.items():
        print(table(dataset, found), end="\n\n")
        if arguments.record:
            with arguments.record.open("a", encoding="utf-8") as handle:
                handle.write("\n".join(record_lines(dataset, found, methods, runs)) + "\n")
    if arguments.list_errors:
        last = results[list(results)[-1]][arguments.list_errors]
        print(f"not found by {arguments.list_errors}:", *error_lines(last["missed"]), sep="\n")


if __name__ == "__main__":
    # `python -I` ignores PYTHONUTF8, and a Windows pipe would get the ANSI code page.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--datasets", nargs="+", choices=sorted(data.DATASETS), required=True)
    parser.add_argument("--names-list", type=Path)
    parser.add_argument("--only", nargs="*", default=[])
    parser.add_argument("--record", type=Path)
    parser.add_argument("--list-errors")
    main(parser.parse_args())
