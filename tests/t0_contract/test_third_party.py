"""The THIRD_PARTY check: every model on disk under models/ is named in docs/THIRD_PARTY.md.

Why: build-plan.md Phase 0, Gate: "CI fails if a model in `models/` is absent from
`THIRD_PARTY.md`" (issue #28). A model that sits on the machine with no row of its own has no
recorded source, revision or license, and could be loaded or shipped unchecked. CLAUDE.md asks
for every model revision pinned by commit hash, so a revision folder must be one.

Test matrix:

Equivalence classes:
  EC1  models/<name>/<revision>/ whose revision is in the file      no line
  EC2  a revision that is not in the file                           one line, name/revision
  EC3  a revision folder that is not a full commit hash ("main", a short hash, a hash with a tail)
                                                                    one line: not pinned
  EC4  files directly in a name folder, the folder named in the file as `models/<name>/`
                                                                    no line
  EC5  such files, the folder not named                             one line, the name
  EC6  a file at the top of models/, named or not                   as EC4 and EC5, by its path
  EC7  an empty name folder                                         no line
  EC8  no models folder (the repository on GitHub: models/ is not in git), or a file by that
       name                                                          no line
  EC9  this laptop's models/ against the repository's docs/THIRD_PARTY.md    no line

Boundaries:
  B1  the hash in the file only in a shorter form (its first 7 characters)    one line
  B2  a hash in capitals on disk          not pinned: git and the hub write hashes in lowercase
  B3  a name folder with both revision folders and loose files    each judged
  B4  names that differ in case ("Zeta", "alpha")    in Python's order, capitals first, not
      the order NTFS lists them in

Adversarial:
  A1  a revision folder named like a word the file holds ("main", "Models")    not pinned,
      whatever the file says
  A2  a name folder in Hebrew, its files not named    one line, the Hebrew name
  A3  a hash or a path that the file holds only inside a longer one (the first 40 characters
      of a SHA-256; `models/e2` inside `models/e2_onnx/`)    one line each

Not applicable: the document axes, and the Hebrew axes of the test-matrix skill other than A2:
the input is folder names and the text of one file.

Known limits:
  - On GitHub there is no models/ folder (it is in .gitignore), so there EC9 checks nothing:
    the check bites on the machine that holds the models, in the fast suite run there.
  - A revision passes when its hash appears anywhere in the file as a whole hash, not only in
    the table of models: a hash named in a paragraph counts as named.
  - The name folder is not compared with the model's name: a recorded hash passes under any
    folder, and a model saved inside a recorded revision folder passes with it.
  - Deeper folders are not looked into: a revision folder is judged by its name only.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# A pinned revision: a full git commit hash, as git and the Hugging Face hub write it.
COMMIT = re.compile(r"[0-9a-f]{40}")


def holds_hash(text: str, revision: str) -> bool:
    """Say whether the text holds the hash whole, not as part of a longer run of hex digits.

    Why: the first 40 characters of a SHA-256 in the file must not pass for a commit hash.
    """
    return re.search(rf"(?<![0-9a-f]){revision}(?![0-9a-f])", text) is not None


def holds_path(text: str, path: str) -> bool:
    """Say whether the text holds the path whole, not as the start of a longer name.

    Why: `models/e2` must not pass because the file names `models/e2_onnx/`.
    """
    return re.search(rf"{re.escape(path)}(?![\w.-])", text) is not None


def by_name(folder: Path) -> list[Path]:
    """Return the entries of a folder sorted by name as strings, capitals first, on every system.

    Why: on Windows sorted() of paths ignores case, so the lines would come out in another
    order there than on Linux.
    """
    return sorted(folder.iterdir(), key=lambda path: path.name)


def judge_folder(folder: Path, third_party: str) -> list[str]:
    """Return one line per revision folder or loose file of one name folder that is not named.

    Why: a name folder may hold revision folders, files, or both, and each is judged.
    """
    found = []
    for revision in (path for path in by_name(folder) if path.is_dir()):
        if not COMMIT.fullmatch(revision.name):
            found.append(f"{folder.name}/{revision.name}: not pinned")
        elif not holds_hash(third_party, revision.name):
            found.append(f"{folder.name}/{revision.name}: not in THIRD_PARTY.md")
    if any(path.is_file() for path in folder.iterdir()) and not holds_path(third_party, f"models/{folder.name}/"):
        found.append(f"{folder.name}: not in THIRD_PARTY.md")
    return found


def unlisted(models: Path, third_party: str) -> list[str]:
    """Return one line per model on disk that the THIRD_PARTY text does not name.

    Why: the judgement of the check, apart from where the folder and the text come from.

    Contract: for each name folder, each revision folder must be a full commit hash that the
    text holds whole ("<name>/<revision>: not pinned" or "<name>/<revision>: not in
    THIRD_PARTY.md"); files directly in a name folder, or at the top of `models`, need their
    path `models/<name>/` or `models/<file>` whole in the text. Sorted by name as strings. A
    missing `models` gives [].
    """
    if not models.is_dir():
        return []
    found = []
    for entry in by_name(models):
        if entry.is_dir():
            found.extend(judge_folder(entry, third_party))
        elif not holds_path(third_party, f"models/{entry.name}"):
            found.append(f"{entry.name}: not in THIRD_PARTY.md")
    return found


HASH = "7b1256fc0846e22d1af431eae299e2dcecee2778"
OTHER = "ac70130828d5a6811c2dc451e2255424c96f0eb0"


def make(models: Path, *paths: str) -> Path:
    """Make the folders (ending in /) and files given, under `models`; return `models`."""
    for path in paths:
        target = models / path
        if path.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"w")
    return models


def test_ec1_a_listed_revision(tmp_path: Path) -> None:
    assert unlisted(make(tmp_path, f"joint/{HASH}/model.bin"), f"| x | `{HASH}` |") == []


def test_ec2_a_revision_not_listed(tmp_path: Path) -> None:
    assert unlisted(make(tmp_path, f"large/{OTHER}/model.bin"), f"| x | `{HASH}` |") == [f"large/{OTHER}: not in THIRD_PARTY.md"]


def test_ec3_a_revision_that_is_not_a_commit_hash(tmp_path: Path) -> None:
    models = make(tmp_path, "joint/main/", "joint/7b1256f/", f"joint/{HASH}-old/")
    assert unlisted(models, f"main 7b1256f {HASH}-old") == ["joint/7b1256f: not pinned", f"joint/{HASH}-old: not pinned", "joint/main: not pinned"]


def test_ec4_loose_files_in_a_named_folder(tmp_path: Path) -> None:
    assert unlisted(make(tmp_path, "e2_onnx/ner.onnx"), "written to `models/e2_onnx/`") == []


def test_ec5_loose_files_in_a_folder_not_named(tmp_path: Path) -> None:
    assert unlisted(make(tmp_path, "e2_onnx/ner.onnx"), "written to `models/e2_onnx_run3/`") == ["e2_onnx: not in THIRD_PARTY.md"]
    assert unlisted(tmp_path, "the e2_onnx export") == ["e2_onnx: not in THIRD_PARTY.md"]


def test_ec6_a_file_at_the_top(tmp_path: Path) -> None:
    models = make(tmp_path, "stray.onnx", "named.onnx")
    assert unlisted(models, "`models/named.onnx`") == ["stray.onnx: not in THIRD_PARTY.md"]


def test_ec7_an_empty_name_folder(tmp_path: Path) -> None:
    assert unlisted(make(tmp_path, "empty/"), "") == []


def test_ec8_no_models_folder(tmp_path: Path) -> None:
    assert unlisted(tmp_path / "models", "") == []
    (tmp_path / "models").write_bytes(b"not a folder")
    assert unlisted(tmp_path / "models", "") == []


def test_ec9_this_machine() -> None:
    assert unlisted(ROOT / "models", (ROOT / "docs" / "THIRD_PARTY.md").read_text(encoding="utf-8")) == []


def test_b1_a_short_hash_in_the_file(tmp_path: Path) -> None:
    assert unlisted(make(tmp_path, f"joint/{HASH}/m"), HASH[:7]) == [f"joint/{HASH}: not in THIRD_PARTY.md"]


def test_b2_a_hash_in_capitals(tmp_path: Path) -> None:
    assert unlisted(make(tmp_path, f"joint/{HASH.upper()}/m"), HASH.upper()) == [f"joint/{HASH.upper()}: not pinned"]


def test_b3_revisions_and_loose_files_in_one_folder(tmp_path: Path) -> None:
    models = make(tmp_path, f"joint/{HASH}/m", "joint/extra.bin")
    assert unlisted(models, HASH) == ["joint: not in THIRD_PARTY.md"]
    assert unlisted(models, "`models/joint/`") == [f"joint/{HASH}: not in THIRD_PARTY.md"]


def test_a1_a_revision_named_like_a_word_of_the_file(tmp_path: Path) -> None:
    assert unlisted(make(tmp_path, "joint/Models/"), "Models main") == ["joint/Models: not pinned"]


def test_a2_a_hebrew_folder_not_named(tmp_path: Path) -> None:
    assert unlisted(make(tmp_path, "שמות/list.txt"), "") == ["שמות: not in THIRD_PARTY.md"]


def test_b4_names_that_differ_in_case_are_sorted_as_python_sorts(tmp_path: Path) -> None:
    models = make(tmp_path, "alpha/x.bin", "Zeta/x.bin", "joint/alpha/", "joint/Zeta/")
    assert unlisted(models, "") == [
        "Zeta: not in THIRD_PARTY.md",
        "alpha: not in THIRD_PARTY.md",
        "joint/Zeta: not pinned",
        "joint/alpha: not pinned",
    ]


def test_a3_a_hash_or_a_path_only_inside_longer_text(tmp_path: Path) -> None:
    sha = "e686ac235181498b9bef5c3f660db18e42c0120dc21e0a5cead5950c4151d760"
    models = make(tmp_path, f"x/{sha[:40]}/m", "e2")
    assert unlisted(models, f"SHA-256 `{sha}`; written to `models/e2_onnx/`") == [
        "e2: not in THIRD_PARTY.md",
        f"x/{sha[:40]}: not in THIRD_PARTY.md",
    ]
