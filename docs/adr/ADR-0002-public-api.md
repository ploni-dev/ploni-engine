# ADR-0002: A four-function public API, frozen at Phase 10

Date: 2026-11-11. Status: accepted.

## Context

The desktop app is one consumer of the engine. A Word add-in, a local privacy gateway and an MCP server are all on the post-v1 list (`build-plan.md` section 13). If each consumer reaches into engine internals, each becomes a rewrite rather than an integration.

## Decision

The public surface is exactly four functions: `analyze`, `apply`, `verify`, `rehydrate`, plus `api_version` as a module constant. Everything else under `ploni/` is internal and may change freely.

A contract suite in `tests/t0_contract/` pins the signatures, the exception types and the shape of every returned object. The API is frozen at the end of Phase 10.

## Consequences

Changing the public API becomes deliberate and visible: the contract tests fail, `ploni/api.py` is CODEOWNERS-protected, and `api_version` moves.

The cost is that the first design has to be good enough to live with, which is why the freeze is at Phase 10 and not Phase 1.
