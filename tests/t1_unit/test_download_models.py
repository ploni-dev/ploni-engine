"""Tests of scripts/download_models.py: the pinned models and the rows of docs/THIRD_PARTY.md.

Why: build-plan.md Phase 0 asks for `scripts/download_models.py` "with pinned revisions,
writing `docs/THIRD_PARTY.md` with name, URL, revision hash and license per model" (issue #28).
The pins are data a reviewer compares with the hub; the rows must stay what the data says.

Test matrix:

Equivalence classes:
  EC1  url()                           the hub's page of the repository at the pinned commit
  EC2  row()                           every column, in the table's order, values in backquotes
                                       where they are names
  EC3  table()                         the header, the line under it, one row per model in order
  EC4  replace_table()                 the table under `## Models` replaced; text before and
                                       after unchanged
  EC5  the repository                  the table of docs/THIRD_PARTY.md is table(MODELS)
  EC6  the pins of MODELS              a full lowercase commit for each revision, a SHA-256 for
                                       each weights file, folders unique, a license for each;
                                       each weights hash one that docs/THIRD_PARTY.md records
  EC7  download(), weights as pinned   fetch called once with the repository, the revision, the
                                       folder models/<folder>/<revision>, no token, the file
                                       filter; returns the folder
  EC8  main()                          `--rows` rewrites the table; a model's folder name
                                       downloads that model; no argument or an unknown name is a
                                       usage error (exit 2)

Boundaries:
  B1  a model with `allow` (only those files) and one with `ignore` (all but those)
  B2  replace_table() on a file whose table is the last thing in it
  B3  a model with an empty `allow`    fetches no file, not every file

Error paths:
  E1  download() whose weights do not have the pinned hash    ValueError, naming the folder
  E2  replace_table() with no `## Models` heading, or the heading and no table before the next
      `## ` heading (whose table must not be taken)    ValueError
  E3  row() with a `|` in a value                              ValueError: it would split the cell

Adversarial:
  A1  a GLiNER v0 or v1 checkpoint (CC-BY-NC, CLAUDE.md) in MODELS    none there
  A2  a pin by branch name ("main") in MODELS                           none there (EC6)
  A3  a model whose filter lets a pickle or the model's own Python through, or whose allow list
      has a wildcard    none there

Not applicable: the Hebrew axes and the document axes: the input is the pins and one table of
a Markdown file.

Known limits:
  - No test touches the network: download() is called with a stand-in for the hub's fetch.
"""

from pathlib import Path

import pytest

from scripts import download_models as dm

ROOT = Path(__file__).resolve().parents[2]
THIRD_PARTY = ROOT / "docs" / "THIRD_PARTY.md"
JOINT = dm.MODELS[0]
HEADER = "| Model | URL | Revision | License | License source | Used by | Shipped |\n|---|---|---|---|---|---|---|\n"


def test_ec1_url() -> None:
    assert dm.url(JOINT) == "https://huggingface.co/dicta-il/dictabert-joint/tree/7b1256fc0846e22d1af431eae299e2dcecee2778"


def test_ec2_row() -> None:
    model = JOINT._replace(license="CC BY 4.0", license_source="the README", used_by="E1 only", shipped="no")
    assert dm.row(model) == (
        "| `dicta-il/dictabert-joint` | https://huggingface.co/dicta-il/dictabert-joint/tree/7b1256fc0846e22d1af431eae299e2dcecee2778"
        " | `7b1256fc0846e22d1af431eae299e2dcecee2778` | CC BY 4.0 | the README | E1 only | no |"
    )


def test_ec3_table() -> None:
    text = dm.table(dm.MODELS[:2])
    assert text == HEADER + dm.row(dm.MODELS[0]) + "\n" + dm.row(dm.MODELS[1]) + "\n"


def test_ec4_replace_table() -> None:
    text = "# T\n\n## Models\n\n| A |\n|---|\n| 1 |\n\nAfter.\n"
    assert dm.replace_table(text, "| B |\n|---|\n") == "# T\n\n## Models\n\n| B |\n|---|\n\nAfter.\n"


def test_ec5_the_repository() -> None:
    assert dm.table(dm.MODELS) in THIRD_PARTY.read_text(encoding="utf-8")


def test_ec6_the_pins() -> None:
    assert len({model.folder for model in dm.MODELS}) == len(dm.MODELS)
    for model in dm.MODELS:
        assert dm.COMMIT.fullmatch(model.revision), model.folder
        assert len(model.sha256) == 64 and all(c in "0123456789abcdef" for c in model.sha256), model.folder
        assert model.license and model.license_source and model.weights, model.folder


def fake_fetch(calls: list[dict[str, object]], weights: bytes):  # type: ignore[no-untyped-def]
    """A stand-in for huggingface_hub.snapshot_download that writes one weights file."""

    def fetch(repo: str, **kwargs: object) -> str:
        calls.append({"repo": repo, **kwargs})
        folder = Path(str(kwargs["local_dir"]))
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "model.safetensors").write_bytes(weights)
        return str(folder)

    return fetch


