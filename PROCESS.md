# Engineering Process: how this project actually gets built

Companion to `build-plan.md`. That document says *what* to build. This one says *how work is executed, reviewed and gated*.
Version 1.1, 2026-11-01. Owner: Achia.

---

## 0. The one rule that matters most

**The agent never moves the goalposts.**

When a gate cannot be met, the work stops and reports the measured number. It does not weaken a test, lower a baseline, loosen a threshold, skip a case, or add an exception to make the gate pass. Code changes and gate changes never travel in the same pull request, and a gate change requires a human decision recorded in writing.

This is the same discipline Achia already uses for hardware investigation: state the prediction and the disagreement threshold before running, never proceed from an assumed result, every claim carries a measured number or a `file:line` source. Agentic coding fails in exactly the place that protocol was built to protect, so the protocol applies here unchanged.

Everything else in this document exists to make that rule enforceable rather than aspirational.

---

## 1. The four-role review of the process itself

### Engineering manager

*"The failure mode of agentic coding is not bad code. It is unreviewable code."*

A session that touches 40 files across two phases produces a diff nobody reads, which means nobody is actually reviewing, which means the gates are theater. Resolution: hard size limits per pull request (section 6.3), one feature per branch, one sub-task per PR, and every PR body carries printed evidence rather than a claim.

*"Velocity is measured in gates passed, not commits merged."*

The status artifact is a gate burn-down, not a commit count.

### Architect

*"Architectural boundaries that live only in prose will be violated by week three."*

Resolution: enforce the layering from `build-plan.md` section 4 in CI with an import test (section 5.2). A PR with `detect/` importing `write/` fails the build, not the review.

*"Minimalism tooling and deliberate architecture will collide, and the tooling will win unless we decide now."*

Ponytail exists to delete abstractions. Three of ours are deliberate and load-bearing: `DocumentAdapter`, `Detector`, and the `safety/` wrappers. Resolution: an **approved abstractions register** (section 4.4). Ponytail flags them, you answer with an ADR number, and the abstraction stays. Anything not in the register and not justified in the PR body gets deleted.

*"Decisions get forgotten and then re-litigated."*

Resolution: short numbered ADRs in `docs/adr/`. One page each. Every architectural call in `build-plan.md` sections 2 and 4 gets backfilled as ADR-0001 onward in Phase 0.

### Product manager

*"A green test suite is not a demonstrated capability."*

Resolution: every milestone has an **exit demo** in addition to its numeric gate. A phase is not closed without both.

*"Scope creep in a side project is invisible until the project is dead."*

Resolution: `build-plan.md` is in the repo. Any change to scope or a gate is a PR against the plan itself. Drift becomes a diff.

*"Tomer needs a narrow surface or he becomes a bottleneck on everything."*

Resolution: he owns exactly `ploni/i18n/claims/`, enforced by CODEOWNERS. Not in force as of 2026-11-15: Tomer is not involved for now, and the question goes to Achia (`CLAUDE.md`, "Who decides").

### Senior software engineer

*"Tests after implementation test the implementation, not the requirement."*

Resolution: for every gate and every public function, the test is written and failing before the implementation lands. The PR shows both.

*"'One function does one thing' plus 'test every function' can produce fifty three-line helpers each with a test file, and that is worse than what it replaced."*

This is the real tension in what we are asking for, and it has to be resolved explicitly or the codebase inflates. Resolution: single responsibility applies at the level of a **meaningful unit of behavior**, not at the level of every expression. The test obligation attaches to every public function and to every private function containing real logic, branching or arithmetic. A private helper that is a named expression with no branches does not get its own test file; it is covered through its caller. Section 4.3 draws the line precisely.

*"A flaky test in an ML pipeline is a test that will be deleted within a month."*

Resolution: pinned thread counts, fixed seeds, fixed matter key, pinned model revisions. Any test that flakes twice is fixed or deleted the same day, never retried until green.

---

## 2. Repository

**One private GitHub repo**, `ploni-engine`, owned by an organization rather than a personal account, because branch protection and CODEOWNERS on a private repo need a paid plan and the organization is what carries it.

### 2.1 In the repo

