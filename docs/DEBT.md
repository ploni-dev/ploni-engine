# Carried debt

Ponytail findings and other shortcuts deliberately carried rather than fixed now (PROCESS.md section 7.1). Reviewed at every phase close.

Each item needs a named reason and an issue number. Debt with neither is not debt, it is a bug nobody wrote down.

| # | What | Reason carried | Issue | Opened | Phase to fix |
|---|---|---|---|---|---|
| 1 | The program never switches the safety helpers on: nothing calls the log setup, the temp folder or the start-up sweeps | No product code reads a document, logs or writes a temp file yet, so there is nothing for them to guard; they are switched on with the first code that does | #211 | 2026-11-24 | Phase 1, first: before the first PR that makes product code read a document, log or write a temp file |
| 2 | A second process's start-up sweep destroys the temp files of a run that is still working | No caller exists yet; one process runs at a time until the worker process of ADR-0006 is built | #212 | 2026-11-24 | Phase 1, first: the same deadline |
| 3 | An uncaught error prints its message, and the core types show document text when printed | No code builds these types from a document yet. The second half changes how the core types print, which is Achia's to decide before it is built | #213 | 2026-11-24 | Phase 1, first: the same deadline |
| 4 | Product code can still use Python's `tempfile` directly | The ban was approved on 2026-11-18 and is not built; no product code writes a temp file yet | #214 | 2026-11-24 | Phase 1, first: the same deadline |
| 5 | `selftest` says "offline OK" with the low-level network module loaded | The no-network test of the fast suite holds the import rule; what `selftest` itself proves is tracked in `docs/STATUS.md` | #215 | 2026-11-24 | Phase 1 or later |
| 6 | A log field key taken from data is written, and only a written rule stands against it | No product code calls `event` yet | #216 | 2026-11-24 | Phase 1, first: the same deadline |
| 7 | The layering test does not judge the three base parts | The parts it leaves out hold no code that could break the layering yet | #217 | 2026-11-24 | Phase 1 or later |
| 8 | The inventory's docstring is wrong for a symbolic link to a folder inside a revision folder | Words only; the code's behaviour is tested | #218 | 2026-11-24 | Phase 1 or later |
| 9 | Running the command-line file by its path fails outside the development environment | The supported ways, `ploni` and `python -m ploni`, work and are tested; the packager's launcher is Phase 13 | #219 | 2026-11-24 | Phase 1 for the docstring line; Phase 13 for the launcher |
| 10 | Ids are treated as safe to print, but the plan makes them plain hashes of names | Nothing builds ids yet; the question of how ids are made is on #169 | #220 | 2026-11-24 | With #169, before ids are built |
| 11 | Two package docstrings lack two of the four parts | Words only | #221 | 2026-11-24 | Phase 1 or later |

Items 1 to 11 are the findings of the Ponytail pass over the whole module at the close of Phase 0 (issue #210; commit `7279581`, 2026-11-24), which found nothing that must be fixed before the close: no code under `ploni/` reads a document yet. Achia triaged them on 2026-11-25: "Carry all, five first in Phase 1 (Recommended)" (#210). Items 1, 2, 3, 4 and 6 carry the pass's deadline.
