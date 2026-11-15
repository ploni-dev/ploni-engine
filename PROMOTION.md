# Promotion and Enforcement: how code reaches production, and how the rules are guaranteed

Third document, alongside `build-plan.md` (what to build) and `PROCESS.md` (how work is done).
This one answers two questions: **how does code actually get to production**, and **what guarantees the rules are followed rather than merely stated**.
Version 1.0, 2026-11-01. Owner: Achia.

---

## 1. The principle

**A rule that lives only in `CLAUDE.md` is a request, not a constraint.**

An agent under pressure to finish a task will follow a stated rule most of the time. Most of the time is not a guarantee, and you will not know which turn was the exception. So the architecture does not rely on the agent's compliance or its self-report. It relies on this:

> Every check that can run in a place the agent cannot write to, runs there. Everything else is structured so that skipping it produces an artifact that contradicts itself.

Three consequences that shape everything below:

1. **The gate runs on GitHub, not on the agent's machine.** Locally run tests reported in a message are a claim. The same tests run by GitHub Actions as a required status check are a fact. The agent cannot edit the result.
2. **Numbers must be bound to the code that produced them.** A pasted metric is unverifiable. A metric in a results file that carries the code SHA, which CI compares to `HEAD`, cannot be fabricated without also forging a matching commit.
3. **Quantities only ratchet upward.** Test count, fixture count, assertion count, baselines. Any decrease requires a separate approved pull request. This turns "do not weaken the tests" from a request into an invariant.

What this does not give you: certainty that the agent never tries. What it gives you is that every attempt either fails mechanically or leaves a visible, named artifact you have to approve.

---

## 2. Branch topology

```
  main ────────●───────●───────●──────────●─────────────●──────▶  always green
               ▲       ▲       ▲          ▲             ▲
               │       │       │          │             │
        feat/1-types  fix/…  feat/2-docx  │      hotfix/0.1.1
                                          │             ▲
                                   release/0.1.0 ──●──● │
                                                   │    │
                                                 tag v0.1.0
```

| Branch | Lifetime | Rules |
|---|---|---|
| `main` | permanent | Never pushed to directly. Every commit arrives by squash merge from a PR with required checks green. Must be green and releasable in principle at every commit. |
| `feat/<phase>-<slug>` | hours to days | One concern. Deleted on merge, never reused. |
| `fix/<slug>`, `test/<slug>`, `docs/<slug>`, `chore/<slug>` | short | Same rules. |
| `release/<x.y.z>` | days | Cut from `main` at feature freeze. Only stabilization commits. Tagged, then deleted. |
| `hotfix/<x.y.z>` | hours | Cut from the release tag, not from `main`. Merged back into `main` after the tag. |

### 2.1 There is no `develop` branch, deliberately

Git-flow's `develop` exists so a team can integrate without destabilizing a release line. With one developer and one reviewer it adds a merge step that nobody benefits from reviewing. `main` protected plus release branches gives the same safety with one fewer place for work to rot.

### 2.2 A phase is a milestone, not a branch

This is the natural wrong turn, so it is stated explicitly. Phase 2 has several PRs. They each go to `main` separately. There is no long-lived `phase-2` integration branch.

The reason: a long-lived integration branch defers the moment of truth. Bugs compound behind it, the eventual merge is unreviewable, and `main` stops being a trustworthy baseline.

**The constraint this creates:** every PR must leave `main` green and coherent. For a library this is easy, because a new module that nothing calls yet is inert. The rule that follows: **wire it up last.** The PR that adds `ploni/detect/hebrew_ner.py` does not register it in the pipeline. A later, small PR does, once it is proven.

If a change genuinely cannot be split without breaking `main`, that is a design signal, not a reason for a long branch. Put the new path behind a flag in `config.py`, default off, and flip it in the final PR.

---

## 3. Two production boundaries, not one

"Production" means two different things here and conflating them is where sloppiness enters.

**Boundary 1: merge to `main`.** The code is integrated and trusted. Nobody is running it yet. Gated by the fast suite and the review of Level 2.

**Boundary 2: a release tag.** A signed, packaged installer a person installs on their laptop. For a desktop product, this is the real production boundary. Gated by the full suite, the metric gates, the persona acceptance tests and a clean-VM install.

