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
A group of key items (an Item's group, as the names that stand once) has a line of its own,
named type:group: tp, its items a detection matches exactly, and fn, the rest; no detection is
of a group, so its fp stay on its type's line, and the group's line has none. `report` gives
one line per type, one per group, and one for the total; `main` prints it for a named detector.

A type the key does not hold, which only a detector names, is shown as OTHER and its number,
never by its name, so that no text can be printed through a type's name.

Known limits: near misses are not counted apart, a detection of one is a fp of its type.
"""

import builtins
import contextlib
import importlib
import io
import logging
import os
import sys
import traceback
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass

from eval.heldout.generator import GROUP_MARK, Batch, build

Detection = tuple[int, int, str]
Detector = Callable[[str], Iterable[Detection]]
Span = tuple[int, int, int, str]
TOTAL = "TOTAL"
USAGE = "usage: python -m eval.heldout.scorer <module>:<function>"
# A detection is a triple: start, end, type.
TRIPLE = 3
# The process's file handles of the output and the error stream.
HANDLES = (1, 2)
OTHER = "OTHER"
OWN_CLASS = "an error of its own class"


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
    returned, sorted by name. total holds the sums of per_type. per_group maps each group of the
    key, named type:group and sorted, to its tp and fn.
    """

    per_type: dict[str, Counts]
    total: Counts
    per_group: dict[str, Counts]


def _checked(detections: Iterable[object], doc: int, length: int) -> list[tuple[int, int, str]]:
    """Return a document's detections as triples; one that is no span of it is an error, not a fp.

    The error names the document, the detection and the numbers, never text. A start or an end
    must be an int itself, and a type a str itself, not a class of the detector's (nor a bool),
    whose own formatting could print text (scorer review 3, finding 6).
    """
    found = []
    for index, detection in enumerate(detections):
        where = f"document {doc}, detection {index}"
        if not isinstance(detection, tuple | list) or len(detection) != TRIPLE:
            raise ValueError(f"{where}: not a (start, end, type) triple")
        start, end, kind = detection
        if type(start) is not int or type(end) is not int or type(kind) is not str:
            raise ValueError(f"{where}: start and end must be int and type a str")
        if not 0 <= start < end <= length:
            raise ValueError(f"{where}: span ({start}, {end}) is not inside a text of length {length}")
        found.append((start, end, kind))
    return found


class DetectorError(Exception):
    """A detector raised, or exited, while it read a document of the batch.

    Why: the detector's own message, and its traceback, may quote the document, which the session
    that writes the detectors must not see. Contract: the message names the document's index and
    the class of the error, by its name when it is a built-in error and as OWN_CLASS for any
    other, whose name the detector or a library chose; the detector's error is not chained to it.
    """


def _class_name(error: BaseException) -> str:
    """Return the name of an error's class when it is a built-in error, else OWN_CLASS."""
    kind = type(error)
    return kind.__name__ if getattr(builtins, kind.__name__, None) is kind else OWN_CLASS


def _detections(detector: Detector, text: str, doc: int) -> list[object]:
    """Return what the detector returns for one text, any error or exit of its turned into a DetectorError.

    An interrupt stops the run as before, raised again with no message and nothing chained.
    """
    try:
        return list(detector(text))
    except KeyboardInterrupt:
        raise KeyboardInterrupt from None
    except BaseException as error:  # noqa: BLE001 re-raised as DetectorError at once, without its message
        raise DetectorError(f"document {doc}: the detector raised {_class_name(error)}") from None


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
    the detector raises or exits, with the type of its error only.

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
    per_group: dict[str, Counts] = defaultdict(Counts)
    for item in (item for item in batch.key if item.group):
        counts = per_group[f"{item.type}{GROUP_MARK}{item.group}"]
        if (item.doc, item.start, item.end, item.type) in found:
            counts.tp += 1
        else:
            counts.fn += 1
    return Scores(rows, total, dict(sorted(per_group.items())))


def report(scores: Scores) -> list[str]:
    """Return the lines that show scores: one per type, sorted, one per group, then the total.

    Why: what a PR body and the session that writes the detectors read; names and numbers only.

    Contract: a type's line is its name, then tp, fp, fn, partial, recall and precision, each
    after its label, recall and precision with three decimals; a type with no item in the key
    (tp and fn both 0), which only a detector named, is shown as OTHER_1, OTHER_2 and so on, in
    the order of its name; a group's line is its name, tp, fn and recall. The last line is TOTAL's.
    """
    def line(name: str, row: Counts) -> str:
        return f"{name:<17} tp {row.tp:5d}  fp {row.fp:5d}  fn {row.fn:5d}  partial {row.partial:5d}  recall {row.recall:.3f}  precision {row.precision:.3f}"

    named, others = [], 0
    for name, row in scores.per_type.items():
        if row.tp + row.fn == 0:
            others += 1
            name = f"{OTHER}_{others}"
        named.append(line(name, row))
    groups = [f"{name:<17} tp {row.tp:5d}  fn {row.fn:5d}  recall {row.recall:.3f}" for name, row in scores.per_group.items()]
    return [*named, *groups, line(TOTAL, scores.total)]


@contextlib.contextmanager
def _held_back() -> Iterator[None]:
    """Hold back, while the block runs, all a detector could write to the screen as it reads.

    Why: the session that writes the detectors reads what `main` prints, and a detector's own
    output may quote a document (review 1 of the branch, finding 2; scorer reviews 1 and 2).
    Contract: inside the block logging is off; sys.stdout and sys.stderr, and the interpreter's
    original sys.__stdout__ and sys.__stderr__, are buffers thrown away; and the process's file
    handles 1 and 2 lead to the null device, so that a stream or a logging handler made before
    the block, os.write and a C extension write nothing to the screen either. On leaving, the
    original streams are flushed into the null device, a stream the detector closed passed over
    (scorer review 3, finding 8), then everything is put back as it was. Raises OSError when the
    null device or a file handle cannot be opened or copied.
    """
    for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__):
        if stream is not None:
            stream.flush()
    was_off, originals = logging.root.manager.disable, (sys.__stdout__, sys.__stderr__)
    null = os.open(os.devnull, os.O_WRONLY)
    saved = [os.dup(handle) for handle in HANDLES]
    logging.disable(logging.CRITICAL)
    for handle in HANDLES:
        os.dup2(null, handle)
    # Through the module's namespace, as the two are final names to a type checker (scorer
    # review 3, finding 10).
    vars(sys).update(__stdout__=io.StringIO(), __stderr__=io.StringIO())
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            yield
    finally:
        for stream in originals:
            if stream is not None:
                with contextlib.suppress(ValueError, OSError):
                    stream.flush()
        vars(sys).update(__stdout__=originals[0], __stderr__=originals[1])
        for handle, copy in zip(HANDLES, saved, strict=True):
            os.dup2(copy, handle)
            os.close(copy)
        os.close(null)
        logging.disable(was_off)


