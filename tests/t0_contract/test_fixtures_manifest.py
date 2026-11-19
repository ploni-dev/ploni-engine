"""The fixtures check: every file under tests/fixtures/ has a row in tests/fixtures/MANIFEST.md.

Why: build-plan.md section 7, principle 4: "`tests/fixtures/` has a manifest with a provenance
note per file". PROCESS.md section 2 forbids real client documents in any form, including
fixtures; a file with no row, or a row with no provenance, has no recorded source, so nobody can
tell it is not one (issue #29).

Test matrix:

Equivalence classes:
  EC1  a fixture with a row: its path in backquotes, a provenance    no line
  EC2  a fixture with no row                                         one line, its path
  EC3  no fixture at all, only the manifest                          no line
  EC4  the repository's tests/fixtures/ against its MANIFEST.md      no line
  EC5  a fixture whose row has an empty provenance                   one line

Boundaries:
  B1  a fixture in a subfolder        named by its path from tests/fixtures/, with "/"
  B2  the manifest itself             never asks for a row of its own

Adversarial:
  A1  a path the manifest holds only as the start of a longer one (`a.docx.bak`), only outside
      the table (also on a line with a "|" that does not start a row), or with no backquotes
      one line
  A2  a fixture with a Hebrew name, not named    one line, the Hebrew name

Not applicable: the document axes, and the Hebrew axes of the test-matrix skill other than A2:
the input is file names and the text of one file.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
MANIFEST_NAME = "MANIFEST.md"


def provenances(manifest: str) -> dict[str, str]:
    """Return the manifest's table as path -> provenance.

    Why: a path counts only in a row of the table, not anywhere in the text, and only with its
    provenance beside it.

    Contract: a row is a line that starts with "| `"; its first cell is the backquoted path, its
    second the provenance, stripped. Other lines are ignored.
    """
    rows = {}
    for line in manifest.splitlines():
        if line.startswith("| `"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            rows[cells[0].strip("`")] = cells[1] if len(cells) > 1 else ""
    return rows


def unlisted(folder: Path, manifest: str) -> list[str]:
    """Return the fixture paths under `folder` that have no row with a provenance in `manifest`.

    Why: the check itself, kept apart from the repository's folder so that it can be tested on
    folders made for each case.

    Contract: paths are relative to `folder`, with "/", sorted. The manifest file at the top of
    `folder` is not a fixture. A row whose provenance is empty does not count.
    """
    rows = provenances(manifest)
    paths = (path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file())
    return sorted(path for path in paths if path != MANIFEST_NAME and not rows.get(path))


def test_ec1_named(tmp_path: Path) -> None:
    (tmp_path / "a.docx").write_bytes(b"x")
    assert unlisted(tmp_path, "| `a.docx` | written for the test | #1 |") == []


def test_ec2_not_named(tmp_path: Path) -> None:
    (tmp_path / "a.docx").write_bytes(b"x")
    assert unlisted(tmp_path, "| `b.docx` | written for the test | #1 |") == ["a.docx"]


def test_ec3_no_fixture(tmp_path: Path) -> None:
    (tmp_path / MANIFEST_NAME).write_text("# Fixtures\n", encoding="utf-8")
    assert unlisted(tmp_path, "# Fixtures\n") == []


def test_ec4_the_repository() -> None:
    manifest = (FIXTURES / MANIFEST_NAME).read_text(encoding="utf-8")
    assert unlisted(FIXTURES, manifest) == []


def test_ec5_an_empty_provenance(tmp_path: Path) -> None:
    (tmp_path / "a.docx").write_bytes(b"x")
    assert unlisted(tmp_path, "| `a.docx` |  | #1 |") == ["a.docx"]
    assert unlisted(tmp_path, "| `a.docx` |") == ["a.docx"]


def test_b1_a_subfolder(tmp_path: Path) -> None:
    (tmp_path / "docx").mkdir()
    (tmp_path / "docx" / "a.docx").write_bytes(b"x")
    assert unlisted(tmp_path, "| `a.docx` | written | #1 |") == ["docx/a.docx"]
    assert unlisted(tmp_path, "| `docx/a.docx` | written | #1 |") == []


def test_b2_the_manifest_needs_no_row(tmp_path: Path) -> None:
    (tmp_path / MANIFEST_NAME).write_text("nothing", encoding="utf-8")
    assert unlisted(tmp_path, "nothing") == []


def test_a1_not_in_a_row_of_its_own(tmp_path: Path) -> None:
    (tmp_path / "a.docx").write_bytes(b"x")
    assert unlisted(tmp_path, "| `a.docx.bak` | written | #1 |") == ["a.docx"]
    assert unlisted(tmp_path, "The rules name `a.docx` in a sentence.") == ["a.docx"]
    assert unlisted(tmp_path, "| a.docx | written | #1 |") == ["a.docx"]
    assert unlisted(tmp_path, "`a.docx` | a note, not a row") == ["a.docx"]


def test_a2_a_hebrew_name(tmp_path: Path) -> None:
    (tmp_path / "כתב_תביעה.docx").write_bytes(b"x")
    assert unlisted(tmp_path, "| `a.docx` | written | #1 |") == ["כתב_תביעה.docx"]
