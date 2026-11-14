# Status

Three sections first: what is done, what is in flight, and what waits on Achia. Then the phase table, one row per phase close. Gates passed is the only velocity metric here (PROCESS.md section 11).

As of 2026-11-14, end of day. No product code yet. Phase 0 is not started.

## Done

The three week-one experiments of `build-plan.md` section 11, a fourth that Achia asked for on 2026-11-14, and the tooling around them. Each line names its PRs.

| What | Where it stands | PRs |
|---|---|---|
| Ponytail skills | Version 5.3.3 vendored at a pinned commit, checked against upstream | #5 |
| Rule: Ponytail review before merge | In `CLAUDE.md` | #6 |
| Development rules of 2026-11-12 | In `CLAUDE.md`, `PROCESS.md` and `PROMOTION.md`, approved by Achia on 2026-11-13. No rule is enforced by a machine yet | #16 |
| E1 Hebrew PERSON recall | **449 of 470 mentions found, 95.53 percent**, on ten Supreme Court civil judgments. The threshold (below 80) is not crossed. The number is above the prediction (85 to 92). Private parties 274 of 294, 93.20 percent. 13 of the 21 errors are one surname in one document. Counted by Claude, and **not checked by a person**: on 2026-11-14 Achia read only the first page of `doc06` and asked for a ground truth in its place, which is E4. A proposed decision is in the note | #11, #47, #50, #52, #54 |
| E4 PERSON recall against planted names | Not in the plan; built at Achia's request. 40 Hebrew documents written by a script that knows where every name is. **1,084 of 1,145 found, 94.67 percent**, inside the prediction (90 to 96). 51 of the 61 errors are of two kinds: a surname after `משפחת` or `האחים` (22 of 55 found), and a given name alone that is an everyday word (151 of 169). Four Claude readers then counted four of the documents as E1's were counted and agreed with the planted names on 123 of 123 items. **That check shows less than it was meant to:** the three names the model missed in those documents were all on the list of hints the readers were given, so a reader's unaided search was tested on no case. A third part then measured that list of hints by script, with no reader: it holds **57 of the 57** mentions the model missed. So a reader who has the list is pointed to every miss in this text. Whether a reader finds a miss that nothing points to is still not shown | #55, #56, #57, #59, #60 |
| E3 prefix-preserving replacement | 94 of 100 in three runs; the score is inside the prediction, the errors are not where the plan guessed. Decided by Achia on 2026-11-13: no hand-written rule layer in Phase 3 for now, and the six failing forms kept as watched tests. Achia: maximum accuracy stays the aim | #9, #7, #14, #49 |
| E2 CPU latency after INT8 | 1.026 seconds per page on mains power for the encoder and NER head alone; 2.7 to 11.7 seconds on battery. Decided by Achia on 2026-11-13: speed is measured and recorded, per stage, and is not a test that has to pass, for now | #10, #8, #12, #13, #48 |
| Plan: Python 3.13 | Phase 0 targets Python 3.13, not 3.11. Decided by Achia on 2026-11-13 | #51 |
| Phase tracking on GitHub | 14 milestones, one per phase. Issues #17 to #30 for Phase 0 and #31 to #46 for Phase 1 | none, made with `gh` |

Findings notes: `docs/findings/2026-11-13-e1-hebrew-recall.md`, `docs/findings/2026-11-14-e4-planted-names.md`, `docs/findings/2026-11-11-e3-prefix-replacement.md` and `docs/findings/2026-11-11-e2-int8-latency.md`. The E1 and E4 notes have an empty `## Decision`. The other two are decided.

## In flight

Nothing. No branch is open besides the one that carries this file.

## Waiting on Achia

1. **The decision on E1 and E4.** One question: is the model good enough at finding names to start building (Phase 0)? The E1 note proposes yes. The E4 note proposes that E4 stands in for the check by a person that E1 did not get. E1: 449 of 470 on real judgments, counted by Claude and not checked. E4: 1,084 of 1,145 on generated text, counted by a script. The E1 note also proposes that the surname shared by several people in `doc10` becomes a named test in Phase 6, and that E1 is run again on documents closer to a lawyer's own before Phase 3 records its baseline; which documents, and from where, is Achia's to say (issue #4). The E4 note adds: both weak kinds, a surname after a group word and a given name alone that is an everyday word, become named test cases in the plan. It does not propose a further test of the readers (its option 3) now.
2. **One command, before the CI workflows can be pushed** (issue #22): `gh auth refresh -h github.com -s workflow`. The token on the laptop has no `workflow` scope.
3. **Three open points of E3, before Phase 3 writes its prefix tests:** how `לה` on a surname is scored; what the product replaces when a surname begins with ה, a design question that goes to Achia when Phase 3 reaches it; and the three forms the 100 did not hold, with how a test that is expected to fail is marked and whether such tests count toward Phase 3's gate. Later, not before Phase 3: the cross-check in Phase 6 against an entity's other mentions, which needs a PR to `build-plan.md`, and whether E3 is run again.
4. **Two things that follow from the E2 decision.** A waiver, if a timing past its threshold should be recorded and not stop work: `PROCESS.md` section 10 still says it stops, and only Achia enters a waiver in `docs/WAIVERS.md`. And a PR to `build-plan.md` that gives per-stage timing a home and brings the plan's timing gates into line; Claude can write it, and it changes the plan, so Achia approves it. It comes before the first phase that has a stage to time.
5. **The reference machine.** Which machine `docs/REFERENCE_MACHINE.md` names, and whether the product should say anything to a user on battery. Neither blocks work now.
6. **The Ponytail level** to write into `CLAUDE.md`. `full` has been used so far.
7. **Two open process decisions** of `PROCESS.md` section 13: self-review discipline (point 4) and Tomer's access (point 6). Neither blocks Phase 0.

Not waiting on anyone, and not done:

- The merged branches of 2026-11-11 to 2026-11-14 are still on GitHub. They can be deleted from each PR's page.
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
- 2026-11-14: Achia chose not to check E1 by reading and asked for a ground truth. E4 was built for it, reviewed and run: 1,084 of 1,145 planted names found, 94.7 percent, as predicted, with 51 of the 61 errors in two known kinds of mention. Four Claude readers agreed with the planted names on 123 of 123 items, but the review of the note found that the readers were pointed to every name the model had missed in those four documents (three names), so their own search was not tested. A third part measured that list by script: it holds all 57 of the names the model missed. A commit of that day carried a test count that had not been measured; the next commit says so. Next: the decision on E1 and E4, then Phase 0.