`main` being green does not mean shippable. Shippable is a tag.

---

## 4. The promotion ladder

Six levels. Each states what is checked and, critically, **who or what enforces it.** "Enforced by" is the column that matters: anything enforced by the agent is not enforced.

### Level 0: pre-commit, on the agent's machine

| Check | Enforced by |
|---|---|
| ruff, mypy on changed files | git hook |
| secret scan | git hook |
| no-network AST scan | git hook |
| docstring presence | git hook |

**Honest limitation:** a hook can be bypassed with `--no-verify`, and the agent could do that. Level 0 exists for speed, not for safety. Every check here is repeated at Level 1, where it cannot be bypassed. Nothing relies on Level 0 alone.

### Level 1: push, fast CI

Required status checks on the PR. Under five minutes. **Enforced by GitHub Actions, which the agent cannot edit the output of.**

| Check | What it catches |
|---|---|
| ruff, mypy | style, types |
| T0 contract, including the layering test | architecture violations, with `file:line` |
| T1 unit | per-function behavior |
| T2 property, reduced example count | invariant violations |
| T3 golden | unintended output changes |
| T8 privacy: network, eval isolation, log canary, temp canary | leak paths |
| Per-PR recall check, from Phase 3 (section 11) | a name that was found before and is now missed |
| Secret scan | credentials |
| Docstring presence, a `Why:` section, and a `Contract:` section on public functions | undocumented public surface |
| Ratchet checks (section 6) | weakened tests or fixtures |
| PR-body structure check (section 5.2) | missing evidence sections |
| Size limits | oversized PRs |
| Skip-marker check | `skip` or `xfail` without an issue link |
| Pinned-dependency check | unpinned or unjustified dependency changes |
| Model manifest check | a model in `models/` absent from `THIRD_PARTY.md` |
| Protected-path co-change check | code and baselines changed in the same PR |

A PR cannot merge with any of these red. Branch protection enforces that, not discipline.

**On the current plan it does not.** See section 11: GitHub Free does not enforce branch protection on a private repository, so today these checks run and report but do not block a merge. Read every "cannot merge" and "enforced by branch protection" claim in this document against that section.

### Level 2: review

What a machine cannot judge. Read in this order, and stop early if an earlier item fails.

1. **Gate evidence.** Is the pasted output real, and does the SHA in the results file match the commit? CI checks the SHA; you check that the number answers the question.
2. **Ponytail section.** Is every finding resolved, and is every rejection backed by an ADR that actually applies?
3. **The test matrix block.** Are the equivalence classes the right ones, and are the applicable Hebrew and structural axes present? A machine counts cases; only you can tell whether the right cases were chosen.
4. **Docstring quality.** Does `Why:` state a real reason, or does it restate the function name?
5. **The implementation.** Last. If the tests did not convince you, send it back without reading it.

**Who reads.** The independent reviewer of the Ponytail rule does these five readings for every PR, and its report says what it found for each. A reading that does not apply to the PR (no code, no tests) is reported as "does not apply", with the reason. A reading that applies and could not be done is a finding. This follows from Achia's decision of 2026-11-15 that Claude merges; until then this level said Achia reads every PR. Until Achia's message of 2026-11-15 that section 11 quotes, it also said that Achia does them for his own PRs. For a PR that needs a decision of Achia's (`CLAUDE.md`, "Merging"), the reviewer also finds that decision at its source, the chat transcript or the cited line, and reports whether the PR does more than it says. Where the list above says "you", read "the reader". By the first lines of this section, anything enforced by the agent is not enforced: Level 2 is discipline, not a check. The author writes the reviewer's brief, so every review run on the commit is pasted with its brief (`CLAUDE.md`, "Merging").

### Level 3: merge to `main`

Squash merge, linear history, branch deleted. Requires Levels 1 and 2. Who runs the merge command, and on what, is in `CLAUDE.md`, "Merging".

