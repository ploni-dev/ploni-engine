# Finding: E2 INT8 latency is not reproducible on this laptop: 1.07, 2.80 and 11.7 seconds per page on the same files, the last above the fail threshold

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

Five runs of `measure.py`, model revision `7b1256fc0846e22d1af431eae299e2dcecee2778`, the same two ONNX files in all five: `ner_fp32.onnx` 735,322,572 bytes, `ner_int8.onnx` 184,958,516 bytes.

| Run | Date | Code | ONNX INT8 median | ONNX FP32 | PyTorch FP32 | Power state |
|---|---|---|---|---|---|---|
| 1 | 2026-11-11 | `2b48fe7` | 1.070 s | 2.017 s | 2.108 s | not recorded |
| 2 | 2026-11-11 | `8fc3977` | 1.066 s | 2.067 s | 2.097 s | not recorded |
| **3, the result** | 2026-11-12 16:31 | `98bfc8c` | **2.796 s** | 6.161 s | 6.773 s | on battery at 38 percent, read by hand |
| 4, a repeat of 3 | 2026-11-12 16:34 | `98bfc8c` | 2.675 s | 6.546 s | 6.039 s | on battery, 36 percent after the run, read by hand |
| 5, a test between two causes | 2026-11-12 17:00 | `b3ec8bc` | 11.715 s | 21.218 s | 21.347 s | on battery at 28 percent, power mode best power efficiency, printed by the run |

**The time is not reproducible on this laptop.** The same two files gave an INT8 median of 1.07 seconds, then 2.7 to 2.8 seconds, then 11.7 seconds. Run 5 is above the plan's fail threshold of 10 seconds.

**Run 3 is the result**, as `PREREGISTRATION.md` fixed in its second amendment (`98bfc8c`) before that run. It is inside the predicted 1 to 3 seconds, 0.2 seconds below the top. Run 5 was pre-registered as a test between two causes, not as a new result (third amendment, `b3ec8bc`), and that amendment says which run is the result does not change. Whether a result can stand beside a later run eleven times the first is for Achia to decide.

**Why the times differ is not established.** What is known:

- The files are the same. For run 3 they were exported again from the committed code, and both came out byte for byte equal to the files runs 1 and 2 timed (SHA-256 `b12eaf92…` for INT8 and `e686ac23…` for FP32, in full in the outputs below and in `PREREGISTRATION.md`).
- The page is the same in runs 2 to 5, and the timed passes are the same code in all five.
- The labels are the same in runs 3, 4 and 5, to the position.
- Power: runs 3, 4 and 5 were on battery. For runs 3 and 4 that was read by hand between the runs, not printed by the run. Run 5 printed it: battery, 28 percent, Windows power mode `961cc777-2547-4f9d-8174-7d86181b8a7a`, which Microsoft's documentation names best power efficiency. The power state of runs 1 and 2 was not recorded and cannot be recovered. The Windows power plan says nothing here: Balanced is the only plan on this laptop.
- The harness: in runs 3 and 4 it hashed about 1.7 GB of files and called git twice just before the first timed pass, which runs 1 and 2 did not do. For run 5 that work was moved after the timed passes, and run 5 was slower still. So that work is not needed for a slow run. Whether it added to runs 3 and 4 is not known.
- What the laptop had just done: the re-export finished within a minute before run 3. Before run 5 the laptop had run two test suites and one E3 run in the previous quarter of an hour. Run 1 also came a few minutes after its export and was fast.
- Run 4 repeated run 3 three minutes later. The prediction, a median within 10 percent of 2.796 seconds, was stated in the working session before the run and is in no commit. It came out 2.675, 4 percent lower. The two runs agree, which rules out a cause shorter than three minutes and nothing longer.
- Run 5's reading was fixed in a commit before it: within 15 percent of 1.066 seconds if the work before the clock had caused the slowdown, within 15 percent of 2.736 if it had not. It came out 11.715, so neither reading holds.
- Read by hand, not printed by any run: between runs 3 and 4 the machine showed about 7 percent processor use and 3.4 GB of free memory; half a minute after run 5, 3.5 GB free, the battery-saver flag off, and the processor at full speed when idle.
- No run was made on mains power with the state recorded, and none on a laptop that had been left idle first.

Run 3, code at `98bfc8c`, raw output:

