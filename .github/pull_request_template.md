## Orientation
Goal:
Deliverable:
Gate:
Downstream risk if wrong:

## Phase, issue, branch
Phase N, issue #NN, feat/N-slug

## What this does

## Gate evidence
<!-- The actual command and its actual output. Numbers, not claims.
     Results file SHA if a metric gate applies. -->

```
```

## Prediction vs measurement
Predicted:
Measured:
Within threshold: yes / no

## Test evidence
<!-- Failing-first output, then passing output. -->

Equivalence classes and axes covered:
Sample size:
Surviving mutants, for a PR that changes code under ploni/:

## Ponytail review
<!-- Skill output on the final diff, pasted. Run by a session or subagent that did not write the code. -->

Commit reviewed:
Reviewed by:
Docstrings still describe the code: yes / no
Findings accepted:
Findings rejected, with the ADR number justifying each:

## Who merges
<!-- CLAUDE.md, "Merging". Every review run on the last commit is pasted above, each with its brief. -->
Needs a decision of Achia's: yes / no, because:
The decision (question as asked, his answer, date; or a line that names him and the date):

## Modern Web Guidance
<!-- Only when the PR touches HTML, CSS or browser JavaScript; delete this section otherwise.
     One line per guide used: file and line, what it changed, what was left out. -->

## Golden file changes
None, or: changed because ...

## Checklist
- [ ] One concern, one branch
- [ ] Failing test written before implementation
- [ ] Docstring with Why on every public function touched
- [ ] Edge cases from equivalence classes covered
- [ ] Ponytail review run and findings addressed
- [ ] No test, threshold, fixture or baseline weakened
- [ ] No baseline or gate change in this PR
- [ ] Fast suite green locally