A decision of Achia's is additionally required (`CLAUDE.md`, "Merging": his decision on the thing, not a yes to the merge) if the PR touches a path of this list, the Level 3 list: `ploni/api.py`, `eval/baselines.json`, `config.py` gate values, any CI workflow, `docs/adr/APPROVED_ABSTRACTIONS.md`, `docs/WAIVERS.md`, `CLAUDE.md`, `build-plan.md`, `PROCESS.md`, `PROMOTION.md`, `ploni/i18n/claims/`, and, added 2026-11-15: the rest of `docs/adr/`, `docs/findings/README.md`, `.ratchet.json` when a counter falls or is removed, `pyproject.toml` and any other pytest, ruff or mypy configuration file, `.claude/settings.json`, `.claude/settings.local.json` and any other hook or hook configuration, any checker script or `make` target that a workflow step or a hook calls (test files are covered by kind, not by this), `.claude/skills/`, `.github/CODEOWNERS` and `.github/pull_request_template.md`. `CLAUDE.md`, "Merging", adds the PRs that need a decision of Achia's by what they do and not by path. `.github/CODEOWNERS` carries the paths of this list that a file pattern can name; GitHub does not enforce it on this plan (section 11).

### Level 4: phase close

Not every PR. Once per milestone.

| Check | Enforced by |
|---|---|
| Full suite: T4 integration, T5 system journeys, T6 metrics, T7 performance. For now T7 fails on no slow time; it still fails on peak memory over its limit and on a time below the low end (`PROCESS.md` section 10) | CI, `run-full` label |
| Metric gates at or above baseline | CI comparing the committed results file to `baselines.json` |
| Results file SHA matches the phase-close commit | CI |
| Ponytail pass over the whole module, findings triaged | you, from the pasted output |
| Mutation testing over the whole of `ploni/`, survivors triaged | you, from the pasted output |
| Carried debt reviewed, each item with a reason and an issue | you |
| Exit demo shown | you, watching it |
| `docs/STATUS.md` phase row appended | CI checks the Phases table gained a row |
| New ADRs merged | you |

### Level 5: release

| Check | Enforced by |
|---|---|
| Everything at Level 4, on a release branch cut from `main` | CI |
| Persona acceptance P1 to P5, including the ten-minute demo | you, by hand |
| Offline journey S13 with networking disabled at the OS level | you, by hand |
| Installer builds, installs and uninstalls on a clean Windows 11 VM | you, by hand |
| Performance budget met on the reference machine. The time rows are not enforced for now: speed is measured and reported (`PROCESS.md` section 10). Peak memory stays a limit. Before a release Achia decides whether time becomes a gate | CI plus the committed results file |
| `THIRD_PARTY.md` complete and verified | CI manifest check plus your read |
| Tag created, artifact hashes published | you |

---

## 5. How each rule is actually enforced

Every rule in `CLAUDE.md` falls into one of three classes. Knowing which class a rule is in tells you how much to trust it. The rules added on 2026-11-12 (the branch limit, the hard function limit, the test commit of its own, mutation testing, the independent Ponytail reviewer and the status sections) are Class C until the checks in item 8 of `PROCESS.md` section 12 are built.

### 5.1 Class A: machine-enforced, cannot be bypassed silently

| Rule | Mechanism |
|---|---|
| No networking imports under `ploni/` | AST test in the fast suite |
| `ploni/` never imports `eval/` | AST test |
| Layering boundaries | AST test, fails with `file:line` |
| No document text in logs or temp files | canary test through the full pipeline |
| Docstring present with a `Why:` section, and a `Contract:` section on public functions | AST test |
| No secrets committed | secret scan |
| Every dependency pinned | requirements parse test |
| Every model in `models/` listed in `THIRD_PARTY.md` | manifest test |
| No direct push to `main` | branch protection |
| Protected paths need approval | CODEOWNERS plus branch protection |
| Baselines not changed in a code PR | changed-paths test |
| PR size limits | changed-files and diff-size test |
| Baseline regression | CI compares the results file to `baselines.json` |
| Test and fixture counts never decrease | the ratchet, section 6 |
| `skip` or `xfail` without an issue link | marker scan |
| CI workflows not edited by a code PR | changed-paths test plus CODEOWNERS |

### 5.2 Class B: mechanically detectable, caught after the fact

These cannot be blocked up front but cannot be hidden either.

