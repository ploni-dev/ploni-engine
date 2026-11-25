# ploni-engine

**Ploni** (פלוני): local, offline, Hebrew-first document pseudonymization for lawyers, accountants and clinicians. Python package and CLI: `ploni`.

כלי מקומי, ללא רשת, להתממת מסמכים בעברית לפני העלאה לכלי AI.

Named for the word Israeli legal writing already uses for an unnamed party. The name is not a claim: the product never says a document is anonymized, compliant or safe to upload (build-plan.md section 1).

## Status

Planning complete. No product code yet. Next: Phase 0 (build-plan.md section 16, PROMOTION.md section 10).

## Read in this order

| File | What it is |
|---|---|
| `CLAUDE.md` | Always-on rules for every Claude Code session |
| `build-plan.md` | v3.0. What to build: architecture, 14 phases, each with a numeric gate |
| `PROCESS.md` | v1.1. How work is done: code standards, tests, Ponytail, session shape |
| `PROMOTION.md` | v1.0. How code reaches `main` and a release tag, and how every rule is enforced |
| `.claude/skills/` | The five project skills: `phase-gate`, `new-detector`, `eval-baseline`, `test-matrix`, `production-gate`. Also four Ponytail skills vendored at a pinned commit, and `modern-web-guidance` with its guides vendored at a pinned commit, both recorded in `docs/THIRD_PARTY.md` |
| `docs/research/` | The market, competition and business-model research the plan is built on |

## Ownership

- Engineering: Achia
- Legal, regulatory and all external-facing claims, including the name's trademark check: Tomer (`ploni/i18n/claims/` once it exists). As of 2026-11-15 Tomer is not involved for now; these questions go to Achia (`CLAUDE.md`, "Who decides")

A line of bad PR 10 of the closing test. Never merged.
