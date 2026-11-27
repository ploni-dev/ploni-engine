# Overview

A short guide to this project for a reader who does not write code. Each fact names where it comes from; that source is the one that counts. Written on 2026-11-27, with `main` at `b2a255e`.

## What Ploni is for

Ploni (פלוני) is the working name; the public name is chosen before launch (`build-plan.md`, opening lines).

It is to be an offline Windows desktop program that lets a professional use cloud AI tools, such as ChatGPT or Claude, on a sensitive document (`build-plan.md` section 1). It has three jobs:

- **Pseudonymize.** Find what identifies people in a document, replace each with a consistent, realistic stand-in, and write out the same format.
- **Show the user what happened, and make them act on it.** Before export the user reviews every entity, its replacement and everything uncertain. Export stays blocked until every open item is resolved. Each file gets a report.
- **Restore.** Turn the safe document back into the original, and turn the AI's answer about the stand-ins back into real names, Hebrew forms included.

Hebrew comes first, with mixed Hebrew and English. The first user is an Israeli lawyer, accountant or clinician working in Word. Not in version 1: any promise of anonymity, reading text inside images, layout-exact PDF output, any cloud part, telemetry or licensing (`build-plan.md` section 1).

The engine comes first. Phases 1 to 10 build a library and a command line; no screen is built before Phase 12 (`build-plan.md` section 0, rule 1).

## How the work is done and checked

Claude writes the code, phase by phase; Achia decides (`build-plan.md`, opening lines; `CLAUDE.md`, "Who decides"). Each phase has a gate with numbers, and a phase is not done until its gate passes (`build-plan.md` section 0, rule 2). A test, a threshold or a baseline is never weakened to pass a gate: if a gate cannot be met, the work stops and a findings note says what was measured (`CLAUDE.md`, "How work is gated").

**Tests first.** For every change of code, a test that fails is written first and committed on its own, with its failing output in the commit message; the code follows in a later commit. On every PR a check reads the order of the commits, for code under `ploni/`, `eval/` and `scripts/`, and turns red when the code came first; it checks the order only, not what the test asks (`CLAUDE.md`, "Tests"; `scripts/check_commit_order.py`). Each detector needs at least 40 examples it must find and 40 it must leave alone (`CLAUDE.md`, "Tests").

**An independent review.** Before every merge, a separate session or helper that did not write the change reviews it, using the Ponytail review skill at its strictest level. Its report names the commit it read. Every finding is accepted, or rejected only by naming one of the approved designs of `docs/adr/APPROVED_ABSTRACTIONS.md`, and only with Achia's decision. Every review is pasted into the PR with the instructions its reviewer got, word for word. A later commit that changes what the branch adds or removes makes the review stale, and it is run again (`CLAUDE.md`, "Ponytail" and "Merging"; `scripts/check_reviewed_commit.py` checks the named commit).

**The merge gate.** Claude merges only through the gate. A guard program runs before each command and file edit of Claude's, and refuses Claude's merge command unless every check on the PR's last commit has finished green and the four required checks (fast-pin, fast-suite, nightly, pr-checks) are among them (`scripts/guard.py`, `REQUIRED_CHECKS`; `docs/STATUS.md`, Done). Going around it, by another command or a call to GitHub, is forbidden by the rules, not stopped by a machine (`CLAUDE.md`, "Merging"; `PROMOTION.md` section 11). Merges are squash merges only. A PR that touches one of the protected files, changes a limit, weakens a test or adds a dependency merges only after Achia decided what it changes: "No answer, no merge" (`CLAUDE.md`, "Merging"; `PROMOTION.md`, Level 3).

**The held-out batch and the score guard.** Achia asked for a batch of documents that the program never learns from, to show on every change whether it got better or worse (`build-plan.md` section 7, "The held-out batch"). Its invented part is 184 documents with 1,100 items to find and 1,100 near misses, made in memory from a fixed seed on each run, so no document is stored. It was written by a separate helper that never read the detector side, and the detectors follow its written rules (`docs/STATUS.md`, the paragraph of 2026-11-26 in Israel; `eval/heldout/SPAN_RULES.md`). On every PR, GitHub scores both `main` and the PR on it, and any drop of any number turns the check red, unless Achia accepted that drop for a reason the PR quotes (`PROMOTION.md` section 11). Its real part, real public documents, is to be measured on the laptop and to stay outside the repository; where it comes from is still open (`build-plan.md` section 7; `docs/STATUS.md`, Waiting on Achia, point 7).

