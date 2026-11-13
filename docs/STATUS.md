# Status

Three sections first: what is done, what is in flight, and what waits on Achia. Then the phase table, one row per phase close. Gates passed is the only velocity metric here (PROCESS.md section 11).

As of 2026-11-13, end of day. No product code yet. Phase 0 is not started.

## Done

The three week-one experiments of `build-plan.md` section 11, and the tooling around them. Each line names its PRs.

| What | Where it stands | PRs |
|---|---|---|
| Ponytail skills | Version 5.3.3 vendored at a pinned commit, checked against upstream | #5 |
| Rule: Ponytail review before merge | In `CLAUDE.md` | #6 |
| Development rules of 2026-11-12 | In `CLAUDE.md`, `PROCESS.md` and `PROMOTION.md`, approved by Achia on 2026-11-13. No rule is enforced by a machine yet | #16 |
| E1 Hebrew PERSON recall | **449 of 470 mentions found, 95.53 percent**, on ten Supreme Court civil judgments. The threshold (below 80) is not crossed. The number is above the prediction (85 to 92). Private parties 274 of 294, 93.20 percent. 13 of the 21 errors are one surname in one document. Counted by Claude, and **unchecked until Achia checks `doc06`**. A proposed decision is in the note | #11, #47, #50, #52 |
| E3 prefix-preserving replacement | 94 of 100 in three runs; the score is inside the prediction, the errors are not where the plan guessed. Decided by Achia on 2026-11-13: no hand-written rule layer in Phase 3 for now, and the six failing forms kept as watched tests. Achia: maximum accuracy stays the aim | #9, #7, #14, #49 |
| E2 CPU latency after INT8 | 1.026 seconds per page on mains power for the encoder and NER head alone; 2.7 to 11.7 seconds on battery. Decided by Achia on 2026-11-13: speed is measured and recorded, per stage, and is not a test that has to pass, for now | #10, #8, #12, #13, #48 |
| Plan: Python 3.13 | Phase 0 targets Python 3.13, not 3.11. Decided by Achia on 2026-11-13 | #51 |
| Phase tracking on GitHub | 14 milestones, one per phase. Issues #17 to #30 for Phase 0 and #31 to #46 for Phase 1 | none, made with `gh` |

Findings notes: `docs/findings/2026-11-13-e1-hebrew-recall.md`, `docs/findings/2026-11-11-e3-prefix-replacement.md` and `docs/findings/2026-11-11-e2-int8-latency.md`. The E1 note has an empty `## Decision`. The other two are decided.

## In flight

Nothing. No branch is open besides the one that carries this file.

## Waiting on Achia

1. **The check of `doc06`, for E1.** One judgment of 8 pages. Open `C:\Users\Achia\ploni-e1-out\doc06.html`, with the `doc06` row of `tally.csv` and the `doc06` line of `misses.csv` beside it: a yellow mark is a name the model found. Claude's count says the model missed one name in it, and that 11 yellow marks are not counted, because they sit in citations and references. If the check changes any line of Claude's count for `doc06` (a missed name, a mark counted wrongly, a half-marked name), all ten documents are counted again (`experiments/e1_hebrew_recall/PREREGISTRATION.md`, "Achia's check").
2. **The decision on E1.** The note proposes: the threshold is not crossed and Phase 0 starts; the surname shared by several people in `doc10` becomes a named test in Phase 6; E1 is run again on documents closer to a lawyer's own before Phase 3 records its baseline. Which documents, and from where, is Achia's to say (issue #4).
3. **One command, before the CI workflows can be pushed** (issue #22): `gh auth refresh -h github.com -s workflow`. The token on the laptop has no `workflow` scope.
4. **Three open points of E3, before Phase 3 writes its prefix tests:** how `לה` on a surname is scored; what the product replaces when a surname begins with ה, a design question that goes to Achia when Phase 3 reaches it; and the three forms the 100 did not hold, with how a test that is expected to fail is marked and whether such tests count toward Phase 3's gate. Later, not before Phase 3: the cross-check in Phase 6 against an entity's other mentions, which needs a PR to `build-plan.md`, and whether E3 is run again.
5. **Two things that follow from the E2 decision.** A waiver, if a timing past its threshold should be recorded and not stop work: `PROCESS.md` section 10 still says it stops, and only Achia enters a waiver in `docs/WAIVERS.md`. And a PR to `build-plan.md` that gives per-stage timing a home and brings the plan's timing gates into line; Claude can write it, and it changes the plan, so Achia approves it. It comes before the first phase that has a stage to time.
6. **The reference machine.** Which machine `docs/REFERENCE_MACHINE.md` names, and whether the product should say anything to a user on battery. Neither blocks work now.
7. **The Ponytail level** to write into `CLAUDE.md`. `full` has been used so far.
8. **Two open process decisions** of `PROCESS.md` section 13: self-review discipline (point 4) and Tomer's access (point 6). Neither blocks Phase 0.

Not waiting on anyone, and not done:

- The merged branches of 2026-11-11 to 2026-11-13 are still on GitHub. They can be deleted from each PR's page.
- Three inconsistencies on `main` that the review of #16 named: `CLAUDE.md` says `tests/t0_contract/test_layering.py` enforces the layering, and that file does not exist yet (issue #18); `PROMOTION.md` points the PR-body check at section 5.3, and it is described in 5.2; `PROCESS.md` asks for four deliberately bad PRs and `PROMOTION.md` for eight (issue #30).
- The laptop has 7.7 GB of memory. The E1 run was stopped once for low memory before it produced anything, and ran through on the second try.

## Phases

| Phase | Gate | Measured | Date | Exit demo shown |
|---|---|---|---|---|
| 0 Foundation and safety | selftest, no-network, no-leak | not started | | |

## Open waivers

None. See `docs/WAIVERS.md`.

## Weekly notes

- 2026-11-11: Repo created, `ploni-dev/ploni-engine`, private on GitHub Free. Planning documents imported. Product named Ploni. Enforcement limits on the free plan recorded in PROMOTION.md section 11. No product code yet. Next: Phase 0.
- 2026-11-12: The three week-one experiments were built, reviewed and merged; E3 and E2 were run, E1 waits for its documents. Fresh reviewers found more than fifty things in work the writing session had thought finished. E2 gave 1.03 seconds on mains and up to 11.7 on battery with the same files. Next: the E1 corpus and run, then Phase 0.
- 2026-11-13: Achia approved the development rules and decided E2 and E3. Claude collected ten Supreme Court judgments, at Achia's instruction, and E1 was run: 449 of 470, 95.5 percent, counted by Claude and not yet checked by a person. A review before the run found that the reader skipped the caption of every judgment; it was fixed first. Next: Achia's check of `doc06` and the decision on E1, then Phase 0.
