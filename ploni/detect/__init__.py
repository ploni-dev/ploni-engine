"""The detectors: each finds one kind of identifying text in a projection and reports it.

Why: recall comes from many independent detectors run side by side, roughly 15 deterministic
ones in Phase 1 and the models of Phases 3 and 4 (ADR-0004). Each implements the one protocol
of `base.py`, so that fusion knows none of them, and none of them replaces anything: detection
decides, the writer acts (PROCESS.md section 4.1). This file holds no code, so importing one
detector loads no other.
"""
