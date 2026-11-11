# E2 pre-registration: CPU latency after INT8

Committed before the first timing was taken. The ONNX files were built before this commit, and nothing was timed on them. The commit order is the evidence.

## What the plan says

`build-plan.md` section 11:

> **E2. CPU latency after INT8.** Export to ONNX, quantize dynamic INT8, measure wall clock on one A4 page of Hebrew on the reference machine.
> Prediction: 1 to 3 seconds per page.
> Threshold: above 10 seconds per page, quantization or batching is wrong.

"E1 or E2 failing changes the plan." Section 8.2 adds: "A number below the low end is also a finding: suspect the model is not seeing the full text."

## Readings fixed here

**These are Claude's readings, not Achia's decisions.** Achia can amend any of them; an amendment means a new run, recorded as a new run.

| Open point | Reading |
|---|---|
| "Export to ONNX" | The encoder and the NER head only, opset 17. This is the fallback Phase 3 and Phase 13 name for when the joint export is hard. It was taken up front, not after a failed attempt at the joint export. |
| "Quantize dynamic INT8" | `onnxruntime.quantization.quantize_dynamic`, per-channel, signed 8-bit weights (Phase 13: "Dynamic INT8 first, per-channel"). No pre-processing pass, no static calibration. |
| "One A4 page of Hebrew" | `page.txt`: an invented statement of claim, 13 paragraphs, 407 words. A page is taken to be 400 to 500 words. |
| How the page reaches the model | One paragraph per input, because Phase 3 never lets a window cross a block break, all 13 in one batched call padded to the longest (Phase 13: "Batch the document's windows into one inference call"). No paragraph is longer than one window. |
| "Wall clock" | Tokenizing the 13 paragraphs, one inference call, and taking the top label at each position. Loading the model and building the session are not included; cold start has its own budget line in section 8.2. |
| The number | The median of 5 runs after 1 warm-up run. Minimum and maximum are reported beside it. |
| Threads | 4 inside an operation, 1 across operations, the count E1 uses. |
| "The reference machine" | Section 8.1 defines it as 8 cores, 16 GB, no GPU, Windows 11, recorded in `docs/REFERENCE_MACHINE.md`. That file does not exist and no such machine is available. The run is on Achia's laptop: Intel Core 5 120U, 10 cores, 12 logical processors, 7.72 GB RAM, Windows 11, no GPU used. **The result is therefore not the plan's measurement.** It is a measurement on a machine with half the reference memory. |

## Decision rule

`latency.verdict(seconds)` on the INT8 median:

- above 10 seconds: `threshold_crossed`. Per the plan, quantization or batching is wrong.
- 1 to 3 seconds inclusive: `inside_prediction`.
- anything else: `outside_prediction`, which includes under 1 second.

## Checks that are not the measurement

- **The export is right.** The FP32 graph must give the same top label as PyTorch FP32 at every real position of the page. If it does not, the run is a harness fault and no time is reported.
- **INT8 still labels the page.** How many positions the INT8 graph labels the same as PyTorch FP32, and how many positions each labels as an entity, are printed. This is a diagnostic, not an accuracy measurement: Phase 13 requires the full eval after any quantization change, and there is no eval yet.
- **FP32 references.** The same page through the FP32 graph and through PyTorch FP32, timed the same way, so the INT8 time has something beside it.

## Known limits

- **Not the product's model.** The exported graph has no prefix, morphology or lemma head. Phase 3 needs prefix segmentation on every page, so the product's time per page is this time plus those heads. The lemma head projects every position onto the whole vocabulary and is not small.
- **Not the reference machine**, as above.
- One page, one text, one machine, one thread count. No sweep.
- 13 short inputs padded to the longest is cheaper than a page that is one long paragraph, which would be one or two full windows. A wall of text is not measured here.
- Nothing here says what INT8 costs in recall.

## Amendment after run 1, before run 2

Run 1 was taken at `2b48fe7`. The Ponytail review of the harness then found that two invented identifiers on `page.txt`, an ID number and a company number, passed the Israeli check digit, so each could be a real identifier (`build-plan.md` Phase 7). The last digit of each was changed so the check fails. Nothing else on the page changed: 13 paragraphs, 407 words.

Because the input changed, the timing is taken again as run 2 with the same rule, readings and thresholds. Both runs are reported. Run 2 is the result; run 1 is kept as the record of what was measured first.
