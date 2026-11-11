"""Find the E1 documents on disk and read them into paragraphs.

Why: the ten documents are real, so they live outside the repository
(CLAUDE.md: no real client documents in the repo, in any form) and nothing
derived from them, not even a file name, may reach the terminal. This module is
where both rules are kept.

Known limits: `.txt` and `.docx` only. A `.docx` yields body paragraphs and
table cells; headers, footers, footnotes, endnotes, comments and text boxes are
not read, and neither is text inside a tracked insertion or a content control,
because python-docx 1.2.0 builds paragraph text from direct `w:r` and
`w:hyperlink` children only (`docx/oxml/text/paragraph.py:60`). The hand count
is over the extracted text, so these are outside the E1 number by definition.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import docx
from docx.table import Table

SUPPORTED_SUFFIXES = frozenset({".txt", ".docx"})
# Word writes "~$name.docx" beside an open document; dotfiles are OS litter.
IGNORED_NAME_PREFIXES = (".", "~$")


class UnsupportedDocumentError(ValueError):
    """A file in the corpus directory is in a format this harness cannot read.

    Why: skipping it quietly would make the run cover fewer than ten documents
    without anyone deciding that.

    Contract: the message names suffixes and counts only, never a file name,
    because a file name can identify a client.
    """


def is_inside(path: Path, directory: Path) -> bool:
    """Say whether `path` is `directory` or lies anywhere below it.

    Why: the run refuses a corpus or output directory inside the repository, so
    a real document can never be one `git add` away from a commit.

    Contract: neither path needs to exist. Both are resolved first, so `..`
    segments and symbolic links do not hide the real location.
    """
    resolved = path.resolve()
    resolved_directory = directory.resolve()
    return resolved == resolved_directory or resolved_directory in resolved.parents


def list_documents(corpus_dir: Path) -> list[Path]:
    """Return the documents in `corpus_dir`, sorted by file name.

    Why: the sorted position is what turns a file into `doc01`..`doc10`, so the
    order has to be the same on every run.

    Contract: looks at the directory's own entries only. Sub-directories and
    names starting with `.` or `~$` are ignored. Raises
    UnsupportedDocumentError if any remaining file is not `.txt` or `.docx`
    (suffix compared case-insensitively).
    """
    files = [
        entry
        for entry in sorted(corpus_dir.iterdir(), key=lambda entry: entry.name)
        if entry.is_file() and not entry.name.startswith(IGNORED_NAME_PREFIXES)
    ]
    unsupported = Counter(
        entry.suffix.lower() or "(none)"
        for entry in files
        if entry.suffix.lower() not in SUPPORTED_SUFFIXES
    )
    if unsupported:
        listing = ", ".join(f"{count} x {suffix}" for suffix, count in sorted(unsupported.items()))
        raise UnsupportedDocumentError(
            f"unsupported files in the corpus directory: {listing}; "
            f"supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
        )
    return files


def document_id(position: int) -> str:
    """Name the document at a 1-based sorted position, e.g. `doc03`.

    Why: this id stands in for the file name everywhere outside the private
    output directory, including the tally and the findings note.

    Contract: `position` starts at 1. Two digits, zero-padded.
    """
    return f"doc{position:02d}"


def _non_blank(texts: Iterator[str]) -> list[str]:
    """Strip each text and drop the ones that are empty afterwards.

    Why: an empty paragraph gives the model nothing and clutters the worksheet.

    Contract: order preserved; inner whitespace untouched.
    """
    return [stripped for text in texts if (stripped := text.strip())]


def _docx_block_texts(container) -> Iterator[str]:
    """Yield paragraph texts of a document body or table cell, in document order.

    Why: names in contracts and court headers often sit in tables, which
    `Document.paragraphs` leaves out.

    Contract: `container` is a python-docx Document or table cell. Recurses into
    nested tables. A merged cell is yielded once, not once per grid position.
    """
    for block in container.iter_inner_content():
        if not isinstance(block, Table):
            yield block.text
            continue
        seen_cells = set()
        for row in block.rows:
            for cell in row.cells:
                # python-docx repeats a merged cell for every grid position it spans.
                if cell._tc in seen_cells:
                    continue
                seen_cells.add(cell._tc)
                yield from _docx_block_texts(cell)


def read_paragraphs(path: Path) -> list[str]:
    """Read one document into its non-empty paragraphs.

    Why: a paragraph is the unit handed to the model (see PREREGISTRATION.md),
    so every supported format is reduced to the same shape here.

    Contract: `.txt` is decoded as UTF-8 with an optional byte order mark, one
    paragraph per line. `.docx` gives body paragraphs and table cells in
    document order. Raises UnsupportedDocumentError for any other suffix and
    UnicodeDecodeError for a `.txt` that is not UTF-8.

    Known limits: see the module docstring for what a `.docx` read leaves out.
    A Windows-1255 text file is rejected, not guessed at.
    """
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return _non_blank(iter(path.read_text(encoding="utf-8-sig").splitlines()))
    if suffix == ".docx":
        return _non_blank(_docx_block_texts(docx.Document(str(path))))
    raise UnsupportedDocumentError(f"unsupported document suffix: {suffix or '(none)'}")
