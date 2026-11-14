"""Compare a reader's count of the four part-two documents with the gold.

Why: E1's count was made by Claude readers and no person checked it. Here the same kind
of reader counts documents whose right answer the generator knows, so the reader's
count can be checked by a script. The rule is PREREGISTRATION.md, "The second part,
fixed before the run"; this file adds nothing to it.

Contract: `python -I reader_check.py --folder F`, where F holds, for each document of
`generate.PART_TWO_DOCUMENTS`, the span list `run.py --worksheets-dir` wrote
(`docNN_spans.csv`) and the reader's two files in E1's formats (`docNN_marks.csv`,
`docNN_misses.csv`). Prints the agreement per document and pooled, the verdict against
the pre-registered prediction and threshold, and every disagreement: each gold item on
which the reader and the script differ, and each item the reader lists and the gold
does not have. Names are printed: allowed here because every sentence and every name
is generated. Raises ReaderFileError for a file that does not follow E1's guide, so
that a malformed file is refused and never read kindly.

Known limits. All of them come from the pre-registered rule, which this script follows:
- People the reader lists beyond the gold are counted, people short of it are not: a
  highlight that holds two names and is marked found with `extra` 0 agrees.
- One highlight that covers one name fully and a second name in part has no faultless
  answer. Marked partial with a line, the first name disagrees; marked found, the second
  does. Marked found with a partial line, the file is refused.
- One highlight that covers a counted name and a name that is not counted disagrees
  whatever the reader marks.
- Two highlights on one name, both marked found, cost nothing.
- A miss line that writes the name otherwise (another apostrophe) is not paired: the
  mention disagrees and the line is a reader-only item, so it costs two.
- Lines wider than the name are paired in file order; out of reading order they can take
  each other's mention and cost two.
- It cannot tell whether the reader saw the gold; the pre-registration says so.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
# `python -I` drops the script folder.
sys.path[:0] = [str(HERE)]

import generate
import score

VERDICTS = frozenset({"found", "partial", "surplus", "not_person"})
MISS_KINDS = frozenset({"missed", "partial"})
SPAN_COLUMNS = ("highlight", "paragraph", "start", "end", "text")
MARK_COLUMNS = ("highlight", "verdict", "extra")
MISS_COLUMNS = ("paragraph", "text", "kind", "highlight")
# PREREGISTRATION.md, "The second part": 98 percent agreement or more; below 95 crosses.
PREDICTED_AGREEMENT_PERCENT = 98
THRESHOLD_AGREEMENT_PERCENT = 95


class ReaderFileError(ValueError):
    """A reader's file, or a span list, is not what E1's guide and `run.py` produce."""


class Highlight(NamedTuple):
    """One PER highlight of the model, with what the reader said about it.

    Contract: `number` as printed on the worksheet; `start` inclusive and `end`
    exclusive in characters of paragraph `paragraph`; `text` as the span list gives it,
    without white space at its edges; `verdict` one of VERDICTS; `extra` the reader's
    count of further people inside it. `label` is always the person label, so that
    `score.outcome` can read a highlight as a span.
    """

    number: int
    paragraph: int
    start: int
    end: int
    text: str
    verdict: str
    extra: int
    label: str = score.PERSON_LABEL


class MissLine(NamedTuple):
    """One line of the reader's list of misses.

    Contract: `kind` is `missed` or `partial`. `highlight` is the number of the partial
    highlight for a partial line, and None for a missed one.
    """

    paragraph: int
    text: str
    kind: str
    highlight: int | None


class ReaderFiles(NamedTuple):
    """What one reader left for one document: every highlight with its verdict, and the miss lines in file order."""

    highlights: list[Highlight]
    misses: list[MissLine]


class Comparison(NamedTuple):
    """The reader against the gold for one document.

    Contract: `items` are the gold items, counted and not counted. `agreeing` of them
    are judged the same by the reader and by the script. `reader_only` are what the
    reader lists and the gold does not have. Agreement is `agreeing` over `items` plus
    `reader_only`. `disagreements` has one line per gold item that does not agree,
    then one line per highlight or miss line that gives reader-only items.
    """

    items: int
    agreeing: int
    reader_only: int
    disagreements: list[str]


def _rows(path: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
    """Read a comma-separated file whose header must hold the given columns.

    Why: a file with no header would lose its first line without a word, and a reader
    would be blamed for a mention the reader did list.

    Contract: cells are stripped; a byte-order mark is allowed; other columns are
    ignored. Raises ReaderFileError when the file is empty or its header lacks a
    column of `columns`.
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = [name.strip() for name in reader.fieldnames or []]
        lacking = [name for name in columns if name not in header]
        if lacking:
            raise ReaderFileError(f"{path.name}: the header lacks the column {', '.join(lacking)}")
        return [{(key or "").strip(): (value or "").strip() for key, value in row.items()} for row in reader]


