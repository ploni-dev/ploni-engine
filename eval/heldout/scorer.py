"""Score a detector on the held-out batch: per type, what it found, what it missed, what it marked wrongly.

Why: every PR from Phase 1 on carries these numbers, and a worse one blocks a merge until Achia
decides (build-plan.md section 7, "The held-out batch"). The session that writes the detectors
reads only what this prints, never the documents, the generator or its key (Achia, 2026-11-26,
issue 283). So the scorer prints type names and numbers, never a document or an identifier.

Contract: a detector is a callable from a document's text to an iterable of (start, end, type):
start and end in code points of that text, end exclusive, type a string. `score` runs it once
per document of a batch and counts, per type, by exact span and type:
- tp: a detection whose document, start, end and type equal a key item's;
- fp: any other detection, a detection of a type the batch does not hold included;
- fn: a key item that no detection equals;
- partial: those fp that share at least one character with a key item of the same type in the
  same document. A partial overlap is not a hit: it counts as a fp, and the item it overlaps, if
  nothing equals it, as a fn. `partial` only shows how many of the fp are a span that differs
  from the key's (a word more, a prefix less), as against a detection with nothing under it.
A detection returned twice is counted once. recall is tp / (tp + fn), precision tp / (tp + fp),
each 0.0 when its denominator is 0. The total sums the counts over the types (micro-averaged).
`report` gives one line per type and one for the total; `main` prints it for a named detector.

Known limits: near misses are not counted apart, a detection of one is a fp of its type; a type
name the detector invents is printed as given, so text in a type name would be printed.
"""

import contextlib
import importlib
import io
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from eval.heldout.generator import Batch, build

Detection = tuple[int, int, str]
Detector = Callable[[str], Iterable[Detection]]
Span = tuple[int, int, int, str]
TOTAL = "TOTAL"
USAGE = "usage: python -m eval.heldout.scorer <module>:<function>"
# A detection is a triple: start, end, type.
TRIPLE = 3


@dataclass
class Counts:
    """The four counts of one type, with the recall and precision they give.

    Why: a row of the report, and the numbers a PR compares before and after.

    Contract: tp, fp, fn and partial as the module docstring defines them; recall and precision
    are fractions from 0.0 to 1.0, 0.0 when their denominator is 0.
    """

    tp: int = 0
    fp: int = 0
    fn: int = 0
    partial: int = 0

    @property
    def recall(self) -> float:
        """Return the share of the key's items found. Why: what a gate on recall reads. Contract: tp / (tp + fn), or 0.0."""
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def precision(self) -> float:
        """Return the share of detections that are key items. Why: what a gate on precision reads. Contract: tp / (tp + fp), or 0.0."""
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0


@dataclass(frozen=True)
class Scores:
    """The counts of every type, and of all types together.

    Why: what `score` returns and `report` prints.

    Contract: per_type maps to its Counts every type of the key and any other type a detector
    returned, sorted by name. total holds the sums.
    """

    per_type: dict[str, Counts]
    total: Counts


def _checked(detections: Iterable[object], doc: int, length: int) -> list[tuple[int, int, str]]:
    """Return a document's detections as triples; one that is no span of it is an error, not a fp.

    The error names the document, the detection and the numbers, never text.
    """
    found = []
    for index, detection in enumerate(detections):
        where = f"document {doc}, detection {index}"
        if not isinstance(detection, tuple | list) or len(detection) != TRIPLE:
            raise ValueError(f"{where}: not a (start, end, type) triple")
        start, end, kind = detection
        if not all(isinstance(at, int) and not isinstance(at, bool) for at in (start, end)) or not isinstance(kind, str):
            raise ValueError(f"{where}: start and end must be int and type a str")
        if not 0 <= start < end <= length:
            raise ValueError(f"{where}: span ({start}, {end}) is not inside a text of length {length}")
        found.append((start, end, kind))
    return found


class DetectorError(Exception):
    """A detector raised while it read a document of the batch.

    Why: the detector's own message, and its traceback, may quote the document, which the session
    that writes the detectors must not see. Contract: the message names the document's index and
    the error's type only; the detector's error is not chained to it.
    """


