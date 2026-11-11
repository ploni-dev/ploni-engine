"""The pre-registered page and decision rule of experiment E2.

Why: build-plan.md section 11, E2. Kept apart from the scripts that load
torch and onnxruntime so the rule and the page check can be tested without
either.
"""

from __future__ import annotations

from pathlib import Path

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
