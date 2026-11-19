"""The only sanctioned logging, temp-file and atomic-write helpers (ADR-0005).

Why: no document text may reach a log or a temp file, and an export must not be left half
written (CLAUDE.md, "Hard constraints"; ADR-0005). Every other part of ploni/ does these three
things through the modules here and nowhere else.
"""
