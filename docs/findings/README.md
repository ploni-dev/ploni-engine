# Findings

A findings note is written when a gate cannot be met, or when a measurement disagrees with its prediction beyond the stated threshold (PROCESS.md section 10). It is also the only permitted form of a waiver request (PROMOTION.md section 8).

Nothing is tuned, loosened or worked around while a finding is open. Implementation on that path stops until `## Decision` is filled in by Achia.

File name: `YYYY-MM-DD-slug.md`. Template:

```markdown
# Finding: <one line>

## What was being measured
## Prediction and threshold
(as stated before the run, not after)
## Measured result
(raw output, pasted; results file SHA if there is one)
## What this rules in and what it rules out
## Options, with the cost of each
## Recommendation
## Scope requested
(only for a waiver request: which rule, which files, until when)
## Decision
(left blank; Achia fills this in)
```

These notes are the project's memory. Six months from now, "why is this threshold 0.92 and not 0.98" has an answer with the raw numbers attached.
