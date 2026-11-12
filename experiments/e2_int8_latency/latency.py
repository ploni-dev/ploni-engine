"""The pre-registered page and decision rule of experiment E2.

Why: build-plan.md section 11, E2. Kept apart from the scripts that load
torch and onnxruntime so the rule and the page check can be tested without
either.
"""

from __future__ import annotations

import ctypes
import hashlib
import time
import uuid
from pathlib import Path

# PREREGISTRATION.md, "The number": the median of 5 runs after 1 warm-up run.
WARM_UP_RUNS = 1
TIMED_RUNS = 5
# build-plan.md section 11, E2: "Prediction: 1 to 3 seconds per page."
PREDICTED_LOW_SECONDS = 1.0
PREDICTED_HIGH_SECONDS = 3.0
# build-plan.md section 11, E2: "Threshold: above 10 seconds per page".
THRESHOLD_SECONDS = 10.0
# PREREGISTRATION.md: what "one A4 page of Hebrew" was taken to mean.
PAGE_WORDS = range(400, 501)


def verdict(seconds: float) -> str:
    """Place a per-page time against the plan's prediction.

    Why: the pre-registered decision rule, in code so it cannot drift once the
    number is known.

    Contract: `seconds` is wall clock for one page. "threshold_crossed" above
    10, "inside_prediction" from 1 to 3 inclusive, otherwise
    "outside_prediction", which includes a time under 1 second
    (build-plan.md section 8.2: below the low end is also a finding). Raises
    ValueError when `seconds` is not positive.
    """
    if seconds <= 0:
        raise ValueError("a measured time is positive")
    if seconds > THRESHOLD_SECONDS:
        return "threshold_crossed"
    if PREDICTED_LOW_SECONDS <= seconds <= PREDICTED_HIGH_SECONDS:
        return "inside_prediction"
    return "outside_prediction"


def read_page(path: Path) -> list[str]:
    """Read the test page as paragraphs.

    Why: Phase 3 never lets a window cross a block break, so the page goes to
    the model one paragraph at a time.

    Contract: UTF-8 text, one paragraph per line, blank lines dropped. Raises
    ValueError unless the page holds 400 to 500 whitespace-separated words.
    """
    paragraphs = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    words = sum(len(paragraph.split()) for paragraph in paragraphs)
    if words not in PAGE_WORDS:
        raise ValueError(f"the page holds {words} words, expected {PAGE_WORDS.start} to {PAGE_WORDS.stop - 1}")
    return paragraphs


def timed(label_page) -> tuple[list[float], object]:
    """Run `label_page` to warm up, then on the clock.

    Why: this decides what is warm-up and what is counted, so it is the part of
    the measurement a later edit could change without the number looking wrong.

    Contract: calls `label_page` WARM_UP_RUNS times untimed, then TIMED_RUNS
    times. Returns the wall-clock seconds of each timed call, in order, and
    what the last call returned.
    """
    for _ in range(WARM_UP_RUNS):
        label_page()
    seconds = []
    for _ in range(TIMED_RUNS):
        start = time.perf_counter()
        labels = label_page()
        seconds.append(time.perf_counter() - start)
    return seconds, labels


def describe_power(ac_line_status: int, battery_percent: int) -> str:
    """Put the Windows power status into words for the report.

    Why: the same files took 2.6 times as long in a later run, and the power
    state of the earlier runs had been written down nowhere. The report says it
    itself from now on.

    Contract: the arguments are `ACLineStatus` and `BatteryLifePercent` of
    Windows `GetSystemPowerStatus`: 0 on battery, 1 on mains, 255 unknown; a
    charge of 0 to 100, 255 unknown. An unknown value is said to be unknown.
    """
    source = {0: "on battery", 1: "on mains"}.get(ac_line_status, "power source unknown")
    charge = f"{battery_percent} percent" if 0 <= battery_percent <= 100 else "charge unknown"
    return f"{source}, battery {charge}"


class _PowerStatus(ctypes.Structure):
    """The SYSTEM_POWER_STATUS structure of the Windows API."""

    _fields_ = [
        ("ac_line_status", ctypes.c_ubyte),
        ("battery_flag", ctypes.c_ubyte),
        ("battery_percent", ctypes.c_ubyte),
        ("system_status_flag", ctypes.c_ubyte),
        ("battery_life_time", ctypes.c_ulong),
        ("battery_full_life_time", ctypes.c_ulong),
    ]


def read_power_state() -> str:
    """Read the laptop's power state from Windows, as one line for the report.

    Why: see `describe_power`. The Windows power plan is not printed: on this
    laptop Balanced is the only plan, on mains and on battery alike. The power
    mode of Windows 11 (best efficiency, balanced, best performance) can
    differ between the two, so its identifier is printed as Windows gives it.

    Contract: Windows only. Returns `describe_power` of the current status,
    then the effective power mode as a GUID. Raises OSError if either call
    fails.
    """
    status = _PowerStatus()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        raise OSError("GetSystemPowerStatus failed")
    mode = (ctypes.c_ubyte * 16)()
    if ctypes.windll.powrprof.PowerGetEffectiveOverlayScheme(ctypes.byref(mode)) != 0:
        raise OSError("PowerGetEffectiveOverlayScheme failed")
    described = describe_power(status.ac_line_status, status.battery_percent)
    return f"{described}, power mode {uuid.UUID(bytes_le=bytes(mode))}"


def file_sha256(path: Path) -> str:
    """Return the hex SHA-256 of one file.

    Why: a file size does not identify an ONNX graph. The hash printed by the
    export and again by the timing run shows they are the same file.

    Contract: raises FileNotFoundError if the file is missing.
    """
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()
