"""Test matrix for evaluate and data.

One hand-made document unless a case says otherwise:
  paragraph 0  `מר יעקב כהן חתם.`     gold: the full name, person A, with a title
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

step_table and STACKS
  EC23 every key of the table          gives what the function of that name in layers gives
  EC24 every stack                     is made of the keys its name says

marked
  EC11 two detectors                   what either marks
  EC12 steps in order                  each works on what the one before left: a name that only
                                       the group step found is carried when carry comes after
                                       it, and not when carry comes before
  EC25 whole words off and on          the token as it is; the whole word
  EC26 a threshold                     takes a token the model did not choose; none without it

extra_words
  EC13 a word in no planted name       extra, and extra without titles
  EC14 a title                         extra, not in the second number
  EC15 a word of a planted name        marked, not extra
  B2   nothing marked                  three zeros

rows_of / measure / pooled / table
  EC16 everything found                all 3/3, group 1/1, no_trigger 1/1, the kind 3/3
  EC17 the group name missed           all 2/3, group 0/1, one missed mention
  EC27 half a name marked              not found: E4's strict rule
  EC28 a person named once, an Arabic name    in the rows `lonely` and `arabic`
  EC29 two detectors                   their seconds added, the larger memory
  EC18 pooled over two results         counts and seconds added, memory the largest
  EC19 the table                       best recall first; then fewer extra words; then fewer
                                       seconds; then the name

load_runs / check_request / evaluate / record_lines / read_name_list
  EC30 run files of two detectors on a real corpus    scored; a detector not run on every
                                       corpus is left out and named
  E1   a file made on another corpus, or on another text    ValueError that names the file
  E2   the held-out corpus with another corpus, or without named methods    ValueError
  EC31 the held-out corpus by itself with named methods    allowed
  EC32 a record line                   the corpus, the method, its detectors with model and
                                       hashes; the list's label only for a method that uses it
  EC33 a list of names                 its names, and a label with file name, count and hash

data
  EC20 the three corpora               the sizes the pre-registration names
  EC21 lonely                          a person named once, never a group mention
  EC22 the seed                        put back after a load; two loads give the same text
  EC34 the digest                      the same on every run; pinned for the three corpora;
                                       another text gives another digest
"""

import hashlib
import json
from pathlib import Path

import generate
import pytest

import data
import evaluate
import layers

PARAGRAPHS = ["מר יעקב כהן חתם.", "כהן הלך אל משפחת לוי."]
# The digests of the three corpora as they were when the pre-registration was amended.
DIGESTS = {
    "e4": "4693fae9b1c502bc01c4cca43ba0104b983ce662cb8dd845da447822c75617f2",
    "select": "7485e877ca8135c80b12765c6f7557498b1d624d02bfc52967c5f9e2aaff32f2",
    "heldout": "65bb3866dc7a8eb43d7424ac7891a4852d1a921e11fc9bccfff34977e7895714",
}


def gold(paragraph: int, name: str, person: str, form: str, classes: frozenset[str] = frozenset(), paragraphs: list[str] = PARAGRAPHS) -> generate.Gold:
    """Build one planted name at the place it stands in the paragraphs."""
    start = paragraphs[paragraph].index(name)
    return generate.Gold(paragraph, start, start + len(name), name, person, form, "", False, classes, True)


DOCUMENT = generate.Document(
    "doc01", "hand", "letter", 1, PARAGRAPHS,
    [gold(0, "יעקב כהן", "A", "title_full"), gold(1, "כהן", "A", "surname"), gold(1, "לוי", "B", "group_family")],
)  # fmt: skip
FULL = (0, 3, 11)
SURNAME = (1, 0, 3)
GROUP = (1, PARAGRAPHS[1].index("לוי"), PARAGRAPHS[1].index("לוי") + 3)


