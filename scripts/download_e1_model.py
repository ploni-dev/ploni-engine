"""Download the model snapshot used by experiment E1, at one pinned commit.

Why: build-plan.md section 11 runs E1 before any product code exists, so the
Phase 0 `scripts/download_models.py` is not there yet, and CLAUDE.md allows
downloads under scripts/ only. This file is the one place E1 touches the
network; the experiment itself runs offline against the directory written here.

Contract: run as a script, no arguments. Writes
`models/dictabert-joint/<REVISION>/` under the repo root (gitignored) and prints
one `sha256  bytes  name` line per file. Raises whatever `huggingface_hub`
raises on a network or revision error; nothing is caught, so a partial download
is never reported as a success.

Known limits: no license capture and no docs/THIRD_PARTY.md regeneration. Since
issue #28 the row is written by `scripts/download_models.py --rows` from its MODELS,
which holds this model with the same pin and files; edit the row there, not by hand.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from huggingface_hub import snapshot_download

REPO_ID = "dicta-il/dictabert-joint"
# Source: `git ls-remote https://huggingface.co/dicta-il/dictabert-joint`,
# refs/heads/main on 2026-11-11.
REVISION = "7b1256fc0846e22d1af431eae299e2dcecee2778"
MODELS_ROOT = Path(__file__).resolve().parent.parent / "models"


def snapshot_dir() -> Path:
    """Return the directory the pinned snapshot is stored in.

    Why: the revision is part of the path so that a second pin can never
    silently overwrite the files a recorded measurement was taken with.

    Contract: no arguments, no I/O. Returns an absolute path that may not exist.
    """
    return MODELS_ROOT / "dictabert-joint" / REVISION


def download_snapshot() -> Path:
    """Fetch every file of REPO_ID at REVISION into `snapshot_dir()`.

    Why: the model ships executable Python beside its weights, and a pin by
    branch name would let that code change between a review and a run.

    Contract: returns the snapshot directory. Sends no stored account token
    (`token=False`), so the request carries nothing identifying the user.
    Raises `huggingface_hub` errors unchanged.

    Known limits: a re-run trusts files already present; delete the directory
    to force a clean fetch.
    """
    target = snapshot_dir()
    # Not fetched: the pickle copy of the weights, which is never loaded, and the
    # model's Python, which runs from the vendored copy in the experiment folder.
    snapshot_download(
        REPO_ID, revision=REVISION, local_dir=target, token=False, ignore_patterns=["pytorch_model.bin", "*.py"]
    )
    return target


def file_sha256(path: Path) -> str:
    """Return the hex SHA-256 of one file.

    Why: the findings note cites the exact weights a number was measured with,
    and a commit hash alone cannot be re-checked against files on disk.

    Contract: `path` must be a readable file. Reads in chunks, so a weights
    file larger than free memory is fine. Raises OSError if unreadable.
    """
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def inventory_lines(directory: Path) -> list[str]:
    """Describe every model file under `directory` as `sha256  bytes  name`.

    Why: this listing is the model inventory pasted into the findings note.

    Contract: returns lines sorted by relative path, with forward slashes.
    Skips the `.cache` folder the hub client writes its own bookkeeping into.
    """
    files = sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and ".cache" not in path.relative_to(directory).parts
    )
    return [
        f"{file_sha256(path)}  {path.stat().st_size:>10}  "
        f"{path.relative_to(directory).as_posix()}"
        for path in files
    ]


if __name__ == "__main__":
    print(f"{REPO_ID} @ {REVISION}")
    print("\n".join(inventory_lines(download_snapshot())))