All source, tests, fixtures, the eval harness, `build-plan.md`, `PROCESS.md`, `CLAUDE.md`, `docs/adr/`, `docs/findings/`, `docs/STATUS.md`, `docs/REFERENCE_MACHINE.md`, `eval/baselines.json`.

### 2.2 Not in the repo

- `models/` is gitignored; models arrive via `scripts/download_models.py` with pinned revisions.
- **No real client documents, ever, in any form, including fixtures.** The corpus is synthetic or self-authored, and `tests/fixtures/MANIFEST.md` records provenance per file.
- No secrets. There are none in v1 by design, and a pre-commit scan keeps it that way.

### 2.3 Branch protection on `main`

- No direct pushes. PR required. Fast CI green required. Linear history, squash merge.
- GitHub enforces none of this on a private repository of the free plan (`PROMOTION.md` section 11). Once built, the merge gate enforces "fast CI green" for a merge made with the plain `gh pr merge`. Nothing enforces the rest.
- CODEOWNERS review on the Level 3 list of `PROMOTION.md`.

### 2.4 One feature, one branch

`feat/<phase>-<slug>` for features, `fix/<slug>`, `test/<slug>`, `docs/<slug>`, `chore/<slug>`.

One branch does one thing. A branch that grows a second concern is split before review, not after. Deleted on merge. Never reused.

At most three branches are open at once, where open means not merged and not closed, pushed or not. At three, no new branch is cut until one merges; a waiver request, a findings note and the status PR do not count toward the three. Every work branch (`feat`, `fix`, `test`, `docs`, `chore`) is cut from `main`; release and hotfix branches follow `PROMOTION.md` section 2. A work branch cut from another open branch has to say why in its PR body, because a stack turns one merge into several: when the branch below is squash-merged, every branch above it must take `main` in before it can merge. On 2026-11-12 seven branches were open at once, six of them in one stack, and two of those had to be merged with `main` by hand before they could go in.

### 2.5 Commits

Conventional commits, module-scoped: `feat(detect): israeli ID checksum detector`. Any commit that produces a measurement puts the measurement in the body.

---

## 3. Three homes for rules

This distinction matters and is easy to get wrong.

**A machine holds every rule a machine can check.** A hook, the linter or CI refuses the change, and nobody has to remember the rule. A written rule is advice that a session can miss; a check is not. So a rule stays in `CLAUDE.md` only while no check enforces it yet: once a hook, lint rule or test covers a rule, its line in `CLAUDE.md` shrinks to a pointer at the check. Until Phase 0 builds the checks (section 12), every rule below is enforced by review alone, and section 11 of `PROMOTION.md` says what that is worth.

**`CLAUDE.md` holds what is always true.** It is read every turn of every session, so it holds the rules that apply to all work and are cheap to check: no network imports, docstring contract, single responsibility, test obligation, layering, commit format. Rules that apply every turn do not belong behind an invocation.

**Skills hold multi-step procedures for a kind of task.** Five of them (section 8.4), each covering something that recurs often enough to be worth encoding and is too long to live in always-on rules.

Keep `CLAUDE.md` short enough that reading it every time is free.

---

## 4. Code standards

### 4.1 One function, one thing

A function has a single reason to change. Practical tests, applied in review:

- Its docstring's first line describes the behavior without using "and".
- You can name it precisely without a conjunction. `parse_and_validate_id` is two functions.
- It does not both decide and act. Detection decides; policy decides; the writer acts. A function that detects an entity and also replaces it violates the architecture, not just style.
- It has one level of abstraction. Mixing byte offsets and business rules in one body is a split.

Two limits. The soft one is enforced in review: a function body over 40 lines or with cyclomatic complexity over 8 needs a justification in the PR body or a split. The hard one is enforced by the linter from Phase 0 and by review until then: a function over 50 statements or with complexity over 10 is split, and no justification lifts that. The linter counts statements, not lines (ruff `PLR0915` and `C901`). Vendored third-party code is exempt: it is pinned byte for byte and cannot be split. The numbers are a judgment, not a measurement.

### 4.2 The docstring contract

Every module, class and public function carries a docstring. It answers four things, in this order:

1. **What** it does, one line, no "and".
2. **Why** it exists. This is the part that is usually missing and the part that is worth the most in six months. Not "validates the ID" but why validation happens here, at this layer, in this form.
3. **Contract**: arguments, return, and what it raises. Units and coordinate systems stated explicitly, because half the bugs in this project will be offset bugs.
4. **Known limits**: what it deliberately does not handle.

```python
def split_proclitic(token: str, segmentation: list[str]) -> tuple[str, str]:
    """Split a Hebrew token into its proclitic prefix and its base.

    Why: replacement must rewrite only the name and leave the prefix in
    place, so that "וליעקב" becomes "ולדוד" rather than "דוד". Doing this
    with a regex over the prefix letters is wrong, because many real names
    begin with those same letters (ברק, משה, שרה), so we consume the
    model's morphological segmentation instead of guessing.

    Contract: `token` is the surface form as it appears in the document;
    `segmentation` is the morpheme list for this token from
    dictabert-joint, in document order. Returns (prefix, base), where
    prefix is "" when the token carries none. Raises
    SegmentationMismatch if the morphemes do not reassemble into token.

    Known limits: does not handle construct state or possessive
    suffixes; those are handled one layer up in resolve_surface_form.
    See ADR-0007.
    """
```

Rules:
- A docstring that only restates the function name is a blocking review comment. `"""Validates the ID."""` on `validate_id` adds nothing.
- Comments inside the body explain **why**, never what. If a line needs a comment to say what it does, rename things instead.
- Every magic number, threshold and offset convention is either a named constant or carries a comment with its source.
- Where a value comes from the plan, cite it: `# build-plan.md Phase 3: stride 128`.

### 4.3 The test obligation, and where it stops

| Code | Test obligation |
|---|---|
| Public function in any module | Its own test: happy path, every documented error, and the edge cases from its equivalence classes (section 7) |
| Private function with branching, arithmetic, parsing or state | Its own test, same standard |
| Private helper that is a named expression with no branches | No separate test; covered through its caller |
| Module as a whole | A module suite in `tests/t4_integration/test_<module>.py` exercising the module's public surface end to end, not function by function |
| Anything crossing a layer boundary | A contract test in `tests/t0_contract/` |
| Any invariant statable over generated input | A property test in `tests/t2_property/` |

**The test is written first and shown failing.** The failing tests are a commit of their own, before the commit that implements, and that commit's message carries the failing output. A commit that holds both a test and the code it tests cannot show which came first, so it counts as tests written after. That is visible in the commit order and is a blocking review comment.

**A passing test can still check nothing.** Before a PR that changes code under `ploni/`, mutation testing is run on the changed modules: a tool makes small deliberate errors in the code, and a test suite that still passes has not noticed them. Running it and pasting the surviving mutants into the PR body is required. Answering each survivor, with a test or by naming it equivalent, is expected and does not block a merge: some survivors are equivalent, and a full run is slow. At phase close it is run over the whole of `ploni/` (section 7.4). Phase 0 picks a tool that runs on the development machine, which is Windows, and pins it.

Coverage is a diagnostic, not a target. The questions in review are "is every documented error path tested" and "are the edge cases from the equivalence classes present", not "what is the percentage".

### 4.4 The approved abstractions register

`docs/adr/APPROVED_ABSTRACTIONS.md` lists every deliberate indirection with its ADR number and the one-line reason it exists:

| Abstraction | ADR | Why it is not over-engineering |
|---|---|---|
| `DocumentAdapter` protocol | ADR-0003 | Isolates the riskiest component; a DOCX rewrite must not cascade into detection, and XLSX, PDF and EML plug in behind it without touching anything above |
| `Detector` protocol | ADR-0004 | Roughly 15 implementations in Phase 1 alone; fusion must not know about any of them |
| `safety/` wrappers | ADR-0005 | Logging and temp-file redaction must be impossible to bypass accidentally |
| Four-function public API | ADR-0002 | The Word add-in and the gateway are consumers, not rewrites |
| Worker process | ADR-0006 | Real cancellation, memory isolation, deterministic thread counts |

