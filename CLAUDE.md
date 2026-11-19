# Project rules

## Hard constraints
- No networking imports anywhere under ploni/. Downloads live in scripts/ only.
- eval/ may use the network. ploni/ must never import from eval/.
- No document text in logs or temp files. Use ploni/safety/ helpers.
- Pin every dependency version and every model revision by commit hash.
- Never use PyMuPDF. It is AGPL.
- GLiNER v0 and v1 checkpoints are CC-BY-NC and unusable here. Only v2.1 and PII variants.
- No real client documents in the repo, in any form, including fixtures.

## Branching
- One feature, one branch, one concern. feat/<phase>-<slug>, fix/, test/, docs/, chore/.
- A branch that grows a second concern is split, not extended.
- At most three open branches: not merged, not closed. At three, cut no new branch
  until one merges. A waiver request, a findings note or the status PR does not count.
- Cut every work branch (feat, fix, test, docs, chore) from main. One cut from another
  open branch says why in its PR body.
- Create the branch explicitly with git before any work. Do not rely on an auto-generated
  name: the account-level branch prefix setting is "claude" and cannot be cleared, so an
  auto-named branch lands as claude/... and loses the phase the convention carries.

## Function design
- One function, one reason to change. If its name or its docstring's first line needs
  "and", it is two functions.
- A function does not both decide and act.
- Body over 40 lines or complexity over 8 needs a justification in the PR body or a split.
- Over 50 statements or complexity over 10 is split. No justification lifts that.
  Vendored third-party code is exempt.

## Docstrings
- Every module, class and public function has one.
- It answers: What (one line, no "and"), Why it exists, Contract (args, returns,
  raises, units and coordinate systems), Known limits.
- A docstring that restates the function name is a blocking review comment.
- Body comments explain why, never what. Rename instead of explaining.
- Every magic number is a named constant or carries its source.
- Where a value comes from the plan, cite it: # build-plan.md Phase 3: stride 128

## Web code (HTML, CSS, browser JavaScript)
- Before writing any, invoke the modern-web-guidance skill and read the guides that
  fit (Achia, 2026-11-15). HTML that Python code writes counts. The guides are
  vendored at a pinned commit under .claude/skills/modern-web-guidance/guides/.
- Never run or install the source's own program (npx modern-web-guidance). It is not
  pinned, and it reports search words to Google.
- Nothing is loaded from another host: no CDN, no remote font, script or polyfill.
- A PR that touches web code carries ## Modern Web Guidance in its body: each guide
  used, with file and line, what it changed, what was left out.
- The Ponytail reviewer of such a PR invokes the skill too, finds the guides itself,
  and puts what it finds in its review.
- Where a guide and this file disagree, this file wins.

## Tests
- Write the failing test first, in a commit of its own before the implementation. Its
  message carries the failing output.
- Before a PR that changes code under ploni/, run mutation testing on the changed
  modules. Paste the surviving mutants into the PR body.
- Every public function and every private function with real logic gets its own test.
- Every module gets a suite in tests/t4_integration/ over its public surface.
- Enumerate equivalence classes, boundaries, Hebrew axes and adversarial cases in the
  test file before implementing. See the test-matrix skill.
- Minimum samples: detectors 40 positive and 40 negative; invariants 500 generated
  cases, 5,000 at phase close.
- Coverage is a diagnostic, never a target.

## Ponytail
- Ponytail is used here as a skill, at level `ultra` (Achia, 2026-11-15). Invoke it at
  the start of any session that writes code, before writing any, so its rules are in
  context while the code is written.
- At `ultra` the push-back is a question to Achia before building. It drops nothing by
  itself, and never a test, a gate or a plan deliverable.
- Invoke it again on the diff before every PR. Paste the output into the PR body.
- That review is run by a session or subagent that did not write the code, and its
  output names the commit it reviewed.
- Ponytail runs before merge. No branch merges until the Ponytail review has run on
  its final diff. A commit that changes what the branch itself adds or removes makes
  that review stale: run it again and replace the output in the PR body before the
  merge. Taking main into the branch, with no other change, does not.
- Every finding accepted, or rejected with an ADR number from
  docs/adr/APPROVED_ABSTRACTIONS.md.
- Ponytail never removes error handling, validation, safety/, a test, a fixture, or a
  registered abstraction. Those findings are rejected on sight.
- If the ponytail skill is not available in this session, write that under ## Ponytail
  review in the PR body, in those words. Never claim it ran, and never quietly skip it.
  Its status is tracked in docs/THIRD_PARTY.md.

## Merging
- Squash merge only, with the plain `gh pr merge <N> --squash`: no `--admin`, no
  `--auto`. Never around the merge gate: no other merge command, no API call, no local
  merge pushed to main, no check status set by hand, no edit of the gate's own files
  to get a merge through.
- Never past a red, pending or skipped check. Once the fast CI workflow is on main,
  a missing check counts as red too. The one merge command that may be run on such
  a PR is the gate's own test, on a PR that targets a scratch branch
  (`PROMOTION.md` sections 10 and 11).
