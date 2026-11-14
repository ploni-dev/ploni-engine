"""More of the test matrix for generate, added after the first review and before any run.

People
  EC19 a given name and its surname come from the same origin: Arabic with Arabic,
       transliterated with transliterated, the rest with the rest
  EC20 a person who shares a surname gets a given name of that surname's origin
  A1   (over 50 seeds) a cited or firm name is never a person's surname

buckets_of
  EC21 a given name: given_ordinary, given_also_word or given_plain, by its classes
  EC22 a prefix on the name -> prefixed, prefix_on_name; on a title -> prefixed,
       prefix_on_title; on a group word -> prefixed only
  EC23 alone on a line -> alone

Errors
  E5   load_bank: a line without four fields, an unknown class, an unknown kind or
       gender, a name listed twice, an empty name -> TemplateError
  E6   parse_template: a brace that is no slot, a person declared twice, a surname
       shared with nobody, no kind, a prefix on a * slot, an unknown * form, a person
       with no title, an unknown class -> TemplateError

The corpus as committed
  C6   the five fillings of a template share no full name
  C7   the four documents of the second part are the first filling of the first
       template of each kind, and each holds a name that is not counted
  C8   no bare surname, and no title with a bare surname, for a person whose surname
       another person of the document carries
  C9   the classes in names.tsv: only known ones; prefix_initial exactly on the names
       that begin with a prefix letter; one origin at most; not both kinds of word
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from generate import (
    FILLINGS,
    NAME_CLASSES,
    PART_TWO_DOCUMENTS,
    Bank,
    Gold,
    TemplateError,
    buckets_of,
    corpus,
    fill,
    load_bank,
    parse_template,
)

HERE = Path(__file__).resolve().parent.parent
HEADER = "% kind letter\n@ A m title=מר\n@ B f title=השופטת\n"
ORIGIN_BANK = Bank(
    given={
        "m": [("יעקב", frozenset()), ("אחמד", frozenset({"arabic"})), ("בוריס", frozenset({"translit", "prefix_initial"}))],
        "f": [("רחל", frozenset()), ("אמל", frozenset({"arabic"})), ("נטשה", frozenset({"translit"}))],
    },
    surnames=[
        ("כהן", frozenset()), ("גבאי", frozenset({"also_word"})), ("מנסור", frozenset({"arabic", "prefix_initial"})),
        ("זועבי", frozenset({"arabic"})), ("פטרוב", frozenset({"translit"})), ("מילר", frozenset({"translit", "prefix_initial"})),
    ],
)


def origin(classes: frozenset[str]) -> str:
    return next((name for name in ("arabic", "translit") if name in classes), "hebrew")


def test_ec19_ec20_names_of_one_person_share_an_origin():
    header = "% kind letter\n@ A m title=מר\n@ B f title=גב' surname=A\n"
    template = parse_template(header + "{A:given} {A:surname} {B:given}")
    seen = set()
    for seed in range(80):
        _, gold = fill(template, ORIGIN_BANK, random.Random(seed))
        a_given, a_surname, b_given = (origin(item.classes) for item in gold)
        assert a_given == a_surname == b_given
        seen.add(a_given)
    assert seen == {"hebrew", "arabic", "translit"}


def test_a1_cited_and_firm_names_over_50_seeds():
    template = parse_template(HEADER + "{A:full} {B:full} {*:cited} {*:firm} {*:cited}")
    for seed in range(50):
        paragraphs, gold = fill(template, ORIGIN_BANK, random.Random(seed))
        names = [paragraphs[item.paragraph][item.start : item.end] for item in gold]
        people = {name.split(" ")[1] for name, item in zip(names, gold) if item.counted}
        others = {name for name, item in zip(names, gold) if not item.counted}
        assert len(people) == 2 and not people & others


def item(form: str, prefix: str = "", alone: bool = False, classes=frozenset()) -> Gold:
    return Gold(paragraph=0, start=0, end=3, name="כהן", person="A", form=form, prefix=prefix, alone=alone,
                classes=frozenset(classes), counted=True)


@pytest.mark.parametrize(
    ("gold", "expected"),
    [
        (item("given", classes={"ordinary"}), ["given", "given_ordinary"]),
        (item("given", classes={"also_word"}), ["given", "given_also_word"]),
        (item("given", classes={"arabic"}), ["given", "given_plain"]),
        (item("given", classes={"ordinary", "prefix_initial"}), ["given", "given_ordinary"]),
        (item("surname", prefix="ל"), ["surname", "prefixed", "prefix_on_name"]),
        (item("full", prefix="ו"), ["full", "prefixed", "prefix_on_name"]),
        (item("title_surname", prefix="ל"), ["title_surname", "prefixed", "prefix_on_title"]),
        (item("title_full", prefix="ול"), ["full", "prefixed", "prefix_on_title"]),
        (item("group_brothers", prefix="ל"), ["group", "prefixed"]),
        (item("full", alone=True), ["full", "alone"]),
        (item("title_initial_surname"), ["initial_surname"]),
    ],
)
def test_ec21_ec22_ec23_buckets_of(gold: Gold, expected: list[str]):
    assert buckets_of(gold) == expected


@pytest.mark.parametrize(
    "body",
    ["given\tm\tיעקב\n", "given\tm\tיעקב\tgreen\n", "given\tx\tיעקב\t\n", "nickname\tm\tיעקב\t\n",
     "surname\tm\tכהן\t\n", "given\tm\tיעקב\t\ngiven\tm\tיעקב\t\n", "given\tm\t\t\n"],
    ids=["three_fields", "unknown_class", "bad_gender", "bad_kind", "surname_with_gender", "listed_twice", "empty_name"],
)
def test_e5_bad_bank_file(tmp_path: Path, body: str):
    path = tmp_path / "names.tsv"
    path.write_text("kind\tgender\tname\tclasses\n" + body, encoding="utf-8")
    with pytest.raises(TemplateError):
        load_bank(path)


def test_load_bank_reads_a_good_file(tmp_path: Path):
    path = tmp_path / "names.tsv"
    path.write_text(
        "kind\tgender\tname\tclasses\ngiven\tf\tטל\tordinary\nsurname\t-\tבן דוד\talso_word,prefix_initial\n",
        encoding="utf-8",
    )
    bank = load_bank(path)
    assert bank.given == {"m": [], "f": [("טל", frozenset({"ordinary"}))]}
    assert bank.surnames == [("בן דוד", frozenset({"also_word", "prefix_initial"}))]


@pytest.mark.parametrize(
    "template",
    [
        HEADER + "כך {A:full אמר.",
        HEADER + "כך A:full} אמר.",
        HEADER + "@ A f title=גב'\nכך {A:full}.",
        "% kind letter\n@ A m title=מר surname=Z\nכך {A:full}.",
        "@ A m title=מר\nכך {A:full}.",
        HEADER + "כך {*:cited:ל}.",
        HEADER + "כך {*:nickname}.",
        "% kind letter\n@ A m\nכך {A:full}.",
        "% kind letter\n@ A m title=מר class=green\nכך {A:full}.",
    ],
    ids=["open_brace", "close_brace", "declared_twice", "shares_nobody", "no_kind", "prefix_on_star",
         "unknown_star_form", "no_title", "unknown_class"],
)
def test_e6_bad_template(template: str):
    with pytest.raises(TemplateError):
        parse_template(template)


@pytest.fixture(scope="module")
def committed():
    return corpus(HERE / "templates", HERE / "names.tsv")


def test_c6_fillings_of_a_template_share_no_full_name(committed):
    by_template: dict[str, list[set[str]]] = {}
    for document in committed:
        names = {gold.name for gold in document.gold if gold.counted and gold.form in ("full", "title_full")}
        by_template.setdefault(document.template, []).append(names)
    for fillings in by_template.values():
        assert len(fillings) == FILLINGS
        for index, names in enumerate(fillings):
            assert all(not names & other for other in fillings[index + 1 :])


def test_c7_the_documents_of_the_second_part(committed):
    assert PART_TWO_DOCUMENTS == ("doc01", "doc11", "doc21", "doc31")
    chosen = [document for document in committed if document.doc_id in PART_TWO_DOCUMENTS]
    assert [document.filling for document in chosen] == [1, 1, 1, 1]
    assert sorted(document.kind for document in chosen) == ["contract", "judgment", "letter", "medical"]
    assert all(any(not gold.counted for gold in document.gold) for document in chosen)


def test_c8_no_bare_surname_for_a_person_who_shares_it(committed):
    for document in committed:
        carriers: dict[str, set[str]] = {}
        for gold in document.gold:
            if gold.counted and gold.form in ("full", "title_full"):
                carriers.setdefault(gold.name.split(" ", 1)[1], set()).add(gold.person)
        shared = {surname for surname, people in carriers.items() if len(people) > 1}
        for gold in document.gold:
            if gold.counted and gold.form in ("surname", "title_surname"):
                assert gold.name not in shared, (document.doc_id, gold.paragraph)


def test_c9_classes_of_the_bank():
    bank = load_bank(HERE / "names.tsv")
    assert NAME_CLASSES == {"ordinary", "also_word", "prefix_initial", "arabic", "translit"}
    for names in (*bank.given.values(), bank.surnames):
        for name, classes in names:
            assert classes <= NAME_CLASSES
            assert ("prefix_initial" in classes) == (name[0] in "והבלמכש")
            assert len(classes & {"arabic", "translit"}) < 2
            assert not {"ordinary", "also_word"} <= classes