def test_ec7_download_with_the_pinned_weights(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    model = JOINT._replace(sha256="2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")
    monkeypatch.setattr(dm, "MODELS_ROOT", tmp_path)
    folder = dm.download(model, fake_fetch(calls, b"hello"))
    assert folder == tmp_path / model.folder / model.revision
    assert calls == [{"repo": model.repo, "revision": model.revision, "local_dir": folder, "token": False, "allow_patterns": None, "ignore_patterns": list(model.ignore)}]


def test_b1_allow_and_ignore(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert JOINT.allow is None and JOINT.ignore
    golem = next(model for model in dm.MODELS if model.allow)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(dm, "MODELS_ROOT", tmp_path)
    with pytest.raises(ValueError):
        dm.download(golem, fake_fetch(calls, b"x"))
    assert calls[0]["allow_patterns"] == list(golem.allow or ()) and calls[0]["ignore_patterns"] == list(golem.ignore)


def test_b2_a_table_at_the_end() -> None:
    assert dm.replace_table("## Models\n\n| A |\n|---|\n", "| B |\n") == "## Models\n\n| B |\n"


def test_e1_weights_with_another_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dm, "MODELS_ROOT", tmp_path)
    with pytest.raises(ValueError, match=JOINT.folder):
        dm.download(JOINT, fake_fetch([], b"not the weights"))


def test_e2_no_models_table() -> None:
    with pytest.raises(ValueError):
        dm.replace_table("# T\n\nNo table.\n", "| B |\n")
    with pytest.raises(ValueError):
        dm.replace_table("## Models\n\nNo table yet.\n", "| B |\n")
    with pytest.raises(ValueError):
        dm.replace_table("## Models\n\nNo table.\n\n## Other\n\n| X |\n|---|\n", "| B |\n")


def test_e3_a_bar_in_a_value() -> None:
    with pytest.raises(ValueError):
        dm.row(JOINT._replace(used_by="E1 | E2"))


def test_ec8_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    copy = tmp_path / "THIRD_PARTY.md"
    copy.write_text("## Models\n\n| old |\n|---|\n\nAfter.\n", encoding="utf-8")
    monkeypatch.setattr(dm, "THIRD_PARTY", copy)
    assert dm.main(["--rows"]) == 0
    assert copy.read_text(encoding="utf-8") == "## Models\n\n" + dm.table(dm.MODELS) + "\nAfter.\n"
    fetched: list[str] = []
    monkeypatch.setattr(dm, "download", lambda model, fetch=None: fetched.append(model.folder))
    assert dm.main([JOINT.folder]) == 0 and fetched == [JOINT.folder]
    with pytest.raises(SystemExit) as no_argument:
        dm.main([])
    with pytest.raises(SystemExit) as unknown:
        dm.main(["gliner_multi"])
    assert no_argument.value.code == 2 and unknown.value.code == 2


def gliner_not_allowed(repo: str) -> bool:
    """Say whether a repository is a GLiNER checkpoint that CLAUDE.md does not allow.

    CLAUDE.md: "GLiNER v0 and v1 checkpoints are CC-BY-NC and unusable here. Only v2.1 and PII
    variants."
    """
    name = repo.lower()
    return name.startswith("urchade/gliner") and "v2.1" not in name and "pii" not in name


def test_a1_no_gliner_v0_or_v1() -> None:
    names = ("urchade/gliner_multi", "urchade/gliner_base", "urchade/gliner_multi-v2.1", "urchade/gliner_multi_pii-v1")
    assert [gliner_not_allowed(repo) for repo in names] == [True, True, False, False]
    assert not [model.repo for model in dm.MODELS if gliner_not_allowed(model.repo)]


def test_ec6_the_hashes_are_those_the_record_holds() -> None:
    text = THIRD_PARTY.read_text(encoding="utf-8")
    assert [model.folder for model in dm.MODELS if model.sha256 not in text] == []


def test_a3_no_model_fetches_a_pickle_or_python() -> None:
    for model in dm.MODELS:
        if model.allow is not None:
            pickles = (".py", ".bin", ".pkl", ".pickle", ".pt", ".pth", ".ckpt")
            assert not [pattern for pattern in model.allow if pattern.endswith(pickles) or any(c in pattern for c in "*?[")], model.folder
        else:
            assert {"*.py", "pytorch_model.bin"} <= set(model.ignore), model.folder


def test_b3_an_empty_allow_fetches_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(dm, "MODELS_ROOT", tmp_path)
    with pytest.raises(ValueError):
        dm.download(JOINT._replace(allow=()), fake_fetch(calls, b"x"))
    assert calls[0]["allow_patterns"] == []