- Never ask Achia whether to merge (Achia, 2026-11-15; his words are in
  `PROMOTION.md` section 11). Merge a PR when three things hold, and only then. A PR
  that cannot pass does not merge: stop and report.
  1. Every check on its last commit has finished and is green, and the fast-suite
     check is one of them.
  2. The Ponytail review of that commit reports the five readings of `PROMOTION.md`
     Level 2 and leaves no finding open, and none rejected unless Achia decided that
     rejection.
  3. If the PR needs a decision of Achia's, the decision is quoted in the PR, and the
     reviewer found it at its source and reports that the PR does no more, but for
     choices that only narrow Claude (last bullet).
- Until the merge gate works, only these merge. "Works" is in `PROMOTION.md` section
  11, with the list of what each issue named here may hold; that list wins over the
  text of the issue.
  - A PR that changes only `.md` files. While no workflow is on main it has no check
    and merges on 2 and 3.
  - The PRs of issues #17 and #22, then #69, which must refuse a red PR, then #18
    and #19, then #24, then #25. Each merges on all three, its own check green on
    GitHub.

  Nothing else merges. This order is Claude's reading of "all the gating we defined".
  Tell Achia in chat when the gate works, with the number of the refused PR, before
  the first merge of any other kind.
- Paste every review that was run on that commit into the PR, each with the brief its
  reviewer got, word for word. A finding in any of them counts. A finding of an
  earlier review of the PR stays listed there, with what was done about it.
- A PR needs a decision of Achia's when it touches a path of the Level 3 list in
  `PROMOTION.md`; or changes a threshold, baseline, gate value or limit wherever it
  lives; or lowers a ratchet counter; or removes, weakens, skips or deselects a test;
  or removes a fixture or edits one so that it asks less; or adds or replaces a
  dependency or a model; or asks for or uses a waiver; or fills the `## Decision` of a
  findings note; or rejects a Ponytail finding. In doubt, it does. Say in the PR
  whether it does, and why. Granting a waiver is Achia's own act: he fills the
  `## Decision` of the request and edits `docs/WAIVERS.md`. Claude does neither.
- Such a PR merges only after Achia decided what it changes. Ask him that, in plain
  words, not whether to merge. No answer, no merge. Put the question, his answer and
  the date in the PR. What he already decided needs no new question: quote his words,
  or cite a line that names him and the date. A line marked as Claude's reading is
  not his decision.
- The PR does no more than his decision says. What goes beyond it is left out or
  asked first. One thing may stay: a choice of Claude's that only narrows what Claude
  may do, compared with his decision, and changes nothing else. Each is listed in the
  PR, and the reviewer reports for each that it only narrows.

## How work is gated
- Read the relevant build-plan.md phase section first. Restate goal, deliverable, gate.
- Never weaken a test, threshold or baseline to pass a gate. If a gate cannot be met,
  stop and write docs/findings/<date>-<slug>.md, then report.
- Code changes and baseline or gate changes never share a PR. One exception: a PR that adds a
  `# noqa: <code>` line, which names the rule it skips on that one line, raises
  `suppressions_ceiling` in `.ratchet.json` in the same PR, and that raise needs no decision of
  Achia's; the reviewer checks that each new one carries its reason on the line (Achia,
  2026-11-20, "Same PR, no ask each time"). A raise for a bare `# noqa`, a file-wide
  `ruff: noqa` or `flake8: noqa`, or a `type: ignore` line still needs his decision: he was
  asked about a noqa that skips one rule on one line only.
- Speed is measured, for every stage, and recorded at every phase. For now it is not a
  gate: a slow time blocks no merge and stops no work (Achia, 2026-11-13 and
  2026-11-15). This covers the run time of the pipeline only: not memory, not the
  persona and demo budgets, no other gate. A time below the plan's low end is still
  a finding and still stops work.
- Say in `docs/STATUS.md` when a time is clearly worse than the last one measured. At
  every phase close it shows the last two times of each stage side by side.

## Architecture boundaries (enforced by tests/t0_contract/test_layering.py)
- adapters/ may not import detect/, resolve/, policy/, write/
- detect/ may not import write/, rehydrate/, report/
- Only api.py is public. Everything else is internal.

## Measurement discipline
- State the prediction and the disagreement threshold before running a measurement.
- Report the measured number. Never infer a result you did not measure.
- Every claim needs a measured number or a file:line source.

## Commits
- Conventional commits, module-scoped. Measurements go in the commit body.
- Attribution lines per the session reminder.

## Status
- docs/STATUS.md opens with three sections: Done, In flight, Waiting on Achia. Bring it
  up to date in a docs PR of its own at the end of a working day that merged anything
  other than a status PR.
- End a working session by printing the three lists as they are now, and say where
  the file is behind.

## Who decides
- Achia decides alone. For now Tomer has no access to the repository and is not asked
  (Achia, 2026-11-15). If he joins, that is a new decision. A legal or regulatory
  question goes to Achia: explain the risk in plain words and ask.

## Exceptions (PROMOTION.md section 8)
- You have no authority to waive any rule, test, threshold or gate. No flag, comment or
  environment variable turns a gate off.
- If a rule should not apply or a gate cannot be met, the only permitted action is a
  waiver request: a PR touching exactly one new file in docs/findings/, with an empty
  ## Decision section. Then report and stop. No workaround in the meantime.