def main(argv: list[str]) -> int:
    """Print the report of a detector, named as module:function, on the batch of SEED.

    Why: the session that writes the detectors and a PR's gate run it as one command and read
    only its numbers.

    Contract: argv is [module:function]; the function is imported and scored, all it writes
    while it runs held back as `_held_back` says. Prints the lines of `report`, returns 0. A
    DetectorError (for any error or exit of the detector) or a ValueError of `score`: its
    message, which holds no text, on the error stream, returns 1. An interrupt is raised with no
    message. Any other argv: the usage line on the error stream, returns 2. An import that
    fails is raised.

    Known limits: the detector is Ploni's own code, run on invented documents, so what this
    guards against is a slip, such as a debug print or a log line, not a detector built to leak;
    what keeps the batch from the session that writes the detectors is that session's isolation
    from it (Achia, 2026-11-26, issue 283), not a sandbox here. Still not held back are what the
    detector writes through a copy of file handle 1 or 2 that it made before scoring (os.dup at
    import); what its module prints while it is imported, before scoring starts; what it writes
    to a console or a terminal it opens itself; and what a process it started writes after the
    command has ended. When `main` is called from Python rather than run as the command, what a
    thread, an atexit handler or a finalizer of the detector writes after `main` has returned is
    not held back either; the command ends without running them, also when `main` raises (scorer
    review 3, finding 7; scorer review 4, finding 12).
    """
    if len(argv) != 1 or ":" not in argv[0]:
        print(USAGE, file=sys.stderr)
        return 2
    module, _, name = argv[0].partition(":")
    detector = getattr(importlib.import_module(module), name)
    try:
        with _held_back():
            scores = score(detector)
    except (DetectorError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    for line in report(scores):
        print(line)
    return 0


if __name__ == "__main__":
    # Ends at once after the report, also when main raises (exit 1, its traceback written first),
    # so that a thread or an atexit handler of the detector that would print at shutdown never
    # runs (scorer review 3, finding 7; scorer review 4, finding 12).
    code = 1
    try:
        code = main(sys.argv[1:])
    finally:
        if sys.exc_info()[0] is not None:
            traceback.print_exc()
        for stream in (sys.stdout, sys.stderr):
            with contextlib.suppress(ValueError, OSError):
                stream.flush()
        os._exit(code)
