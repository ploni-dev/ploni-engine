# ADR-0004: The Detector protocol

Date: 2026-11-11. Status: accepted.

## Context

Phase 1 alone has roughly 15 deterministic detectors, and Phases 3 and 4 add Hebrew NER and a multilingual zero-shot detector. Recall comes from unioning independent detectors at low thresholds, so the set grows over time.

If fusion knows about individual detectors, every new detector edits fusion, and the measured numbers can no longer be attributed to one change.

## Decision

Every detector implements one protocol: `name`, `produces`, `requires_morph`, `detect`. Fusion knows about none of them. A detector conformance suite asserts in-range spans, declared types only, and confidence in `[0, 1]`.

A detector that appears to need a fusion change is a design discussion, not a code change. The session stops and raises it.

## Consequences

Adding a detector is a module plus a fixture file plus measured numbers, one per commit, so a precision or recall regression has exactly one candidate cause.

Detection decides; it never replaces. That separation is enforced by the protocol having no write path.