def run(*spans: tuple[int, int, int], seconds: float = 1.0, peak: int = 100, chance: float = 1.0, chosen: int = 1) -> dict:
    """Build the file of a detector that marks the given spans."""
    rows = [[*span, chance, chosen] for span in spans]
    return {"model": "m", "hashes": {"model.safetensors": "abc"}, "seconds": seconds, "peak_mb": peak, "tokens": {"doc01": rows}}


def method(*detectors: str, steps: tuple[str, ...] = (), threshold: float | None = None, words: bool = True) -> evaluate.Method:
    """Build a method over the named detectors."""
    return evaluate.Method("m", detectors, threshold, words, steps)


STEPS = evaluate.step_table(frozenset())


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
    with_chance = [item for item in evaluate.grid(["a"], {"a"}, has_list=False) if " at " in item.name]
    assert [item.name for item in with_chance] == [
        text for threshold in evaluate.THRESHOLDS for text in (f"a at {threshold}", f"a at {threshold} + titles, carry")
    ]
    assert [item.threshold for item in with_chance] == [threshold for threshold in evaluate.THRESHOLDS for _ in range(2)]
    assert [item.steps for item in with_chance][:2] == [(), ("titles", "carry")]


def test_ec9_ec10_grid_unions_and_the_list() -> None:
    two = [item for item in evaluate.grid(["a", "b"], set(), has_list=True) if len(item.detectors) > 1]
    assert [item.name for item in two] == ["a or b", "a or b + titles, carry"]
    assert [item.steps for item in two] == [(), ("titles", "carry")]
    three = {item.detectors for item in evaluate.grid(["a", "b", "c"], set(), has_list=False) if len(item.detectors) > 1}
    assert three == {("a", "b"), ("a", "c"), ("b", "c"), ("a", "b", "c")}
    assert any(item.steps == ("list",) for item in evaluate.grid(["a"], set(), has_list=True))
    assert [item.name for item in evaluate.grid(["a", "b"], {"a"}, has_list=True) if not item.whole_words] == ["a", "b"]


def test_ec23_every_key_of_the_step_table_runs_the_function_of_its_name() -> None:
    names = frozenset({"הלך"})
    steps = evaluate.step_table(names)
    spans = [FULL]
    assert steps["group"](PARAGRAPHS, spans) == layers.after_triggers(PARAGRAPHS, spans) == [GROUP]
    with_titles = [(0, 3, 7), GROUP]
    assert steps["titles"](PARAGRAPHS, []) == layers.after_triggers(PARAGRAPHS, [], titles=True) == with_titles
    assert steps["carry"](PARAGRAPHS, spans) == layers.propagate(PARAGRAPHS, spans) == [SURNAME]
    # One word marked once is carried by `carry` and not by `carry strong`.
    assert steps["carry"](PARAGRAPHS, [(0, 8, 11)]) == [SURNAME]
    assert steps["carry_strong"](PARAGRAPHS, [(0, 8, 11)]) == layers.propagate(PARAGRAPHS, [(0, 8, 11)], strong=True) == []
    assert steps["list"](PARAGRAPHS, spans) == layers.from_list(PARAGRAPHS, spans, names) == [(1, 4, 7)]
    assert set(steps) == {"group", "titles", "carry", "carry_strong", "list"}


def test_ec24_every_stack_is_made_of_the_steps_its_name_says() -> None:
    assert evaluate.STACKS == {
        "group": ("group",),
        "titles": ("titles",),
        "carry": ("carry",),
        "carry strong": ("carry_strong",),
        "list": ("list",),
        "titles, carry": ("titles", "carry"),
        "titles, carry strong": ("titles", "carry_strong"),
        "titles, list, carry": ("titles", "list", "carry"),
    }
    assert evaluate.STACKS[evaluate.MAIN_STACK] == ("titles", "carry")


def test_ec11_two_detectors() -> None:
    runs = {"a": run(FULL), "b": run(SURNAME)}
    assert evaluate.marked(method("a", "b", words=False), DOCUMENT, runs, STEPS) == [FULL, SURNAME]


