"""Test matrix for tally: parse_id_list, parse_row, pool, verdict, errors_concentrated,
format_report, write_template and read_tally.

parse_id_list
  EC1  blank cell                      -> empty set
  EC2  "3 17 22"                       -> {3, 17, 22}
  B1   lowest and highest legal id     -> accepted
  E1   id of zero or above the highest -> TallyError
  E2   not a number                    -> TallyError
  E3   the same id twice               -> TallyError

parse_row
  EC3  fully annotated row             -> counts, found derived
  EC4  found_adjust positive and negative
  E4   a count left blank (document not annotated yet) -> TallyError
  E5   negative count                  -> TallyError
  E6   an id in both lists             -> TallyError
  A1   a bad id list names the document and the column, and never repeats the cell
  EC9  public_ids and missed_public split found and errors into public figures
       and private parties, and the two groups add up to the whole
  EC10 found_adjust_public moves the public count only
  E12  a public id that is also not a person; missed_public above missed;
       public found below zero or above found -> TallyError

gap_verdict  (pre-registration: 10 points, at least 30 mentions per group)
  B10  29 mentions in either group     -> too_few_mentions
  B11  exactly 10 points               -> large_gap
  B12  9.9 points                      -> small_gap
  EC11 private recall above public     -> large_gap as well
  E7   categories do not sum to missed plus partial -> TallyError
  E8   missed_other_label above missed -> TallyError
  E9   derived found below zero        -> TallyError

verdict  (build-plan.md section 11: prediction 85 to 92, threshold below 80)
  B2   79 of 100, and 7999 of 10000    -> threshold_crossed
  B3   exactly 80 of 100               -> outside_prediction
  B4   8499 of 10000                   -> outside_prediction
  B5   exactly 85 and exactly 92       -> inside_prediction
  B6   9201 of 10000, and 100 of 100   -> outside_prediction
  E10  total of zero                   -> TallyError
  P1   500 generated cases agree with exact Fraction comparison

errors_concentrated  (pre-registration: more than half)
  B7   exactly half                    -> False
  B8   one more than half              -> True
  B9   no errors at all                -> None

pool, format_report, template round trip
  EC5  pool adds every count
  EC6  report carries the pooled fraction, the verdict and one line per document
  EC7  a document with no person mention prints n/a and does not break the pool
  EC8  template written, filled in, read back
  E11  template never overwrites an existing tally -> FileExistsError
  EC12 template lists the placeholder highlights the run found in not_person_ids,
       and leaves that cell empty for a document with none
"""

from __future__ import annotations

import csv
import random
from fractions import Fraction
from pathlib import Path

import pytest

from tally import (
    FIELDS,
    DocumentCount,
    TallyError,
    errors_concentrated,
    format_report,
    gap_verdict,
    parse_id_list,
    parse_row,
    pool,
    read_tally,
    verdict,
    write_template,
)

GENERATED_CASES = 500  # CLAUDE.md Tests: invariants 500 generated cases
SEED = 20261111


def row(**overrides: str) -> dict[str, str]:
    base = {
        "doc_id": "doc01",
        "per_highlights": "20",
        "not_person_ids": "4",
        "partial_ids": "7 9",
        "found_adjust": "0",
        "missed": "3",
        "missed_other_label": "1",
        "err_ordinary_word": "2",
        "err_proclitic": "1",
        "err_both": "1",
        "err_other": "1",
        "found_adjust_public": "0",
        "missed_public": "0",
    }
    return {**base, **overrides}


def count(found: int, partial: int, missed: int, concentrated: int = 0) -> DocumentCount:
    errors = partial + missed
    return DocumentCount(
        doc_id="doc01",
        per_highlights=found + partial,
        not_person=0,
        partial=partial,
        found_adjust=0,
        missed=missed,
        missed_other_label=0,
        err_ordinary_word=concentrated,
        err_proclitic=0,
        err_both=0,
        err_other=errors - concentrated,
    )


def test_ec1_blank_id_list():
    assert parse_id_list("", 10) == frozenset()
    assert parse_id_list("   ", 10) == frozenset()


