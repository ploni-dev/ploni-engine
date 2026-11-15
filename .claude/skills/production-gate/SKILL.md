---
name: production-gate
description: Run the merge-to-main gate for a branch: the Ponytail skill pass with ADR-justified rejections, the evidence checklist, and the phase-close extras. Use before opening a PR or closing a phase.
---

# The production gate

`main` is the integration boundary; a release tag is the shipping boundary. Nothing crosses either without evidence. Run this before opening any PR.

**You have no authority to waive any rule here.** If something cannot be met, section 6 is the only permitted path.

## 1. Ponytail

Ponytail is installed here **as a skill**, invoked by name. If the installed copy also exposes mode or review commands, use them; the obligations are the same either way.

1. **It should already have been invoked at the start of this session, before any code was written**, at level `ultra` (`CLAUDE.md`, Ponytail). Its rules have to be in context while code is written. Retrofitting minimalism afterwards produces a rewrite, not a review. If it was not invoked at the start, say so plainly in the PR body rather than pretending otherwise.
2. **A session or subagent that did not write the code invokes it on the final diff** as a review pass (`CLAUDE.md`, Ponytail). Its output names the commit it reviewed. On a PR that Claude merges, it also reports the five readings of `PROMOTION.md` Level 2, and every review run on that commit is pasted with its brief (`CLAUDE.md`, "Merging").
3. Paste its output into the PR body under `## Ponytail review`.
4. Resolve **every** finding as one of:
   - **Accepted**: change the code.
   - **Rejected**: cite the ADR number from `docs/adr/APPROVED_ABSTRACTIONS.md` that justifies the abstraction. A rejection with no ADR is not a rejection. Either delete the abstraction, or open an ADR and argue for it in its own PR.

At phase close, run it over the whole module or repo rather than a single diff, and triage findings into fix-now or carried debt. Carried debt goes in `docs/DEBT.md` with a named reason and an issue number, unless the skill tracks debt itself.

### Intensity

`ultra`, decided by Achia on 2026-11-15 (`CLAUDE.md`, Ponytail). This file said the middle level until then, because the extra pressure of the highest level lands on exactly the validation and error handling this product cannot trade away. Two rules of `CLAUDE.md` hold that risk: Ponytail never removes error handling, validation, `safety/`, a test, a fixture or a registered abstraction; and at `ultra` the push-back is a question to Achia before building, which drops nothing by itself.

### What Ponytail must never remove

Absolute, because this product's entire value is correctness:

- error handling
- input validation
- anything under `ploni/safety/`
- any test
- any fixture
- anything in the approved abstractions register

A finding pointing at one of these is rejected on sight and the rejection is recorded. Fewer lines is worth nothing here if it costs a validation path.

## 2. The registered abstractions, so they are not re-argued every PR

Ponytail will flag these. The answer is the ADR number.

| Abstraction | ADR | Why it stays |
|---|---|---|
| `DocumentAdapter` protocol | ADR-0003 | Isolates the riskiest component; a DOCX rewrite must not cascade into detection, and XLSX, PDF and EML plug in behind it |
| `Detector` protocol | ADR-0004 | Roughly 15 implementations; fusion must know about none of them |
| `safety/` wrappers | ADR-0005 | Log and temp-file redaction must be impossible to bypass by accident |
| Four-function public API | ADR-0002 | The Word add-in and the gateway are consumers, not rewrites |
| Worker process | ADR-0006 | Real cancellation, memory isolation, deterministic thread counts |

Anything **not** in the register and not justified in the PR body gets deleted. Adding a row is CODEOWNERS-protected.

## 3. Leave main green

Every PR must leave `main` coherent, because phases are milestones and not branches: each PR merges separately. So **wire it up last**. The PR that adds a new module does not register it in the pipeline; a later small PR does, once it is proven. If a change cannot be split without breaking `main`, put the new path behind a flag in `config.py`, default off, and flip it in the final PR.

## 4. The merge checklist

Every row needs evidence, not assertion. CI enforces some of these and will reject the PR without you; the rest are read at review (`PROMOTION.md` Level 2 says by whom).

| Condition | Evidence |
|---|---|
| One concern, one branch | the diff |
| Fast CI green on GitHub | the required check, not a local run |
| Layering, docstring, ratchet, size and structure checks green | CI |
| Failing test written before implementation | commit order within the branch, plus the failing output pasted |
| Every new public function has its own test | review |
| Every private function with real logic has its own test | review |
| Module suite updated if the public surface changed | review |
| Equivalence classes, boundaries and applicable Hebrew axes enumerated in the test file | review |
| Sample size at or above the minimum for this kind of code | the number, in the PR body |
| Phase gate met, or marked not applicable | pasted command and output, with the results file SHA matching HEAD |
| Prediction stated before the run and compared to the measurement | PR body |
| No test, threshold, fixture or baseline weakened | ratchet plus review |
| No baseline or gate change in this PR | the diff |
| Ponytail review run, every finding resolved | PR body |
| Web code, if the PR has any, written with the `modern-web-guidance` skill | `## Modern Web Guidance` in the PR body |
| Docstrings answer Why, not just What | review |
| Golden file diffs explained | PR body |

## 5. PR body

Use the body in `.github/pull_request_template.md`. It is not printed here: a copy falls behind the file.

A PR missing the gate evidence, the orientation block or the Ponytail section is closed unreviewed.

## 6. If a gate cannot be met, or a rule should not apply

Stop. Do not weaken anything, do not proceed with a simpler approach in the meantime, do not grant yourself an exception.

Open a waiver request: a PR touching exactly one new file, `docs/findings/<YYYY-MM-DD>-<slug>.md`, and nothing else, containing the rule in question, why the work cannot proceed under it, what was measured with raw output, the prediction and threshold as stated before the run, the options with their costs, your recommendation, the scope requested (which rule, which files, until when), and an empty `## Decision` section.

Then report and stop. Only Achia can grant it, by filling in the decision and adding an entry to `docs/WAIVERS.md`. A PR relying on a waiver cites `waiver: WAIVER-NNN` in its body; CI verifies the ID exists, has not expired, and that the changed paths are inside its scope.

## 7. Phase close, a higher bar than merge

In addition to everything above:

- Full suite green: T4 integration, T5 system journeys, T6 metrics, T7 performance. For now T7 fails on no slow time; it still fails on peak memory over its limit and on a time below the low end (`PROCESS.md` section 10)
- Metric gates at or above baseline, with the results file committed and its SHA matching the phase-close commit (see the `eval-baseline` skill)
- Ponytail pass over the whole module or repo, findings triaged
- Mutation testing over the whole of `ploni/`, survivors triaged
- Carried debt reviewed; each item has a named reason and an issue
- Open waivers listed, expired ones closed
- Exit demo shown: a thing you can watch, not just a green suite
- One row appended to `docs/STATUS.md`: phase, gate, measured number, date, exit demo shown
- Any new ADRs merged

## 8. What CI cannot do, stated plainly

Ponytail is an agent-side skill, not a CI binary, so no workflow can run its review for you. CI can only assert that the `## Ponytail review` section exists and is non-empty. The substance is checked at review (`PROMOTION.md` Level 2 says by whom), and the presence of the section is not the gate: the gate is that every finding was actually resolved.

The same is true of docstring quality, of whether the chosen equivalence classes cover the real input space, and of whether an ADR cited in a rejection actually applies. Those are judgments for the reader at review, not for the author. Do not report them as passed; report what you did and let the review decide.
