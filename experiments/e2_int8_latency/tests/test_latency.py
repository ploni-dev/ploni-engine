"""Test matrix for latency.py (experiment E2, build-plan.md section 11).

verdict(seconds)
  B1  0.99  -> outside_prediction   (below the low end is a finding too, section 8.2)
  B2  1.0   -> inside_prediction
  B3  3.0   -> inside_prediction
  B4  3.01  -> outside_prediction
  B5  10.0  -> outside_prediction   (the threshold is "above 10 seconds")
  B6  10.01 -> threshold_crossed
  E1  0 or negative -> ValueError
  Invariant, 500 generated cases: threshold_crossed iff seconds > 10

read_page(path)
  EC1  the shipped page.txt: 400 to 500 words, the pre-registered size of "one A4 page"
  EC2  blank lines are dropped, one paragraph per line
  E1   a page outside 400 to 500 words -> ValueError
  Adversarial: no nine-digit number on the shipped page passes the Israeli ID
  check digit (build-plan.md Phase 7: such a value may be a real identifier)
"""

import random
import re
from pathlib import Path

import pytest

import latency

GENERATED_CASES = 500  # CLAUDE.md: invariants get 500 generated cases


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0.99, "outside_prediction"),
        (1.0, "inside_prediction"),
        (3.0, "inside_prediction"),
        (3.01, "outside_prediction"),
        (10.0, "outside_prediction"),
        (10.01, "threshold_crossed"),
    ],
)
def test_verdict_boundaries(seconds, expected):
    assert latency.verdict(seconds) == expected


@pytest.mark.parametrize("seconds", [0, -1.5])
def test_e1_verdict_rejects_a_non_positive_time(seconds):
    with pytest.raises(ValueError):
        latency.verdict(seconds)


def test_invariant_threshold_crossed_iff_above_ten_seconds():
    rng = random.Random(20261111)
    for _ in range(GENERATED_CASES):
        seconds = rng.uniform(0.001, 30)
        assert (latency.verdict(seconds) == "threshold_crossed") is (seconds > 10)


def test_ec1_shipped_page_is_one_a4_page():
    paragraphs = latency.read_page(Path(latency.__file__).with_name("page.txt"))
    assert 400 <= sum(len(p.split()) for p in paragraphs) <= 500


def test_ec2_read_page_drops_blank_lines(tmp_path):
    path = tmp_path / "page.txt"
    path.write_text("\n".join(["מילה " * 250, "", "  ", "מילה " * 200]) + "\n", encoding="utf-8")
    assert [len(p.split()) for p in latency.read_page(path)] == [250, 200]


@pytest.mark.parametrize("words", [399, 501])
def test_e1_read_page_rejects_a_page_of_the_wrong_size(tmp_path, words):
    path = tmp_path / "page.txt"
    path.write_text("מילה " * words, encoding="utf-8")
    with pytest.raises(ValueError):
        latency.read_page(path)


def passes_id_check_digit(digits: str) -> bool:
    # build-plan.md Phase 1, israeli_id_checksum_ok.
    doubled = (int(ch) * (1 + i % 2) for i, ch in enumerate(digits))
    return sum(n if n < 10 else n - 9 for n in doubled) % 10 == 0


def test_adversarial_page_holds_no_checksum_valid_identifier():
    assert passes_id_check_digit("000000018") and not passes_id_check_digit("000000019")
    text = Path(latency.__file__).with_name("page.txt").read_text(encoding="utf-8")
    assert [n for n in re.findall(r"\d{9}", text) if passes_id_check_digit(n)] == []