| Rule | How it is detected |
|---|---|
| **Test written before implementation** | CI inspects commit order within the PR: the first commit touching `tests/.../test_X.py` must precede the first commit touching the module `X` implements. Squash merge preserves the branch's commit list for this check. The failing tests are a commit of their own, with no implementation in it. This covers every PR that changes code under `ploni/`, `eval/` or `scripts/`. |
| Declared sample size matches reality | CI parses the test-matrix block at the top of the test file and counts the test functions, then compares to the declared minimum for that kind of code |
| Ponytail actually run | CI asserts the `## Ponytail review` section exists and is non-empty. Substance is Level 2. |
| Orientation step performed | CI asserts the PR body contains the goal, deliverable, gate and downstream-risk lines |
| Metric number not fabricated | the results file carries the code SHA, the model bundle version and the name bank version; CI asserts the SHA equals `HEAD`. A number with no matching results file fails. |

### 5.3 Class C: human judgment only

No mechanism exists and pretending otherwise is worse than admitting it.

- Whether a `Why:` docstring states a real reason.
- Whether the chosen equivalence classes cover the actual input space.
- Whether a Ponytail rejection is legitimate or convenient.
- Whether the implementation is correct.
- Whether an exit demo actually demonstrated the thing.
- Whether web code follows the Modern Web Guidance guides, and whether the right guides were found (the Web code rules of `CLAUDE.md`, added 2026-11-15). No machine checks any of them yet.

These are the six jobs of the reader at Level 2, and yours at Level 4. Level 2 says who reads: the independent reviewer, which is not a human. Everything in Class A exists so that your attention is available for Class C instead of being spent on things a machine should have caught.

---

## 6. The ratchet

The general defense against quiet erosion. A set of counters that may only increase. CI stores the current values in `.ratchet.json` on `main` and compares on every PR.

| Counter | Rule |
|---|---|
| Test functions per test file | may not decrease |
| Assertions per test file | may not decrease |
| Fixture cases per fixture file | may not decrease |
| `eval/baselines.json` metric values | may not decrease |
| Number of registered detectors | may not decrease |
| Number of system journeys | may not decrease |

A decrease fails the build with the exact counter and the delta. To decrease one legitimately, for instance after merging two redundant tests, the PR body carries a line:

```
ratchet-override: tests/t1_unit/test_phone_il.py  -3  merged duplicate separator cases into a parametrized case
```

CI accepts the override only when the line is present and the PR touches no file under `ploni/`. So loosening a test and changing code in the same breath is impossible.

**Why a ratchet rather than a coverage target:** a coverage percentage can be gamed by adding trivial tests. A ratchet on real counters cannot be gamed in the direction that matters, which is downward.

---

## 7. Evidence that cannot be fabricated

The weakest point in any agent workflow is a number in a message. Three mechanisms close it.

**The results file.** `eval/run_eval.py` writes `eval/results/<git-sha>.json` containing the metrics plus the code SHA, model bundle version and name bank version. CI asserts a results file exists whose SHA equals `HEAD` whenever a protected path changed. A fabricated metric would require forging a file named after a commit that does not exist.

**CI is the source of truth for anything CI can run.** The pasted output in a PR body is a convenience for your reading, not the gate. The gate is the green check from GitHub. When the two disagree, CI is right.

**Staleness is a failure, not a silence.** If `ploni/` changed and no results file exists for the new SHA, the build fails. An out-of-date measurement cannot pass as a current one.

---

## 8. The exception protocol

You asked for a hard guarantee: the agent may never grant itself an exception. This is how.

### 8.1 The agent has no authority to waive anything

Stated in `CLAUDE.md`, and backed by the fact that the mechanisms in Class A do not have an agent-accessible override. There is no flag, no comment directive, no environment variable that turns a gate off.

### 8.2 Requesting an exception

When the agent believes a rule should not apply, or a gate cannot be met, the **only** permitted action is to stop and open a waiver request. It is a PR that touches exactly one new file, `docs/findings/<YYYY-MM-DD>-<slug>.md`, and nothing else:

```markdown
# Waiver request: <one line>

## Rule or gate in question
## Why the work cannot proceed under it
## What was measured
(raw output, pasted; with the results file SHA if there is one)
## Prediction and threshold, as stated before the run
## Options, with the cost of each
## Recommendation
## Scope requested
Which rule, for which files, until when (a phase number or a date).
## Decision
(left blank; Achia fills this in)
```

