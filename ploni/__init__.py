"""Ploni: an offline tool that replaces identifying information in a document with surrogates.

Why: one package holds the whole engine, so that each consumer (the desktop app first; a Word
add-in, a local gateway or an MCP server later) reaches it through one public module,
`api.py`, and the rest can change freely (ADR-0002). `api.py` is not written yet; until it
is, the package runs as the installed `ploni` command (pyproject.toml) or `python -m ploni`.
"""