```
E2 CPU latency, model revision 7b1256fc0846e22d1af431eae299e2dcecee2778
model.safetensors sha256 c59db02c002b69fd3c072c310e3ba578d036386477248d1c8576d896cc06aa1c
ner_int8.onnx sha256 b12eaf9283bbc40ae7473461a93e4b8872b44478503af9ad51e7fb0922b83b05
ner_fp32.onnx sha256 e686ac235181498b9bef5c3f660db18e42c0120dc21e0a5cead5950c4151d760
code 98bfc8cae31e85dae74d36fa300793b6066f7011
page: 13 paragraphs, 407 words, 542 positions of which 516 are text, batch (13, 66)
machine: Intel64 Family 6 Model 186 Stepping 3, GenuineIntel, 12 logical processors, threads 4
torch 2.15.0+cpu, onnxruntime 1.31.1
backend       median     min     max   seconds, 5 runs after 1 warm-up
onnx int8      2.796   2.735   3.344
onnx fp32      6.161   5.966   6.707
torch fp32     6.773   6.137   6.810
verdict on the onnx int8 median: inside_prediction
onnx int8    labels equal to torch fp32: 513/516 text positions, not labelled O: 57
onnx fp32    labels equal to torch fp32: 516/516 text positions, not labelled O: 57
torch fp32   labels equal to torch fp32: 516/516 text positions, not labelled O: 57
```

Run 4, code at `98bfc8c`. Only these lines of its output were kept; the header lines were not:

```
code 98bfc8cae31e85dae74d36fa300793b6066f7011
backend       median     min     max   seconds, 5 runs after 1 warm-up
onnx int8      2.675   2.636   2.896
onnx fp32      6.546   6.378   6.783
torch fp32     6.039   5.521   6.361
verdict on the onnx int8 median: inside_prediction
onnx int8    labels equal to torch fp32: 513/516 text positions, not labelled O: 57
onnx fp32    labels equal to torch fp32: 516/516 text positions, not labelled O: 57
torch fp32   labels equal to torch fp32: 516/516 text positions, not labelled O: 57
```

Run 5, code at `b3ec8bc`, raw output:

```
E2 CPU latency, model revision 7b1256fc0846e22d1af431eae299e2dcecee2778
model.safetensors sha256 c59db02c002b69fd3c072c310e3ba578d036386477248d1c8576d896cc06aa1c
config.json sha256 507f247f97ccaed18308054d58b5f063dd2cc01e69204d13218703dc2512932c
tokenizer.json sha256 4e520fd9025a2fd5f2dce1d04df5922954c8ff050cc3e67d4bc54a7347eccb32
ner_int8.onnx sha256 b12eaf9283bbc40ae7473461a93e4b8872b44478503af9ad51e7fb0922b83b05
ner_fp32.onnx sha256 e686ac235181498b9bef5c3f660db18e42c0120dc21e0a5cead5950c4151d760
code b3ec8bc2662149aca78bc5ff7cd8e54422f8b48b
power before the timed passes: on battery, battery 28 percent, power mode 961cc777-2547-4f9d-8174-7d86181b8a7a
page: 13 paragraphs, 407 words, 542 positions of which 516 are text, batch (13, 66)
machine: Intel64 Family 6 Model 186 Stepping 3, GenuineIntel, 12 logical processors, threads 4
torch 2.15.0+cpu, onnxruntime 1.31.1
backend       median     min     max   seconds, 5 runs after 1 warm-up
onnx int8     11.715   7.582  12.569
onnx fp32     21.218  16.140  22.825
torch fp32    21.347  19.637  23.524
verdict on the onnx int8 median: threshold_crossed
onnx int8    labels equal to torch fp32: 513/516 text positions, not labelled O: 57
onnx fp32    labels equal to torch fp32: 516/516 text positions, not labelled O: 57
torch fp32   labels equal to torch fp32: 516/516 text positions, not labelled O: 57
```

The run started at 17:00:03 and ended at 17:06:56.

Runs 1 and 2 follow as they were first written up, when run 2 was the result. Between those two runs, two invented identifiers on the page had their last digit changed, because the Ponytail review found they passed the Israeli ID check digit (`PREREGISTRATION.md`, amendment, committed as `8fc3977` before run 2). The rule, the readings and the thresholds did not change.

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

What the five runs say together:

- The INT8 median is inside the predicted 1 to 3 seconds in runs 1 to 4: at the low end in runs 1 and 2 (1.070 and 1.066), near the top in runs 3 and 4 (2.796 and 2.675). In run 5 it is 11.715 seconds, above the fail threshold of 10, and its five timed passes ran from 7.582 to 12.569 seconds, a far wider spread than in any other run.
- INT8 is 1.8 to 2.4 times faster than the FP32 graph (2.067 / 1.066 in run 2, 6.161 / 2.796 in run 3, 6.546 / 2.675 in run 4, 21.218 / 11.715 in run 5) and a quarter of its size. The backends run in a fixed order, INT8 first, so part of that ratio may be the order.
- The FP32 graph gives the same label as PyTorch wherever the two were compared, so the export is right for this page: at every computed position in runs 1, 2 and 5, and at every text position in runs 3 and 4, where the 26 marker positions were left out of the check by a mistake the third amendment records.
- On the 516 positions that are text, INT8 changes the label at 3, and both label 57 positions as part of an entity (runs 3, 4 and 5). Runs 1 and 2 counted the 26 `[CLS]` and `[SEP]` positions as well, which is where "4 of 542" and "59 against 60" came from. Subtracting run 3 from run 2, one of those four changes and the one entity position that looked lost were on marker positions and mean nothing. That is a subtraction between two runs, not a count inside one. Which entities the three real changes touch was not examined.