def test_ec12_each_step_works_on_what_the_one_before_left() -> None:
    paragraphs = ["משפחת לוי באה.", "אחר כך לוי הלך."]
    document = generate.Document("doc01", "hand", "letter", 1, paragraphs, [])
    runs = {"a": run()}
    after_group, later = (0, 6, 9), (1, 7, 10)
    assert evaluate.marked(method("a", steps=("group", "carry")), document, runs, STEPS) == [after_group, later]
    assert evaluate.marked(method("a", steps=("carry", "group")), document, runs, STEPS) == [after_group]


def test_ec25_whole_words_off_and_on() -> None:
    runs = {"a": run((0, 4, 6))}
    assert evaluate.marked(method("a", words=False), DOCUMENT, runs, STEPS) == [(0, 4, 6)]
    assert evaluate.marked(method("a", words=True), DOCUMENT, runs, STEPS) == [(0, 3, 7)]


def test_ec26_a_threshold_takes_a_token_the_model_did_not_choose() -> None:
    runs = {"a": run((0, 3, 7), chance=0.2, chosen=0)}
    assert evaluate.marked(method("a"), DOCUMENT, runs, STEPS) == []
    assert evaluate.marked(method("a", threshold=0.1), DOCUMENT, runs, STEPS) == [(0, 3, 7)]
    assert evaluate.marked(method("a", threshold=0.3), DOCUMENT, runs, STEPS) == []


def test_ec13_to_b2_extra_words() -> None:
    title = (0, 0, 2)
    plain_word = (0, 12, 15)
    assert evaluate.extra_words(DOCUMENT, []) == (0, 0, 0)
    assert evaluate.extra_words(DOCUMENT, [FULL]) == (0, 0, 2)
    assert evaluate.extra_words(DOCUMENT, [FULL, title]) == (1, 0, 3)
    assert evaluate.extra_words(DOCUMENT, [FULL, title, plain_word]) == (2, 1, 4)


def test_ec16_ec17_measure() -> None:
    everything = evaluate.measure(method("a"), [DOCUMENT], {"a": run(FULL, SURNAME, GROUP)}, STEPS)
    assert everything["rows"] == {"all": [3, 3], "letter": [3, 3], "group": [1, 1], "no_trigger": [1, 1]}
    assert everything["missed"] == []
    assert (everything["extra"], everything["marked"], everything["words"]) == (0, 4, 9)
    without = evaluate.measure(method("a"), [DOCUMENT], {"a": run(FULL, SURNAME, seconds=2.0, peak=300)}, STEPS)
    assert without["rows"] == {"all": [2, 3], "letter": [2, 3], "group": [0, 1], "no_trigger": [1, 1]}
    assert [item.gold.name for _, item in without["missed"]] == ["לוי"]
    assert 2.0 <= without["seconds"] < 3.0
    assert without["peak_mb"] == 300


def test_ec27_half_a_name_marked_is_not_found() -> None:
    half = evaluate.measure(method("a", words=False), [DOCUMENT], {"a": run((0, 3, 7), SURNAME)}, STEPS)
    assert half["rows"]["all"] == [1, 3]
    assert [(item.gold.name, item.verdict) for _, item in half["missed"]] == [("יעקב כהן", "partial"), ("לוי", "missed")]


def test_ec28_the_rows_of_a_person_named_once_and_of_a_name_class() -> None:
    paragraphs = ["אחמד חתם.", "מר כהן הלך."]
    golds = [gold(0, "אחמד", "A", "given", frozenset({"arabic"}), paragraphs), gold(1, "כהן", "B", "title_surname", frozenset(), paragraphs)]
    document = generate.Document("doc01", "hand", "contract", 1, paragraphs, golds)
    result = evaluate.measure(method("a", words=False), [document], {"a": run((0, 0, 4))}, STEPS)
    assert result["rows"]["lonely"] == [1, 2]
    assert result["rows"]["arabic"] == [1, 1]
    assert result["rows"]["no_trigger"] == [1, 1]
    assert result["rows"]["contract"] == [1, 2]
    assert "translit" not in result["rows"]


