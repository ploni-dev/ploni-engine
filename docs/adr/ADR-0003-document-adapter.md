# ADR-0003: The DocumentAdapter protocol

Date: 2026-11-11. Status: accepted.

## Context

The offset layer is the riskiest component in the product. If `TextProjection` and its anchors are wrong, every phase downstream inherits the bug, and the failure the user sees is "the tool broke my document", which is unrecoverable trust damage.

v1 ships DOCX and TXT. XLSX, PDF and EML are Tier 1 on the post-v1 list.

## Decision

Format handling sits behind a `DocumentAdapter` protocol: `extract`, `write`, `inventory`. An adapter conformance suite in `tests/t0_contract/` runs against every registered adapter, so a new format inherits the whole test battery rather than being tested from scratch.

## Consequences

A rewrite of DOCX handling cannot touch detection, resolution or writing. Adding a format is a new module plus a fixture corpus, with no change above the protocol line.

The cost is one layer of indirection over what is currently a single implementation. That is the point: the second implementation is already scheduled.
