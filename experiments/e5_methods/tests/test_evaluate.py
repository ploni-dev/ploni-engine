"""Test matrix for evaluate and data.

One hand-made document unless a case says otherwise:
  paragraph 0  `מר יעקב כהן חתם.`     gold: the full name, person A
  paragraph 1  `כהן הלך אל משפחת לוי.` gold: `כהן` (A, surname), `לוי` (B, a group word before it)
So A is named twice and B once, but B is named as a group and is not "lonely".

chosen
  EC1  no threshold                    the rows the model chose
  EC2  a threshold                     the rows at or over it, chosen or not
  B1   a chance equal to the threshold taken

whole_words
  EC3  a span of half a word           the whole word
  EC4  a span over two words           both words, one span each
  EC5  two spans in one word           the word once
  EC6  a span in another paragraph     only that paragraph's word

grid
  EC7  one detector without chances    itself, whole words, every stack without the list
  EC8  a detector with chances         also every threshold, alone and with the main stack
  EC9  two detectors                   one union; three: three pairs and all three
  EC10 a list was given                the stacks with the list step are there

marked
  EC11 two detectors                   what either marks
  EC12 steps in order                  each works on what the one before left

extra_words
  EC13 a word in no planted name       extra, and extra without titles
  EC14 a title                         extra, not in the second number
  EC15 a word of a planted name        marked, not extra
  B2   nothing marked                  three zeros

rows_of / measure / pooled / table
  EC16 everything found                all 3/3, group 1/1, the kind 3/3
  EC17 the group name missed           all 2/3, group 0/1, one missed mention
  EC18 pooled over two results         counts and seconds added, memory the largest
  EC19 the table                       best recall first; fewer extra words breaks a tie

data
  EC20 the three corpora               the sizes the pre-registration names
  EC21 lonely                          a person named once, never a group mention
  EC22 the seed                        put back after a load; two loads give the same text
"""

import generate
import pytest

import data
import evaluate

PARAGRAPHS = ["מר יעקב כהן חתם.", "כהן הלך אל משפחת לוי."]


def gold(paragraph: int, name: str, person: str, form: str) -> generate.Gold:
    """Build one planted name at the place it stands in PARAGRAPHS."""
    start = PARAGRAPHS[paragraph].index(name)
    return generate.Gold(paragraph, start, start + len(name), name, person, form, "", False, frozenset(), True)


DOCUMENT = generate.Document(
    "doc01", "hand", "letter", 1, PARAGRAPHS,
    [gold(0, "יעקב כהן", "A", "title_full"), gold(1, "כהן", "A", "surname"), gold(1, "לוי", "B", "group_family")],
)  # fmt: skip
FULL = (0, 3, 11)
SURNAME = (1, 0, 3)
GROUP = (1, PARAGRAPHS[1].index("לוי"), PARAGRAPHS[1].index("לוי") + 3)


def run(*spans: tuple[int, int, int], seconds: float = 1.0, peak: int = 100) -> dict:
    """Build the file of a detector that marks the given spans, as certain."""
    rows = [[*span, 1.0, 1] for span in spans]
    return {"model": "m", "hashes": {}, "seconds": seconds, "peak_mb": peak, "tokens": {"doc01": rows}}


def method(*detectors: str, steps: tuple[str, ...] = (), threshold: float | None = None, words: bool = True) -> evaluate.Method:
    """Build a method over the named detectors."""
    return evaluate.Method("m", detectors, threshold, words, steps)


def test_ec1_ec2_b1_chosen() -> None:
    rows = [[0, 0, 2, 0.9, 1], [0, 3, 5, 0.3, 0], [0, 6, 8, 0.05, 0], [1, 0, 2, 0.4, 1]]
    assert evaluate.chosen(rows, None) == [(0, 0, 2), (1, 0, 2)]
    assert evaluate.chosen(rows, 0.3) == [(0, 0, 2), (0, 3, 5), (1, 0, 2)]
    assert evaluate.chosen(rows, 0.5) == [(0, 0, 2)]


def test_ec3_to_ec6_whole_words() -> None:
    paragraphs = ["יעקב כהן חתם", "כהן הלך"]
    assert evaluate.whole_words(paragraphs, [(0, 1, 2)]) == [(0, 0, 4)]
    assert evaluate.whole_words(paragraphs, [(0, 2, 6)]) == [(0, 0, 4), (0, 5, 8)]
    assert evaluate.whole_words(paragraphs, [(0, 0, 1), (0, 2, 3)]) == [(0, 0, 4)]
    assert evaluate.whole_words(paragraphs, [(1, 0, 1)]) == [(1, 0, 3)]
    assert evaluate.whole_words(paragraphs, []) == []


def test_ec7_ec8_grid_for_one_detector() -> None:
    plain = [item.name for item in evaluate.grid(["a"], set(), has_list=False)]
    assert plain[:2] == ["a", "a + whole words"]
    assert "a + titles, carry" in plain
    assert not any("list" in name or " at " in name for name in plain)
    with_chance = [item.name for item in evaluate.grid(["a"], {"a"}, has_list=False)]
    assert [name for name in with_chance if " at " in name] == [
        text for threshold in evaluate.THRESHOLDS for text in (f"a at {threshold}", f"a at {threshold} + titles, carry")
    ]


