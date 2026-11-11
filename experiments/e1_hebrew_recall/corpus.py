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
is over the extracted text, so these are outside the E1 number by definition;
`unread_characters` says how much body text that was, so it is never silent.
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

import docx
from docx.oxml.ns import qn
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


class DocumentReadError(ValueError):
    """A document could not be read, or held no text.

    Why: the errors python-docx and the file system raise carry the full path,
    and a file name can identify a client.

    Contract: the message names the document id and the kind of failure only.
    """


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

    Contract: order preserved. Each text goes through `_visible` first.
    """
    return [stripped for text in texts if (stripped := _visible(text).strip())]


def _visible(text: str) -> str:
    """Rewrite characters the model's tokenizer cannot represent as a reader sees them.

    Why: the tokenizer at the pinned commit turns a no-break space, a thin
    space, a zero-width space, a soft hyphen or a stray byte order mark into
    `[UNK]` together with the words beside it, so a name next to one would be
    counted as a model miss. Phase 3 normalizes whitespace the same way.

    Contract: every Unicode space separator (category Zs) becomes a plain
    space; every format character (category Cf: zero-width, soft hyphen, byte
    order mark, direction marks) is removed. Nothing else changes.
    """
    return "".join(
        " " if unicodedata.category(character) == "Zs" else character
        for character in text
        if unicodedata.category(character) != "Cf"
    )


def _docx_paragraphs(container) -> Iterator:
    """Yield the paragraphs of a document body or table cell, in document order.

    Why: names in contracts and court headers often sit in tables, which
    `Document.paragraphs` leaves out.

    Contract: `container` is a python-docx Document or table cell. Recurses into
    nested tables. A merged cell is yielded once, not once per grid position.
    """
    for block in container.iter_inner_content():
        if not isinstance(block, Table):
            yield block
            continue
        seen_cells = set()
        for row in block.rows:
            for cell in row.cells:
                # python-docx repeats a merged cell for every grid position it spans.
                if cell._tc in seen_cells:
                    continue
                seen_cells.add(cell._tc)
                yield from _docx_paragraphs(cell)


def read_paragraphs(path: Path) -> list[str]:
    """Read one document into its non-empty paragraphs.

    Why: a paragraph is the unit handed to the model (see PREREGISTRATION.md),
    so every supported format is reduced to the same shape here.

    Contract: `.txt` is decoded as UTF-8 with an optional byte order mark, one
    paragraph per line. `.docx` gives body paragraphs and table cells in
    document order. Characters the tokenizer cannot represent are rewritten by
    `_visible`. Raises UnsupportedDocumentError for any other suffix and
    UnicodeDecodeError for a `.txt` that is not UTF-8.

    Known limits: see the module docstring for what a `.docx` read leaves out.
    A Windows-1255 text file is rejected, not guessed at.
    """
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return _non_blank(iter(path.read_text(encoding="utf-8-sig").splitlines()))
    if suffix == ".docx":
        return _non_blank(block.text for block in _docx_paragraphs(docx.Document(str(path))))
    raise UnsupportedDocumentError(f"unsupported document suffix: {suffix or '(none)'}")


def unread_characters(path: Path) -> int:
    """Count the body text of a `.docx` that `read_paragraphs` does not return.

    Why: a name typed with Track Changes on, or sitting in a content control,
    a field or a text box, is skipped by python-docx without a sign. A count
    may be printed where the text may not, and a non-zero count tells the
    annotator the worksheet is missing words.

    Contract: characters in every `w:t` under the document body, minus those in
    the runs `read_paragraphs` reads. 0 for a `.txt`. Headers, footers and
    notes are separate parts of the file and are not in either number.
    """
    if path.suffix.lower() != ".docx":
        return 0
    document = docx.Document(str(path))
    total = sum(len(element.text or "") for element in document.element.body.iter(qn("w:t")))
    read = sum(
        len(element.text or "")
        for paragraph in _docx_paragraphs(document)
        for element in paragraph._p.xpath("./w:r/w:t | ./w:hyperlink/w:r/w:t")
    )
    return total - read


def read_checked(doc_id: str, path: Path) -> list[str]:
    """Read one document, failing under its id and never under its file name.

    Why: `run_model` lets a failure stop the run, and the traceback goes to the
    terminal.

    Contract: returns what `read_paragraphs` returns. Raises DocumentReadError
    naming `doc_id` and the kind of the original error, with the original
    error suppressed, if the file cannot be read; and if it holds no text, so
    a scanned or empty document cannot pass as one with no names in it.
    """
    try:
        paragraphs = read_paragraphs(path)
    except Exception as error:
        raise DocumentReadError(f"{doc_id}: cannot be read ({type(error).__name__})") from None
    if not paragraphs:
        raise DocumentReadError(f"{doc_id}: no text was read")
    return paragraphs
