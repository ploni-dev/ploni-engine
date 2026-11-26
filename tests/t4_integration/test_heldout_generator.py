"""Module suite of the held-out batch's generator: its public surface, `build`, end to end.

Why: the unit tests check the parts of the batch one rule at a time. This suite checks the
batch as one thing that the scorer and a reader of the gate rely on: the key and the near misses
together cover every document, the counts are what the PR body reports, and a build twice in one
process, or after another seed's build, gives the same batch. Every assertion is on indexes,
counts or a digest, so a failure prints no text.

Test matrix:
  G1  the batch's documents, key and near misses fit together: every item's document exists
      and every document holds at least one item
  G2  a build of another seed between two builds of SEED changes nothing (no shared state)
  G3  every planted item is a whole word of its document: the characters on either side are
      not letters or digits glued to it, but for a Hebrew proclitic before it
  G4  each type has as many near misses as positives

Not applicable: the document-structure axes (plain text only, Phase 2 adds structure).
"""

from collections import Counter

from eval.heldout.generator import SEED, TYPES, build
from tests.heldout_oracles import digest

BATCH = build(SEED)


def test_g1_documents_and_items_fit_together() -> None:
    items = BATCH.key + BATCH.near_misses
    assert [index for index, item in enumerate(items) if not 0 <= item.doc < len(BATCH.documents)] == []
    assert sorted(set(range(len(BATCH.documents))) - {item.doc for item in items}) == []


def test_g2_no_state_is_shared_between_builds() -> None:
    first = digest(build(SEED))
    build(SEED + 7)
    same = digest(build(SEED)) == first
    assert same


def latin_or_digit(ch: str) -> bool:
    """Whether a character is an ASCII letter or digit."""
    return ch.isascii() and ch.isalnum()


def test_g3_every_item_is_a_whole_word() -> None:
    glued = []
    for index, item in enumerate(BATCH.key):
        text = BATCH.documents[item.doc]
        left = text[item.start - 1] if item.start else " "
        right = text[item.end] if item.end < len(text) else " "
        if latin_or_digit(left) or latin_or_digit(right) or (right.isalpha() and not right.isascii()):
            glued.append(index)
    assert glued == []


def test_g4_each_type_has_as_many_near_misses_as_positives() -> None:
    positives = Counter(item.type for item in BATCH.key)
    near = Counter(item.type for item in BATCH.near_misses)
    assert sorted(kind for kind in TYPES if positives[kind] != near[kind]) == []