def test_ec29_two_detectors_add_their_seconds_and_keep_the_larger_memory() -> None:
    runs = {"a": run(FULL, seconds=10.0, peak=100), "b": run(SURNAME, seconds=20.0, peak=300)}
    both = evaluate.measure(method("a", "b"), [DOCUMENT], runs, STEPS)
    assert 30.0 <= both["seconds"] < 31.0
    assert both["peak_mb"] == 300


def test_ec18_pooled() -> None:
    one = evaluate.measure(method("a"), [DOCUMENT], {"a": run(FULL, SURNAME, GROUP, seconds=1.0, peak=100)}, STEPS)
    two = evaluate.measure(method("a"), [DOCUMENT], {"a": run(FULL, seconds=2.0, peak=300)}, STEPS)
    both = evaluate.pooled([one, two])
    assert both["rows"]["all"] == [4, 6]
    assert both["rows"]["group"] == [1, 2]
    assert both["peak_mb"] == 300
    assert both["seconds"] == pytest.approx(one["seconds"] + two["seconds"], abs=0.11)
    assert len(both["missed"]) == 2
    assert both["words"] == 18


def test_ec19_the_table_puts_the_best_first() -> None:
    def result(found: int, extra: int, seconds: float) -> dict:
        return {"rows": {"all": [found, 3]}, "extra": extra, "extra_no_title": extra, "marked": 4, "words": 9, "seconds": seconds, "peak_mb": 1}

    # The names are in the opposite order of the answer, so that the order of the names cannot give it.
    results = {"a worse": result(2, 0, 1.0), "b noisy": result(3, 2, 1.0), "c slow": result(3, 0, 9.0), "d clean": result(3, 0, 1.0), "e clean": result(3, 0, 1.0)}
    lines = evaluate.table("t", results).splitlines()
    assert [line.split(" | ")[0].removeprefix("| ") for line in lines[4:]] == ["d clean", "e clean", "c slow", "b noisy", "a worse"]
    assert lines[2].split(" | ")[:3] == ["| method", "recall", "found"]
    assert "100.00%" in lines[4]
    assert "66.67%" in lines[8]


def fake_run(dataset: str, skip: frozenset[str] = frozenset()) -> dict:
    """Build the run file of a made-up detector that marks every planted name but the forms in `skip`."""
    documents = data.load(dataset)
    tokens = {
        document.doc_id: [[item.paragraph, item.start, item.end, 1.0, 1] for item in document.gold if item.counted and item.form not in skip]
        for document in documents
    }
    return {"detector": "hf", "model": "made-up", "hashes": {"model.safetensors": "abc"}, "dataset": dataset,
            "corpus_sha256": data.digest(documents), "seconds": 5.0, "peak_mb": 100, "tokens": tokens}  # fmt: skip


def write(folder: Path, name: str, content: dict) -> None:
    """Write one run file."""
    (folder / name).write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")


def test_ec30_evaluate_scores_run_files_and_names_a_detector_that_is_left_out(tmp_path: Path) -> None:
    write(tmp_path, "every.select.json", fake_run("select"))
    write(tmp_path, "every.e4.json", fake_run("e4"))
    write(tmp_path, "nogroup.select.json", fake_run("select", frozenset(generate.GROUP_WORDS)))
    results, methods, runs, left_out = evaluate.evaluate(tmp_path, ["select", "e4"], evaluate.NameList(frozenset(), ""), [])
    assert left_out == ["nogroup"]
    assert set(results) == {"select", "e4", "all"}
    assert results["select"]["every"]["rows"]["all"] == [450, 450]
    assert results["all"]["every"]["rows"]["all"] == [1595, 1595]
    assert results["all"]["every"]["extra"] == 0
    assert all(name.startswith("every") for name in methods)
    assert set(runs) == {"select", "e4"}
    one, _, _, none_left = evaluate.evaluate(tmp_path, ["select"], evaluate.NameList(frozenset(), ""), ["nogroup + whole words", "nogroup + group"])
    assert none_left == []
    assert one["select"]["nogroup + whole words"]["rows"]["group"] == [0, 30]
    assert one["select"]["nogroup + group"]["rows"]["group"] == [30, 30]
    with pytest.raises(KeyError):
        evaluate.evaluate(tmp_path, ["select"], evaluate.NameList(frozenset(), ""), ["no such method"])


