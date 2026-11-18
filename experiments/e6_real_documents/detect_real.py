"""Run one detector over one pile of E6's real decisions, by E5's runner.

Why: the detectors must see a real document exactly as they saw E5's generated text, so
that the two kinds of numbers differ only in the text (PREREGISTRATION.md, "What is run").

Contract: `python -I detect_real.py --corpus DIR --pile open|closed --detector KIND
--model-dir M --out FILE [--sha256 HASH] [--onnx-file F] [--budget-seconds N]`, offline,
in the environment of `experiments/e2_int8_latency/requirements.txt`. The arguments after
the pile are those of `experiments/e5_methods/detect.py`, and the file written is the same,
under the corpus name `e6-open` or `e6-closed`. The key must exist and be the frozen one:
no detector is run on a document before its key is frozen. The closed pile is refused
until `results/CHOSEN.md` exists.

Known limits: as E5's `detect.py`. The run file holds places and no text; it is still
written outside the repository, with the other files of the run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]  # `python -I` drops the script folder

import real

import detect


def run(
    corpus_dir: Path, pile: str, detector: str, model_dir: Path, out: Path,
    onnx_file: Path | None = None, budget: float | None = None, sha256: str | None = None,
) -> None:  # fmt: skip
    """Run one detector over one pile.

    Why: the one way a detector reaches a real document: after its key is frozen,
    and for the closed pile after the methods to be judged are written down.

    Contract: as `detect.run_documents`, on the documents `real.load` gives for the pile,
    under the name `e6-<pile>`. Raises ValueError for the closed pile before
    `real.CHOSEN` exists, and as `real.load` and `detect.run_documents` do.
    """
    real.check_closed(pile)
    detect.run_documents(detector, model_dir, f"e6-{pile}", real.load(corpus_dir, pile), out, onnx_file, budget, sha256)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--pile", choices=(real.OPEN, real.CLOSED), required=True)
    parser.add_argument("--detector", choices=("joint", "hf", "onnx"), required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--onnx-file", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--budget-seconds", type=float)
    arguments = parser.parse_args()
    if (arguments.detector == "onnx") != (arguments.onnx_file is not None):
        parser.error("--onnx-file goes with --detector onnx, and only with it")
    run(arguments.corpus, arguments.pile, arguments.detector, arguments.model_dir, arguments.out, arguments.onnx_file, arguments.budget_seconds, arguments.sha256)