def test_ec2_id_list():
    assert parse_id_list("3 17 22", 30) == frozenset({3, 17, 22})


def test_b1_lowest_and_highest_id():
    assert parse_id_list("1 30", 30) == frozenset({1, 30})


@pytest.mark.parametrize("cell", ["0", "31", "-2"])
def test_e1_id_out_of_range(cell: str):
    with pytest.raises(TallyError):
        parse_id_list(cell, 30)


def test_e2_id_not_a_number():
    with pytest.raises(TallyError):
        parse_id_list("3 x", 30)


def test_e3_id_repeated():
    with pytest.raises(TallyError):
        parse_id_list("3 3", 30)


def test_ec3_complete_row():
    parsed = parse_row(row())
    assert (parsed.not_person, parsed.partial, parsed.missed) == (1, 2, 3)
    assert parsed.found == 20 - 1 - 2
    assert parsed.total == 17 + 2 + 3
    assert parsed.errors == 5


def test_ec4_found_adjust_both_signs():
    assert parse_row(row(found_adjust="2")).found == 19
    assert parse_row(row(found_adjust="-1")).found == 16


@pytest.mark.parametrize("field", ["found_adjust", "missed", "err_other", "per_highlights"])
def test_e4_blank_count_means_not_annotated(field: str):
    with pytest.raises(TallyError):
        parse_row(row(**{field: ""}))


def test_e5_negative_count():
    with pytest.raises(TallyError):
        parse_row(row(missed="-1"))


def test_e6_id_in_both_lists():
    with pytest.raises(TallyError):
        parse_row(row(not_person_ids="7"))


def test_e7_categories_do_not_sum_to_errors():
    with pytest.raises(TallyError):
        parse_row(row(err_other="2"))


def test_e8_other_label_above_missed():
    with pytest.raises(TallyError):
        parse_row(row(missed_other_label="4"))


def test_e9_found_below_zero():
    with pytest.raises(TallyError):
        parse_row(row(found_adjust="-18"))


@pytest.mark.parametrize(("found", "total"), [(79, 100), (7999, 10000), (0, 5)])
def test_b2_below_eighty_crosses_threshold(found: int, total: int):
    assert verdict(found, total) == "threshold_crossed"


def test_b3_exactly_eighty_does_not_cross():
    assert verdict(80, 100) == "outside_prediction"


def test_b4_just_below_eighty_five():
    assert verdict(8499, 10000) == "outside_prediction"


@pytest.mark.parametrize("found", [85, 88, 92])
def test_b5_prediction_range_is_inclusive(found: int):
    assert verdict(found, 100) == "inside_prediction"


@pytest.mark.parametrize(("found", "total"), [(9201, 10000), (100, 100)])
def test_b6_above_ninety_two(found: int, total: int):
    assert verdict(found, total) == "outside_prediction"


def test_e10_total_of_zero():
    with pytest.raises(TallyError):
        verdict(0, 0)


def test_p1_verdict_agrees_with_exact_fractions():
    rng = random.Random(SEED)
    for _ in range(GENERATED_CASES):
        total = rng.randint(1, 3000)
        found = rng.randint(0, total)
        recall = Fraction(found, total)
        if recall < Fraction(80, 100):
            expected = "threshold_crossed"
        elif Fraction(85, 100) <= recall <= Fraction(92, 100):
            expected = "inside_prediction"
        else:
            expected = "outside_prediction"
        assert verdict(found, total) == expected


def test_b7_exactly_half_is_not_concentrated():
    assert errors_concentrated(count(10, 2, 2, concentrated=2)) is False


def test_b8_more_than_half_is_concentrated():
    assert errors_concentrated(count(10, 2, 2, concentrated=3)) is True


def test_b9_no_errors():
    assert errors_concentrated(count(10, 0, 0)) is None


def test_ec5_pool_adds_every_count():
    pooled = pool([parse_row(row()), parse_row(row(doc_id="doc02"))])
    assert pooled.doc_id == "all"
    assert (pooled.per_highlights, pooled.found, pooled.total) == (40, 34, 44)
    assert (pooled.partial, pooled.missed, pooled.missed_other_label) == (4, 6, 2)
    assert pooled.err_ordinary_word == 4


