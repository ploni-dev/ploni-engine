# ADR-0006: Inference runs in a worker process

Date: 2026-11-11. Status: accepted.

## Context

A 60-page document is roughly 120 model windows plus a verification pass, several minutes of work. The user must be able to cancel it. Determinism requires pinned thread counts. A crash in the model layer must not take the UI with it.

Threads give none of these cleanly: Python threads cannot be killed, thread counts leak across the process, and a native crash in the runtime takes everything down.

## Decision

Inference runs in a separate worker process, talking to the UI over a local IPC channel with streaming progress. Thread counts are pinned in the worker.

## Consequences

Cancellation is real: the worker is terminated and the session leaves no partial output and no partial mapping (journey S11). Memory is isolated and reclaimed. `intra_op_num_threads` and `inter_op_num_threads` are fixed, which is a precondition for byte-identical output across runs.

The cost is IPC plumbing and serialization at the boundary, which is the price of being able to cancel and of being reproducible.
