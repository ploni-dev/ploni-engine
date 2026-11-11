# Waivers

A waiver is the only way a rule or gate does not apply, and only Achia grants one (PROMOTION.md section 8). The agent has no waiver authority.

To grant one: fill in `## Decision` in the findings note, then add an entry here. Every waiver carries an expiry. A PR relying on one cites `waiver: WAIVER-NNN` in its body.

Format:

```
WAIVER-001
rule:    the rule or gate being waived
scope:   which files or paths
reason:  why, in one line
granted: YYYY-MM-DD
expires: a phase number or a date
issue:   #NN
finding: docs/findings/YYYY-MM-DD-slug.md
```

## Active

None.

## Expired

None.