When Ponytail flags one of these, the answer is the ADR number, and the abstraction stays. When it flags anything **not** in this register, the default is to delete the abstraction. Adding a row to this file is a CODEOWNERS-protected change, so growing the register is deliberate.

### 4.5 Static checks

`pyproject.toml` holds one ruff configuration and one mypy configuration, written in Phase 0. A PR passes both with no warnings.

- **ruff, on `ploni/`, `eval/`, `scripts/`, `tests/` and `experiments/`:** likely bugs, errors caught and dropped, unsafe calls, the hard limit of section 4.1, unused and commented-out code, and `print` under `ploni/`.
- **ruff's banned imports:** PyMuPDF anywhere, and networking modules under `ploni/`. Two hard constraints of `CLAUDE.md` become a lint error.
- **mypy, strict, on `ploni/` only.** Not on `experiments/`, which is not product code.
- **Vendored third-party code is outside both tools:** `experiments/*/vendored/` today, and the model's code wherever Phase 3 puts it. It is pinned byte for byte, so it cannot be changed to satisfy a linter.
- **Suppressions:** a `noqa` or a `type: ignore` carries its reason on the same line. Phase 0 adds a ceiling counter for them to `.ratchet.json`: a number that may not rise, where the ratchet's existing counters may not fall.

None of this exists yet. There is no `pyproject.toml`, and neither tool is installed or pinned.

---

## 5. CI

### 5.1 Two workflows

**Fast suite**, every push and PR, under five minutes: ruff, mypy, T0 contract including layering, T1 unit, T2 property at reduced example counts, T3 golden, T8 privacy, secret scan, docstring presence check. Also the per-PR recall check that Achia decided on 2026-11-15, from Phase 3 (`PROMOTION.md` section 11 says what it is and why Phase 3); whether the five minutes still hold with it is measured when it is built.

**Full suite**, on a `run-full` label, on phase-close PRs, and nightly: everything above at full example counts, plus T4 integration, T5 system journeys, T6 metric gates, T7 performance.

### 5.2 The layering test

A test, not a lint rule, so it runs everywhere:

```python
LAYERS = {
    "ploni.adapters": {"ploni.types", "ploni.safety", "ploni.errors"},
    "ploni.detect":   {"ploni.types", "ploni.morph", "ploni.safety", "ploni.errors", "ploni.config"},
    "ploni.resolve":  {"ploni.types", "ploni.morph", "ploni.safety", "ploni.errors"},
    "ploni.policy":   {"ploni.types", "ploni.morph", "ploni.mapping", "ploni.safety", "ploni.errors"},
    "ploni.write":    {"ploni.types", "ploni.adapters", "ploni.safety", "ploni.errors"},
}
```
Walk every module's AST, assert each intra-project import is allowed for its layer, fail with the offending `file:line`.

### 5.3 The docstring check

A test, not a style preference: every module, class and public function has a docstring, and it contains a `Why:` section; a public function's docstring also contains a `Contract:` section. Mechanical presence only. Quality is a review judgment, because no linter can tell a real reason from a restated name.

### 5.4 The models problem, and the honest answer

Metric gates need models over a gigabyte and real measurements. On a hosted runner that is slow and brittle.

Decision: **metric gates run locally and their results are committed.** `eval/run_eval.py` writes `eval/results/<git-sha>.json` with the metrics, the code SHA, the model bundle version and the name bank version. CI asserts a results file exists for the current code hash whenever a protected path changed. If the code changed and the measurement did not, the build fails, so a stale number becomes visible instead of staying quiet.

### 5.5 What CI cannot enforce

Ponytail is an agent-side skill, not a CI binary, so no workflow can run its review for you. What CI can do is assert that the PR body contains a filled `## Ponytail review` section. The substance is checked at review; `PROMOTION.md` Level 2 says who reads. Say this plainly rather than pretending the pipeline enforces it.

### 5.6 Pre-commit

ruff, mypy on changed files, secret scan, no-network AST scan, docstring presence. Fast only. A slow pre-commit hook gets bypassed with `--no-verify`, which makes it worse than no hook.

---

## 6. Scoping and merging

### 6.1 Milestones map to phases

Fourteen milestones, one per row of `build-plan.md` section 10. A milestone closes when its numeric gate passes **and** its exit demo has been shown.

