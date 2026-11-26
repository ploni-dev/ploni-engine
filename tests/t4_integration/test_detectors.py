"""Module suite for eval/detectors.py: `detect_all` has the shape the held-out scorer calls.

Why: `CLAUDE.md`, Tests: every module gets a suite over its public surface. The scorer takes "a
callable from a document's text to a list of (start, end, type)", starts and ends ints, the type
a str, each a span of its text (PR #288). This holds `detect_all` to that shape, with the
detectors of today (none) and with the conforming detector of the T0 suite, over texts made up
here; it does not run the scorer, which tests other than the batch's own may not read.

Matrix:
  M1  over made-up texts, with no detector and with Digits: a list of triples of (int, int,
      str), each 0 <= start < end <= len(text)
  M2  `eval.detectors:detect_all`, the name the workflow gives the scorer, names a function that exists:
      the module is eval.detectors and the name is its function (an import by a computed
      name is refused in tests/, so the scorer's own resolving is not run here)
"""

from eval import detectors
from tests.detector_contract import Digits

TEXTS = ("", "7", "ת.ז. 123456782", "עו״ד כהן, ת\"א 12345-01-20", "שָׁלוֹם 42\nשורה 2", "‏תיק 55‎ 📄 9")


def test_m1_the_shape_the_scorer_calls() -> None:
    for text in TEXTS:
        for found in (detectors.detect_all(text), detectors.detect_all(text, (Digits(),))):
            assert isinstance(found, list)
            for start, end, kind in found:
                assert type(start) is int and type(end) is int and type(kind) is str
                assert 0 <= start < end <= len(text)


def test_m2_the_name_the_workflow_gives_resolves() -> None:
    module, _, function = "eval.detectors:detect_all".partition(":")
    assert module == detectors.__name__
    assert getattr(detectors, function) is detectors.detect_all