def _whole_number(cell: str, what: str) -> int:
    """Read a cell that must hold a whole number of zero or more."""
    if not cell.isdecimal():
        raise ReaderFileError(f"{what} is not a whole number")
    return int(cell)


def _read_misses(path: Path) -> list[MissLine]:
    """Read the reader's list of misses.

    Contract: every line has a known kind, a text and a paragraph number. A partial
    line names a highlight; a missed line names none. Raises ReaderFileError otherwise.
    """
    lines = []
    for row in _rows(path, MISS_COLUMNS):
        kind, cell = row["kind"], row["highlight"]
        if kind not in MISS_KINDS or not row["text"]:
            raise ReaderFileError(f"{path.name}: a line with an unknown kind or no text")
        if kind == "missed" and cell:
            raise ReaderFileError(f"{path.name}: a missed line carries a highlight number")
        number = _whole_number(cell, f"{path.name}: the highlight of a partial line") if kind == "partial" else None
        lines.append(MissLine(_whole_number(row["paragraph"], f"{path.name}: a paragraph"), row["text"], kind, number))
    return lines


def _read_marks(path: Path) -> dict[int, tuple[str, int]]:
    """Read the reader's verdict and `extra` for every highlight.

    Contract: returns number -> (verdict, extra). Raises ReaderFileError for a number
    listed twice, an unknown verdict, or an `extra` that is not a whole number.
    """
    marks: dict[int, tuple[str, int]] = {}
    for row in _rows(path, MARK_COLUMNS):
        number = _whole_number(row["highlight"], f"{path.name}: a highlight number")
        if number in marks or row["verdict"] not in VERDICTS:
            raise ReaderFileError(f"{path.name}: highlight {number} is marked twice or with an unknown verdict")
        marks[number] = (row["verdict"], _whole_number(row["extra"], f"{path.name}: extra of highlight {number}"))
    return marks


def read_reader_files(folder: Path, doc_id: str) -> ReaderFiles:
    """Read one document's three files as one checked set.

    Why: the comparison must not guess what a malformed file meant.

    Contract: reads `docNN_spans.csv`, `docNN_marks.csv` and `docNN_misses.csv` from
    `folder`. Raises ReaderFileError unless the marks give exactly one known verdict
    and a whole `extra` to every highlight of the span list, and the highlights marked
    partial are exactly those that the partial lines name. One partial highlight may
    have several lines: it can cover part of two names.
    """
    spans = {}
    for row in _rows(folder / f"{doc_id}_spans.csv", SPAN_COLUMNS):
        number, paragraph, start, end = (_whole_number(row[name], f"{doc_id}: a span's {name}") for name in SPAN_COLUMNS[:4])
        spans[number] = (paragraph, start, end, row["text"])
    marks = _read_marks(folder / f"{doc_id}_marks.csv")
    if set(marks) != set(spans):
        raise ReaderFileError(f"{doc_id}: the marks do not cover the highlights exactly once")
    misses = _read_misses(folder / f"{doc_id}_misses.csv")
    if {line.highlight for line in misses if line.kind == "partial"} != {n for n, (verdict, _) in marks.items() if verdict == "partial"}:
        raise ReaderFileError(f"{doc_id}: the partial lines and the highlights marked partial are not the same")
    return ReaderFiles([Highlight(number, *spans[number], *marks[number]) for number in sorted(spans)], misses)