### 6.2 Issues

One issue per sub-task, created when the phase starts, not up front for the whole project. Each carries the phase, the slice of deliverable, the tests it must add, and its acceptance condition. An issue that cannot state its acceptance condition is not ready to start.

### 6.3 Pull request limits

| Limit | Value |
|---|---|
| One phase per PR | hard |
| One concern per branch | hard |
| Production files changed | 10 soft, 15 hard |
| Net production lines | 400 soft, 800 hard (tests, fixtures, golden files excluded) |
| Reviewable in | 15 minutes |

Over a hard limit, split before review. No exception for "it is all related".

### 6.4 PR body template

The template is `.github/pull_request_template.md`. It is not printed here: a copy falls behind the file.

**A PR missing pasted gate evidence or a Ponytail section is closed unreviewed.** This is the highest-leverage rule in the document, because it makes "I ran it" impossible to assert without showing output.

### 6.5 Review order

Read the gate evidence, then the Ponytail section, then the tests, then the implementation. If the tests do not convince you, stop and send it back without reading the implementation.

---

## 7. The production gate

Merging to `main` is the production boundary. Everything below must hold, with evidence in the PR body.

### 7.1 Ponytail, as a hard condition

Ponytail is used here **as a skill**, not as a marketplace plugin, so it is invoked by name rather than through slash commands. If the installed copy also exposes the mode and review commands, use them; the obligations below are the same either way.

Required on every branch before merge:

1. **Invoke the ponytail skill at the start of the session, before writing code.** Its rules have to be in context while the code is being written. Retrofitting minimalism after the fact produces a rewrite instead of a review.
2. **Invoke it again on the final diff** as a review pass, and paste its output into the PR body. The pass is run by a session or subagent that did not write the code: on 2026-11-12 fresh reviewers found more than fifty things in five branches that the writing session had either reviewed already or thought finished. The output names the commit it reviewed. A later commit that changes what the branch itself adds or removes makes the review stale; taking `main` into the branch, with no other change, does not. The reviewer also answers one fixed question: does every docstring the change touches still describe its code.
3. Every finding either **accepted** (code changed) or **rejected with an ADR number** from the approved abstractions register. A rejection with no ADR is not a rejection; either delete the abstraction or open an ADR and argue for it.
4. At every phase close, run it over the whole module or repo rather than a single diff, and triage the findings into fix-now or carried debt.
5. Carried debt is recorded in `docs/DEBT.md` with a named reason and an issue number. Reviewed at every phase close. If the skill tracks debt itself, use that instead and keep the file as a pointer to it.

What Ponytail must never be allowed to delete, and the rule is absolute because this product's whole value is correctness: error handling, input validation, the `safety/` layer, any test, any fixture, and anything in the approved abstractions register. If a Ponytail finding points at one of these, it is rejected on sight and the rejection is recorded.

### 7.2 The edge-case battery: a large representative sample

"Tested" in this project does not mean a happy path and one error. Every module ships a battery built from explicit equivalence classes, so the sample represents the space rather than the cases that happened to come to mind.

For each public function, enumerate in the test file:

- **Equivalence classes** of valid input, one case each.
- **Boundaries** of every class: zero, one, maximum, maximum plus one, empty, single element, duplicate elements.
- **Invalid input** per documented error path, each asserting the specific exception.
- **Hebrew-specific axes**, which is where this product actually breaks: proclitics and their combinations; ktiv male and haser; final letter forms; niqqud present and absent; gershayim as both `"` and `״`, geresh as both `'` and `׳`; names that are ordinary words; mixed Hebrew and Latin in one span; RTL and LTR runs adjacent; geresh inside transliterated names.
- **Structural axes** for document code: text split across runs, span at a block break, span at a window edge, text in a header, in a footnote, in a comment, in a tracked deletion, in a table cell, in a text box.
- **Adversarial cases**: the input designed to break this specific function, named as such in the test.

Minimum sample sizes, enforced at review:

