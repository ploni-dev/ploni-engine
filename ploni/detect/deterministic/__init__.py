"""The deterministic detectors: checksum-backed and pattern-backed identifiers, one module each.

Why: build-plan.md Phase 1 builds the structured identifiers (ID numbers, bank and card numbers,
phones, case numbers and the rest) before any model, one module per kind (section 4.7), each a
Detector of `ploni/detect/base.py`. This file holds no code, so importing one detector loads no
other through it; a detector that reuses another's helpers imports that module itself (the
company number detector imports the Israeli ID detector's, issue #33).
"""