Then it reports and stops. No implementation continues on that path. No partial workaround. No "proceeding with the simpler approach in the meantime".

### 8.3 Granting an exception

Only you, and only by doing both:

1. Filling in `## Decision` in the findings note.
2. Adding an entry to `docs/WAIVERS.md`, which is CODEOWNERS-protected:

```
WAIVER-003
rule: test-first commit order
scope: tests/t2_property/test_projection.py
reason: hypothesis strategy had to exist before the invariant could be stated
granted: 2026-11-14
expires: end of Phase 3
issue: #41
```

### 8.4 Using an exception

A PR relying on a waiver carries `waiver: WAIVER-003` in its body. CI asserts that the ID exists in `docs/WAIVERS.md`, that it has not expired, and that the PR's changed paths fall inside the waiver's scope. An invented or expired ID fails the build.

### 8.5 Waivers expire

Every waiver has an expiry. A CI job fails the build when an expired waiver is still referenced, and `docs/STATUS.md` lists open waivers at every phase close. Waivers do not accumulate quietly into a second, softer rulebook.

---

## 9. The failure modes this is built against

Written out explicitly, because naming them is what makes the countermeasures checkable.

| What an agent might do to make progress | What stops it |
|---|---|
| Mark a failing test `skip` or `xfail` | marker scan requires an issue link; ratchet catches the lost assertion |
| Delete an assertion or a test case | ratchet, with the exact delta reported |
| Narrow a fixture so the code passes | fixture-count ratchet |
| Lower a baseline | CODEOWNERS plus the co-change check plus the ratchet |
| Loosen a threshold in config | gate values live in a protected file |
| Paste a number it did not measure | results file must carry a SHA matching `HEAD` |
| Report a locally green suite that is not green | CI is the required check, not the message |
| Write tests after the implementation | commit-order check |
| Grow the PR to carry an unrelated change through | size limits plus one-concern review |
| Skip Ponytail | PR-body section check |
| Reject a Ponytail finding without justification | CI requires an ADR reference; you check that it applies |
| Add a dependency quietly | pinned-dependency check plus a justification line |
| Ship a model that is not licensed for this | manifest check against `THIRD_PARTY.md` |
| Edit a CI workflow to make a check pass | workflows are CODEOWNERS-protected and cannot change in a code PR |
| Bypass the pre-commit hook | every Level 0 check is repeated at Level 1 |
| Push straight to `main` | branch protection |
| Claim a rule does not apply here | no agent-accessible waiver mechanism exists; section 8 is the only path |

### What is still not guaranteed, stated plainly

The agent can still write a `Why:` docstring that is technically present and substantively empty. It can choose equivalence classes that miss the real input space. It can write a test that asserts the wrong thing and passes. It can reject a Ponytail finding with an ADR that does not really apply.

None of those is mechanically detectable. They are exactly what Level 2 is for, and they are the reason PRs are capped at fifteen minutes of reading. The size limits are not bureaucracy; they are what makes the only unmechanizable check in the system actually happen.

---

## 10. Phase 0 setup checklist for all of this

In this order. Nothing in Class A exists until it is built, so build it before the code it protects.

1. Private repo. Branch protection on `main`: no direct push, PR required, required status checks, squash merge only, linear history, delete branch on merge.
2. `CODEOWNERS` covering every protected path in Level 3.
3. `CLAUDE.md`, including the statement that the agent has no waiver authority.
4. `build-plan.md`, `PROCESS.md`, `PROMOTION.md` committed.
5. Fast CI workflow with every Class A check wired up.
6. Full CI workflow behind the `run-full` label.
7. Pre-commit hooks, and the further checks listed under item 8 of `PROCESS.md` section 12.
8. `.ratchet.json`, `docs/WAIVERS.md` (empty), `docs/STATUS.md`, `docs/findings/` (empty), `docs/adr/` with ADR-0001 onward and `APPROVED_ABSTRACTIONS.md`.
9. `eval/baselines.json` skeleton, `eval/results/` (empty).
10. PR template containing every required section, so the structure check has something to match.
11. The five skills saved.
12. Milestones for all fourteen phases. Issues for Phase 0 and Phase 1.

