"""Download the candidate models of experiment E5, each at one pinned commit.

Why: `CLAUDE.md` allows downloads under scripts/ only and asks for every model revision to
be pinned by commit hash. E5 compares several models (`experiments/e5_methods/
PREREGISTRATION.md`); this file is the one place E5 touches the network, and the experiment
itself runs offline against the folders written here.

Contract: `python scripts/download_e5_models.py NAME [NAME ...]`, NAME a key of CANDIDATES.
For each, writes `models/<name>/<revision>/` under the repo root (gitignored), checks the
SHA-256 of the weights against the hash the hub recorded for the pinned commit, and prints
one `sha256  bytes  name` line per file. Raises ValueError when a hash is not the pinned
one, and whatever `huggingface_hub` raises on a network or revision error; nothing is
caught, so a partial download is never reported as a success.

The name `hebrew-names` fetches, in the same way, the given-name tables that the `list`
step of E5 uses, from a GitHub repository at a pinned commit, each file checked against
the id the commit records for it.

Known limits: the licence of each model is read by a person at the pinned commit and
written by hand, since issue #28 into MODELS of `scripts/download_models.py`, which writes
the table of `docs/THIRD_PARTY.md`; this script does not read it. A re-run trusts
files already present, but hashes them again.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path
from typing import NamedTuple

from huggingface_hub import snapshot_download

from download_e1_model import MODELS_ROOT, file_sha256, inventory_lines


class Candidate(NamedTuple):
    """One model of E5: where it comes from, which files are fetched, what the weights must be.

    Why: the pin of a candidate is data in one place, which `docs/THIRD_PARTY.md` and the
    pre-registration repeat and a reviewer can compare.

    Contract: `revision` is a full commit of the hub repository. `files` are the only files
    fetched: never a pickle of the weights and never Python of the model's own. `weights`
    is the path of the weights file inside the snapshot and `sha256` its hash, as the hub
    records it for that commit.
    """

    repo: str
    revision: str
    files: tuple[str, ...]
    weights: str
    sha256: str


TOKENIZER_FILES = ("config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt", "README.md", "LICENSE")
# Source of every revision and hash: `git ls-remote https://huggingface.co/<repo> refs/heads/main`
# and `https://huggingface.co/api/models/<repo>/revision/<commit>?blobs=true`, read on 2026-11-17.
CANDIDATES = {
    "golem": Candidate(
        "CordwainerSmith/GolemPII-v2-small",
        "fbaf0f7a9092c50c9ecc27e3d33ba1352ac40883",
        ("model.safetensors", *TOKENIZER_FILES),
        "model.safetensors",
        "e94e31a5bbe17c4fbfbd12ef5ffef2ea16209f03975ce8e1bac876e3660f8c47",
    ),
    "large": Candidate(
        "dicta-il/dictabert-large-ner",
        "ac70130828d5a6811c2dc451e2255424c96f0eb0",
        ("model.safetensors", *TOKENIZER_FILES),
        "model.safetensors",
        "763e556ec1c0dd676f48c9b306aec90bb11322f682f0c3d0de9574c01ba10272",
    ),
    "seter": Candidate(
        "shoresh-labs/seter-pii-he-ar",
        "280425059728cd9bba14a4c3c0cd1f57c5278c00",
        ("model.safetensors", *TOKENIZER_FILES),
        "model.safetensors",
        "7a0cad0c815b5da87eae9bc1edacbe2e0080e77430a50758cd3a1d9cbd38cbfc",
    ),
    "seter_fast": Candidate(
        "shoresh-labs/seter-pii-he-ar-fast",
        "2744c393718de9a911d9db3478341984a99a7cdb",
        ("model.safetensors", *TOKENIZER_FILES),
        "model.safetensors",
        "803221b925bc4e7e4be590e08ea9795ef9104585cbbadbfd6078457801b06fe0",
    ),
    "seter_fast_int8": Candidate(
        "shoresh-labs/seter-pii-he-ar-fast",
        "2744c393718de9a911d9db3478341984a99a7cdb",
        ("onnx/model_quantized.onnx", *TOKENIZER_FILES),
        "onnx/model_quantized.onnx",
        "386a7ee324ff74fe9bf372250e9986e133a95f97332f4ea4873b3ef3afefae4a",
    ),
}


# The given-name tables of a public project, for the `list` step. MIT, `LICENSE.txt` at the
# commit. Source of the commit and the blob ids: the GitHub API, `repos/<repo>/commits/HEAD`
# and `repos/<repo>/git/trees/<commit>?recursive=1`, read on 2026-11-17.
NAMES_LIST = "hebrew-names"
NAMES_REPO = "alumag/hebrew-names"
NAMES_COMMIT = "e9055afea4c4bd0bb8d55102d543ee106f26041c"
NAMES_FILES = {
    "hebrew_names/dist.christian.female.first": "8aef3d90d6121c1a6ab206981b9d4fbb04e1619c",
    "hebrew_names/dist.christian.male.first": "d33e18f6bdc65ff460e3711154692ff833a6f6de",
    "hebrew_names/dist.druze.female.first": "06d437c85caa2c3c644e6261302400ca2ff33684",
    "hebrew_names/dist.druze.male.first": "fa36e5046f1ad9acfa2435c0fe7f237e49c5df07",
    "hebrew_names/dist.jew.female.first": "7f638c1483b5159dc23721c1aaabcbdbd05e2f7a",
    "hebrew_names/dist.jew.male.first": "cc69094991f626161a2f14fa78d75a3de479e42e",
    "hebrew_names/dist.muslim.female.first": "b60d7f7527968c95109f6837b8f3be42e2691bbb",
    "hebrew_names/dist.muslim.male.first": "782d36b1fcfd988e988a81a5dca0c6265e5de920",
    "hebrew_names/dist.other.female.first": "ffa0d9e7972c7b92d18f808f0e1be0790e987814",
    "hebrew_names/dist.other.male.first": "4e67ba2817fbfb8936be472775aef5df80489ebf",
    "LICENSE.txt": "5fed2cefa61f365679d2480d3e76bdc9632055d0",
}


def snapshot_dir(name: str) -> Path:
    """Return the folder one candidate is stored in.

    Why: the revision is part of the path, so a second pin can never overwrite the files a
    recorded measurement was taken with.

    Contract: `name` is a key of CANDIDATES; KeyError otherwise. No I/O.
    """
    return MODELS_ROOT / name / CANDIDATES[name].revision


def download(name: str) -> Path:
    """Fetch one candidate at its pinned commit.

    Why: a pin by branch name would let the weights change between the run that was
    reported and the next one.

    Contract: fetches the files the candidate lists and no other, then checks the weights.
    Returns the snapshot folder. Sends no stored account token (`token=False`),
    so the request carries nothing that identifies the user. Raises ValueError when the
    weights do not have the pinned hash; `huggingface_hub` errors pass unchanged.
    """
    candidate = CANDIDATES[name]
    target = snapshot_dir(name)
    snapshot_download(candidate.repo, revision=candidate.revision, local_dir=target, token=False, allow_patterns=list(candidate.files))
    found = file_sha256(target / candidate.weights)
    if found != candidate.sha256:
        raise ValueError(f"{name}: the weights have sha256 {found}, not the pinned {candidate.sha256}")
    return target


def git_blob_id(data: bytes) -> str:
    """Return the id git gives a file with this content.

    Why: a file fetched from a GitHub repository is checked against the id that the
    repository's tree records for it at the pinned commit.

    Contract: the 40 lowercase hex characters of SHA-1 over "blob <length>\\0" and the bytes,
    as `git hash-object` gives them.
    """
    return hashlib.sha1(b"blob %d\x00" % len(data) + data, usedforsecurity=False).hexdigest()


def download_names_list() -> Path:
    """Fetch the given-name tables of NAMES_REPO at NAMES_COMMIT.

    Why: E5's `list` step needs a list of names that does not come from the corpora
    (`experiments/e5_methods/names_list.py`).

    Contract: returns the folder, `models/hebrew-names/<commit>/`, holding the ten tables
    and the project's licence file. Each file is checked against the id the pinned commit
    records for it; ValueError when one differs, before it is written. URL errors pass
    unchanged.
    """
    target = MODELS_ROOT / NAMES_LIST / NAMES_COMMIT
    target.mkdir(parents=True, exist_ok=True)
    for path, blob in NAMES_FILES.items():
        with urllib.request.urlopen(f"https://raw.githubusercontent.com/{NAMES_REPO}/{NAMES_COMMIT}/{path}", timeout=60) as reply:
            data = reply.read()
        if git_blob_id(data) != blob:
            raise ValueError(f"{path}: git blob {git_blob_id(data)}, not the pinned {blob}")
        (target / Path(path).name).write_bytes(data)
    return target


if __name__ == "__main__":
    if not sys.argv[1:]:
        # Nothing is fetched without a name: together the candidates are several gigabytes.
        sys.exit(f"name one or more of: {', '.join(sorted([*CANDIDATES, NAMES_LIST]))}")
    for wanted in sys.argv[1:]:
        if wanted == NAMES_LIST:
            print(f"{NAMES_LIST}: {NAMES_REPO} @ {NAMES_COMMIT}")
            print("\n".join(inventory_lines(download_names_list())))
            continue
        print(f"{wanted}: {CANDIDATES[wanted].repo} @ {CANDIDATES[wanted].revision}")
        print("\n".join(inventory_lines(download(wanted))))
