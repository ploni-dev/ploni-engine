"""The fixtures check: every file under tests/fixtures/ has a row in tests/fixtures/MANIFEST.md.

Why: build-plan.md section 7, principle 4: "`tests/fixtures/` has a manifest with a provenance
note per file". PROCESS.md section 2 forbids real client documents in any form, including
fixtures; a file with no row has no recorded source, so nobody can tell it is not one (issue #29).

Test matrix:

Equivalence classes:
  EC1  a fixture whose path is in the manifest, in backquotes       no line
  EC2  a fixture whose path is not in the manifest                  one line, its path
  EC3  no fixture at all, only the manifest                         no line
  EC4  the repository's tests/fixtures/ against its MANIFEST.md     no line

Boundaries:
  B1  a fixture in a subfolder        named by its path from tests/fixtures/, with "/"
  B2  the manifest itself             never asks for a row of its own

Adversarial:
  A1  a path the manifest holds only as the start of a longer one (`a.docx` inside
      `a.docx.bak`), or without backquotes    one line
  A2  a fixture with a Hebrew name, not named    one line, the Hebrew name

Not applicable: the document axes, and the Hebrew axes of the test-matrix skill other than A2:
the input is file names and the text of one file.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
MANIFEST_NAME = "MANIFEST.md"


def unlisted(folder: Path, manifest: str) -> list[str]:
    """Return the fixture paths under `folder` that `manifest` does not name in backquotes.

    Contract: paths are relative to `folder`, with "/", sorted. The manifest file at the top
    of `folder` is not a fixture. A path counts as named only as a whole backquoted string.
    """
    paths = (path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file())
    return sorted(path for path in paths if path != MANIFEST_NAME and f"`{path}`" not in manifest)


def test_ec1_named(tmp_path: Path) -> None:
    (tmp_path / "a.docx").write_bytes(b"x")
    assert unlisted(tmp_path, "| `a.docx` | written for the test |") == []


def test_ec2_not_named(tmp_path: Path) -> None:
    (tmp_path / "a.docx").write_bytes(b"x")
    assert unlisted(tmp_path, "| `b.docx` | written for the test |") == ["a.docx"]


def test_ec3_no_fixture(tmp_path: Path) -> None:
    (tmp_path / MANIFEST_NAME).write_text("# Fixtures\n", encoding="utf-8")
    assert unlisted(tmp_path, "# Fixtures\n") == []


def test_ec4_the_repository() -> None:
    manifest = (FIXTURES / MANIFEST_NAME).read_text(encoding="utf-8")
    assert unlisted(FIXTURES, manifest) == []


def test_b1_a_subfolder(tmp_path: Path) -> None:
    (tmp_path / "docx").mkdir()
    (tmp_path / "docx" / "a.docx").write_bytes(b"x")
    assert unlisted(tmp_path, "`a.docx`") == ["docx/a.docx"]
    assert unlisted(tmp_path, "`docx/a.docx`") == []


def test_b2_the_manifest_needs_no_row(tmp_path: Path) -> None:
    (tmp_path / MANIFEST_NAME).write_text("nothing", encoding="utf-8")
    assert unlisted(tmp_path, "nothing") == []


def test_a1_only_inside_a_longer_path(tmp_path: Path) -> None:
    (tmp_path / "a.docx").write_bytes(b"x")
    assert unlisted(tmp_path, "`a.docx.bak` and a.docx") == ["a.docx"]


def test_a2_a_hebrew_name(tmp_path: Path) -> None:
    (tmp_path / "כתב_תביעה.docx").write_bytes(b"x")
    assert unlisted(tmp_path, "`a.docx`") == ["כתב_תביעה.docx"]