**Mutation testing.** A passing test can still check nothing. Before a PR that changes product code, a tool makes small deliberate errors in the code; an error the tests do not notice is a "survivor". The survivors are pasted into the PR, and each is answered with a new test or judged harmless (`PROCESS.md` section 4; `CLAUDE.md`, "Tests"). The tool is Cosmic Ray 8.9.0, run on the laptop (`docs/THIRD_PARTY.md`).

**Privacy rules.** The product has no network code: a test and the linter refuse it (`CLAUDE.md`, "Hard constraints"). Document text never goes into a log or a temporary file; all of that goes through the helpers in `ploni/safety/`, and tests push marked strings through them to check (`CLAUDE.md`, "Hard constraints"; `docs/STATUS.md`, Done). No real client document is in the repository, and every file of test documents has a row saying where it came from (`CLAUDE.md`; `tests/fixtures/MANIFEST.md`). The made-up ID numbers that tests use are made when the tests run and never stored, by his choice of 2026-11-27 (`tests/invented_numbers.py`), and on GitHub a failing test does not print the values it tested (`tests/conftest.py`). The repository is public until 1 December 2026, by his choice, and is switched back to private then (`docs/STATUS.md`, In flight).

**Measured, not guessed.** Before a measurement its expected result is written down, and every claim needs a measured number or a file and line (`CLAUDE.md`, "Measurement discipline").

## What is built so far

- **Phase 0, foundation and safety: closed on 2026-11-25.** The program installs and runs `ploni selftest`, which lists the models on the laptop and prints "offline OK"; the safety helpers, the tests and checks above, and the merge gate (`docs/STATUS.md`, Phases table and Done).
- **Phase 1, the detectors of structured numbers: under way.** So far: four of the five carried safety fixes, the invented part of the held-out batch, the shared shape every detector follows, and the score guard (`docs/STATUS.md`, Done); the rule for keyed ids in the plan (PR #298); and the first detector, Israeli ID numbers. On its own test examples it finds 100 percent and is right 100 percent, where the gate asks 98; on the invented part of the held-out batch it finds 98.0 percent and is right 96.1 percent (PRs #301 and #303).

## What comes next

The phases of `build-plan.md`, Part IV, each with its gate:

- **Phase 1** (the rest): company and non-profit numbers, bank accounts, credit cards, phones, emails, web and IP addresses, car plates, court case numbers, land plots, dates, amounts, addresses, title and role words before names, names already hidden in the source, and health fund, military and passport numbers.
- **Phase 2:** read and write real Word files exactly, and back again.
- **Phase 3:** find names, places and organizations in real Hebrew, with its prefixes and word forms.
- **Phase 4:** English and mixed-language text, custom kinds of items, and one list of findings with no overlaps.
- **Phase 5:** the measuring tool, built before the things it measures.
- **Phase 6:** findings across the document become a small set of people and things.
- **Phase 7:** stand-ins that keep the document meaningful, and rules for numbers.
- **Phase 8:** the interface the screens will drive, with the review gate enforced in code.
- **Phase 9:** the safe output file, with nothing left behind.
- **Phase 10:** the way back: restore, rehydrate the AI's answer, and verify.
- **Phase 11:** the per-file report and the usage log.
- **Phase 12:** the application itself, usable without a manual.
- **Phase 13:** fast enough, installable, and shown to work offline.

Beside the phases: experiments aiming at 100 percent of names found, which Achia asked for ("remember we need accuracy of 100%"), running two models together with three new ones on new Supreme Court documents (`docs/STATUS.md`, Waiting on Achia, point 1).

## Where each kind of document lives

- `build-plan.md`: what to build. The product, the design, the tests, and the 14 phases with their gates.
- `CLAUDE.md`: the rules Claude reads at every turn; under a rule that a check enforces, a line names the check.
- `PROCESS.md`: how the work is done, reviewed and gated.
- `PROMOTION.md`: how code reaches `main`, which files are protected, and how each rule is enforced.
- `docs/STATUS.md`: where things stand: Done, In flight, Waiting on Achia, the phase table, and a dated paragraph for each working day.
- `docs/DEBT.md`: shortcuts and findings carried on purpose, each with its reason, its issue and the phase that fixes it.
- `docs/findings/`: a note for each experiment, for a measurement that missed its prediction, or for a gate that cannot be met; each ends with a Decision section that is Achia's.
- `docs/adr/`: the records of the main design decisions, and the list of approved designs a review may not remove.
- `docs/THIRD_PARTY.md`: every model, package and tool used, with its source, version and licence.
- `eval/heldout/SPAN_RULES.md`: exactly what each detector must mark in the held-out batch, written by the batch's writer.
