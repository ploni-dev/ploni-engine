"""Turn the hand count into the E1 number and compare it with the prediction.

Why: the count is done by a person, per document, over a few hours. Doing the
arithmetic by hand as well would add a second place for an error that nobody
could re-check, and the comparison with the prediction must be the one written
down in PREREGISTRATION.md before the run, not one chosen after seeing it.

Contract: run as `python tally.py <tally.csv>`; prints the report. The tally
file holds numbers and highlight ids only, never document text.

Known limits: the arithmetic is only as good as the annotation. Nothing here
can tell a careful count from a careless one.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path

# build-plan.md section 11, E1: "Prediction: 85 to 92 percent PERSON recall".
PREDICTED_RECALL_LOW_PERCENT = 85
PREDICTED_RECALL_HIGH_PERCENT = 92
# build-plan.md section 11, E1: "Threshold: below 80 percent".
THRESHOLD_RECALL_PERCENT = 80

ID_LIST_FIELDS = ("not_person_ids", "partial_ids")
COUNT_FIELDS = (
    "missed",
    "missed_other_label",
    "err_ordinary_word",
    "err_proclitic",
    "err_both",
    "err_other",
)
FIELDS = ("doc_id", "per_highlights", *ID_LIST_FIELDS, "found_adjust", *COUNT_FIELDS)


class TallyError(ValueError):
    """The tally file is incomplete or contradicts itself.

    Why: a blank cell read as zero would turn an unannotated document into a
    perfect score, so every inconsistency stops the report instead.

    Contract: the message names the document id and the field.
    """


@dataclass(frozen=True)
class DocumentCount:
    """The hand count for one document, or for all of them pooled.

    Why: one shape for a document and for the pool keeps every formula in one
    place.

    Contract: all fields are counts of person-name mentions except
    `per_highlights` and `not_person`, which count model highlights.
    `found_adjust` is signed: +1 for each extra person inside a highlight that
    holds two names, -1 for each surplus highlight where two adjacent
    highlights cover one name. The four `err_*` fields partition `errors`.
    """

    doc_id: str
    per_highlights: int
    not_person: int
    partial: int
    found_adjust: int
    missed: int
    missed_other_label: int
    err_ordinary_word: int
    err_proclitic: int
    err_both: int
    err_other: int

    @property
    def found(self) -> int:
        """Mentions fully covered by `PER` highlights."""
        return self.per_highlights - self.not_person - self.partial + self.found_adjust

    @property
    def errors(self) -> int:
        """Mentions not found under the strict rule: partial plus missed."""
        return self.partial + self.missed

    @property
    def total(self) -> int:
        """Every person-name mention in the extracted text."""
        return self.found + self.errors


def parse_id_list(cell: str, highest: int) -> frozenset[int]:
    """Read a cell of space-separated highlight numbers.

    Why: recording which highlights were wrong, not just how many, lets a
    second reader re-check the count against the worksheet.

    Contract: a blank cell is the empty set. Raises TallyError for anything
    that is not an integer, an id outside `1..highest`, or a repeated id.
    """
    ids = []
    for token in cell.split():
        if not token.isdecimal() or not 1 <= int(token) <= highest:
            raise TallyError(f"highlight id {token!r} is not a number in 1..{highest}")
        ids.append(int(token))
    if len(ids) != len(set(ids)):
        raise TallyError(f"a highlight id is listed twice: {cell!r}")
    return frozenset(ids)


def _parse_count(row: dict[str, str], field: str, *, signed: bool = False) -> int:
    """Read one integer cell that the annotator must have filled in.

    Why: blank means "not annotated yet", which is different from zero.

    Contract: raises TallyError when the cell is blank, not an integer, or
    negative while `signed` is False.
    """
    cell = (row.get(field) or "").strip()
    if not cell:
        raise TallyError(f"{row.get('doc_id')}: {field} is blank; the document is not annotated")
    try:
        value = int(cell)
    except ValueError:
        raise TallyError(f"{row.get('doc_id')}: {field} is not a whole number") from None
    if value < 0 and not signed:
        raise TallyError(f"{row.get('doc_id')}: {field} is negative")
    return value


def _check_consistent(count: DocumentCount) -> None:
    """Reject a count whose parts cannot all be true together.

    Why: these are the slips a tired annotator makes, and each one would move
    the recall figure without leaving a trace.

    Contract: raises TallyError if `found` is negative, if more misses are
    marked as covered by another label than there are misses, or if the four
    error categories do not add up to `errors`.
    """
    categorised = (
        count.err_ordinary_word + count.err_proclitic + count.err_both + count.err_other
    )
    if count.found < 0:
        raise TallyError(f"{count.doc_id}: more exceptions than highlights")
    if count.missed_other_label > count.missed:
        raise TallyError(f"{count.doc_id}: missed_other_label is larger than missed")
    if categorised != count.errors:
        raise TallyError(
            f"{count.doc_id}: error categories add to {categorised}, "
            f"but partial plus missed is {count.errors}"
        )


def parse_row(row: dict[str, str]) -> DocumentCount:
    """Turn one annotated tally row into a checked DocumentCount.

    Why: every later number is derived from these rows, so a bad row is
    stopped here.

    Contract: `row` maps the names in FIELDS to cell text. Raises TallyError
    for a blank or invalid cell, a highlight id listed as both partial and not
    a person, or an inconsistent count.
    """
    per_highlights = _parse_count(row, "per_highlights")
    not_person = parse_id_list(row.get("not_person_ids") or "", per_highlights)
    partial = parse_id_list(row.get("partial_ids") or "", per_highlights)
    if not_person & partial:
        raise TallyError(f"{row.get('doc_id')}: a highlight is both partial and not a person")
    count = DocumentCount(
        doc_id=row["doc_id"],
        per_highlights=per_highlights,
        not_person=len(not_person),
        partial=len(partial),
        found_adjust=_parse_count(row, "found_adjust", signed=True),
        **{field: _parse_count(row, field) for field in COUNT_FIELDS},
    )
    _check_consistent(count)
    return count


def pool(counts: list[DocumentCount]) -> DocumentCount:
    """Add the counts of several documents into one.

    Why: the primary E1 number is pooled over all documents
    (PREREGISTRATION.md, "Pooling").

    Contract: returns a DocumentCount with `doc_id` "all" and every other
    field summed. An empty list gives all zeros.
    """
    numeric = [name for name in DocumentCount.__dataclass_fields__ if name != "doc_id"]
    return DocumentCount(
        doc_id="all",
        **{name: sum(getattr(count, name) for count in counts) for name in numeric},
    )


def verdict(found: int, total: int) -> str:
    """Place a recall of `found / total` against the plan's prediction.

    Why: this is the pre-registered decision rule, written once in code so the
    comparison cannot drift after the number is known.

    Contract: returns "threshold_crossed" below 80 percent, "inside_prediction"
    from 85 to 92 percent inclusive, otherwise "outside_prediction". Compares
    integers, so no rounding can move a boundary case. Raises TallyError when
    `total` is not positive.
    """
    if total <= 0:
        raise TallyError("no person-name mention was counted, so recall is undefined")
    percent_scaled = found * 100
    if percent_scaled < THRESHOLD_RECALL_PERCENT * total:
        return "threshold_crossed"
    if (
        PREDICTED_RECALL_LOW_PERCENT * total
        <= percent_scaled
        <= PREDICTED_RECALL_HIGH_PERCENT * total
    ):
        return "inside_prediction"
    return "outside_prediction"


def errors_concentrated(count: DocumentCount) -> bool | None:
    """Say whether errors are concentrated in ordinary-word and proclitic forms.

    Why: the plan predicts where the errors fall, not only how many there are.

    Contract: True when more than half of `errors` are in the ordinary-word,
    proclitic or both categories (PREREGISTRATION.md); None when there are no
    errors to place.
    """
    if count.errors == 0:
        return None
    predicted_kinds = count.err_ordinary_word + count.err_proclitic + count.err_both
    return predicted_kinds * 2 > count.errors


def _ratio(numerator: int, denominator: int) -> str:
    """Format a fraction as `n/d = p%`, or `n/a` when the denominator is zero.

    Why: the exact fraction is the measurement; the percentage is for reading.

    Contract: two decimals, for display only. Never used in a comparison.
    """
    if denominator == 0:
        return "n/a"
    return f"{numerator}/{denominator} = {100 * numerator / denominator:.2f}%"


def format_report(counts: list[DocumentCount]) -> str:
    """Build the text report pasted into the findings note.

    Why: one fixed layout, produced by code, so the note carries raw output
    instead of a retyped summary.

    Contract: `counts` holds one checked DocumentCount per document. Returns
    the pooled strict recall with its verdict, the lenient and any-label
    figures, `PER` precision, the error breakdown, the macro mean, and one line
    per document. Raises TallyError when no mention was counted at all.
    """
    pooled = pool(counts)
    with_mentions = [count for count in counts if count.total > 0]
    macro = sum(count.found / count.total for count in with_mentions) / max(len(with_mentions), 1)
    concentrated = {True: "yes", False: "no", None: "n/a"}[errors_concentrated(pooled)]
    lines = [
        f"documents: {len(counts)}",
        f"strict PERSON recall, pooled: {_ratio(pooled.found, pooled.total)}",
        f"verdict: {verdict(pooled.found, pooled.total)} "
        f"(prediction {PREDICTED_RECALL_LOW_PERCENT} to {PREDICTED_RECALL_HIGH_PERCENT} percent, "
        f"threshold below {THRESHOLD_RECALL_PERCENT} percent)",
        f"lenient recall (partial counted as found): "
        f"{_ratio(pooled.found + pooled.partial, pooled.total)}",
        f"any-label recall (found, or missed but under another label): "
        f"{_ratio(pooled.found + pooled.missed_other_label, pooled.total)}",
        f"macro mean of per-document strict recall: {100 * macro:.2f}% "
        f"over {len(with_mentions)} documents with at least one mention",
        f"PER highlight precision: "
        f"{_ratio(pooled.per_highlights - pooled.not_person, pooled.per_highlights)}",
        f"errors: {pooled.errors} (partial {pooled.partial}, missed {pooled.missed}); "
        f"ordinary_word {pooled.err_ordinary_word}, proclitic {pooled.err_proclitic}, "
        f"both {pooled.err_both}, other {pooled.err_other}",
        f"errors concentrated in ordinary-word and proclitic forms: {concentrated}",
        "per document (strict recall, partial, missed):",
    ]
    lines += [
        f"  {count.doc_id}  {_ratio(count.found, count.total)}  "
        f"partial {count.partial}  missed {count.missed}"
        for count in counts
    ]
    return "\n".join(lines)


def write_template(path: Path, per_highlights: dict[str, int]) -> None:
    """Write an unannotated tally file, one row per document.

    Why: the highlight count comes from the model run and must not be retyped;
    everything else is left blank so an unannotated row cannot pass for zeros.

    Contract: `per_highlights` maps document id to its number of `PER`
    highlights; rows are written in the mapping's order. Raises
    FileExistsError if `path` exists, so a re-run never wipes a hand count.
    """
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, restval="")
        writer.writeheader()
        for doc_id, highlights in per_highlights.items():
            writer.writerow({"doc_id": doc_id, "per_highlights": highlights})


def read_tally(path: Path) -> list[DocumentCount]:
    """Read and check every row of an annotated tally file.

    Why: the report must refuse a half-finished count as a whole.

    Contract: accepts UTF-8 with or without a byte order mark, which Excel
    adds on save. Raises TallyError on the first bad row.
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [parse_row(row) for row in csv.DictReader(handle)]


if __name__ == "__main__":
    print(format_report(read_tally(Path(sys.argv[1]))))
