"""The code lines of a GitHub workflow, as the pin tests of the check workflows compare them.

Why: a pin built from line patterns let edits through that switch a check off and leave the pin
green (the review of #164 measured 18 on pr-size.yml; #166 measured the same kinds on the four
older ones), so each pin compares a workflow's code lines with an exact list. GitHub's parser
(YamlDotNet, which the runner imports) takes space and tab as whitespace and ends a line, or a
comment, at LF, CR, U+0085, U+2028 and U+2029, where Python's `\\s`, `strip()` and `splitlines()`
take other sets (the reviews of #164, pass 2, and #166, pass 1).

Contract: `code_lines(path)` reads the file as UTF-8 and raises ValueError, naming the file, when
it holds any character outside ASCII, so no character with another meaning for GitHub reaches
the comparison. Otherwise it returns the file's lines, split at LF, CR and CRLF (`read_text`
turns each into LF), without comment lines and blank lines, with a trailing comment (one or more
spaces, then `#`) cut and trailing spaces dropped, indentation kept.

Known limits: a tab is kept where YAML takes it as whitespace (before a trailing comment, or at
the end of a line), so the same workflow with a tab there reads as other lines: a pin fails
closed. A ` #` inside a quoted value would be cut too; no workflow pinned here has one. The
five workflows are ASCII (measured in #166); a non-ASCII character in one of them, even in a
comment, makes its pin raise.
"""

from __future__ import annotations

import re
from pathlib import Path

TRAILING_COMMENT = re.compile(r" +#.*$")


def code_lines(path: Path) -> list[str]:
    """Return the lines of a workflow that YAML reads, to compare with an exact list.

    Why: the pin tests compare a whole workflow, not patterns in it (the module docstring).
    Contract: args, the workflow file; returns its code lines as the module docstring says;
    raises ValueError on a character outside ASCII, OSError when the file cannot be read.
    Known limits: those of the module docstring.
    """
    text = path.read_text(encoding="utf-8")
    if not text.isascii():
        raise ValueError(f"{path.name}: a character outside ASCII")
    lines = text.split("\n")
    return [TRAILING_COMMENT.sub("", line).rstrip(" ") for line in lines if line.strip(" ") and not line.lstrip(" ").startswith("#")]