def _pair_missed_lines(lines: list[MissLine], counted: list[generate.Gold], reader: list[str | None]) -> list[MissLine]:
    """Pair the reader's missed lines with mentions the reader gave no highlight verdict.

    Contract: `reader[i]` is the reader's verdict for `counted[i]` so far, None where no
    highlight marked found or partial overlaps it. A line can take a mention of its own
    paragraph whose name its text holds, or whose name holds its text. Each line takes
    one mention and each mention one line; lines in file order, mentions in reading
    order, lines whose text is exactly the name first. Sets `reader[i]` to `missed` for
    every mention that got a line, and returns the lines that were left over.
    """
    for exact in (True, False):
        left = []
        for line in lines:
            taken = next(
                (
                    index
                    for index, gold in enumerate(counted)
                    if reader[index] is None
                    and gold.paragraph == line.paragraph
                    and (line.text == gold.name if exact else gold.name in line.text or line.text in gold.name)
                ),
                None,
            )
            if taken is None:
                left.append(line)
            else:
                reader[taken] = "missed"
        lines = left
    return lines


def _overlapping(gold: generate.Gold, highlights: list[Highlight]) -> list[Highlight]:
    """Return the highlights that share at least one character with a gold span."""
    return [h for h in highlights if h.paragraph == gold.paragraph and h.start < gold.end and gold.start < h.end]


def _reader_only_highlights(doc_id: str, counted: list[generate.Gold], highlights: list[Highlight]) -> list[tuple[int, str]]:
    """List the people the reader counts through highlights and the gold does not have.

    Contract: one (items, line) pair per highlight that gives any. A highlight marked
    found stands for one person plus its `extra`; each of these beyond the counted
    mentions it overlaps is one item, so on plain text it is one plus its `extra`. A
    highlight marked partial gives one plus its `extra` only when it overlaps no
    counted mention. Other verdicts give nothing.
    """
    listed = []
    for highlight in highlights:
        overlapped = sum(bool(_overlapping(gold, [highlight])) for gold in counted)
        if highlight.verdict == "found" or (highlight.verdict == "partial" and not overlapped):
            items = max(0, 1 + highlight.extra - overlapped)
            if items:
                listed.append((items, f"{doc_id} ¶{highlight.paragraph} highlight {highlight.number} [{highlight.text}] "
                                      f"marked {highlight.verdict}, extra {highlight.extra}: {items} reader-only"))
    return listed


def _check_spans(document: generate.Document, highlights: list[Highlight]) -> None:
    """Refuse a span list that is not of this document.

    Contract: raises ReaderFileError when a highlight names a paragraph the document
    does not have, or when the text at its position, without white space at its edges,
    is not the text the span list gives.
    """
    for highlight in highlights:
        inside = highlight.paragraph < len(document.paragraphs)
        if not inside or document.paragraphs[highlight.paragraph][highlight.start : highlight.end].strip() != highlight.text:
            raise ReaderFileError(f"{document.doc_id}: highlight {highlight.number} is not of this document")


