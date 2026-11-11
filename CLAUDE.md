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

## Function design
- One function, one reason to change. If its name or its docstring's first line needs
  "and", it is two functions.
- A function does not both decide and act.
- Body over 40 lines or complexity over 8 needs a justification in the PR body or a split.

## Docstrings
- Every module, class and public function has one.
- It answers: What (one line, no "and"), Why it exists, Contract (args, returns,
  raises, units and coordinate systems), Known limits.
- A docstring that restates the function name is a blocking review comment.
- Body comments explain why, never what. Rename instead of explaining.
- Every magic number is a named constant or carries its source.
- Where a value comes from the plan, cite it: # build-plan.md Phase 3: stride 128

## Tests
- Write the failing test first. Show it failing.
- Every public function and every private function with real logic gets its own test.
- Every module gets a suite in tests/t4_integration/ over its public surface.
- Enumerate equivalence classes, boundaries, Hebrew axes and adversarial cases in the
  test file before implementing. See the test-matrix skill.
- Minimum samples: detectors 40 positive and 40 negative; invariants 500 generated
  cases, 5,000 at phase close.
- Coverage is a diagnostic, never a target.

## Ponytail
- Ponytail is used here as a skill. Invoke it at the start of any session that writes
  code, before writing any, so its rules are in context while the code is written.
- Invoke it again on the diff before every PR. Paste the output into the PR body.
- Every finding accepted, or rejected with an ADR number from
  docs/adr/APPROVED_ABSTRACTIONS.md.
- Ponytail never removes error handling, validation, safety/, a test, a fixture, or a
  registered abstraction. Those findings are rejected on sight.

## How work is gated
- Read the relevant build-plan.md phase section first. Restate goal, deliverable, gate.
- Never weaken a test, threshold or baseline to pass a gate. If a gate cannot be met,
  stop and write docs/findings/<date>-<slug>.md, then report.
- Code changes and baseline or gate changes never share a PR.

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

## Exceptions (PROMOTION.md section 8)
- You have no authority to waive any rule, test, threshold or gate. No flag, comment or
  environment variable turns a gate off.
- If a rule should not apply or a gate cannot be met, the only permitted action is a
  waiver request: a PR touching exactly one new file in docs/findings/, with an empty
  ## Decision section. Then report and stop. No workaround in the meantime.
