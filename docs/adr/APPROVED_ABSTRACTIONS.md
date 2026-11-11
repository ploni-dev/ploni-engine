# Approved abstractions

Ponytail exists to delete indirection, and it is right to flag everything on this list. These five are deliberate and load-bearing, so the answer to a finding against one of them is the ADR number, and the abstraction stays (PROCESS.md section 4.4).

Anything **not** on this list, and not justified in the PR body, gets deleted.

Adding a row is a CODEOWNERS-protected change, so the register grows deliberately rather than by habit.

| Abstraction | ADR | Why it is not over-engineering |
|---|---|---|
| Four-function public API | [ADR-0002](ADR-0002-public-api.md) | The desktop UI, a Word add-in and a gateway are consumers of one frozen contract, not rewrites of the engine |
| `DocumentAdapter` protocol | [ADR-0003](ADR-0003-document-adapter.md) | Isolates the riskiest component; a DOCX rewrite must not cascade into detection, and XLSX, PDF and EML plug in behind it |
| `Detector` protocol | [ADR-0004](ADR-0004-detector-protocol.md) | Roughly 15 implementations in Phase 1 alone; fusion must know about none of them |
| `safety/` wrappers | [ADR-0005](ADR-0005-safety-wrappers.md) | Log and temp-file redaction must be impossible to bypass by accident |
| Worker process | [ADR-0006](ADR-0006-worker-process.md) | Real cancellation, memory isolation, deterministic thread counts |

A finding that points at error handling, input validation, `ploni/safety/`, any test, any fixture, or any row above is rejected on sight and the rejection is recorded. Fewer lines is worth nothing here if it costs a validation path.