| Kind of code | Minimum |
|---|---|
| Detector | 40 positive, 40 negative, with the Hebrew and separator axes present |
| Pure function with a stated invariant | 500 generated cases in T2, 5,000 at phase close |
| Document adapter | the full 15-file fixture corpus |
| Module suite | every public function exercised, plus the module's own failure modes |
| Full pipeline | the 200-document eval corpus |

A property test is how you get a large sample honestly. Write the invariant, let `hypothesis` generate thousands of cases, and record the example count in the PR body. Hand-written examples cover what you thought of; generated cases cover what you did not.

### 7.3 The merge checklist

| Condition | Evidence |
|---|---|
| Fast suite green | CI |
| Layering and docstring checks green | CI |
| Every new public function has its own test | review |
| Equivalence classes and boundaries enumerated in the test file | review |
| Sample size at or above the minimum for this kind of code | PR body |
| Phase gate met, or not applicable to this PR | pasted output |
| No baseline, threshold or test weakened | review plus diff |
| Ponytail review clean or every finding justified by ADR | PR body |
| Docstrings answer Why, not just What | review |
| Golden diffs explained | PR body |

### 7.4 Phase close, which is a higher bar than merge

Additionally: full suite green, metric gates at or above baseline with the results file committed, a Ponytail pass over the whole module or repo rather than a single diff with findings triaged, mutation testing over the whole of `ploni/` with the survivors triaged, carried debt reviewed, exit demo shown, `docs/STATUS.md` row appended, and any new ADRs merged.

---

## 8. Running a Claude Code session

### 8.1 Scoping

One session, one issue, one branch, one PR. A session that finds it needs to change something outside its issue stops and says so rather than growing.

### 8.2 Shape

1. **Orient.** Read `CLAUDE.md`, the relevant `build-plan.md` phase section, the issue. Restate goal, deliverable, gate and downstream risk before touching code.
2. **Invoke the ponytail skill**, before any code is written.
3. **Branch.** One concern.
4. **Enumerate the test matrix.** Equivalence classes, boundaries, Hebrew axes, adversarial cases, before any implementation.
5. **Write the failing tests.** Run them. Commit them on their own, with the failing output in the commit message.
6. **Implement.** Smallest change that passes. Docstring with Why on everything public.
7. **Measure.** Run the gate. Capture real output.
8. **Ponytail review.** A session or subagent that did not write the code invokes the skill on the final diff. Accept or justify every finding.
9. **PR.** Body template, all evidence pasted.

### 8.3 Never

- Change a baseline, threshold or gate.
- Mark a test `skip` or `xfail` to get green.
- Touch two phases or two concerns.
- Rewrite a golden file without explaining why.
- Claim a measurement you did not run.
- Install an unpinned dependency.
- Add a model not recorded in `docs/THIRD_PARTY.md`.
- Delete error handling, validation, a test or a fixture because Ponytail suggested it.

### 8.4 The five skills

- **`phase-gate`**: run a numbered phase end to end with its gate. Recurs 14 times.
- **`new-detector`**: add a detector with its fixture corpus and measured numbers. Recurs roughly 15 times in Phase 1.
- **`eval-baseline`**: run the metric suite, compare to baselines, handle regressions and baseline changes. Every phase boundary.
- **`test-matrix`**: build the equivalence-class and edge-case battery for a function or module. Every feature branch.
- **`production-gate`**: the merge-to-main gate, including Ponytail, evidence collection and the checklist. Every PR.

Everything always true lives in `CLAUDE.md`, not in a skill.

---

## 9. CLAUDE.md

`CLAUDE.md` at the repository root is the file itself. This section used to print a copy of it, and the copy was behind the file from the first commit, so it is gone. Change the file, not a copy of it.

---

## 10. Stop and report

When a gate cannot be met, or a measurement disagrees with its prediction beyond the stated threshold, work stops and `docs/findings/<YYYY-MM-DD>-<slug>.md` is written:

```markdown
# Finding: <one line>
## What was being measured
## Prediction and threshold
## Measured result
(raw output, pasted)
## What this rules in and what it rules out
## Options, with the cost of each
## Recommendation
## Decision
(left blank; Achia fills this in)
```

The note is a PR of its own. Nothing is tuned or loosened, and no further implementation happens on that path until the decision line is filled.

