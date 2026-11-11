# ADR-0005: The safety/ wrappers

Date: 2026-11-11. Status: accepted.

## Context

The product's entire promise is that a sensitive document never leaks. The loudest leak paths are not the model: they are a document surface landing in a log line, a temp file surviving a crash, or a half-written artifact after an interrupted export.

A leak found by whoever audits this product, rather than by us, ends the product.

## Decision

`ploni/safety/` provides the only sanctioned logging, temp-file and atomic-write helpers. `logging.py` redacts, `tempfiles.py` creates and removes securely, `atomic.py` writes then renames so a crash leaves either a complete artifact or none.

Canary tests run the full pipeline over a document seeded with unique strings and assert that no canary appears in any log record, any temp file, or any artifact other than the encrypted mapping. They run on every commit.

## Consequences

Bypassing the wrappers has to be deliberate, and the canary test catches it on the next commit rather than at audit time.

A Ponytail finding against anything under `safety/` is rejected on sight. Thinner code here buys nothing worth having.
