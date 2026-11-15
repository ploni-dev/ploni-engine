# Status

Three sections first: what is done, what is in flight, and what waits on Achia. Then the phase table, one row per phase close. Gates passed is the only velocity metric here (PROCESS.md section 11).

As of 2026-11-15, end of day. No product code yet. Phase 0 is not started.

## Done

The three week-one experiments of `build-plan.md` section 11, a fourth that Achia asked for on 2026-11-14, the rules, and the tooling around them. Each line names its PRs.

| What | Where it stands | PRs |
|---|---|---|
| Ponytail skills | Version 5.3.3 vendored at a pinned commit, checked against upstream | #5 |
| Rule: Ponytail review before merge | In `CLAUDE.md` | #6 |
| Development rules of 2026-11-12 | In `CLAUDE.md`, `PROCESS.md` and `PROMOTION.md`, approved by Achia on 2026-11-13. No rule is enforced by a machine yet | #16 |
| Rule decisions of 2026-11-15 | Decided by Achia, one question at a time: eight deliberately bad PRs must be rejected by CI before Phase 0 closes; Ponytail is used at level `ultra`; speed is measured and is not a gate for now; Tomer is not involved for now, and a legal or regulatory question goes to Achia. In `CLAUDE.md`, `PROCESS.md`, `PROMOTION.md` and `build-plan.md` | #65, #66 |
| Who merges, and the merge gate | Every PR is reviewed before merge by a session that did not write it. Who merges is in `CLAUDE.md`, "Merging", and `PROMOTION.md` section 11. For now nothing merges without Achia's yes to that PR by number. Once the gate works, Claude merges when every check is green, the independent review leaves no finding open and none rejected, and the PR is not one of Achia's. **The gate is not built** (issue #69), so still no rule is enforced by a machine | #67 |
| A small recall check on every PR | Decided by Achia on 2026-11-15: a fixed set of invented documents with known names, and a PR fails when a name that was found before is now missed. **Decided, not built:** it is built in Phase 3; the phase is Claude's reading. In `PROMOTION.md` section 11 and `build-plan.md` section 7 | #67, #68 |
| Rule: web code follows the Modern Web Guidance guides | Asked for by Achia on 2026-11-15. 209 guide files vendored at a pinned commit as a skill; `CLAUDE.md`, "Web code". The source's own program is never installed or run. The one piece of web code in the repository, the worksheet page of E1 and E4, was read against 15 guides: one small finding, not applied (below) | #63 |
| E1 Hebrew PERSON recall | **449 of 470 mentions found, 95.53 percent**, on ten Supreme Court civil judgments. The threshold (below 80) is not crossed. The number is above the prediction (85 to 92). Private parties 274 of 294, 93.20 percent. 13 of the 21 errors are one surname in one document. Counted by Claude, and **not checked by a person**: on 2026-11-14 Achia read only the first page of `doc06` and asked for a ground truth in its place, which is E4. A proposed decision is in the note | #11, #47, #50, #52, #54 |
| E4 PERSON recall against planted names | Not in the plan; built at Achia's request. 40 Hebrew documents written by a script that knows where every name is. **1,084 of 1,145 found, 94.67 percent**, inside the prediction (90 to 96). 51 of the 61 errors are of two kinds: a surname after `משפחת` or `האחים` (22 of 55 found), and a given name alone that is an everyday word (151 of 169). Four Claude readers then counted four of the documents as E1's were counted and agreed with the planted names on 123 of 123 items. **That check shows less than it was meant to:** the three names the model missed in those documents were all on the list of hints the readers were given, so a reader's unaided search was tested on no case. A third part then measured that list of hints by script, with no reader: it holds **57 of the 57** mentions the model missed. So a reader who has the list is pointed to every miss in this text. Whether a reader finds a miss that nothing points to is still not shown | #55, #56, #57, #59, #60 |
| E3 prefix-preserving replacement | 94 of 100 in three runs; the score is inside the prediction, the errors are not where the plan guessed. Decided by Achia on 2026-11-13: no hand-written rule layer in Phase 3 for now, and the six failing forms kept as watched tests. Achia: maximum accuracy stays the aim | #9, #7, #14, #49 |
| E2 CPU latency after INT8 | 1.026 seconds per page on mains power for the encoder and NER head alone; 2.7 to 11.7 seconds on battery. Decided by Achia on 2026-11-13: speed is measured and recorded, per stage, and is not a test that has to pass, for now | #10, #8, #12, #13, #48 |
| Plan: Python 3.13 | Phase 0 targets Python 3.13, not 3.11. Decided by Achia on 2026-11-13 | #51 |
| Phase tracking on GitHub | 14 milestones, one per phase. Issues #17 to #30 and #69 (the merge gate) for Phase 0, #31 to #46 for Phase 1, and #64 for Phase 12. #70 has no milestone | none, made with `gh` |

Findings notes: `docs/findings/2026-11-13-e1-hebrew-recall.md`, `docs/findings/2026-11-14-e4-planted-names.md`, `docs/findings/2026-11-11-e3-prefix-replacement.md` and `docs/findings/2026-11-11-e2-int8-latency.md`. The E1 and E4 notes have an empty `## Decision`. The other two are decided.

## In flight

Nothing. No branch is open besides the one that carries this file.

## Waiting on Achia

1. **The decision on E1 and E4.** One question: is the model good enough at finding names to start building (Phase 0)? The E1 note proposes yes. The E4 note proposes that E4 stands in for the check by a person that E1 did not get. E1: 449 of 470 on real judgments, counted by Claude and not checked. E4: 1,084 of 1,145 on generated text, counted by a script. The E1 note also proposes that the surname shared by several people in `doc10` becomes a named test in Phase 6, and that E1 is run again on documents closer to a lawyer's own before Phase 3 records its baseline; which documents, and from where, is Achia's to say (issue #4). The E4 note adds: both weak kinds, a surname after a group word and a given name alone that is an everyday word, become named test cases in the plan. It does not propose a further test of the readers (its option 3) now; in its place it proposes that a name standing once with no title becomes a hard case of the Phase 5 corpus.
2. **One command, before the CI workflows and the merge gate can be pushed** (issues #22 and #69): `gh auth refresh -h github.com -s workflow`. The token on the laptop has no `workflow` scope.
3. **Three open points of E3, before Phase 3 writes its prefix tests:** how `לה` on a surname is scored; what the product replaces when a surname begins with ה, a design question that goes to Achia when Phase 3 reaches it; and the three forms the 100 did not hold, with how a test that is expected to fail is marked and whether such tests count toward Phase 3's gate. Later, not before Phase 3: the cross-check in Phase 6 against an entity's other mentions, which needs a PR to `build-plan.md`, and whether E3 is run again.
4. **The reference machine.** Which machine `docs/REFERENCE_MACHINE.md` names, and whether the product should say anything to a user on battery. Neither blocks work now.
5. **A block on the `modern-web-guidance` command: yes or no.** A reviewer of #63 proposed a deny rule in `.claude/settings.json` for any command that contains that name. Today the ban is words only. It is a permission setting, so Claude does not add it alone. The file arrives with the merge gate (issue #69); the answer is needed then.
6. **Which browser shows the Phase 12 screens.** Until that is said, web code uses no feature that only one browser engine has; that line is Claude's choice (#63). Not needed before Phase 12.
7. **The trademark check on the name Ploni, and the name question.** `build-plan.md` (line 3, and open decision 6 at its end) left two things with Tomer: a trademark check, and whether a name tied to anonymity clashes with the rule that the product never claims anonymity. Since 2026-11-15 a question the plan gives to Tomer goes to Achia (#65, #66). Not needed before Phase 0.

Not waiting on anyone, and not done:

- The merged branches of 2026-11-11 to 2026-11-15 are still on GitHub. They can be deleted from each PR's page.
- One inconsistency on `main` that the review of #16 named: `CLAUDE.md` says `tests/t0_contract/test_layering.py` enforces the layering, and that file does not exist yet (issue #18). The other two it named were fixed in #65, and issue #30 now says eight as the files do.
- The worksheet page of E1 and E4 marks a name with a background colour only, at about 1.4 to 1 against white, where the guide asks for 3 to 1. The fix is one CSS line, a border. It is not applied: the experiments are finished, and their readers worked from a text version (#63, issue #70).
- Six choices in the rule text of #67 are Claude's, not Achia's words. All six are listed in the body of #67. Nothing is needed unless he wants one changed. Four are stricter than what he said, and were put to him in the chat message of 2026-11-15 that asked for the merge of #67: every merge needs his yes until the fast suite also holds the network test, the two canaries and the layering test; a new or replaced dependency or model is his; a PR with a rejected review finding is his; a hook refuses Claude's edit of `.claude/settings.json`. One is later than what he was told, not stricter: the recall check starts in Phase 3, where he had been told "Phase 2 or so", and until then the gate does not test that idea. The sixth is a reading, in the PR body only: that the gate, once it works, answers the first trigger for the paid plan.
- Three choices in #63 are Claude's too, listed in its body: the source's own program is not run, and the guides are found by file name and text search; a feature that only one browser engine has is not used (item 6 above); document text does not go into a URL or into browser storage.
- `PROCESS.md` section 13 still shows items 3 and 5 as open: where the Ponytail version is recorded, and where the experiments live. `docs/THIRD_PARTY.md` and the `experiments/` folder already answer them. Striking them changes a rule file, so that PR is Achia's to approve.
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
- 2026-11-15: Achia decided the open rule points one question at a time: eight bad PRs, Ponytail `ultra`, a review by a session that did not write the change and automatic tests on every PR behind a free local merge gate, who merges, speed not a gate, Tomer not involved. He also asked for a rule that web code follows the Modern Web Guidance guides, and decided a small recall check on every PR. All of it is on `main` (#63, #65 to #68), merged on his yes: one for #63, #65 and #66 together, one each for #67 and #68. The text on who merges went through three passes by an independent reviewer, 22 findings, all taken. The merge gate is described and not built. Next: the decision on E1 and E4, then Phase 0, which starts with the merge gate (issue #69).
