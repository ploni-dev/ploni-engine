"""Test matrix for corpus: is_inside, list_documents, read_paragraphs, document_id.

No real document is used anywhere here. Every text is written for the test.

is_inside
  EC1  a file below the directory            -> True
  EC2  the directory itself                  -> True
  EC3  a sibling directory                   -> False
  EC4  the parent directory                  -> False
  A1   sibling whose name extends the directory's name (repo vs repo-private) -> False
  A2   a path that leaves and re-enters through ".."                          -> True

list_documents
  EC5  .txt and .docx                        -> returned, sorted by name
  EC6  sub-directories, dotfiles, Word lock files (~$...) -> ignored
  B1   empty directory                       -> empty list
  E1   any other suffix                      -> UnsupportedDocumentError
  A3   the error text never contains a file name (names can identify a client)

read_paragraphs
  EC7  .txt                                  -> one paragraph per non-blank line
  EC8  .docx body paragraphs and table cells -> document order
  B2   UTF-8 byte order mark                 -> not part of the first paragraph
  B3   blank and whitespace-only lines       -> dropped
  H1   niqqud, gershayim (both code points), geresh, final letters, Latin run -> unchanged
  E2   unsupported suffix                    -> UnsupportedDocumentError
  H2   characters the tokenizer cannot see (no-break and thin space, zero-width
       space, soft hyphen, inner byte order mark, direction marks) -> a plain
       space or nothing, in .txt and in .docx

unread_characters
  EC9  .txt, plain .docx, merged table cells -> 0
  A4   .docx text in a tracked insertion     -> its length
  A5   .docx text in a content control       -> its length

read_checked
  EC10 a readable document                   -> its paragraphs
  E3   a file that is not a Word package     -> DocumentReadError naming the id,
       never the file name
  B5   a document with no text               -> DocumentReadError

document_id
  B4   1 -> doc01, 10 -> doc10
"""

from __future__ import annotations

from pathlib import Path

import docx
import pytest

from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from corpus import (
    DocumentReadError,
    UnsupportedDocumentError,
    document_id,
    is_inside,
    list_documents,
    read_checked,
    read_paragraphs,
    unread_characters,
)


def test_ec1_file_below_directory(tmp_path: Path):
    assert is_inside(tmp_path / "a" / "b.txt", tmp_path)


def test_ec2_directory_itself(tmp_path: Path):
    assert is_inside(tmp_path, tmp_path)


def test_ec3_sibling_directory(tmp_path: Path):
    assert not is_inside(tmp_path / "other", tmp_path / "repo")


def test_ec4_parent_directory(tmp_path: Path):
    assert not is_inside(tmp_path, tmp_path / "repo")


def test_a1_sibling_with_extended_name(tmp_path: Path):
    assert not is_inside(tmp_path / "repo-private" / "x.txt", tmp_path / "repo")


def test_a2_dotdot_path_that_resolves_inside(tmp_path: Path):
    assert is_inside(tmp_path / "repo" / ".." / "repo" / "x.txt", tmp_path / "repo")


def test_ec5_supported_files_sorted(tmp_path: Path):
    for name in ["b.txt", "a.docx", "c.TXT"]:
        (tmp_path / name).write_bytes(b"")
    assert [p.name for p in list_documents(tmp_path)] == ["a.docx", "b.txt", "c.TXT"]


def test_ec6_directories_dotfiles_and_lock_files_ignored(tmp_path: Path):
    (tmp_path / "out").mkdir()
    for name in [".DS_Store", "~$a.docx", "a.docx"]:
        (tmp_path / name).write_bytes(b"")
    assert [p.name for p in list_documents(tmp_path)] == ["a.docx"]


def test_b1_empty_directory(tmp_path: Path):
    assert list_documents(tmp_path) == []


def test_e1_unsupported_suffix_raises(tmp_path: Path):
    (tmp_path / "scan.pdf").write_bytes(b"")
    with pytest.raises(UnsupportedDocumentError):
        list_documents(tmp_path)


def test_a3_error_text_has_no_file_name(tmp_path: Path):
    (tmp_path / "חוזה-משפחת-כהן.pdf").write_bytes(b"")
    with pytest.raises(UnsupportedDocumentError) as raised:
        list_documents(tmp_path)
    assert "כהן" not in str(raised.value)
    assert ".pdf" in str(raised.value)


