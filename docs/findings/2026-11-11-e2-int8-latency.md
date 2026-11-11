# Finding: E2 INT8 latency is 1.07 seconds per page for the NER head alone, on a laptop that is not the reference machine

## What was being measured

`build-plan.md` section 11, experiment E2: wall clock to run one A4 page of Hebrew through `dicta-il/dictabert-joint` after ONNX export and dynamic INT8 quantization.

What was actually exported and timed is narrower than the plan's sentence, in two ways fixed before the first run in `experiments/e2_int8_latency/PREREGISTRATION.md` at `2b48fe7`:

- The graph is the encoder and the NER head only. The prefix, morphology and lemma heads are not in it.
- The machine is Achia's laptop (Intel Core 5 120U, 10 cores, 12 logical processors, 7.72 GB RAM, Windows 11), not the reference machine of section 8.1, which is not yet defined in `docs/REFERENCE_MACHINE.md`.

## Prediction and threshold

As stated before the run (`build-plan.md` section 11, and `PREREGISTRATION.md` at `2b48fe7`):

- Prediction: 1 to 3 seconds per page.
- Threshold: above 10 seconds per page, quantization or batching is wrong.
- Section 8.2: a number below the low end is also a finding.

## Measured result

Two runs of `measure.py` on 2026-11-11, model revision `7b1256fc0846e22d1af431eae299e2dcecee2778`. The ONNX files came from `export.py` at `2b48fe7`: `ner_fp32.onnx` 735,322,572 bytes, `ner_int8.onnx` 184,958,516 bytes.

**Run 2 is the result.** Between the runs, two invented identifiers on the page had their last digit changed, because the Ponytail review found they passed the Israeli ID check digit (`PREREGISTRATION.md`, amendment, committed as `8fc3977` before run 2). The rule, the readings and the thresholds did not change.

Run 2, code at `8fc3977`, raw output:

```
E2 CPU latency, model revision 7b1256fc0846e22d1af431eae299e2dcecee2778
page: 13 paragraphs, 407 words, 542 positions, batch (13, 66)
machine: Intel64 Family 6 Model 186 Stepping 3, GenuineIntel, 12 logical processors, threads 4
torch 2.15.0+cpu, onnxruntime 1.31.1
backend       median     min     max   seconds, 5 runs after 1 warm-up
onnx int8      1.066   1.041   1.132
onnx fp32      2.067   1.905   2.112
torch fp32     2.097   2.085   2.138
verdict on the onnx int8 median: inside_prediction
onnx int8    labels equal to torch fp32: 538/542, positions not labelled O: 59
onnx fp32    labels equal to torch fp32: 542/542, positions not labelled O: 60
torch fp32   labels equal to torch fp32: 542/542, positions not labelled O: 60
```

Run 1, code at `2b48fe7`, the page before the two digits changed, raw output:

```
E2 CPU latency, model revision 7b1256fc0846e22d1af431eae299e2dcecee2778
page: 13 paragraphs, 407 words, 541 positions, batch (13, 66)
machine: Intel64 Family 6 Model 186 Stepping 3, GenuineIntel, 12 logical processors, threads 4
torch 2.15.0+cpu, onnxruntime 1.31.1
backend       median     min     max   seconds, 5 runs after 1 warm-up
onnx int8      1.070   1.064   1.123
onnx fp32      2.017   1.974   2.048
torch fp32     2.108   2.081   2.128
verdict on the onnx int8 median: inside_prediction
onnx int8    labels equal to torch fp32: 533/541, positions not labelled O: 60
onnx fp32    labels equal to torch fp32: 541/541, positions not labelled O: 60
torch fp32   labels equal to torch fp32: 541/541, positions not labelled O: 60
```

- The INT8 median is 1.066 seconds (1.070 in run 1), inside the predicted 1 to 3 and at its low end.
- INT8 is 1.9 times faster than the FP32 graph (2.067 / 1.066) and a quarter of its size.
- The FP32 graph gives the same label as PyTorch at every position in both runs, so the export is right for this page.
- INT8 changes the label at 4 of 542 positions (8 of 541 in run 1), and in run 2 it labels one position fewer as an entity, 59 against 60. Which entities the changes touch was not examined.

## What this rules in and what it rules out

Rules in:

- The ONNX and dynamic INT8 path works for this model's encoder and NER head with the pinned packages, on the first attempt, and halves the time.
- On this laptop the NER head is not what will break the per-page budget. The threshold is nine times the measured time.

Rules out:

- "Quantization or batching is wrong", for the part that was exported.

Does not settle:

- **The product's time per page.** Phase 3 needs prefix segmentation on every page, and that head is not in the graph. The lemma head, if the product uses it, projects every position onto the whole vocabulary. The real number is 1.07 seconds plus those heads, and how much they add was not measured.
- **The reference machine.** The laptop has more cores and half the memory of the machine section 8.1 describes.
- **What INT8 costs in recall.** Four to eight changed labels on one page, and one entity position lost in run 2, is a reason to look, not a measurement. Phase 13 requires the full eval after any quantization change, and a loss of 2 points of recall is not acceptable there.
- **A page that is one long paragraph.** The 13 paragraphs here pad to 66 positions. A wall of text is one or two windows of 512, and attention cost grows with the square of the length.
- Being at the low end. All 541 positions were labelled and no paragraph was truncated, so the model saw the full text; the time is low because the inputs are short.

## Options, with the cost of each

1. **Take E2 as not failing and go on.** No cost now. The risk is reading "1.07 seconds" as the product's number, which it is not.
2. **Size the missing heads before Phase 3 starts.** Time the same page through PyTorch with the prefix and morphology heads on, beside the 2.097 seconds measured here for the NER head alone. About an hour, no new dependency, its own pre-registration. It says how far 1.07 is from the real figure without waiting for the joint export.
3. **Export the joint model now.** This is Phase 13 work. The prefix head takes extra inputs built by the model's own Python, so the export is not a one-liner. One to two sessions.
4. **Write `docs/REFERENCE_MACHINE.md`.** Either name a real 16 GB machine and re-run there, or decide that this laptop is the reference, which makes every budget in section 8.2 harder to meet on memory and is a change to the plan.

## Recommendation

Options 1 and 2 together, and option 4 as a decision for Achia. E2 does not fail and nothing in it changes the architecture. Option 2 is cheap and removes the largest unknown in this note. Option 3 stays where the plan put it.

The changed labels should be the first thing the Phase 5 eval harness is pointed at once it exists.

## Scope requested

None. This is not a waiver request.

## Decision

