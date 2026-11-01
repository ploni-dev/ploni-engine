---
name: phase-gate
description: Run a numbered phase of build-plan.md end to end: orient, write the failing test first, implement, prove the numeric gate with pasted output, and open the PR. Use when starting or continuing a build-plan phase.
---

# Running a build-plan phase

This project gates work on measured numbers, not on code review impressions. Follow these steps in order. Do not reorder them, and do not skip step 1 because the phase feels familiar.

## 1. Orient before touching code

Read, in this order:

1. `CLAUDE.md` at the repo root.
2. The phase's own section in `build-plan.md` Part IV.
3. The GitHub issue for this sub-task.

Then write out, in two or three sentences each:

- **Goal**: what this phase is for.
- **Deliverable**: the files that will exist when it is done.
- **Gate**: the exact numeric condition, quoted from the plan.
- **Downstream risk**: what breaks in later phases if this one is wrong.

If the plan's gate for this phase is ambiguous, stop and ask. Do not invent a gate.

## 2. Branch

`phase-<N>/<slug>`, one branch per PR.

## 3. Write the failing test first

For every gate condition, the test exists and fails before the implementation lands. Run it and keep the failing output: it goes in the PR body as evidence that the test actually tests something.

Put tests in the right tier directory:

- `tests/t0_contract/` interfaces, adapter and detector conformance, layering
- `tests/t1_unit/` hand-built examples
- `tests/t2_property/` hypothesis invariants
- `tests/t3_golden/` frozen verified output
- `tests/t4_integration/` two or more phases composed
- `tests/t5_system/` full user journeys
- `tests/t6_metrics/` metric gates via the eval harness
- `tests/t7_perf/` performance budget
- `tests/t8_privacy/` network, logs, temp files, scrub, co-location

## 4. Implement

The smallest change that passes the test. Respect the layering rules in `CLAUDE.md`; the layering test will catch a violation but catching it in review wastes a round trip.

## 5. Measure

Run the phase gate. Capture the real command and the real output.

State the prediction and the disagreement threshold from the plan, then the measured value, then whether it is within threshold. If the plan gave no prediction for this measurement, state your own before running it, not after.

## 6. If the gate fails

Stop. Do not:

- weaken the test, the threshold or a baseline
- mark anything `skip` or `xfail`
- add a special case to make the number come out right
- keep tuning until it passes

Instead write `docs/findings/<YYYY-MM-DD>-<slug>.md` with: what was measured, the prediction and threshold, the raw measured output, what this rules in and rules out, the options with the cost of each, your recommendation, and an empty `## Decision` section for Achia. Open that findings note as its own PR and report. Implementation on that path stops until the decision line is filled in.

## 7. Open the PR

Use this body. A PR without pasted gate evidence will be closed unreviewed.

```markdown
## Phase and issue
Phase N, issue #NN

## What this does

## Gate evidence
(paste the actual command and its actual output)

## Prediction vs measurement
Predicted:
Measured:
Within threshold: yes / no

## Tests added

## Golden file changes
None, or: changed because ...

## Checklist
- [ ] Failing test written before implementation
- [ ] No test, threshold or baseline weakened
- [ ] No baseline or gate change in this PR
- [ ] Fast suite green locally
- [ ] Layering test green
```

## Hard limits on a single PR

- One phase only. Never two.
- At most 15 production files changed, 10 preferred.
- At most 800 net lines of production code, 400 preferred. Tests, fixtures and golden files do not count.
- Reviewable in 15 minutes. If it is not, split it before asking for review.

Over a hard limit, split the PR. There is no exception for "it is all related".

## Never, in any session

- Change a baseline, threshold or gate (that is the `eval-baseline` skill, and a separate PR)
- Touch two phases
- Delete or rewrite a golden file without explaining why in the PR body
- Claim a measurement you did not run
- Install an unpinned dependency
- Add a model that is not recorded in `docs/THIRD_PARTY.md`

## Closing a phase

A phase closes when both are true:

1. Its numeric gate passes, with the output recorded.
2. Its exit demo has been shown: a thing you can watch, not just a green suite.

Then append one row to `docs/STATUS.md`: phase, gate, measured number, date, exit demo shown.