def compare(document: generate.Document, files: ReaderFiles) -> Comparison:
    """Compare one reader's files with the gold of one document.

    Why: this is the measurement of the second part: how often a reader and the script
    say the same about a planted name.

    Contract: the rule of PREREGISTRATION.md, "The second part". For a counted mention
    the script's verdict is `score.outcome` on the highlights; the reader's is partial
    if an overlapping highlight is marked partial, else found if one is marked found,
    else missed if a missed line is paired with it, else nothing, which disagrees. A
    name that is not counted agrees if every highlight on it is marked not_person.
    Raises ReaderFileError as `_check_spans` does.
    """
    _check_spans(document, files.highlights)
    counted = [gold for gold in document.gold if gold.counted]
    reader: list[str | None] = []
    for gold in counted:
        verdicts = {highlight.verdict for highlight in _overlapping(gold, files.highlights)}
        reader.append("partial" if "partial" in verdicts else "found" if "found" in verdicts else None)
    left_over = _pair_missed_lines([line for line in files.misses if line.kind == "missed"], counted, reader)
    disagreements = []
    for gold, said in zip(counted, reader, strict=True):
        verdict = score.outcome(gold, document.paragraphs[gold.paragraph], files.highlights).verdict
        if said != verdict:
            disagreements.append(f"{document.doc_id} ¶{gold.paragraph} [{gold.name}] script {verdict}, reader {said or 'nothing'}")
    for gold in document.gold:
        if not gold.counted and any(h.verdict != "not_person" for h in _overlapping(gold, files.highlights)):
            disagreements.append(f"{document.doc_id} ¶{gold.paragraph} [{gold.name}] not counted, reader counted it")
    agreeing = len(document.gold) - len(disagreements)
    by_highlight = _reader_only_highlights(document.doc_id, counted, files.highlights)
    disagreements += [line for _, line in by_highlight]
    disagreements += [f"{document.doc_id} ¶{line.paragraph} miss line [{line.text}] fits no mention: 1 reader-only" for line in left_over]
    return Comparison(len(document.gold), agreeing, sum(items for items, _ in by_highlight) + len(left_over), disagreements)


def agreement_verdict(agreeing: int, total: int) -> str:
    """Compare the agreement with the pre-registered prediction and threshold.

    Contract: exact integer arithmetic. `inside_prediction` at
    PREDICTED_AGREEMENT_PERCENT or more; `threshold_crossed` below
    THRESHOLD_AGREEMENT_PERCENT; otherwise `outside_prediction`. `total` is the gold
    items plus the reader-only items. Raises ValueError when nothing was compared.
    """
    if total <= 0:
        raise ValueError("nothing was compared")
    if agreeing * 100 >= PREDICTED_AGREEMENT_PERCENT * total:
        return "inside_prediction"
    if agreeing * 100 < THRESHOLD_AGREEMENT_PERCENT * total:
        return "threshold_crossed"
    return "outside_prediction"


def main(folder: Path) -> None:
    """Print the agreement of the readers with the gold for the four documents.

    Contract: see the module docstring. The corpus is generated again from the
    committed templates, so the gold is never read from a file a reader could reach.
    """
    documents = {document.doc_id: document for document in generate.corpus(HERE / "templates", HERE / "names.tsv")}
    agreeing = total = 0
    disagreements: list[str] = []
    for doc_id in generate.PART_TWO_DOCUMENTS:
        result = compare(documents[doc_id], read_reader_files(folder, doc_id))
        whole = result.items + result.reader_only
        print(f"{doc_id}: gold items {result.items}, agreeing {result.agreeing}, reader-only {result.reader_only}, "
              f"agreement {result.agreeing}/{whole} = {result.agreeing * 100 / whole:.2f}%")
        agreeing += result.agreeing
        total += whole
        disagreements += result.disagreements
    print(f"reader against gold, pooled: {agreeing}/{total} = {agreeing * 100 / total:.2f}%")
    print(f"verdict: {agreement_verdict(agreeing, total)} (prediction {PREDICTED_AGREEMENT_PERCENT} percent or more, "
          f"threshold below {THRESHOLD_AGREEMENT_PERCENT} percent)")
    print("disagreements:", *(f"  {line}" for line in disagreements or ["none"]), sep="\n")


if __name__ == "__main__":
    # `python -I` ignores PYTHONUTF8, and a Windows pipe would get the ANSI code page.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--folder", type=Path, required=True)
    main(parser.parse_args().folder)
