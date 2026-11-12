"""Test matrix for smoke.finds_people_only_where_named.

No model is loaded: the entity lists are written by hand.

  EC1  a PER span in the first sentence and none in the last -> True
  E1   no entity anywhere (a head that only says O, or a wrong label map) -> False
  E2   a PER span in the last sentence, which names nobody   -> False
  E3   the first sentence labelled, but never as PER         -> False
"""

from __future__ import annotations

import pytest

from smoke import SENTENCES, finds_people_only_where_named

NOTHING = [[] for _ in SENTENCES]


def with_entities(first: list, last: list) -> list[list[tuple[int, int, str]]]:
    return [first, *NOTHING[1:-1], last]


def test_ec1_names_found_where_they_are():
    assert finds_people_only_where_named(with_entities([(6, 18, "PER")], []))


@pytest.mark.parametrize(
    "per_sentence",
    [
        NOTHING,  # E1
        with_entities([(6, 18, "PER")], [(0, 3, "PER")]),  # E2
        with_entities([(6, 18, "ORG")], []),  # E3
    ],
)
def test_e1_e2_e3_wrong_reading_of_the_model(per_sentence):
    assert not finds_people_only_where_named(per_sentence)