def test_ec6_report_carries_fraction_verdict_and_documents():
    report = format_report([count(88, 4, 8, concentrated=7), count(40, 0, 0)])
    assert "128/140" in report
    assert "inside_prediction" in report
    assert "88/100" in report
    assert "40/40" in report


def test_ec7_document_without_person_mentions():
    report = format_report([count(0, 0, 0), count(9, 0, 1)])
    assert "n/a" in report
    assert "9/10" in report


def test_ec8_template_round_trip(tmp_path: Path):
    path = tmp_path / "tally.csv"
    write_template(path, {"doc01": 20, "doc02": 0}, {"doc01": [], "doc02": []})
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [r["doc_id"] for r in rows] == ["doc01", "doc02"]
    assert rows[0]["per_highlights"] == "20"
    assert rows[0]["missed"] == ""
    assert rows[0]["public_ids"] == ""

    with pytest.raises(TallyError):
        read_tally(path)  # nothing annotated yet

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(row())
    assert read_tally(path) == [parse_row(row())]


def test_e11_template_never_overwrites(tmp_path: Path):
    path = tmp_path / "tally.csv"
    path.write_text("annotated by hand", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_template(path, {"doc01": 1}, {"doc01": []})
    assert path.read_text(encoding="utf-8") == "annotated by hand"


def test_a1_bad_id_list_names_document_and_column_without_the_cell():
    with pytest.raises(TallyError) as caught:
        parse_row(row(doc_id="doc04", partial_ids="7,9 יעקב"))
    message = str(caught.value)
    assert "doc04" in message and "partial_ids" in message
    assert "7,9" not in message and "יעקב" not in message


def test_ec9_public_and_private_split():
    split = parse_row(row(public_ids="1 2 7", missed_public="1"))
    assert (split.public_found, split.public_errors) == (2, 2)
    assert (split.private_found, split.private_errors) == (15, 3)
    assert split.public_total + split.private_total == split.total
    pooled = pool([split, split])
    assert (pooled.public_found, pooled.private_errors) == (4, 6)


def test_ec10_found_adjust_public_moves_only_the_public_count():
    adjusted = parse_row(row(public_ids="1 2", found_adjust="1", found_adjust_public="1"))
    assert (adjusted.found, adjusted.public_found, adjusted.private_found) == (18, 3, 15)


@pytest.mark.parametrize(
    "overrides",
    [
        {"public_ids": "4"},
        {"missed_public": "4"},
        {"found_adjust_public": "-1"},
        {"public_ids": "1", "found_adjust_public": "17"},
    ],
    ids=["public_and_not_a_person", "more_than_missed", "below_zero", "above_found"],
)
def test_e12_inconsistent_public_counts(overrides):
    with pytest.raises(TallyError, match="doc01"):
        parse_row(row(**overrides))


@pytest.mark.parametrize(
    ("public", "private", "expected"),
    [
        ((29, 29), (50, 100), "too_few_mentions"),
        ((30, 30), (20, 29), "too_few_mentions"),
        ((27, 30), (80, 100), "large_gap"),
        ((27, 30), (801, 1000), "small_gap"),
        ((24, 30), (90, 100), "large_gap"),
    ],
)
def test_gap_verdict_boundaries(public, private, expected):
    assert gap_verdict(*public, *private) == expected


def test_report_carries_both_groups_and_the_gap():
    report = format_report([parse_row(row(public_ids="1 2 7", missed_public="1"))])
    assert "public figures: 2/4" in report
    assert "private parties: 15/18" in report
    assert "too_few_mentions" in report


def test_ec12_template_lists_placeholder_highlights_as_not_person(tmp_path: Path):
    path = tmp_path / "tally.csv"
    write_template(path, {"doc01": 20, "doc02": 3}, {"doc01": [2, 7, 19], "doc02": []})
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [r["not_person_ids"] for r in rows] == ["2 7 19", ""]
    assert rows[0]["missed"] == ""
