"""Time one page of Hebrew through the INT8 graph, with two FP32 references.

Why: build-plan.md section 11, E2. The prediction, the threshold and what is
timed are in PREREGISTRATION.md and latency.py, committed before the first
timing was taken.

Contract: `python -I measure.py --model-dir M --onnx-dir O`, offline, after
export.py has written O. Prints the hashes of the model files and of the two
graphs, the commit, the power state, the times, the verdict on the INT8 median
and how far each graph's labels agree with PyTorch FP32. Stops before any time
is printed if the weights are not the pinned file or if the FP32 graph
disagrees with PyTorch at any computed position: then the export is wrong and
no time measured on it means anything.

Known limits: see PREREGISTRATION.md. Times include tokenization and exclude
loading the model. The backends run in a fixed order, INT8 first. Windows
only, because of the power state. The files are hashed after the timed passes,
so a run on other weights is timed and then refused.
"""

from __future__ import annotations

import argparse
import os
import platform
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "e1_hebrew_recall")]

import numpy
import onnxruntime
import torch
from run_model import MAX_POSITIONS, TORCH_THREADS, code_revision, load_ner_model, pinned_model_hashes
from transformers import AutoTokenizer

import latency
from export import FP32_NAME, INT8_NAME, NerOnly


def onnx_labeller(path: Path, tokenizer, paragraphs: list[str]):
    """Return a function that tokenizes the page and labels it with one graph."""
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = TORCH_THREADS
    options.inter_op_num_threads = 1
    session = onnxruntime.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])

    def label_page() -> numpy.ndarray:
        encoded = tokenizer(paragraphs, padding=True, return_tensors="np")
        feed = {"input_ids": encoded["input_ids"], "attention_mask": encoded["attention_mask"]}
        return session.run(["logits"], feed)[0].argmax(-1)

    return label_page


def torch_labeller(model, tokenizer, paragraphs: list[str]):
    """Return a function that tokenizes the page and labels it with PyTorch FP32."""
    ner = NerOnly(model).eval()

    def label_page() -> numpy.ndarray:
        encoded = tokenizer(paragraphs, padding=True, return_tensors="pt")
        with torch.inference_mode():
            return ner(encoded["input_ids"], encoded["attention_mask"]).argmax(-1).numpy()

    return label_page


def main(model_dir: Path, onnx_dir: Path) -> None:
    """Time the three backends one after the other and print the report."""
    torch.set_num_threads(TORCH_THREADS)
    paragraphs = latency.read_page(HERE / "page.txt")
    power = latency.read_power_state()
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    encoded = tokenizer(paragraphs, padding=True, return_tensors="np", return_special_tokens_mask=True)
    computed = encoded["attention_mask"].astype(bool)
    # [CLS] and [SEP] of each paragraph are computed but are not text.
    text = computed & ~encoded["special_tokens_mask"].astype(bool)
    if computed.shape[1] > MAX_POSITIONS:
        raise ValueError(f"a paragraph encodes to {computed.shape[1]} positions, limit {MAX_POSITIONS}")

    # One backend in memory at a time: the laptop cannot hold all three.
    results = {}
    for name, file in (("onnx int8", INT8_NAME), ("onnx fp32", FP32_NAME)):
        results[name] = latency.timed(onnx_labeller(onnx_dir / file, tokenizer, paragraphs))
    model, _ = load_ner_model(model_dir)
    results["torch fp32"] = latency.timed(torch_labeller(model, tokenizer, paragraphs))
    other = model.config.label2id["O"]
    reference = results["torch fp32"][1]
    # PREREGISTRATION.md: if the export is wrong, no time is reported. Every
    # computed position is compared, the [CLS] and [SEP] ones too.
    if not (results["onnx fp32"][1] == reference)[computed].all():
        sys.exit("the FP32 graph disagrees with PyTorch: the export is wrong, no time is reported")
    # Hashed after the clock has stopped and before anything is printed: reading
    # 1.7 GB of files just before the timed passes would be work the earlier
    # runs did not do. Weights that are not the pinned file raise here.
    hashes = pinned_model_hashes(model_dir)
    hashes |= {name: latency.file_sha256(onnx_dir / name) for name in (INT8_NAME, FP32_NAME)}
    code = code_revision()

    words = sum(len(paragraph.split()) for paragraph in paragraphs)
    print(f"E2 CPU latency, model revision {model_dir.name}")
    for name, digest in hashes.items():
        print(f"{name} sha256 {digest}")
    print(f"code {code['commit']}{', uncommitted changes' if code['dirty'] else ''}")
    print(f"power before the timed passes: {power}")
    print(
        f"page: {len(paragraphs)} paragraphs, {words} words, {int(computed.sum())} positions "
        f"of which {int(text.sum())} are text, batch {computed.shape}"
    )
    print(f"machine: {platform.processor()}, {os.cpu_count()} logical processors, threads {TORCH_THREADS}")
    print(f"torch {torch.__version__}, onnxruntime {onnxruntime.__version__}")
    print(
        f"{'backend':<12} {'median':>7} {'min':>7} {'max':>7}   "
        f"seconds, {latency.TIMED_RUNS} runs after {latency.WARM_UP_RUNS} warm-up"
    )
    for name, (seconds, _) in results.items():
        print(f"{name:<12} {statistics.median(seconds):>7.3f} {min(seconds):>7.3f} {max(seconds):>7.3f}")
    print(f"verdict on the onnx int8 median: {latency.verdict(statistics.median(results['onnx int8'][0]))}")
    for name, (_, labels) in results.items():
        same = int((labels == reference)[text].sum())
        print(
            f"{name:<12} labels equal to torch fp32: {same}/{int(text.sum())} text positions, "
            f"not labelled O: {int((labels != other)[text].sum())}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--onnx-dir", type=Path, required=True)
    arguments = parser.parse_args()
    main(arguments.model_dir, arguments.onnx_dir)