**Speed is the exception, for now.** Decided by Achia on 2026-11-13 and again on 2026-11-15: speed is measured for every stage and recorded at every phase, and it is not a test that has to pass. A slow time, past its target or its fail threshold, stops no work and blocks no merge. This holds until Achia turns speed into a gate.

- What it covers: the run time of the pipeline's own work, and nothing else. Peak memory stays a limit. The time a person needs in the persona and demo gates is not touched. No other gate is touched (`docs/findings/2026-11-11-e2-int8-latency.md`, Decision, point 2).
- A time below the low end of the plan's table is still a finding and still stops work: it points at missed text (`build-plan.md` section 8.2).
- T7 fails on no slow time, so a slow time does not turn the full suite red. It still fails on peak memory over its limit and on a time below the low end.
- Each time is reported with the power state of its run. The same files took 1.03 seconds on mains power and up to 11.7 on battery (`docs/findings/2026-11-11-e2-int8-latency.md`).
- At every phase close `docs/STATUS.md` shows the last two times of each stage side by side, and says when one is clearly worse.

Findings notes are the project's memory. Six months later, "why is this threshold 0.92 and not 0.98" has an answer with the raw numbers attached.

---

## 11. Cadence and status

**Per working day:** `docs/STATUS.md` opens with three sections: Done, In flight, Waiting on Achia. At the end of a working day that merged anything other than a status PR, it is brought up to date in a docs PR of its own. It is not edited by every PR: two open PRs that change the same lines conflict, and a line saying "in flight" would be wrong on `main` the moment its PR merged. A status that lives only in PR bodies is nowhere when nothing has been pushed, which is how 2026-11-12 began.

**Per session:** the PR body is the status report, and the session ends by printing the three lists as they are now, saying where `docs/STATUS.md` is behind them.

**Per phase close:** one row appended to `docs/STATUS.md`: phase, gate, measured number, date, exit demo shown. That file is the whole project status in one screen.

**Weekly, fifteen minutes:** which gates moved, which numbers changed, what is blocked, what the next session is. Three lines appended to `docs/STATUS.md`.

Gates passed is the only velocity metric that means anything here.

---

## 12. Phase 0, revised

`build-plan.md` Phase 0 builds the code skeleton. It also builds the process scaffolding, in this order:

1. Private repo, branch protection, CODEOWNERS.
2. `CLAUDE.md` at the repository root.
3. `build-plan.md` and `PROCESS.md` committed.
4. Ponytail available as a skill; its invocation name and, if it has them, its mode commands recorded in `CLAUDE.md`.
5. The five skills saved.
6. ADR-0001 onward backfilling decisions already made, plus `docs/adr/APPROVED_ABSTRACTIONS.md`.
7. Milestones for all 14 phases. Issues for Phase 0 and Phase 1 only.
8. Fast and full CI workflows, pre-commit, the layering test, the docstring check, the PR-body Ponytail-section check. With them, the checks the rules of 2026-11-12 need:
   - `pyproject.toml` with the ruff and mypy configuration of section 4.5, and the ceiling counter for suppressions in `.ratchet.json`.
   - Hashes in every requirements file, the ones under `experiments/` included, and installs with `--require-hashes`.
   - Claude Code hooks committed in `.claude/settings.json`: refuse `--no-verify`, refuse a push to `main`, refuse an edit to `docs/WAIVERS.md`, the one file only Achia writes, and refuse an edit to the files that hold these hooks and the merge gate: `.claude/settings.json`, `.claude/settings.local.json`, which git ignores on this laptop and which can switch hooks off, and `scripts/guard.py`, the script that the hook entry starts. The rules are in that script and not in the settings file, which holds one command line that cannot be tested (Achia, 2026-11-16; his words are in `PROMOTION.md` section 11). The first version of the two committed files arrives by PR before the hooks are live; a later change is a script that Claude writes and Achia runs, after Claude has told him in plain words what it changes and he has said yes to that change in chat. This fourth hook was Claude's proposal of 2026-11-15, taken from a review. Achia decided it on 2026-11-16. He was asked: "Do you want a guard that stops me from editing the guard files themselves (the settings file and the Python file)?" The first answer offered was "Yes", with its price: "every later change to the guards is a small script that I write and you run once." The second was "No, leave it out. Later changes to the guards go through a normal PR, with nothing for you to run." He wrote: "1 - if u wanna change the guard u need to bring it to my approval". The question named one settings file. That the hook covers `.claude/settings.local.json` as well is Claude's choice, kept from the proposal, and it only narrows what Claude may do. A small set, because a hook that fires wrongly stops work. No hook runs the test suite when a session ends its turn: test-first needs a commit whose tests fail, and section 10 needs a session to be able to stop and report.
   - The merge gate of `PROMOTION.md` section 11, built first: a Claude Code hook in `.claude/settings.json` that refuses the plain `gh pr merge` unless every check on the PR's last commit has finished and is green, and the fast-suite check is one of them. A missing, pending or skipped check counts as red. Decided by Achia on 2026-11-15, in place of paid branch protection.
   - A local `pre-push` git hook that runs the fast suite: the free stand-in for required status checks, which GitHub Free does not enforce on a private repository (`PROMOTION.md` section 11).
   - The commit-order check of `PROMOTION.md` section 5.2. Its row there states what it covers.
   - A check that the commit named in the PR's Ponytail section is the PR's last commit, or that every commit after it is a merge of `main` that leaves the branch's own diff unchanged.
   - A mutation testing tool that runs on Windows, chosen and pinned.
   - `pyproject.toml` and `.claude/settings.json` are in `CODEOWNERS` and on the Level 3 list of `PROMOTION.md` since 2026-11-15, before the files exist, so a code PR cannot loosen a limit with one line of configuration. Check that they still are.
   - The `CLAUDE.md` lines these checks cover shrunk to pointers, and the two rules that waited for a tool added there as pointers: hashed requirements, and no warnings from ruff and mypy.