## What this rules in and what it rules out

Rules in:

- The ONNX and dynamic INT8 path works for this model's encoder and NER head with the pinned packages, and about halves the time. The export is reproducible: two exports, on 2026-11-11 and 2026-11-12, gave the same bytes.
- Nothing about speed. Four runs are inside the prediction and one is above the fail threshold, on the same files.

Rules out:

- That the files changed. The plan reads a time above 10 seconds as "quantization or batching is wrong". In run 5 the quantized file, the batch and the labels are the ones of the runs that took 1.07 and 2.8 seconds, so what moved the time is outside the files. What it is, is not established.
- Reading any one of these numbers as this laptop's time per page.
- An earlier sentence of this note, "on this laptop the NER head is not what will break the per-page budget". Section 8.2 gives 1 to 3 seconds for the whole analysis of a page. In run 3 the NER head alone used 2.8 of them, before the prefix head and before the second model.

Does not settle:

- **The product's time per page.** Phase 3 needs prefix segmentation on every page, and that head is not in the graph. The lemma head, if the product uses it, projects every position onto the whole vocabulary. The plan also runs a second model on every page, GLiNER2 with 205M parameters (Phase 4), and the 1 to 3 seconds of section 8.2 is for all of it. The real number is the time measured here plus those heads plus that model, and how much they add was not measured.
- **Why the same files take 1.07, 2.8 and 11.7 seconds.** Three candidates are on record and none is ruled out: the power state, what the laptop had done just before, and for runs 3 and 4 the work the harness did before the clock. They are listed under "Measured result". Memory pressure is a fourth that nothing here measured during a run.
- **The reference machine.** The laptop has more cores and half the memory of the machine section 8.1 describes.
- **What INT8 costs in recall.** Three changed labels on the text of one page is a reason to look, not a measurement. Phase 13 requires the full eval after any quantization change, and a loss of 2 points of recall is not acceptable there.
- **A page laid out differently.** The 13 paragraphs here pad to 66 positions each, so 858 positions are computed for 542 real ones and 316 are padding. An earlier version of this note said a page that is one long paragraph would cost more. That was never measured and is withdrawn: such a page is two windows of about 650 positions together, which could be cheaper. A page with one long paragraph among short ones pads every row to the long one and would cost more. Neither was timed.
- Being at the low end in runs 1 and 2. All 542 positions were labelled and no paragraph was truncated, so the model saw the full text. Why those two runs were fast is the open question above, not something the page explains.

## Options, with the cost of each

0. **Make one controlled run before reading E2 at all.** Achia plugs the laptop in, sets the Windows power mode for mains in Settings, closes other programs and leaves the laptop idle for ten minutes; then one run, with its prediction committed first. The run now prints the power state itself. It takes two minutes if the laptop is in the state of runs 1 and 2. If that run is near 1.07 seconds, power or load explains the rest; if it is not, the cause is still open.
1. **Take E2 as not failing and go on.** No cost now. Before run 5 this was a fair reading. After it, it means going on with one run above the fail threshold and no explanation.
2. **Size the missing heads before Phase 3 starts.** Time the same page through PyTorch with the prefix and morphology heads on, beside the PyTorch time measured here for the NER head alone (2.097 seconds in run 2, 6.773 in run 3), in a recorded power state. About an hour, no new dependency, its own pre-registration. It says how far the time measured here is from the real figure without waiting for the joint export.
3. **Export the joint model now.** This is Phase 13 work. The prefix head takes extra inputs built by the model's own Python, so the export is not a one-liner. One to two sessions.
4. **Write `docs/REFERENCE_MACHINE.md`.** Either name a real 16 GB machine and re-run there, or decide that this laptop is the reference, which makes every budget in section 8.2 harder to meet on memory and is a change to the plan.

## Recommendation

Option 0, and nothing else until it is done. By the plan's own rule a run above 10 seconds is a failure of E2, and run 5 is above it. I do not think it shows that quantization or batching is wrong, because the files and the labels are the same as in the fast runs; I think it shows that this laptop on battery is not a place to measure time. That is my reading, not a measurement, and the decision is Achia's. After a controlled run: option 2, and option 4 with the power state written into the definition of the reference machine. Option 3 stays where the plan put it.

The changed labels should be the first thing the Phase 5 eval harness is pointed at once it exists.

## Scope requested

None. This is not a waiver request.

## Decision

