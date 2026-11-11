# ADR-0001: Three planning documents, and the agent has no waiver authority

Date: 2026-11-11. Status: accepted.

## Context

The code is written by an agent, phase by phase. The failure mode of agentic coding is not bad code, it is an agent under pressure to finish quietly relaxing the thing that would have caught it: skipping a test, lowering a baseline, deciding a rule does not apply here.

## Decision

Three documents, each answering one question, all version controlled in this repo:

- `build-plan.md`, what to build. Architecture, 14 phases, a numeric gate per phase.
- `PROCESS.md`, how work is executed, reviewed and gated.
- `PROMOTION.md`, how code reaches `main` and a release tag, and how each rule is actually enforced.

`CLAUDE.md` holds only what is true on every turn, because rules that apply every turn do not belong behind an invocation.

The agent has no authority to waive any rule, test, threshold or gate. There is no flag, comment or environment variable that turns a gate off. When a rule should not apply, the only permitted action is a waiver request in `docs/findings/`, with an empty `## Decision` section, and then stop. Only Achia grants it, and every waiver expires.

## Consequences

A scope change or a gate change becomes a diff against the plan, reviewed as code, rather than a decision nobody remembers making.

The cost is friction: a blocked session stops and reports instead of routing around the obstacle. That is the intended behavior, and it is only worth anything if the stop is honored when it is inconvenient.
