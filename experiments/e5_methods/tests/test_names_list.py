"""Test matrix for names_list: names_of, build.

names_of
  EC1  lines of name and numbers                 the names
  EC2  a name of two words                       each word
  EC3  quote marks around a name ('ג'ורג')       taken off at the ends, kept inside
  EC4  `top`                                     only the first lines
  B1   an empty table, blank lines               nothing
  B2   a name of one letter                      left out

build
  EC5  two tables in a folder, UTF-16            the names of both, sorted, each once
  EC6  a file that is no given-name table        not read
  E1   a folder with no table                    FileNotFoundError
"""

from pathlib import Path

import pytest

import names_list

TABLE = "דוד\t100\t2.0\t2.0\t1\nמשה\t90\t1.8\t3.8\t2\nבן ציון\t5\t0.1\t3.9\t3\n'ג'ורג'\t4\t0.1\t4.0\t4\nא\t1\t0.0\t4.0\t5\n\n"


def test_ec1_to_ec3_b2_names_of() -> None:
    assert names_list.names_of(TABLE, None) == {"דוד", "משה", "בן", "ציון", "ג'ורג"}


def test_ec4_top() -> None:
    assert names_list.names_of(TABLE, 2) == {"דוד", "משה"}
    assert names_list.names_of(TABLE, 0) == set()


@pytest.mark.parametrize("table", ["", "\n\n", "\t5\t1\n"])
def test_b1_nothing(table: str) -> None:
    assert names_list.names_of(table, None) == set()


def test_ec5_ec6_build(tmp_path: Path) -> None:
    (tmp_path / "dist.jew.male.first").write_text(TABLE, encoding="utf-16")
    (tmp_path / "dist.jew.female.first").write_text("רחל\t9\t1\t1\t1\nדוד\t1\t1\t2\t2\n", encoding="utf-16")
    (tmp_path / "dist.jew.last").write_text("כהן\t9\t1\t1\t1\n", encoding="utf-16")
    assert names_list.build(tmp_path, None) == sorted({"דוד", "משה", "בן", "ציון", "ג'ורג", "רחל"})
    assert names_list.build(tmp_path, 1) == ["דוד", "רחל"]


def test_e1_no_table(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        names_list.build(tmp_path, None)
