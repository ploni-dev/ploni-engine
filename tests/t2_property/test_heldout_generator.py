"""Property tests of the held-out batch's generator: the key's invariants hold for any seed.

Why: the unit tests check the batch of SEED. A rule that holds there by luck, a span that is
right only because no sentence happened to need a second try, would break the day the seed or
a table changes. So the invariants are checked over the batches of other seeds too, each with
about two thousand items: far more than the 500 generated cases CLAUDE.md asks of an invariant.
Every assertion is on indexes, type names, counts or a digest, so a failure prints no text.

Test matrix (each case: every item of the batches of SEEDS):
  I1  each item's span holds exactly its planted text, and start < end
  I2  no two items of one document overlap
  I3  every type has at least 40 positives and 40 near misses
  I4  the same seed gives the same batch (by digest), twice in one process
  I5  every positive passes the oracle of its type and every near miss fails it, all 22 types
      (tests/heldout_oracles.py, written from the plan)
  B1  the number of cases is at least 500

Not applicable: the Hebrew and document-structure axes, which the unit tests carry on the batch
of SEED; a property here is the same rule over more seeds.
"""

from collections import Counter

import pytest

from eval.heldout.generator import SEED, TYPES, build
from tests.heldout_oracles import digest, valid

# Five seeds other than SEED: about ten thousand items in all, five builds of the fast suite.
SEEDS = tuple(SEED + offset for offset in range(1, 6))
MINIMUM = 40
BATCHES = {seed: build(seed) for seed in SEEDS}


@pytest.mark.parametrize("seed", SEEDS)
def test_i1_spans_hold_their_text(seed: int) -> None:
    batch = BATCHES[seed]
    items = batch.key + batch.near_misses
    assert [index for index, item in enumerate(items) if not item.start < item.end or batch.documents[item.doc][item.start : item.end] != item.text] == []


@pytest.mark.parametrize("seed", SEEDS)
def test_i2_no_overlap(seed: int) -> None:
    batch = BATCHES[seed]
    spans = sorted((item.doc, item.start, item.end) for item in batch.key + batch.near_misses)
    assert [index for index in range(1, len(spans)) if spans[index][0] == spans[index - 1][0] and spans[index][1] < spans[index - 1][2]] == []


@pytest.mark.parametrize("seed", SEEDS)
def test_i3_every_type_reaches_the_minimum(seed: int) -> None:
    batch = BATCHES[seed]
    positives = Counter(item.type for item in batch.key)
    near = Counter(item.type for item in batch.near_misses)
    assert sorted(kind for kind in TYPES if positives[kind] < MINIMUM or near[kind] < MINIMUM) == []


@pytest.mark.parametrize("seed", SEEDS)
def test_i4_the_same_seed_gives_the_same_batch(seed: int) -> None:
    same = digest(build(seed)) == digest(BATCHES[seed])
    assert same


@pytest.mark.parametrize("seed", SEEDS)
def test_i5_every_item_meets_its_oracle(seed: int) -> None:
    batch = BATCHES[seed]
    assert sorted({item.type for item in batch.key if not valid(batch, item)}) == []
    assert sorted({item.type for item in batch.near_misses if valid(batch, item)}) == []


def test_b1_at_least_500_cases() -> None:
    # CLAUDE.md, Tests: an invariant is held over 500 generated cases.
    assert sum(len(batch.key) + len(batch.near_misses) for batch in BATCHES.values()) >= 500
