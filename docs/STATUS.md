# Status

Three sections first: what is done, what is in flight, and what waits on Achia. Then the phase table, one row per phase close. Gates passed is the only velocity metric here (PROCESS.md section 11).

As of 2026-11-12, end of day. No product code yet. Phase 0 is not started.

## Done

The three week-one experiments of `build-plan.md` section 11, and the tooling around them. Each line names its PRs.

| What | Where it stands | PRs |
|---|---|---|
| Ponytail skills | Version 5.3.3 vendored at a pinned commit, checked against upstream | #5 |
| Rule: Ponytail review before merge | In `CLAUDE.md` | #6 |
| E1 Hebrew PERSON recall | Harness built and reviewed, 182 tests. **Not run on any real document.** No recall number exists | #11 |
| E3 prefix-preserving replacement | 94 of 100 in three runs, inside the prediction. The errors are in stacked prefixes, not where the plan guessed. A proposed decision is in the note | #9, #7, #14 |
| E2 CPU latency after INT8 | 1.026 seconds per page on mains power, inside the prediction, for the encoder and NER head alone. On battery the same files took 2.7 to 11.7 seconds. A proposed decision is in the note | #10, #8, #12, #13 |

Findings notes: `docs/findings/2026-11-11-e3-prefix-replacement.md` and `docs/findings/2026-11-11-e2-int8-latency.md`. Both have an empty `## Decision`.

## In flight

| Branch | What | Blocked by |
|---|---|---|
| `docs/development-rules` | The development rules agreed on 2026-11-12, in `CLAUDE.md`, `PROCESS.md` and `PROMOTION.md` | Achia's approval: it changes the rule files |

## Waiting on Achia

1. **The E1 corpus.** Ten published decisions as `.docx` in a folder outside the repository, and the folder's path. Also the choice in issue #4 of where they come from, and whether "no case captioned פלוני" still holds. E1 is the experiment that decides the architecture, and nothing can be run without the documents.
2. **The E1 readings.** `experiments/e1_hebrew_recall/PREREGISTRATION.md` marks the choices Claude made where the plan was silent. They are confirmed or amended before the run.
3. **The decision on E2.** The note proposes: take E2 as passed on mains power for the part that was exported. One run on battery was above the fail threshold, which is why this is Achia's.
4. **The decision on E3.** The note proposes: no rule layer in Phase 3, the failing forms as named tests. It leaves open, for Achia or Tomer, what the product replaces when a surname begins with ה.
5. **The rules PR**, above.
6. **The reference machine.** Which machine `docs/REFERENCE_MACHINE.md` names, and in which power state it is measured.
7. **The Ponytail level** to write into `CLAUDE.md`. `full` has been used so far.

Not waiting on anyone, and not done: the merged branches of 2026-11-12 are still on GitHub. They can be deleted from each PR's page.

## Phases

| Phase | Gate | Measured | Date | Exit demo shown |
|---|---|---|---|---|
| 0 Foundation and safety | selftest, no-network, no-leak | not started | | |

## Open waivers

None. See `docs/WAIVERS.md`.

## Weekly notes

- 2026-11-11: Repo created, `ploni-dev/ploni-engine`, private on GitHub Free. Planning documents imported. Product named Ploni. Enforcement limits on the free plan recorded in PROMOTION.md section 11. No product code yet. Next: Phase 0.
- 2026-11-12: The three week-one experiments were built, reviewed and merged; E3 and E2 were run, E1 waits for its documents. Fresh reviewers found more than fifty things in work the writing session had thought finished. E2 gave 1.03 seconds on mains and up to 11.7 on battery with the same files. Next: the E1 corpus and run, then Phase 0.
