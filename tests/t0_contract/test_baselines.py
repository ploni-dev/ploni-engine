"""The shape of eval/baselines.json: one entry per metric of the plan, each value empty or a number.

Why: build-plan.md section 7, principle 3: "`eval/baselines.json` holds every metric gate", and
Phase 0 asks for its skeleton (issue #29). The harness of Phase 5 reads this file; a broken file,
a missing metric, or a value that is not a number would only show there.

Test matrix:

Equivalence classes:
  EC1  the file                     a JSON object with "about" (text) and "metrics" (an object)
  EC2  the names under "metrics"    exactly the rows of the T6 table of build-plan.md section 7
  EC3  each value                   null (not set yet), a number, or an object of numbers (per
                                    type)

Boundaries:
  B1  a value of true or false      not a number, though Python counts bool as int

Not applicable: the Hebrew and document axes: the input is one JSON file the repository holds.
"""

import json
from pathlib import Path

BASELINES = Path(__file__).resolve().parents[2] / "eval" / "baselines.json"

# build-plan.md section 7, T6: one name per row of the table, the first row split into its
# three metrics and the last into its three.
METRICS = {
    "per_type_precision",
    "per_type_recall",
    "per_type_f1",
    "pre_review_zero_leak_rate",
    "post_review_zero_leak_rate",
    "review_items_per_page",
    "consistency",
    "over_merge_count",
    "under_merge_count",
    "verification_catch_rate",
    "utility_preservation",
    "numeric_conservatism_violations",
    "runtime_per_page_seconds",
    "runtime_60_pages_seconds",
    "peak_rss_mb",
}


def is_number(value: object) -> bool:
    """Say whether `value` is an int or a float, and not a bool."""
    return isinstance(value, int | float) and not isinstance(value, bool)


def is_baseline(value: object) -> bool:
    """Say whether `value` may stand under "metrics": null, a number, or an object of numbers."""
    if isinstance(value, dict):
        return all(is_number(item) for item in value.values())
    return value is None or is_number(value)


def test_ec1_the_file() -> None:
    data = json.loads(BASELINES.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and set(data) == {"about", "metrics"}
    assert isinstance(data["about"], str) and data["about"]
    assert isinstance(data["metrics"], dict)


def test_ec2_the_names() -> None:
    assert set(json.loads(BASELINES.read_text(encoding="utf-8"))["metrics"]) == METRICS


def test_ec3_the_values() -> None:
    metrics = json.loads(BASELINES.read_text(encoding="utf-8"))["metrics"]
    assert [name for name, value in metrics.items() if not is_baseline(value)] == []
    assert [is_baseline(value) for value in (None, 0.98, 3, {"IL_ID": 1.0}, "0.98", [1.0], {"IL_ID": None})] == [True, True, True, True, False, False, False]


def test_b1_a_bool_is_not_a_number() -> None:
    assert [is_baseline(value) for value in (True, False, {"IL_ID": True})] == [False, False, False]
