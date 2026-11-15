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
  Adversarial: no number of eight or nine digits on the shipped page passes the
  Israeli ID check digit (build-plan.md Phase 7: such a value may be a real
  identifier; an older ID is often written with eight digits, the leading zero
  dropped)

timed(label_page)
  EC1  the function is called once to warm up and five times on the clock:
       six calls, five durations, and the labels of the last call returned
  B1   every duration is positive and none includes the warm-up call

file_sha256(path)
  EC1  the SHA-256 of the file's bytes
  E1   a missing file -> FileNotFoundError

describe_power(ac_line_status, battery_percent)  (Windows GetSystemPowerStatus values)
  EC1  on mains (1) and on battery (0), with the charge
  B1   charge 0 and charge 100
  E1   source unknown (255); charge unknown (255) -> said in words, never a guess

read_power_state()  (Windows only)
  EC1  on this machine it returns the source, the charge, the energy saver
       flag, the power mode in effect and the power mode set
"""

import hashlib
import random
import re
import sys
import time
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
    rng = random.Random(20261111)  # noqa: S311 seeded on purpose, so the same input is drawn on every run
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
    assert passes_id_check_digit("18".zfill(9))
    assert [n for n in re.findall(r"\d{8,9}", text) if passes_id_check_digit(n.zfill(9))] == []


def test_ec1_timed_warms_up_once_and_times_five_runs():
    calls = []

    def label_page():
        calls.append(len(calls))
        time.sleep(0.2 if len(calls) == 1 else 0.001)  # only the warm-up call is slow
        return f"labels of call {len(calls)}"

    seconds, labels = latency.timed(label_page)
    assert (latency.WARM_UP_RUNS, latency.TIMED_RUNS) == (1, 5)  # PREREGISTRATION.md
    assert len(calls) == 6
    assert len(seconds) == 5
    assert labels == "labels of call 6"
    assert all(0 < duration < 0.1 for duration in seconds)  # B1: the slow warm-up is not among them


def test_ec1_file_sha256(tmp_path):
    path = tmp_path / "graph.onnx"
    path.write_bytes(b"not a real graph")
    assert latency.file_sha256(path) == hashlib.sha256(b"not a real graph").hexdigest()


def test_e1_file_sha256_of_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        latency.file_sha256(tmp_path / "absent.onnx")


@pytest.mark.parametrize(
    ("ac_line", "percent", "expected"),
    [
        (1, 80, "on mains, battery 80 percent"),
        (0, 38, "on battery, battery 38 percent"),
        (0, 0, "on battery, battery 0 percent"),
        (1, 100, "on mains, battery 100 percent"),
        (255, 50, "power source unknown, battery 50 percent"),
        (1, 255, "on mains, battery charge unknown"),
    ],
)
def test_describe_power(ac_line, percent, expected):
    assert latency.describe_power(ac_line, percent) == expected


@pytest.mark.skipif(sys.platform != "win32", reason="reads the Windows power status")
def test_read_power_state_names_the_flag_and_both_power_modes():
    state = latency.read_power_state()
    guid = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    assert re.fullmatch(
        rf"(on mains|on battery|power source unknown), battery (\d+ percent|charge unknown), "
        rf"energy saver flag [01], power mode in effect {guid}, power mode set {guid}",
        state,
    )
