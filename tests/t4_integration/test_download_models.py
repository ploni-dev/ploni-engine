"""Module suite for scripts/download_models.py: the script run as a program.

Why: the unit tests call `main()`; only a real run shows that the program finds the
docs/THIRD_PARTY.md of the repository it lies in and passes its result on as its exit code.

Matrix (each run is in a temp folder holding a copy of the script and of docs/THIRD_PARTY.md):
  M1  `--rows` on the file as it is in the repository    exit 0, the file unchanged
  M2  `--rows` on a file whose table is out of date       exit 0, the table made new
  M3  no argument                                          exit 2, a usage line, the file unchanged
No run downloads anything.

Not in the fast suite: PROCESS.md section 5.1 puts t4 in the full suite. Until the full
workflow exists it is run by hand: python -m pytest tests/t4_integration
"""

import shutil
import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]


def copy_of_the_repository(folder: Path) -> Path:
    """Copy the script and docs/THIRD_PARTY.md into `folder`; return the copy of the file."""
    (folder / "scripts").mkdir()
    (folder / "docs").mkdir()
    shutil.copy(REPOSITORY / "scripts" / "download_models.py", folder / "scripts")
    return Path(shutil.copy(REPOSITORY / "docs" / "THIRD_PARTY.md", folder / "docs"))


def run(folder: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the copied script from a folder outside it."""
    return subprocess.run([sys.executable, str(folder / "scripts" / "download_models.py"), *arguments], cwd=folder.parent, capture_output=True, text=True, timeout=60, check=False)  # noqa: S603 fixed argv, no shell


def test_m1_rows_on_the_file_as_it_is(tmp_path: Path) -> None:
    third_party = copy_of_the_repository(tmp_path)
    before = third_party.read_bytes()
    assert run(tmp_path, "--rows").returncode == 0
    assert third_party.read_bytes().replace(b"\r\n", b"\n") == before.replace(b"\r\n", b"\n")


def test_m2_rows_on_an_old_table(tmp_path: Path) -> None:
    third_party = copy_of_the_repository(tmp_path)
    original = third_party.read_text(encoding="utf-8")
    third_party.write_text(original.replace("| Model | URL |", "| Model | Link |"), encoding="utf-8")
    assert run(tmp_path, "--rows").returncode == 0
    assert third_party.read_text(encoding="utf-8").replace("\r\n", "\n") == original.replace("\r\n", "\n")


def test_m3_no_argument(tmp_path: Path) -> None:
    third_party = copy_of_the_repository(tmp_path)
    before = third_party.read_bytes()
    done = run(tmp_path)
    assert done.returncode == 2 and "usage:" in done.stderr
    assert third_party.read_bytes() == before