def test_ec7_txt_one_paragraph_per_line(tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_text("שורה ראשונה\nשורה שנייה\n", encoding="utf-8")
    assert read_paragraphs(path) == ["שורה ראשונה", "שורה שנייה"]


def test_ec8_docx_body_and_table_cells_in_order(tmp_path: Path):
    document = docx.Document()
    document.add_paragraph("לפני הטבלה")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "תא ראשון"
    table.cell(0, 1).text = "תא שני"
    document.add_paragraph("אחרי הטבלה")
    path = tmp_path / "a.docx"
    document.save(str(path))
    assert read_paragraphs(path) == ["לפני הטבלה", "תא ראשון", "תא שני", "אחרי הטבלה"]


def test_b2_byte_order_mark_removed(tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_bytes("﻿משה".encode("utf-8"))
    assert read_paragraphs(path) == ["משה"]


def test_b3_blank_lines_dropped(tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_text("\n  \nמשה\n\t\n", encoding="utf-8")
    assert read_paragraphs(path) == ["משה"]


def test_h1_hebrew_forms_unchanged(tmp_path: Path):
    line = "עו\"ד ד״ר ג'ון ג׳ורג׳ מֹשֶׁה ברוך Smith ולכשיעקב"
    path = tmp_path / "a.txt"
    path.write_text(line, encoding="utf-8")
    assert read_paragraphs(path) == [line]


def test_e2_read_unsupported_suffix_raises(tmp_path: Path):
    path = tmp_path / "a.pdf"
    path.write_bytes(b"")
    with pytest.raises(UnsupportedDocumentError):
        read_paragraphs(path)


def test_b4_document_id_is_zero_padded():
    assert document_id(1) == "doc01"
    assert document_id(10) == "doc10"


# Findings of the Ponytail review, 2026-11-11

INVISIBLE = [
    ("משה\u00a0כהן", "משה כהן"),
    ("משה\u2009כהן", "משה כהן"),
    ("מ\u200bשה כהן", "משה כהן"),
    ("מ\u00adשה כהן", "משה כהן"),
    ("משה\ufeff כהן", "משה כהן"),
    ("\u200fמשה כהן\u200e", "משה כהן"),
]


@pytest.mark.parametrize(("raw", "clean"), INVISIBLE)
def test_h2_invisible_characters_in_txt(tmp_path: Path, raw: str, clean: str):
    path = tmp_path / "a.txt"
    path.write_text(f"{raw} הגיע\n", encoding="utf-8")
    assert read_paragraphs(path) == [f"{clean} הגיע"]


def test_h2_invisible_characters_in_docx(tmp_path: Path):
    document = docx.Document()
    for raw, _ in INVISIBLE:
        document.add_paragraph(f"{raw} הגיע")
    path = tmp_path / "a.docx"
    document.save(str(path))
    assert read_paragraphs(path) == [f"{clean} הגיע" for _, clean in INVISIBLE]


def test_ec9_nothing_unread_in_txt_plain_docx_and_merged_cells(tmp_path: Path):
    text = tmp_path / "a.txt"
    text.write_text("משה כהן\n", encoding="utf-8")
    document = docx.Document()
    document.add_paragraph("משה כהן")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).merge(table.cell(0, 1)).text = "תא ממוזג"
    table.cell(1, 0).text = "תא"
    word = tmp_path / "b.docx"
    document.save(str(word))
    assert (unread_characters(text), unread_characters(word)) == (0, 0)


SKIPPED_BY_PYTHON_DOCX = {
    "a4_tracked_insertion": '<w:ins %s w:id="1" w:author="a"><w:r><w:t>יעקב לוי</w:t></w:r></w:ins>',
    "a5_content_control": "<w:sdt %s><w:sdtContent><w:r><w:t>יעקב לוי</w:t></w:r></w:sdtContent></w:sdt>",
}


@pytest.mark.parametrize("xml", SKIPPED_BY_PYTHON_DOCX.values(), ids=SKIPPED_BY_PYTHON_DOCX.keys())
def test_a4_a5_text_python_docx_skips_is_counted(tmp_path: Path, xml: str):
    document = docx.Document()
    document.add_paragraph("לפני")._p.append(parse_xml(xml % nsdecls("w")))
    path = tmp_path / "a.docx"
    document.save(str(path))
    assert read_paragraphs(path) == ["לפני"]
    assert unread_characters(path) == len("יעקב לוי")


def test_ec10_read_checked_returns_the_paragraphs(tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_text("משה כהן\n", encoding="utf-8")
    assert read_checked("doc01", path) == ["משה כהן"]


def test_e3_unreadable_document_error_has_the_id_and_no_file_name(tmp_path: Path):
    path = tmp_path / "CLIENT-NAME.docx"
    path.write_bytes(b"not a Word package")
    with pytest.raises(DocumentReadError) as caught:
        read_checked("doc07", path)
    assert "doc07" in str(caught.value) and "CLIENT" not in str(caught.value)
    assert caught.value.__suppress_context__


def test_b5_document_with_no_text_is_refused(tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_text("\n  \n", encoding="utf-8")
    with pytest.raises(DocumentReadError, match="doc03"):
        read_checked("doc03", path)
