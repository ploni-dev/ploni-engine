"""Download the pinned models, and write their rows of docs/THIRD_PARTY.md.

Why: build-plan.md Phase 0 asks for `scripts/download_models.py` "with pinned revisions, writing
`docs/THIRD_PARTY.md` with name, URL, revision hash and license per model" (issue #28). The pin
of each model is data in one place, MODELS; the table of the file is made from it, so the two
cannot drift apart. CLAUDE.md keeps downloads under scripts/ only.

Contract: `python scripts/download_models.py --rows` rewrites the table under `## Models` in
`docs/THIRD_PARTY.md` from MODELS, and touches nothing else in the file.
`python scripts/download_models.py <folder>` downloads the one model of that folder name into
`models/<folder>/<revision>/` and checks its weights against the pinned SHA-256. No argument,
or a name not in MODELS, is a usage error (exit 2).

Known limits:
- Every model download needs Achia's yes first (build-plan.md section 11). The script does not
  ask; whoever runs it with a model's name must have that yes.
- MODELS holds the four models of the experiments that are on the laptop. They were fetched by
  `scripts/download_e1_model.py` and `scripts/download_e5_models.py`, with the same files and
  pins; those two scripts stay, as the experiments cite them. A product model is added here
  when its phase comes, with Achia's yes.
- The list of given names of E5 (`alumag/hebrew-names`) is data from GitHub, not a model, and
  stays with `scripts/download_e5_models.py`.
- A download runs from the experiments' environment, where `huggingface_hub` is pinned
  (`experiments/e1_hebrew_recall/requirements.txt`); the project's `.venv` does not have it,
  and adding it to a requirements file is a new dependency, Achia's to decide.
- The license of each model is read by a person from the model's card at its commit and
  written into MODELS; the script does not read it.
"""

import argparse
import hashlib
import re
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
MODELS_ROOT = ROOT / "models"
THIRD_PARTY = ROOT / "docs" / "THIRD_PARTY.md"
# A pinned revision: a full commit of the hub repository, never a branch name.
COMMIT = re.compile(r"[0-9a-f]{40}")
HEADING = "## Models"
HEADER = "| Model | URL | Revision | License | License source | Used by | Shipped |\n|---|---|---|---|---|---|---|\n"


class Model(NamedTuple):
    """One pinned model: its source, its files, its row.

    Why: the pin, the files and the license of a model are read by the download and by the
    table of docs/THIRD_PARTY.md, so they live in one place.

    Contract: `folder` is the name under models/. `revision` is a full commit of `repo`.
    `allow`, when set, are the only files fetched; `ignore` are left out. `weights` is the
    weights file inside the snapshot and `sha256` its hash as the hub records it at that
    commit. The last four fields are the row's License, License source, Used by and Shipped.
    """

    folder: str
    repo: str
    revision: str
    allow: tuple[str, ...] | None
    ignore: tuple[str, ...]
    weights: str
    sha256: str
    license: str
    license_source: str
    used_by: str
    shipped: str


TOKENIZER_FILES = ("config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt", "README.md", "LICENSE")
WEIGHTS_AND_TOKENIZER = ("model.safetensors", *TOKENIZER_FILES)
E5_E6 = "`experiments/e5_methods/` and `experiments/e6_real_documents/` only"
# The pins, files and hashes are those of scripts/download_e1_model.py (dictabert-joint) and
# scripts/download_e5_models.py (the other three), and the rows those of docs/THIRD_PARTY.md
# as merged in #110; the hash of dictabert-joint's weights is the one that file records.
MODELS = (
    Model(
        "dictabert-joint",
        "dicta-il/dictabert-joint",
        "7b1256fc0846e22d1af431eae299e2dcecee2778",
        None,
        ("pytorch_model.bin", "*.py"),
        "model.safetensors",
        "c59db02c002b69fd3c072c310e3ba578d036386477248d1c8576d896cc06aa1c",
        "CC BY 4.0",
        "`license: cc-by-4.0` in the front matter of `README.md` at that revision",
        "`experiments/e1_hebrew_recall/`, `experiments/e3_prefix_replacement/`, `experiments/e2_int8_latency/`, "
        "`experiments/e4_planted_names/`, `experiments/e5_methods/` and `experiments/e6_real_documents/` only",
        "no",
    ),
    Model(
        "golem",
        "CordwainerSmith/GolemPII-v2-small",
        "fbaf0f7a9092c50c9ecc27e3d33ba1352ac40883",
        WEIGHTS_AND_TOKENIZER,
        (),
        "model.safetensors",
        "e94e31a5bbe17c4fbfbd12ef5ffef2ea16209f03975ce8e1bac876e3660f8c47",
        "MIT",
        "`license: mit` in the front matter of `README.md` at that revision, and its `LICENSE` file",
        E5_E6,
        "no",
    ),
    Model(
        "large",
        "dicta-il/dictabert-large-ner",
        "ac70130828d5a6811c2dc451e2255424c96f0eb0",
        WEIGHTS_AND_TOKENIZER,
        (),
        "model.safetensors",
        "763e556ec1c0dd676f48c9b306aec90bb11322f682f0c3d0de9574c01ba10272",
        "CC BY 4.0",
        "`license: cc-by-4.0` in the front matter of `README.md` at that revision",
        E5_E6,
        "no",
    ),
    Model(
        "seter_fast",
        "shoresh-labs/seter-pii-he-ar-fast",
        "2744c393718de9a911d9db3478341984a99a7cdb",
        WEIGHTS_AND_TOKENIZER,
        (),
        "model.safetensors",
        "803221b925bc4e7e4be590e08ea9795ef9104585cbbadbfd6078457801b06fe0",
        "MIT",
        "`license: mit` in the front matter of `README.md` at that revision",
        E5_E6,
        "no",
    ),
)


