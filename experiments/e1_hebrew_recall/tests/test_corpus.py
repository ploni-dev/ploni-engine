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

document_id
  B4   1 -> doc01, 10 -> doc10
"""

from __future__ import annotations

from pathlib import Path

import docx
import pytest

from corpus import (
    UnsupportedDocumentError,
    document_id,
    is_inside,
    list_documents,
    read_paragraphs,
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
