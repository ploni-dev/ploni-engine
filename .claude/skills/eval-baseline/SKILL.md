---
name: eval-baseline
description: Run the Ploni metric suite, compare the results against eval/baselines.json, and handle a regression or a proposed baseline change. Use at a phase boundary, after a model or quantization change, or when a baseline needs updating.
---

# Running the metric gates

`eval/baselines.json` is the project's memory of how good it is. Protecting it from quiet erosion is the point of this procedure.

## 1. When to run

- At every phase boundary.
- After any change to a model, a quantization setting, a threshold, a fusion rule, the name banks or the numeric policy.
- Before opening a phase-close PR.

## 2. Run it

```
python eval/run_eval.py --corpus eval/corpus --out eval/results/
```

It writes `eval/results/<git-sha>.json` containing the metrics plus the code SHA, the model bundle version and the name bank version. That triple is what makes a number meaningful later. A metric without its model and name bank version attached is not reproducible.

## 3. The metrics, and what each is for

| Metric | Gate | Why it exists |
|---|---|---|
| Per-type precision, recall, F1 (span and entity level) | checksum types at or above 0.98 recall; PERSON frozen at its first measured baseline and never allowed to regress | model quality |
| Pre-review document zero-leak rate | measured and recorded | what the models deliver alone |
| Post-review document zero-leak rate | 1.0 on the eval corpus | what the product delivers, with a simulated reviewer resolving every item correctly |
| Review burden, items per page | at or below 10 | low precision kills adoption through a different door than low recall |
| Consistency | 1.0 | every occurrence of an entity maps to one surrogate |
| Over-merge count | 0 | merging two people silently rewrites the document's facts |
| Under-merge count | recorded | surfaced to the user, not a failure |
| Verification catch rate | recorded | the value the verification pass adds |
| Utility preservation | at or above 0.9 | a tool that redacts everything scores perfectly on leaks and is useless |
| Numeric conservatism violations | 0 | a destroyed contract is a worse product than a leaky one |
| Runtime per page, runtime for 60 pages | recorded; not a gate for now (`PROCESS.md` section 10) | usability |
| Peak RSS | per the performance budget | usability |

Report the two zero-leak numbers separately, always. Never collapse them into one figure: a single number either overstates the models or understates the product.

## 4. If a metric regressed

This is the important branch. Do not touch `baselines.json`.

1. Confirm it is real: re-run with pinned thread counts and fixed seeds. A number that moves between identical runs is a determinism bug, and that is the finding.
2. Identify the cause by bisecting against the last results file that passed.
3. Either fix the cause, or follow the stop-and-report procedure: write `docs/findings/<YYYY-MM-DD>-<slug>.md` with the prediction, the raw before and after numbers, what it rules in and out, the options with their costs, your recommendation, and an empty `## Decision` section.

Never lower a baseline to make a build green. A lowered baseline is a permanent, invisible loss of product quality, and it is the single most likely way this project degrades without anyone noticing.

## 5. If a baseline should legitimately change

Baselines move up when the product genuinely improved, and they move down only on an explicit recorded human decision.

Either way:

- The baseline change is **its own PR**, touching `eval/baselines.json` and nothing else. Code changes and baseline changes never share a PR.
- The PR body carries the before and after numbers, the results file SHA they came from, and the reason.
- A downward change additionally requires a linked findings note with the `## Decision` section filled in by Achia.
- `eval/baselines.json` is CODEOWNERS-protected, so this requires explicit approval by design.

## 6. After a quantization change, specifically

Quantization is the place where accuracy erodes quietly in exchange for speed. So:

- Run the **full** eval, not a subset.
- Record the pre-quantization and post-quantization numbers side by side in the PR body.
- A recall regression above 1 point rejects the quantization, however much faster it is. Speed that costs recall is not a win in this product.

## 7. Reporting

Paste the real metrics table into the PR body. Then one or two sentences on what moved and why. Do not summarize a table the reviewer can read; say what changed and what it means.