def url(model: Model) -> str:
    """Return the hub's page of the model's repository at its pinned commit.

    Why: the plan asks for a URL per model, and one that names the commit shows the files
    as they were pinned.

    Contract: "https://huggingface.co/<repo>/tree/<revision>".
    """
    return f"https://huggingface.co/{model.repo}/tree/{model.revision}"


def row(model: Model) -> str:
    """Return the model's row of the table, without a line end.

    Why: one row per model, its columns in the table's order.

    Contract: the repository and the revision in backquotes, the URL bare, the other fields
    as written. Raises ValueError when a field holds "|", which would split a cell.
    """
    cells = [f"`{model.repo}`", url(model), f"`{model.revision}`", model.license, model.license_source, model.used_by, model.shipped]
    if any("|" in cell for cell in cells):
        raise ValueError(f"{model.folder}: a field holds '|'")
    return "| " + " | ".join(cells) + " |"


def table(models: Sequence[Model]) -> str:
    """Return the whole table: header, rule line, one row per model.

    Why: the table is written whole, so it never holds a row of a model that is not in MODELS.

    Contract: each line ends in a line end; the models in the order given.
    """
    return HEADER + "".join(row(model) + "\n" for model in models)


def replace_table(text: str, new_table: str) -> str:
    """Return the text with the table under `## Models` replaced by `new_table`.

    Why: the rest of docs/THIRD_PARTY.md is written by hand and must not be touched.

    Contract: the table is the first run of lines that begin with "|" after the heading and
    before the next "## " heading. Raises ValueError when the heading, or a table in its
    section, is missing.
    """
    lines = text.splitlines(keepends=True)
    heading = next((i for i, line in enumerate(lines) if line.rstrip() == HEADING), None)
    if heading is None:
        raise ValueError(f"no {HEADING} heading")
    section_end = next((i for i in range(heading + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    start = next((i for i in range(heading + 1, section_end) if lines[i].startswith("|")), None)
    if start is None:
        raise ValueError(f"no table under {HEADING}")
    end = next((i for i in range(start, len(lines)) if not lines[i].startswith("|")), len(lines))
    return "".join(lines[:start]) + new_table + "".join(lines[end:])


def file_sha256(path: Path) -> str:
    """Return the hex SHA-256 of one file.

    Why: a commit pins the repository; the weights are checked as well against the hash the
    hub records, so that weights changed on disk are not trusted.

    Contract: reads in chunks; raises OSError when the file cannot be read.
    """
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def download(model: Model, fetch: Callable[..., Any] | None = None) -> Path:
    """Fetch one model at its pinned commit into models/<folder>/<revision>/; check its weights.

    Why: a pin by branch name would let the weights change between a measured run and the next.

    Contract: `fetch` is snapshot_download or a stand-in with its arguments; when it is None,
    huggingface_hub is imported here, as only a download needs it (ImportError when it is not
    installed). Sends no stored account token (`token=False`). Returns the folder. Raises
    ValueError, naming the folder, when the weights do not have the pinned hash; the hub's
    errors pass unchanged.

    Known limits: only the weights are checked; the tokenizer and config files are trusted as
    the hub serves them at the commit, and a re-run trusts files already present. A model with
    no `allow` (dictabert-joint) gets every file of its commit but those `ignore` names.
    """
    target = MODELS_ROOT / model.folder / model.revision
    if fetch is None:
        from huggingface_hub import snapshot_download as fetch
    fetch(
        model.repo,
        revision=model.revision,
        local_dir=target,
        token=False,
        allow_patterns=list(model.allow) if model.allow is not None else None,
        ignore_patterns=list(model.ignore),
    )
    found = file_sha256(target / model.weights)
    if found != model.sha256:
        raise ValueError(f"{model.folder}: the weights have SHA-256 {found}, not the pinned {model.sha256}")
    return target


def main(argv: Sequence[str]) -> int:
    """Rewrite the rows, or download one model; return the exit code.

    Why: the entry point of the script, given its arguments so that a test can call it.

    Contract: `--rows` or one folder name of MODELS. Raises SystemExit(2) for anything else,
    as argparse does.
    """
    by_folder = {model.folder: model for model in MODELS}
    parser = argparse.ArgumentParser(prog="download_models.py")
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--rows", action="store_true", help="rewrite the table of docs/THIRD_PARTY.md")
    choice.add_argument("model", nargs="?", choices=sorted(by_folder), help="download one model")
    arguments = parser.parse_args(argv)
    if arguments.rows:
        text = THIRD_PARTY.read_text(encoding="utf-8")
        THIRD_PARTY.write_text(replace_table(text, table(MODELS)), encoding="utf-8", newline="\n")
        return 0
    print(download(by_folder[arguments.model]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