def test_e1_a_run_file_of_another_corpus_or_another_text_is_refused(tmp_path: Path) -> None:
    write(tmp_path, "moved.heldout.json", fake_run("select"))
    with pytest.raises(ValueError, match=r"moved\.heldout\.json"):
        evaluate.load_runs(tmp_path, "heldout", data.digest(data.load("heldout")))
    stale = fake_run("select")
    stale["corpus_sha256"] = "0" * 64
    write(tmp_path, "stale.select.json", stale)
    with pytest.raises(ValueError, match=r"stale\.select\.json"):
        evaluate.load_runs(tmp_path, "select", data.digest(data.load("select")))


@pytest.mark.parametrize(("datasets", "only"), [(["heldout", "select"], ["a"]), (["e4", "select", "heldout"], ["a"]), (["heldout"], [])])
def test_e2_the_held_out_corpus_is_not_scored_for_choosing(tmp_path: Path, datasets: list[str], only: list[str]) -> None:
    with pytest.raises(ValueError, match="heldout"):
        evaluate.check_request(datasets, only)
    with pytest.raises(ValueError, match="heldout"):
        evaluate.evaluate(tmp_path, datasets, evaluate.NameList(frozenset(), ""), only)


def test_ec31_what_may_be_asked_for() -> None:
    evaluate.check_request(["heldout"], ["a + whole words"])
    evaluate.check_request(["select"], [])
    evaluate.check_request(["e4", "select"], [])


def test_ec32_record_lines() -> None:
    runs = {"a": run(FULL)}
    methods = {"a + list": method("a", steps=("list",)), "a + carry": method("a", steps=("carry",))}
    results = {name: evaluate.measure(item, [DOCUMENT], runs, STEPS) for name, item in methods.items()}
    lines = [json.loads(line) for line in evaluate.record_lines("select", results, methods, runs, "names.txt, 3 names, sha256 abc")]
    assert [line["method"] for line in lines] == ["a + list", "a + carry"]
    assert [line["name_list"] for line in lines] == ["names.txt, 3 names, sha256 abc", ""]
    assert lines[0]["dataset"] == "select"
    assert lines[0]["experiment"] == "e5"
    assert lines[0]["detectors"] == [{"name": "a", "model": "m", "hashes": {"model.safetensors": "abc"}}]
    assert lines[1]["steps"] == ["carry"]
    assert lines[1]["rows"]["all"] == [2, 3]
    assert "missed" not in lines[0]


def test_ec33_a_list_of_names(tmp_path: Path) -> None:
    assert evaluate.read_name_list(None) == evaluate.NameList(frozenset(), "")
    path = tmp_path / "names.txt"
    path.write_text("נועה\nרותם\nנועה\n", encoding="utf-8")
    found = evaluate.read_name_list(path)
    assert found.names == frozenset({"נועה", "רותם"})
    assert found.label == f"names.txt, 2 names, sha256 {hashlib.sha256(path.read_bytes()).hexdigest()[:16]}"


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


def test_ec34_the_digest_of_a_corpus() -> None:
    assert {name: data.digest(data.load(name)) for name in data.DATASETS} == DIGESTS
    changed = [DOCUMENT._replace(paragraphs=[*PARAGRAPHS, "עוד שורה."])]
    assert data.digest([DOCUMENT]) != data.digest(changed)
    assert data.digest([DOCUMENT]) == data.digest([DOCUMENT._replace(gold=[])])