The merge gate of section 11 is built first, with the first version of the fast CI workflow of item 5. Until it works, as section 11 says what "works" means, what may merge is in `CLAUDE.md`, "Merging". Until Achia's message of 2026-11-15 that section 11 quotes, this line said that every merge waits for Achia's yes.

### The closing test for Phase 0

**Phase 0 is not closed until eight deliberately bad PRs are each rejected by CI.** Prove the guardrails before trusting them, because a guardrail you never tested is a guardrail you are only assuming:

1. `import requests` under `ploni/`
2. `detect/` importing `write/`
3. A public function with no docstring
4. A public function whose docstring has no `Why:` section
5. A log line containing a canary string
6. A test file with one test function deleted, with no `ratchet-override` line
7. A code change and a `baselines.json` change in the same PR
8. A PR body citing `waiver: WAIVER-999`, which does not exist

For each of the eight, once CI is red, the plain `gh pr merge` is tried and the refusal of the merge gate (section 11) is recorded in that PR. CI going red is not the gate refusing, and a gate that never fired is only assumed. The gate is also tried once on a PR with no check, once while a check is still running, and from each shell tool the session has. The bad PRs target a scratch branch cut from `main`, not `main`, so a gate that fails puts nothing on `main`. The fast workflow runs on a PR to any base branch, and the gate does not look at the base. The number stays eight.

If any of those eight merges, the enforcement layer is decoration and the number eight is the only honest way to find out.

---

## 11. Enforcement status on the current plan

Recorded 2026-11-11. This section overrides any stronger claim made above, and it is the first thing to re-read when deciding whether a rule is real.

### What the repo actually is

`ploni-dev/ploni-engine`, private, on GitHub Free. The decision not to pay is deliberate: GitHub Team is $4 per user per month, and the enforcement it buys is not worth paying for until there is code to protect. Making the repo public would restore every protection for free and is rejected for a different reason: the repo carries the build plan, the competitor analysis and the pricing model, and publishing those to save $4 a month is a bad trade.

### What this costs, exactly

On a private repository, GitHub Free does not enforce branch protection or rulesets, and does not support CODEOWNERS review. So:

- A red required check does **not** block a merge. It reports.
- Nothing stops a direct push to `main`.
- CODEOWNERS on `api.py`, `baselines.json` or the plan files requests nothing and blocks nothing.
- Squash-only and linear history are repo settings and still apply.
- GitHub Actions still runs on private repos within the free monthly minutes, so every Class A check still **runs** and still goes red.

The distinction that matters: the checks are not gone, the **blocking** is gone. A violation is still visible in the PR; it is just no longer impossible to merge past it.

### What this does to section 5

Section 5.1 sorts rules into Class A, machine-enforced and not silently bypassable. On the current plan, every row in that table degrades from "cannot be bypassed" to "cannot be bypassed without it being visible in the PR". That is a real downgrade and it is not a small one: the entire argument of section 1 is that the gate should not depend on anyone's discipline, and today it does.

Class B and Class C are unaffected. They were never blocking.

### What compensates, and what does not

Compensating, honestly:

- Every check still runs in CI and is visible before merge.
- One developer. The failure mode that branch protection exists to stop, someone merging past a red check, has one possible actor here: the agent, which runs the merge command. Until 2026-11-15 this line said it has no one to perform it.
- The agent merges only as `CLAUDE.md`, "Merging", says. It does not ask Achia to approve a merge ("Achia's decision cannot be checked on GitHub", below). Until 2026-11-15 this line said that the agent has no authority to merge, and that merging is a human act, performed by Achia after reading the PR. That is not what happened. From 2026-11-12 the agent ran the merge command under Achia's account. The merge commits of #5 to #11 say "Merged on Achia's instruction in the working session of 2026-11-12"; the merge commits of #12 to #15 say "Merged by Claude". Both are the agent's own record, and the repository shows no Level 2 reading by Achia before them. An agent that pushes to `main` directly is violating `CLAUDE.md`, and that violation shows in the commit history with no PR attached.
- `git log --first-parent main` shows any commit that arrived without a PR. Check it at every phase close.

Not compensating, and worth saying plainly: none of the above is a mechanism. All of it is discipline, which is exactly what section 1 said not to rely on. This section exists so that nobody reads section 4 in six months and believes the gate held when it was only ever requested.

