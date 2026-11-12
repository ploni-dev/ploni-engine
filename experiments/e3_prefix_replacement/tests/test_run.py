"""Test matrix for the weights guard in run.main.

No model is loaded: the hashes and the loader are stand-ins.

  E1   model.safetensors is not the pinned file -> the run exits, the model is
       never loaded, and no count is printed
  EC1  the pinned hash -> the loader is reached
"""

from pathlib import Path

import pytest

import run


class LoaderReached(Exception):
    """Raised by the stand-in loader, so the test stops where the model would load."""


def fake_hashes(weights: str):
    return lambda model_dir: {"model.safetensors": weights, "config.json": "c", "tokenizer.json": "t"}


def refuse_to_load(model_dir):
    raise LoaderReached


def test_e1_other_weights_stop_the_run_before_the_model_loads(monkeypatch, capsys):
    monkeypatch.setattr(run, "model_file_hashes", fake_hashes("0" * 64))
    monkeypatch.setattr(run, "load_ner_model", refuse_to_load)
    with pytest.raises(SystemExit) as stopped:
        run.main(Path("any-folder-name"))
    assert "not the pinned file" in str(stopped.value)
    assert "total" not in capsys.readouterr().out


def test_ec1_pinned_weights_reach_the_loader(monkeypatch):
    monkeypatch.setattr(run, "model_file_hashes", fake_hashes(run.PINNED_WEIGHTS_SHA256))
    monkeypatch.setattr(run, "load_ner_model", refuse_to_load)
    with pytest.raises(LoaderReached):
        run.main(Path("any-folder-name"))