def test_ec9_ec10_grid_unions_and_the_list() -> None:
    two = [item for item in evaluate.grid(["a", "b"], set(), has_list=True) if len(item.detectors) > 1]
    assert [item.name for item in two] == ["a or b", "a or b + titles, carry"]
    three = {item.detectors for item in evaluate.grid(["a", "b", "c"], set(), has_list=False) if len(item.detectors) > 1}
    assert three == {("a", "b"), ("a", "c"), ("b", "c"), ("a", "b", "c")}
    assert any(item.steps == ("list",) for item in evaluate.grid(["a"], set(), has_list=True))
    assert [item.name for item in evaluate.grid(["a", "b"], {"a"}, has_list=True) if not item.whole_words] == ["a", "b"]


def test_ec11_ec12_marked() -> None:
    runs = {"a": run(FULL), "b": run(SURNAME)}
    steps = evaluate.step_table(frozenset())
    assert evaluate.marked(method("a", "b", words=False), DOCUMENT, runs, steps) == [FULL, SURNAME]
    # `carry` works on what `group` left: the group name is found by the first step only.
    stacked = evaluate.marked(method("a", steps=("group", "carry")), DOCUMENT, runs, steps)
    assert GROUP in stacked
    assert SURNAME in stacked
    assert GROUP not in evaluate.marked(method("a", steps=("carry",)), DOCUMENT, runs, steps)


def test_ec13_to_b2_extra_words() -> None:
    title = (0, 0, 2)
    plain_word = (0, 12, 15)
    assert evaluate.extra_words(DOCUMENT, []) == (0, 0, 0)
    assert evaluate.extra_words(DOCUMENT, [FULL]) == (0, 0, 2)
    assert evaluate.extra_words(DOCUMENT, [FULL, title]) == (1, 0, 3)
    assert evaluate.extra_words(DOCUMENT, [FULL, title, plain_word]) == (2, 1, 4)


def test_ec16_ec17_measure() -> None:
    steps = evaluate.step_table(frozenset())
    everything = evaluate.measure(method("a"), [DOCUMENT], {"a": run(FULL, SURNAME, GROUP)}, steps)
    assert everything["rows"] == {"all": [3, 3], "letter": [3, 3], "group": [1, 1]}
    assert everything["missed"] == []
    assert (everything["extra"], everything["marked"], everything["words"]) == (0, 4, 9)
    without = evaluate.measure(method("a"), [DOCUMENT], {"a": run(FULL, SURNAME, seconds=2.0, peak=300)}, steps)
    assert without["rows"] == {"all": [2, 3], "letter": [2, 3], "group": [0, 1]}
    assert [item.gold.name for _, item in without["missed"]] == ["לוי"]
    assert without["seconds"] >= 2.0
    assert without["peak_mb"] == 300


def test_ec18_pooled() -> None:
    steps = evaluate.step_table(frozenset())
    one = evaluate.measure(method("a"), [DOCUMENT], {"a": run(FULL, SURNAME, GROUP, seconds=1.0, peak=100)}, steps)
    two = evaluate.measure(method("a"), [DOCUMENT], {"a": run(FULL, seconds=2.0, peak=300)}, steps)
    both = evaluate.pooled([one, two])
    assert both["rows"]["all"] == [4, 6]
    assert both["rows"]["group"] == [1, 2]
    assert both["peak_mb"] == 300
    assert both["seconds"] == pytest.approx(one["seconds"] + two["seconds"], abs=0.11)
    assert len(both["missed"]) == 2
    assert both["words"] == 18


def test_ec19_the_table_puts_the_best_first() -> None:
    def result(found: int, extra: int) -> dict:
        return {"rows": {"all": [found, 3]}, "extra": extra, "extra_no_title": extra, "marked": 4, "words": 9, "seconds": 1.0, "peak_mb": 1}

    lines = evaluate.table("t", {"worse": result(2, 0), "noisy": result(3, 2), "clean": result(3, 0)}).splitlines()
    assert [line.split(" | ")[0].removeprefix("| ") for line in lines[4:]] == ["clean", "noisy", "worse"]
    assert "100.00%" in lines[4]
    assert "66.67%" in lines[6]


def test_ec20_the_three_corpora_have_the_sizes_the_pre_registration_names() -> None:
    sizes = {}
    for name in data.DATASETS:
        documents = data.load(name)
        counted = sum(item.counted for document in documents for item in document.gold)
        sizes[name] = (len(documents), counted, sum(len(data.lonely(document)) for document in documents))
    assert sizes["e4"][:2] == (40, 1145)
    assert sizes["select"] == (20, 450, 55)
    assert sizes["heldout"] == (20, 425, 55)


def test_ec21_lonely() -> None:
    assert data.lonely(DOCUMENT) == set()
    once = DOCUMENT._replace(gold=[DOCUMENT.gold[0], DOCUMENT.gold[2]])
    assert data.lonely(once) == {0}


def test_ec22_the_seed_is_put_back() -> None:
    before = generate.SEED
    first = data.load("select")
    assert generate.SEED == before
    assert [document.paragraphs for document in data.load("select")] == [document.paragraphs for document in first]
    assert [document.paragraphs for document in data.load("heldout")] != [document.paragraphs for document in first]