### The merge gate, decided 2026-11-15

Achia asked for tests that a PR has to pass in order to merge, and chose the free form of it: a local merge gate, not the paid plan. His words are in the body of the commit that added this section.

- **What it is.** A Claude Code hook, committed in `.claude/settings.json`, that refuses the agent's plain `gh pr merge` unless every check on the PR's last commit has finished and is green, and the fast-suite check is one of them. A missing check, one still running, or one that GitHub marks skipped counts as red. It is the first thing built in Phase 0, with the first version of the fast CI workflow it reads.
- **What it does not do.** It matches one command. It does not stop an agent that goes around it: another merge command, a call to the GitHub API, a local merge pushed to `main`, a check status set by hand, a session started in another folder, an edit of the hook made some other way than the plain edit that a second hook refuses (`PROCESS.md` section 12 item 8). `CLAUDE.md` forbids each of these, and that part is discipline, not mechanism. Two ways need no bad intent, and the test of section 10 looks for the second: a session on a branch cut before the gate was merged does not have the hook file, and the same command typed in another shell tool may not be matched. It is also not branch protection: a merge by hand in the browser, or from a machine without the hook, is not stopped. `git log --first-parent main` at every phase close still shows what arrived and how.
- **Until it works, it does not exist.** "Works" means three things: it is built, it has refused a red PR, and the fast suite holds the network test, the two canaries and the layering test. Without the third, "the check is green" would be true with almost nothing behind it. The third is Claude's reading of Achia's words "especially to test the main ideas". He was told that the time until the gate is built lasts "only for the first step of Phase 0"; with the third it lasts longer. Until the gate works, "What compensates, and what does not" above stays the whole truth, only `.md`-only PRs and the Phase 0 PRs of seven named issues merge (`CLAUDE.md`, "Merging"), and what stands between a change and `main` is the independent review and, from the PR that adds the fast workflow on, its checks. The code merges in a fixed order, and what each PR may hold is this list, which wins over the text of the issue. First #17 (`pyproject.toml` with the ruff and mypy configuration, the pinned requirements files with hashes, `make check`) and #22 (the fast workflow; the full workflow and the pre-commit configuration may come with it); the first of the two to merge carries the fast workflow. Then #69 (the merge gate hook in `.claude/settings.json`, with its test), which must then refuse a red PR. Then #18 (`tests/t0_contract/test_layering.py`) and #19 (the two T8 tests: no networking import under `ploni/`, and nothing under `ploni/` imports `eval/`). Then #24 (`ploni/safety/logging.py` with the log canary test). Then #25 (`ploni/safety/tempfiles.py` with the temp-file canary test). No file under `ploni/` other than those two modules and the empty `__init__.py` files that a test needs in order to import them. So no product code merges before the gate is built and has refused a red PR. `ploni/safety/logging.py` merges on a suite that holds the layering test, the two tests of #19 and its own canary; `ploni/safety/tempfiles.py` on a suite that holds all four. They are the first product code, and trigger 1 of "When to revisit" still stands when they merge. As Claude reads Achia's choice of the local gate and not the paid plan (2026-11-15), no upgrade is made for them. That gap is real and is said here. Achia's yes to each merge stood there too, until his message of 2026-11-15 (next point). The first refusal is tried right after the gate is built, on a red PR that targets a scratch branch, as in section 10; the closing test of Phase 0 tries it again.
- **Achia's decision cannot be checked on GitHub.** On 2026-11-15 Achia was asked who merges until the merge gate is built. He was offered "You say yes to each merge" and "I merge on an independent review plus a test run on this laptop", and chose the first. For his own PRs he chose to say "merge #N" in chat. Later the same day, at the question about #72, he wrote: "Don't ask me if to merge something or not each step, alright? I am not following. Just do what you need to do, and remember, everything you merge has to go through all the gating we defined. If it's not, there is a problem." That takes back his choice of the first. So the agent does not ask him whether to merge. It merges what passes the gating of `CLAUDE.md`, "Merging", and nothing else. Eight things in that gating are not in his message and are Claude's: that his decision on the thing itself (a threshold, a waiver, a rule, a dependency, a findings decision) is still asked, in plain words, and quoted in the PR; that what he already decided needs no new question, where under the rule of #67 such a PR still got one (#68); that a choice of Claude's that only narrows what Claude may do may stay in a PR unasked, listed there and checked by the reviewer; that until the gate works only `.md`-only PRs and the Phase 0 PRs of seven named issues merge, the code in a fixed order; that this lets a `.md`-only PR merge with no check at all while no workflow is on `main`, and some Phase 0 code merge before the gate works; that no upgrade to the paid plan is made for the two safety modules that merge before the gate works, as Claude reads his choice of the local gate; that the reviewer checks the quoted decision at its source; and that Achia is told in chat when the gate works. His message answered the question about #72, a `.md`-only PR with a clean review and no check, so that kind is carried by its context. Claude told him the main points in chat that evening, after this text was first written: no merge questions, what merges before the gate works, that his decisions stay his, and that nothing of Claude's rides along. Those messages did not name the reading on the paid plan, nor that the two safety modules are product code, and they said "Nothing of mine rides along" where a choice that only narrows Claude may stay. He had not replied when this text was written. "A later commit voids the yes" is gone with the yes. In its place: a commit that changes the diff needs the review again (`CLAUDE.md`, Ponytail), and a PR does no more than the decision it quotes. A `## Decision` in a findings note holds his words, quoted from the chat: Claude writes them in, as it did for E2 and E3, and the reviewer checks them at their source. Section 8, `docs/findings/README.md` and the note template still say "Achia fills this in"; outside a waiver that now means his words, written in by Claude. For a waiver both steps of section 8 stay his own acts, and Claude never edits `docs/WAIVERS.md`. The agent writes the PR text and works under Achia's account, so nothing on GitHub tells his decision from the agent's quote of it, and whether a PR needs a decision of Achia's is the agent's own call. Both are discipline, not mechanism, and this is weaker than his yes to each merge was: he no longer sees a PR before it merges. Achia can read any merge afterwards and revert it; `git log --first-parent main` shows each one.
- **What the gate tests on every PR.** The fast suite of Level 1. Of the project's main ideas it carries three: no network access from product code (T8), no document text in logs or temp files (T8, the log and temp canaries), and the layering (T0). The fourth, that no name gets through, is measured in full by T6, which the plan runs at a phase boundary (`build-plan.md` section 7).
- **The per-PR recall check, decided 2026-11-15.** Achia decided that a small form of the fourth idea also runs on every PR: a fixed set of invented documents with known names, and the PR fails if a name that was found before is now missed. It is a row of Level 1.
  - Achia was told "Phase 2 or so". Phase 3 is Claude's reading of the plan: it builds the first model that finds names (`build-plan.md`, Phase 3). The trigger words of Phase 1 find some names earlier, and T1 tests them. Until Phase 3 the gate does not test this idea.
  - T3 golden already turns red when the detection output on a fixture changes, and the author may update a golden file in the same PR with an explanation. This check differs in one thing: its list of names found is a baseline, so a change to it needs a decision of Achia's and never shares a PR with code.
  - It guards against getting worse on a fixed set. It does not measure recall: T6 stays the measure.
  - It needs the model on the CI runner, and `PROCESS.md` section 5.4 found that slow and brittle for the metric gates. If it does not work there, the check runs locally with a committed results file that the gate reads, as section 5.4 does for metrics, and this section is changed to say so. A check that the gate cannot see is not this check. Its run time is measured when it is built.

### When to revisit

Upgrade to Team, one seat, at the first of these:

1. The first PR that contains real product code rather than scaffolding, because that is the first merge where a red check actually means something. On 2026-11-15 Achia chose the local merge gate and not the paid plan. As Claude reads it, that answers this trigger once the gate works, as this section says. Until then the trigger stands. Two modules of product code merge before then, and as Claude reads his choice no upgrade is made for them ("Until it works, it does not exist", above).
2. Tomer, or anyone else, getting write access.
3. The first time a red check is merged past, whatever the reason. If it happens once it will happen again, and at that point $4 is cheap.

Until then, this section is the truthful answer to "is this rule enforced", and the answer for every Class A row is: it runs, it reports, it does not block. Once the merge gate works, the answer for the fast suite becomes: it blocks the agent's plain merge command, and nothing else.
