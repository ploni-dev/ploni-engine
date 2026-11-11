"""Test matrix for the vendored model code (vendored/dictabert_joint/).

  EC1  every vendored file has the SHA-256 that scripts/download_e1_model.py
       printed for the pinned commit, so the code that runs is the code that
       was read
  EC2  the model class run_model loads is defined in the vendored folder, not
       fetched from the hub and not read from the downloaded model folder
  A1   the vendored folder holds no Python file outside the pinned list
"""

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

import run_model

VENDORED = Path(run_model.__file__).resolve().parent / "vendored" / "dictabert_joint"
# dicta-il/dictabert-joint at 7b1256fc0846e22d1af431eae299e2dcecee2778.
PINNED_SHA256 = {
    "BertForJointParsing.py": "adff43130f5ab6a3c6c580c507f206709d4a51028db1a8eff2bbd92bcf244daa",
    "BertForMorphTagging.py": "f16fbd2a640194a07c3a52fd809000241746a19f491a7af6702f4eb86a2f7093",
    "BertForPrefixMarking.py": "6fed41e6041d824b4b5ed3b26ccf32b41ceb9b4ddaf1e961375064a2d0ded1d4",
    "BertForSyntaxParsing.py": "2aebe51bf2ca5f090e2e9347786a4b2c032517efd08ee379b5af790456fe2646",
}


@pytest.mark.parametrize(("name", "expected"), PINNED_SHA256.items())
def test_ec1_vendored_file_is_the_pinned_file(name: str, expected: str):
    assert hashlib.sha256((VENDORED / name).read_bytes()).hexdigest() == expected


def test_ec2_model_class_comes_from_the_vendored_folder():
    assert Path(inspect.getfile(run_model.BertForJointParsing)).parent == VENDORED


def test_a1_no_other_python_file_is_vendored():
    assert sorted(path.name for path in VENDORED.glob("*.py")) == sorted(PINNED_SHA256)
