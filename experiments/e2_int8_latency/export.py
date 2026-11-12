"""Export the encoder and NER head to ONNX, then quantize to dynamic INT8.

Why: build-plan.md section 11, E2, "Export to ONNX, quantize dynamic INT8".
Only the encoder and the NER head are exported, the fallback Phase 3 and
Phase 13 name for when the joint export is hard; PREREGISTRATION.md says what
that leaves out.

Contract: `python -I export.py --model-dir M --out-dir O`, offline. Writes
`O/ner_fp32.onnx` and `O/ner_int8.onnx`. Raises ValueError if O is the model
directory or inside it, so the pinned snapshot stays as downloaded.

Known limits: the prefix, morphology and lemma heads are not in the exported
graph, so the files are not the product's model.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# `python -I` drops the script folder; E1's loader is reused (see e3 run.py).
sys.path[:0] = [str(HERE), str(HERE.parent / "e1_hebrew_recall")]

import torch
from corpus import is_inside
from onnxruntime.quantization import QuantType, quantize_dynamic
from run_model import code_revision, load_ner_model, model_file_hashes

import latency

OPSET = 17
FP32_NAME = "ner_fp32.onnx"
INT8_NAME = "ner_int8.onnx"


class NerOnly(torch.nn.Module):
    """The encoder followed by the NER classifier, and nothing else.

    Why: the model's own forward builds every head and returns a dataclass,
    which neither exports cleanly nor is what E2 times.

    Contract: `forward(input_ids, attention_mask)` returns the NER logits,
    shape (batch, positions, labels). Equal to the model's `ner_logits` in
    eval mode, where its dropout is the identity.
    """

    def __init__(self, model):
        super().__init__()
        self.bert = model.bert
        self.classifier = model.classifier

    def forward(self, input_ids, attention_mask):
        return self.classifier(self.bert(input_ids=input_ids, attention_mask=attention_mask)[0])


def export(model_dir: Path, out_dir: Path) -> None:
    """Write the FP32 graph, then its dynamic INT8 quantization.

    Contract: prints the commit, the hash of the weights, and the size and
    SHA-256 of each file written. Exits before writing anything if the weights
    are not the pinned file.
    """
    if is_inside(out_dir, model_dir):
        raise ValueError("the output directory must not be inside the downloaded model directory")
    code = code_revision()
    weights = model_file_hashes(model_dir)["model.safetensors"]
    if weights != latency.PINNED_WEIGHTS_SHA256:
        sys.exit("model.safetensors is not the pinned file (docs/THIRD_PARTY.md); nothing was exported")
    print(f"code {code['commit']}{', uncommitted changes' if code['dirty'] else ''}")
    print(f"model.safetensors sha256 {weights}")
    out_dir.mkdir(parents=True, exist_ok=True)
    model, tokenizer = load_ner_model(model_dir)
    example = tokenizer(["משפט קצר לדוגמה.", "משפט שני, ארוך מעט יותר, לדוגמה."], padding=True, return_tensors="pt")
    batch_and_positions = {0: "batch", 1: "positions"}
    torch.onnx.export(
        NerOnly(model).eval(),
        (example["input_ids"], example["attention_mask"]),
        str(out_dir / FP32_NAME),
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_axes=dict.fromkeys(["input_ids", "attention_mask", "logits"], batch_and_positions),
        opset_version=OPSET,
        dynamo=False,
        external_data=False,
    )
    # build-plan.md Phase 13: "Dynamic INT8 first, per-channel."
    quantize_dynamic(out_dir / FP32_NAME, out_dir / INT8_NAME, per_channel=True, weight_type=QuantType.QInt8)
    for name in (FP32_NAME, INT8_NAME):
        print(f"{(out_dir / name).stat().st_size:>12}  {latency.file_sha256(out_dir / name)}  {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    arguments = parser.parse_args()
    export(arguments.model_dir, arguments.out_dir)
