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

## Amendment after run 2, before run 3

On 2026-11-12 a Ponytail review of the harness by a fresh reviewer session (PR #10) found nothing that makes runs 1 and 2 wrong as measurements of what this file defines. It led to the changes below, all made before run 3.

Changes to the harness:

- "If it does not, the run is a harness fault and no time is reported" was not what the code did: the times were printed first and the export check came after them. The check now comes first. In runs 1 and 2 the check passed, so no time was printed that should not have been.
- The label comparison counted the `[CLS]` and `[SEP]` positions of each paragraph, 26 of the 542 positions. It now counts text positions only, and the page line prints both numbers.
- The run prints the commit, the SHA-256 of the weights and of the two ONNX files, and stops if the weights are not the pinned file (`docs/THIRD_PARTY.md`). The model's Python is now the vendored copy, not the files in the download folder.
- The ONNX files are exported again from the committed code. Runs 1 and 2 timed two files written at 22:20 on 2026-11-11, about a minute before the first commit `2b48fe7`, so from code that was not yet committed. Hashed afterwards, on 2026-11-12: `ner_int8.onnx` `b12eaf9283bbc40ae7473461a93e4b8872b44478503af9ad51e7fb0922b83b05`, `ner_fp32.onnx` `e686ac235181498b9bef5c3f660db18e42c0120dc21e0a5cead5950c4151d760`.
- The clock (`timed`) moved into `latency.py` and has a test. What is timed did not change.

Corrections to "Known limits":

- "13 short inputs padded to the longest is cheaper than a page that is one long paragraph" was never measured and is withdrawn. What the runs show: the batch is 13 by 66, so 858 positions are computed for 542 real ones, and 316 are padding. Whether the same words as one long paragraph cost more or less was not measured.
- Added: the product runs a second model on every page (`build-plan.md` Phase 4, GLiNER2, 205M parameters), and the 1 to 3 seconds of section 8.2 is the target for the whole analysis of a page. The time measured here is one of the two models, without the prefix head.
- Added: runs 1 and 2 did not record whether the laptop was on mains power or its Windows power mode, and that cannot be recovered. Run 3 records both. The backends always run in the same order, INT8 first and a few seconds after start, so the comparison between backends is partly a comparison of when each ran.

The rule, the readings and the thresholds are unchanged, and `page.txt` is unchanged. Run 3 is taken with the same rule. It is the result, because it is the only run whose code and files are identified by hash; runs 1 and 2 are kept beside it.

## Amendment after run 4, before run 5

Run 3 gave 2.796 seconds and run 4, a repeat three minutes later, 2.675, against 1.066 in run 2, on the same two ONNX files. The second review pass of the harness (PR #10) pointed out that power is not the only thing that changed. Three candidates are on record:

- **The harness itself.** Since the first amendment, `measure.py` hashed about 1.7 GB of files and called git twice just before the first timed pass. Runs 1 and 2 did neither.
- **Power.** Runs 3 and 4 were on battery. The state of runs 1 and 2 is unknown.
- **What the laptop had just done.** The re-export finished within a minute before run 3.

Changes to the harness, made before run 5:

- The hashing and the git calls now come after the timed passes and before anything is printed. The work before the clock is again what it was in runs 1 and 2, plus one read of the power state, which takes no measurable time. A run on weights that are not the pinned file is now timed and then refused; no time is printed for it.
- The export check compares every computed position again, as "at every real position" above says. Since the first amendment it had compared text positions only, 26 fewer, and no amendment said so. In runs 3 and 4 the 26 marker positions were therefore not compared.
- The report prints the power state itself: mains or battery, the charge, and the identifier of the Windows power mode. The Windows power plan is not printed, because Balanced is the only plan on this laptop.
- The pinned weights hash and its check are in one place, `run_model.pinned_model_hashes` of E1.

Run 5 is a test between the first two candidates, on battery, not a new result. It has no single prediction. The reading is fixed here:

- INT8 median within 15 percent of 1.066 seconds (0.906 to 1.226): the work before the clock caused the slowdown of runs 3 and 4, and those two runs measured the harness, not the model.
- INT8 median within 15 percent of the mean of runs 3 and 4, 2.736 seconds (2.325 to 3.146): the work before the clock was not the cause.
- Anything else: neither reading holds, and the note says so.

Which run is the result is not changed here. If run 5 shows that runs 3 and 4 measured the harness, that is a finding for Achia to decide on, in the note.
