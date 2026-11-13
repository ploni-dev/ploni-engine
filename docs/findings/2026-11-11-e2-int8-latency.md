# Finding: E2 INT8 latency is 1.03 seconds per page on mains power and 2.7 to 11.7 on battery, for the NER head alone, on a laptop that is not the reference machine

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

Six runs of `measure.py`, model revision `7b1256fc0846e22d1af431eae299e2dcecee2778`, the same two ONNX files in all six: `ner_fp32.onnx` 735,322,572 bytes, `ner_int8.onnx` 184,958,516 bytes.

| Run | Date | Code | ONNX INT8 median | ONNX FP32 | PyTorch FP32 | Power state |
|---|---|---|---|---|---|---|
| 1 | 2026-11-11 | `2b48fe7` | 1.070 s | 2.017 s | 2.108 s | not recorded |
| 2 | 2026-11-11 | `8fc3977` | 1.066 s | 2.067 s | 2.097 s | not recorded |
| 3 | 2026-11-12 16:31 | `98bfc8c` | 2.796 s | 6.161 s | 6.773 s | on battery at 38 percent, read by hand |
| 4, a repeat of 3 | 2026-11-12 16:34 | `98bfc8c` | 2.675 s | 6.546 s | 6.039 s | on battery, 36 percent after the run, read by hand |
| 5, a test between two causes | 2026-11-12 17:00 | `b3ec8bc` | 11.715 s | 21.218 s | 21.347 s | on battery at 28 percent, power mode best power efficiency, printed by the run |
| **6, the result** | 2026-11-12 21:50 | `a3f7ccd` | **1.026 s** | 1.896 s | 1.968 s | on mains at 60 percent, power mode balanced, printed by the run before and after |

**On mains power the time is 1.03 seconds, and the time of runs 1 and 2 is reproduced.** On battery the same two files took 2.7 to 2.8 seconds and then 11.7 seconds, the last above the plan's fail threshold of 10.

**Run 6 is the result**, as `PREREGISTRATION.md` fixed before it (`a3f7ccd`). The prediction was an INT8 median of 0.906 to 1.226 seconds, within 15 percent of run 2, and it came out 1.026. It is the first run with the full power line, read before and after the timed passes. Run 3 had been the result until then (second amendment, `98bfc8c`), and run 5 was a test between two causes whose reading matched neither (third amendment, `b3ec8bc`).

**Every run with a recorded state on battery is slow, and the one run with a recorded state on mains is fast.** Power state is the candidate this supports. It is not shown to be the cause: two of the three fast runs have no recorded power state, and rest before the run changed together with the power state in run 6, since runs 3 to 5 followed heavy work and run 6 followed ten quiet minutes. What is known:

- The files are the same. For run 3 they were exported again from the committed code, and both came out byte for byte equal to the files runs 1 and 2 timed (SHA-256 `b12eaf92…` for INT8 and `e686ac23…` for FP32, in full in the outputs below and in `PREREGISTRATION.md`).
- The page is the same in runs 2 to 6, and the timed passes are the same code in all six.
- The label counts are the same in runs 3, 4 and 5: 513 of 516 text positions equal to PyTorch, and 57 not labelled O. The labels themselves are not stored, so this is not a comparison position by position.
- Power: runs 3, 4 and 5 were on battery. For runs 3 and 4 that was read by hand between the runs, not printed by the run. Run 5 printed it: battery, 28 percent, Windows power mode `961cc777-2547-4f9d-8174-7d86181b8a7a`, which Microsoft's API documentation names best efficiency (`GUID_POWER_MODE_BEST_EFFICIENCY`). The power mode of runs 3 and 4 was not recorded. On this laptop the energy saver charge level on battery is 30 percent (`powercfg /qh`). Runs 3 and 4 were above it, at 38 and 36 percent, and run 5 below it, at 28. Read after run 5, at 24 and at 23 percent: the mode in effect was best efficiency while the mode set was balanced and the energy saver flag was 0. So Windows was running a different mode from the one set, one meant to save power, and the three battery runs may not have been in one power state. Whether the mode changed between run 4 and run 5 was not observed. The power state of runs 1 and 2 was not recorded and cannot be recovered. The Windows power plan says nothing here: Balanced is the only plan on this laptop.
- The harness: in runs 3 and 4 it hashed about 1.7 GB of files and called git twice just before the first timed pass, which runs 1 and 2 did not do. For run 5 that work was moved after the timed passes, and run 5 was slower still. So that work is not needed for a slow run. Whether it added to runs 3 and 4 is not known.
- What the laptop had just done: the re-export finished within a minute before run 3. Before run 5 the laptop had run two test suites and one E3 run in the previous quarter of an hour. Run 1 also came a few minutes after its export and was fast.
- Run 4 repeated run 3 three minutes later. The prediction, a median within 10 percent of 2.796 seconds, was stated in the working session before the run and is in no commit. It came out 2.675, 4 percent lower. The two runs agree, which rules out a cause shorter than three minutes and nothing longer.
- Run 5's reading was fixed in a commit before it: within 15 percent of 1.066 seconds if the work before the clock had caused the slowdown, within 15 percent of 2.736 if it had not. It came out 11.715, so neither reading holds.
- Read by hand, not printed by any run: between runs 3 and 4 the machine showed about 7 percent processor use and 3.4 GB of free memory; half a minute after run 5, 3.5 GB free, the battery-saver flag off, and the processor at full speed when idle.
- Run 6 was on mains at 60 percent charge. The power mode in effect and the power mode set were both balanced and the energy saver flag was 0, read by the run before and after the timed passes. Every run with a recorded state on battery is slow; the one run with a recorded state on mains is fast.
- Run 6 does not separate the power source from the power mode. On mains the mode in effect was balanced. On battery it was read at 28, 24 and 23 percent only, and was best efficiency each time. No run was made on battery in balanced mode, or on mains in best efficiency.
- For ten minutes before run 6 the session ran file edits, git commands (two of them checked out a second copy of the repository's files) and three short Python scripts: two that edited a Markdown file and one that checked the characters of one. The amendment registered "nothing heavier than file edits and git commands", so the scripts are a departure from its wording, and the judgment that they do not matter was made after the run. Other programs were not closed. Read by hand ten seconds before the run: 12 to 23 percent processor use and 2.2 GB of free memory. That is more processor use and less free memory than the hand readings beside the slow runs (7 percent and 3.4 GB), so on these readings neither explains runs 3 and 4. No processor reading exists near run 5, and none was taken during any run.

Run 6, code at `a3f7ccd`, raw output:

```
E2 CPU latency, model revision 7b1256fc0846e22d1af431eae299e2dcecee2778
model.safetensors sha256 c59db02c002b69fd3c072c310e3ba578d036386477248d1c8576d896cc06aa1c
config.json sha256 507f247f97ccaed18308054d58b5f063dd2cc01e69204d13218703dc2512932c
tokenizer.json sha256 4e520fd9025a2fd5f2dce1d04df5922954c8ff050cc3e67d4bc54a7347eccb32
ner_int8.onnx sha256 b12eaf9283bbc40ae7473461a93e4b8872b44478503af9ad51e7fb0922b83b05
ner_fp32.onnx sha256 e686ac235181498b9bef5c3f660db18e42c0120dc21e0a5cead5950c4151d760
code a3f7ccd2d244887e5290c31b44372bad6df9bb11
power before the timed passes: on mains, battery 60 percent, energy saver flag 0, power mode in effect 00000000-0000-0000-0000-000000000000, power mode set 00000000-0000-0000-0000-000000000000
power after the timed passes:  on mains, battery 60 percent, energy saver flag 0, power mode in effect 00000000-0000-0000-0000-000000000000, power mode set 00000000-0000-0000-0000-000000000000
page: 13 paragraphs, 407 words, 542 positions of which 516 are text, batch (13, 66)
machine: Intel64 Family 6 Model 186 Stepping 3, GenuineIntel, 12 logical processors, threads 4
torch 2.15.0+cpu, onnxruntime 1.31.1
backend       median     min     max   seconds, 5 runs after 1 warm-up
onnx int8      1.026   0.980   1.036
onnx fp32      1.896   1.886   1.947
torch fp32     1.968   1.936   1.975
verdict on the onnx int8 median: inside_prediction
onnx int8    labels equal to torch fp32: 513/516 text positions, not labelled O: 57
onnx fp32    labels equal to torch fp32: 516/516 text positions, not labelled O: 57
torch fp32   labels equal to torch fp32: 516/516 text positions, not labelled O: 57
```

The run started at 21:50:07 and ended at 21:50:55. The all-zero identifier is the balanced power mode.

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

What the six runs say together:

- The INT8 median is inside the predicted 1 to 3 seconds in five of the six runs: at the low end in runs 1, 2 and 6 (1.070, 1.066 and 1.026), near the top in runs 3 and 4 (2.796 and 2.675). In run 5 it is 11.715 seconds, above the fail threshold of 10, and its five timed passes ran from 7.582 to 12.569 seconds, a far wider spread than in any other run.
- INT8 is 1.8 to 2.4 times faster than the FP32 graph (2.067 / 1.066 in run 2, 6.161 / 2.796 in run 3, 6.546 / 2.675 in run 4, 21.218 / 11.715 in run 5, 1.896 / 1.026 in run 6) and a quarter of its size. The backends run in a fixed order, INT8 first, so part of that ratio may be the order.
- The FP32 graph gives the same label as PyTorch wherever the two were compared, so the export is right for this page: at every computed position in runs 1, 2, 5 and 6, and at every text position in runs 3 and 4, where the 26 marker positions were left out of the check by a mistake the third amendment records.
- On the 516 positions that are text, INT8 changes the label at 3, and both label 57 positions as part of an entity (runs 3 to 6). Runs 1 and 2 counted the 26 `[CLS]` and `[SEP]` positions as well, which is where "4 of 542" and "59 against 60" came from. Subtracting run 3 from run 2, one of those four changes and the one entity position that looked lost were on marker positions and mean nothing. That is a subtraction between two runs, not a count inside one. Which entities the three real changes touch was not examined.

## What this rules in and what it rules out

Rules in:

- The ONNX and dynamic INT8 path works for this model's encoder and NER head with the pinned packages, and about halves the time. The export is reproducible: two exports, on 2026-11-11 and 2026-11-12, gave the same bytes.
- On mains power in balanced mode, the encoder and NER head label this page in about one second: 1.026 seconds in run 6, and 1.066 and 1.070 in runs 2 and 1, whose power state was not recorded.

Rules out:

- That the files changed. The plan reads a time above 10 seconds as "quantization or batching is wrong". In run 5 the quantized file and the batch are the ones of the runs that took 1.07 and 2.8 seconds, by hash and by the printed batch shape, and the label counts are equal, so what moved the time is outside the files. Run 6 points at the laptop's power state.
- Reading the mains figure as the time on battery. On battery the same files took 2.6 to 11 times as long (2.675 to 11.715 seconds against 1.026).
- That the per-page budget is safe on battery. Section 8.2 gives 1 to 3 seconds for the whole analysis of a page. On battery the NER head alone used 2.7 to 11.7 of them, before the prefix head and before the second model.

Does not settle:

- **The product's time per page.** Phase 3 needs prefix segmentation on every page, and that head is not in the graph. The lemma head, if the product uses it, projects every position onto the whole vocabulary. The plan also runs a second model on every page, GLiNER2 with 205M parameters (Phase 4), and the 1 to 3 seconds of section 8.2 is for all of it. The real number is the time measured here plus those heads plus that model, and how much they add was not measured.
- **Which part of the power state matters.** Power source, power mode and charge changed together between the fast and the slow runs. Run 5, the slowest, is the only run known to have been below the 30 percent energy saver level, and the mode in effect above 30 percent on battery was never read. What the laptop had done just before each run is a further difference that no run isolated.
- **The reference machine.** The laptop has more cores and half the memory of the machine section 8.1 describes.
- **What INT8 costs in recall.** Three changed labels on the text of one page is a reason to look, not a measurement. Phase 13 requires the full eval after any quantization change, and a loss of 2 points of recall is not acceptable there.
- **A page laid out differently.** The 13 paragraphs here pad to 66 positions each, so 858 positions are computed for 542 real ones and 316 are padding. An earlier version of this note said a page that is one long paragraph would cost more. That was never measured and is withdrawn: such a page is two windows of about 650 positions together, which could be cheaper. A page with one long paragraph among short ones pads every row to the long one and would cost more. Neither was timed.
- Being at the low end. Run 6's median is 0.026 seconds above the low end of the prediction, and one of its five passes took 0.980 seconds. The plan says a number below the low end is a reason to suspect the model is not seeing the full text. All 542 positions were computed and no paragraph was truncated, so that suspicion does not apply to this page. The band committed for run 6 reached down to 0.906 seconds, below the plan's low end of 1 second: a median between the two would have been inside the band and outside the plan's prediction, and the amendment did not say how to read that. Run 6 was 0.026 seconds clear of it.

## Options, with the cost of each

0. **Make one controlled run before reading E2 at all.** Done: run 6, on mains, with the power state printed by the run. What was not controlled: other programs stayed open, and the power mode was whatever Windows had set.
1. **Take E2 as not failing and go on.** With run 6 inside the band fixed before it, this is the reading the pre-registration gives. The cost is the one in the title: the figure holds on mains power only.
2. **Size the missing heads before Phase 3 starts.** Time the same page through PyTorch with the prefix and morphology heads on, beside the PyTorch time measured here for the NER head alone (1.968 seconds in run 6, the one in a recorded state on mains; 2.097 in run 2; 6.773 in run 3), in a recorded power state. About an hour, no new dependency, its own pre-registration. It says how far the time measured here is from the real figure without waiting for the joint export.
3. **Export the joint model now.** This is Phase 13 work. The prefix head takes extra inputs built by the model's own Python, so the export is not a one-liner. One to two sessions.
4. **Write `docs/REFERENCE_MACHINE.md`.** Either name a real 16 GB machine and re-run there, or decide that this laptop is the reference, which makes every budget in section 8.2 harder to meet on memory and is a change to the plan.

## Recommendation

**Proposed decision, for Achia to confirm or change.** The Decision section below is left empty: a run above the fail threshold is on record, and the plan says E2 failing changes the plan, so this one is Achia's.

1. Take E2 as passed, for the encoder and NER head, on mains power (option 1). Run 6 is the result: 1.026 seconds, inside the band committed before it and inside the plan's 1 to 3 seconds. Run 5, above the fail threshold at 11.715 seconds, stays in this note as what the same files did on battery on this laptop, not as a failure of quantization or batching: the files are the same by hash.
2. Until Achia defines the reference machine, timings in this project are taken on mains power and print their power state. A run whose power line shows battery is reported and is not a result.
3. Time the missing heads at the start of Phase 3 (option 2), with their own pre-registration, before the per-page budget is relied on. Until then 1.03 seconds is the time of one of the two models, without the prefix head.
4. Left open for Achia whatever is decided above: which machine is the reference and in which power state it is measured (option 4), and whether the product should say anything to a user on battery. On this laptop, on battery, the same work took 2.6 to 11 times as long, so a user on battery may wait far longer per page than section 8.2 assumes.

The changed labels should be the first thing the Phase 5 eval harness is pointed at once it exists.

## Scope requested

None. This is not a waiver request.

## Decision

Achia, 2026-11-13, in the Claude Code session, in these words:

> I think for now, let's not focus on speed. Let's measure it, make analytics of it, and we will measure also every layer, every stage, so we know where is the most expensive on time place. And later, when we have something working, we will strive to make it better, but right now we just take measurements. We don't make it official tests that you have to pass.

What follows from it, as Claude reads it:

1. E2 is closed as a measurement. It is not read as passed or as failed. The six runs above stay as the record.
2. Until Achia says otherwise, no timing in this project is a test that has to pass. A timing is measured, printed with its power state, and recorded.
3. Every stage of the pipeline records its own time, so that the most expensive stage is known. This is new work: the plan has no per-stage timing. It starts with the first phase that has a stage to time.
4. Work on speed waits until the pipeline works end to end.
5. Not decided here: which machine is the reference, and whether the product says anything to a user on battery. Neither blocks work now.

This decision is about text that this PR does not edit: the fail thresholds of `build-plan.md` section 8.2, the T7 performance tier and the Phase 13 gate "budget met". None of them is in force yet: no T7 test exists and Phase 13 is the last phase. Bringing their text into line with this decision is a change to the plan and goes in a PR of its own.