9. `eval/baselines.json` skeleton, `docs/STATUS.md`, `docs/REFERENCE_MACHINE.md`, `tests/fixtures/MANIFEST.md`.
10. Then the code skeleton from `build-plan.md` Phase 0.

**Phase 0 is not closed until eight deliberately bad PRs are each rejected by CI, and the merge gate has refused each.** The eight are listed in `PROMOTION.md` section 10, "The closing test for Phase 0". This line said four until 2026-11-15, when Achia decided on eight. Prove the guardrails work before trusting them.

---

## 13. Open process decisions for Achia

1. ~~**Repo name.**~~ Decided 2026-11-11: `ploni-engine`.
2. ~~**What the installed ponytail skill actually exposes.**~~ Decided 2026-11-15: the skill takes a level, and this project uses `ultra` (`CLAUDE.md`, `docs/THIRD_PARTY.md`). The recommendation below was the middle level; Achia chose the highest. As first written: Does your copy have intensity modes and separate review, audit and debt commands, or is it a single skill invocation? This changes steps 1, 2 and 4 of section 7.1 from commands into plain invocations. Record the answer in `CLAUDE.md` so every session uses it the same way. If it does have intensity modes, the recommendation is the middle level while writing and the most aggressive level only for a deliberate audit of a finished module, because that extra pressure lands on validation and error handling.
3. **Record the Ponytail version.** It shapes the code that ships, so it is a dependency. Record its source and version in `docs/THIRD_PARTY.md` like any other.
4. ~~**Self-review discipline.**~~ Decided 2026-11-15: every PR is reviewed before merge by a session or subagent that did not write it (`CLAUDE.md`, Ponytail), and who merges is in `CLAUDE.md`, "Merging". As first written: You are the only reviewer. Recommendation: cold review the next session for anything in Phases 2, 3, 7 and 10; merge on green elsewhere.
5. **Where the week-one experiments live.** Recommendation: `experiments/`, excluded from the layering test, the docstring check and coverage, with findings notes as the output. It is not product code and gating it wastes time.
6. ~~**Tomer's access.**~~ Decided 2026-11-15: none for now. Tomer is not involved; legal and regulatory questions go to Achia (`CLAUDE.md`, "Who decides"). If he joins, that is a new decision. As first written: Recommendation: collaborator, CODEOWNERS on `ploni/i18n/claims/` only.