def _detections(detector: Detector, text: str, doc: int) -> list[object]:
    """Return what the detector returns for one text, its own error turned into a DetectorError."""
    try:
        return list(detector(text))
    except Exception as error:  # noqa: BLE001 re-raised as DetectorError at once, without its message
        raise DetectorError(f"document {doc}: the detector raised {type(error).__name__}") from None


def _partial(span: Span, by_place: dict[tuple[int, str], list[Span]]) -> bool:
    """Say whether a span shares a character with a key item of its type in its document."""
    doc, start, end, kind = span
    return any(start < item_end and item_start < end for _, item_start, item_end, _ in by_place.get((doc, kind), []))


def score(detector: Detector, batch: Batch | None = None) -> Scores:
    """Return the counts of a detector on a batch, per type and in total.

    Why: one function makes every PR's numbers, so that two PRs are compared on the same rule.

    Contract: detector as the module docstring says; batch, the batch to score, the batch of
    SEED when None. Returns Scores, counted as the module docstring says. Raises ValueError when
    a detection is not a (start, end, type) triple, when start or end is not an int (a bool is
    not one) or type not a str, or when not 0 <= start < end <= the text's length; the message
    names the document's index and the detection's, and holds no text. Raises DetectorError when
    the detector raises, with the type of its error only.

    Known limits: the detector is called once per document, in order; it is not timed. What the
    detector prints is not held back here; `main` holds it back.
    """
    batch = build() if batch is None else batch
    key = {(item.doc, item.start, item.end, item.type) for item in batch.key}
    found: set[Span] = set()
    for doc, text in enumerate(batch.documents):
        found |= {(doc, start, end, kind) for start, end, kind in _checked(_detections(detector, text, doc), doc, len(text))}
    by_place: dict[tuple[int, str], list[Span]] = defaultdict(list)
    for span in key:
        by_place[(span[0], span[3])].append(span)
    per_type: dict[str, Counts] = defaultdict(Counts)
    for span in key - found:
        per_type[span[3]].fn += 1
    for span in found:
        counts = per_type[span[3]]
        if span in key:
            counts.tp += 1
        else:
            counts.fp += 1
            counts.partial += _partial(span, by_place)
    rows = {kind: per_type[kind] for kind in sorted({span[3] for span in key} | set(per_type))}
    total = Counts(*(sum(getattr(row, name) for row in rows.values()) for name in ("tp", "fp", "fn", "partial")))
    return Scores(rows, total)


def report(scores: Scores) -> list[str]:
    """Return the lines that show scores: one per type, sorted, then the total.

    Why: what a PR body and the session that writes the detectors read; names and numbers only.

    Contract: each line is the type name, then tp, fp, fn, partial, recall and precision, each
    after its label, recall and precision with three decimals. The last line is TOTAL's.
    """
    rows = [*scores.per_type.items(), (TOTAL, scores.total)]
    return [
        f"{name:<17} tp {row.tp:5d}  fp {row.fp:5d}  fn {row.fn:5d}  partial {row.partial:5d}  "
        f"recall {row.recall:.3f}  precision {row.precision:.3f}"
        for name, row in rows
    ]


def main(argv: list[str]) -> int:
    """Print the report of a detector, named as module:function, on the batch of SEED.

    Why: the session that writes the detectors and a PR's gate run it as one command and read
    only its numbers.

    Contract: argv is [module:function]; the function is imported and scored, and what it prints
    while it runs is thrown away. Prints the lines of `report`, returns 0. A DetectorError or a
    ValueError of `score`: its message, which holds no text, on the error stream, returns 1. Any
    other argv: the usage line on the error stream, returns 2. An import that fails is raised.

    Known limits: a detector that writes to the process's own file handles, not through
    sys.stdout and sys.stderr, is not held back.
    """
    if len(argv) != 1 or ":" not in argv[0]:
        print(USAGE, file=sys.stderr)
        return 2
    module, _, name = argv[0].partition(":")
    detector = getattr(importlib.import_module(module), name)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            scores = score(detector)
    except (DetectorError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    for line in report(scores):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
