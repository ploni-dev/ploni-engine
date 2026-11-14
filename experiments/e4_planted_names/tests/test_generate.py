"""Test matrix for generate: parse_template, fill, corpus.

Every text here is invented for the test. The generator's whole point is that its gold
positions are exact, so nearly every case checks `paragraph[start:end]` against the name.

Forms (one person, one slot)
  EC1  full                      -> "given surname", gold is the whole
  EC2  given, surname            -> the one token, gold is the token
  EC3  title_surname             -> "title surname", gold is the surname only
  EC4  title_full                -> "title given surname", gold is "given surname"
  EC5  initial_surname           -> "X' surname", gold is the whole
  EC6  title_initial_surname     -> "title X' surname", gold is "X' surname"
  EC7  group_brothers, group_family -> "האחים surname", "משפחת surname", gold is the surname

Prefix letters
  EC8  on a name form            -> attached to the name, gold starts after them
  EC9  on a title form           -> attached to the title, gold unchanged
  H1   ל, ב, כ before a title or group word that begins with ה -> the ה is dropped (לשופט, לאחים)
  H2   ו, ש, מ before the same   -> the ה stays (והשופט, מהאחים)

Names that are not counted
  EC10 cited                     -> "surname נ' surname", two gold items, not counted
  EC11 firm                      -> "משרד surname ושות'", one gold item, not counted
  EC12 placeholder               -> "פלוני", one gold item, not counted
  A1   their surnames are never a surname of a person of the document

People
  EC13 surname=A                 -> the person carries A's surname
  EC14 class=ordinary            -> the given name is of that class, and the gold says so
  EC15 two people of a document  -> different given names, different surnames unless shared
  B1   the same person twice in one paragraph -> both gold positions exact
  B2   two slots in one paragraph -> the second position accounts for the first replacement

Alone on a line
  EC16 the slot is the whole paragraph, or follows only a list number -> alone is True
  EC17 anything else beside it   -> alone is False

Errors
  E1   a slot names a person the header does not declare -> TemplateError
  E2   an unknown form           -> TemplateError
  E3   an unknown header line    -> TemplateError
  E4   the bank has too few names for the document -> TemplateError

Determinism
  EC18 the same seed gives the same document; another filling gives other names

Invariant, 500 generated templates
  P1   every gold item lies inside its paragraph, its text is the name it claims, and no
       two gold items of a paragraph overlap

The corpus as committed (templates/ and names.tsv)
  C1   40 documents: 8 templates, 5 fillings, 4 kinds with 2 templates each
  C2   at least 1,000 counted mentions
  C3   at least 30 counted mentions of each form bucket, with a prefix, alone on a line,
       and of a given name alone that is an everyday word (PREREGISTRATION.md)
  C4   every gold position holds exactly its name
  C5   generated twice, the corpus is identical

More cases, added after the first review, are in test_generate_more.py.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from generate import (
    FILLINGS,
    FORM_BUCKETS,
    MIN_COUNTED_MENTIONS,
    MIN_PER_BUCKET,
    Bank,
    TemplateError,
    bucket_counts,
    corpus,
    fill,
    load_bank,
    parse_template,
)

HERE = Path(__file__).resolve().parent.parent
BANK = Bank(
    given={
        "m": [("יעקב", frozenset()), ("דוד", frozenset()), ("אור", frozenset({"ordinary"})), ("משה", frozenset({"prefix_initial"}))],
        "f": [("רחל", frozenset()), ("טל", frozenset({"ordinary"})), ("מרים", frozenset())],
    },
    surnames=[
        ("כהן", frozenset()), ("לוי", frozenset()), ("מזרחי", frozenset()), ("פרץ", frozenset()),
        ("ביטון", frozenset()), ("אוחנה", frozenset()), ("גבאי", frozenset()), ("שלום", frozenset({"ordinary"})),
    ],
)
HEADER = "% kind letter\n@ A m title=מר\n@ B f title=השופטת\n"


def one(body: str, header: str = HEADER, seed: int = 1):
    """Fill a one-off template and return (paragraphs, gold)."""
    return fill(parse_template(header + body), BANK, random.Random(seed))


def texts(paragraphs, gold):
    return [paragraphs[item.paragraph][item.start : item.end] for item in gold]


def test_ec1_full():
    paragraphs, gold = one("ביום ראשון הגיע {A:full} למשרד.")
    (item,) = gold
    given, surname = texts(paragraphs, gold)[0].split(" ")
    assert (item.form, item.counted, item.prefix) == ("full", True, "")
    assert given in {name for name, _ in BANK.given["m"]} and surname in {name for name, _ in BANK.surnames}
    assert paragraphs[0] == f"ביום ראשון הגיע {given} {surname} למשרד."


@pytest.mark.parametrize("form", ["given", "surname"])
def test_ec2_single_token(form: str):
    paragraphs, gold = one(f"כך טען {{A:{form}}} בדיון.")
    (name,) = texts(paragraphs, gold)
    assert " " not in name and paragraphs[0] == f"כך טען {name} בדיון."


def test_ec3_title_surname_gold_is_the_surname():
    paragraphs, gold = one("כך טען {A:title_surname} בדיון.")
    (name,) = texts(paragraphs, gold)
    assert paragraphs[0] == f"כך טען מר {name} בדיון." and " " not in name


def test_ec4_title_full_gold_is_given_and_surname():
    paragraphs, gold = one("כך טען {A:title_full} בדיון.")
    (name,) = texts(paragraphs, gold)
    assert paragraphs[0] == f"כך טען מר {name} בדיון." and name.count(" ") == 1


def test_ec5_ec6_initial_and_surname():
    paragraphs, gold = one("כך כתב {A:initial_surname}, וכך {B:title_initial_surname}.")
    first, second = texts(paragraphs, gold)
    assert first[1:3] == "' " and second[1:3] == "' "
    assert paragraphs[0] == f"כך כתב {first}, וכך השופטת {second}."


def test_ec7_group_terms():
    paragraphs, gold = one("כך טענו {A:group_brothers}, וכך {A:group_family}.")
    first, second = texts(paragraphs, gold)
    assert first == second and paragraphs[0] == f"כך טענו האחים {first}, וכך משפחת {first}."
    assert [item.form for item in gold] == ["group_brothers", "group_family"]


def test_ec8_prefix_on_a_name_is_outside_the_gold():
    paragraphs, gold = one("המכתב נשלח {A:surname:ל} {A:given:ול}.")
    surname, given = texts(paragraphs, gold)
    assert paragraphs[0] == f"המכתב נשלח ל{surname} ול{given}."
    assert [item.prefix for item in gold] == ["ל", "ול"]


def test_ec9_prefix_on_a_title_form():
    paragraphs, gold = one("המכתב נשלח {A:title_surname:ל}.")
    (surname,) = texts(paragraphs, gold)
    assert paragraphs[0] == f"המכתב נשלח למר {surname}."


@pytest.mark.parametrize(
    ("slot", "rendered"),
    [
        ("{B:title_surname:ל}", "לשופטת"),
        ("{B:title_surname:ב}", "בשופטת"),
        ("{B:title_surname:כ}", "כשופטת"),
        ("{B:title_surname:ו}", "והשופטת"),
        ("{B:title_surname:ש}", "שהשופטת"),
        ("{B:title_surname:מ}", "מהשופטת"),
        ("{A:group_brothers:ל}", "לאחים"),
        ("{A:group_brothers:ול}", "ולאחים"),
        ("{A:group_brothers:מ}", "מהאחים"),
    ],
)
def test_h1_h2_the_article_after_a_prefix(slot: str, rendered: str):
    paragraphs, gold = one(f"כך נמסר {slot} אתמול.")
    (name,) = texts(paragraphs, gold)
    assert paragraphs[0] == f"כך נמסר {rendered} {name} אתמול."


def test_ec10_ec11_ec12_a1_names_that_are_not_counted():
    paragraphs, gold = one("ראו {*:cited}, וכן {*:firm}, וכן {*:placeholder}. כך {A:full}, וכך {B:full}.")
    cited_one, cited_two, firm, placeholder, a_name, b_name = texts(paragraphs, gold)
    assert f"{cited_one} נ' {cited_two}" in paragraphs[0] and f"משרד {firm} ושות'" in paragraphs[0]
    assert placeholder == "פלוני"
    assert [item.counted for item in gold] == [False, False, False, False, True, True]
    people_surnames = {a_name.split(" ")[1], b_name.split(" ")[1]}
    assert not {cited_one, cited_two, firm} & people_surnames


def test_ec13_shared_surname():
    header = "% kind letter\n@ A m title=מר\n@ B m title=מר surname=A\n"
    paragraphs, gold = one("{A:full} ואחיו {B:full}.", header)
    first, second = texts(paragraphs, gold)
    assert first.split(" ")[1] == second.split(" ")[1] and first.split(" ")[0] != second.split(" ")[0]


def test_ec14_class_constraint_is_met_and_recorded():
    header = "% kind letter\n@ A m title=מר class=ordinary\n"
    for seed in range(20):
        paragraphs, gold = one("כך אמר {A:given}, כלומר {A:surname}.", header, seed)
        given, _ = texts(paragraphs, gold)
        assert given == "אור" and "ordinary" in gold[0].classes


def test_ec15_people_of_one_document_differ():
    for seed in range(50):
        paragraphs, gold = one("{A:full} פגש את {B:full}.", seed=seed)
        first, second = (text.split(" ") for text in texts(paragraphs, gold))
        assert first[0] != second[0] and first[1] != second[1]


def test_b1_b2_positions_after_an_earlier_slot():
    paragraphs, gold = one("{A:full} אמר כי {A:surname} ידע, וכי {B:given:ש} ידעה.")
    full, surname, given = texts(paragraphs, gold)
    assert surname == full.split(" ")[1]
    assert paragraphs[0] == f"{full} אמר כי {surname} ידע, וכי ש{given} ידעה."


@pytest.mark.parametrize(("body", "alone"), [("{A:full}", True), ("3. {A:full}", True), ("3.\t{A:title_full}", True),
                                             ("המערער: {A:full}", False), ("{A:full}, עו\"ד", False)])
def test_ec16_ec17_alone_on_a_line(body: str, alone: bool):
    _, gold = one(body)
    assert gold[0].alone is alone


@pytest.mark.parametrize(
    "template",
    [
        HEADER + "כך {C:full}.",
        HEADER + "כך {A:nickname}.",
        HEADER + "@ C x title=מר\nכך {A:full}.",
        "% colour blue\n" + HEADER + "כך {A:full}.",
    ],
    ids=["e1_undeclared_person", "e2_unknown_form", "e3_bad_person_line", "e3_unknown_header"],
)
def test_e1_e2_e3_bad_template(template: str):
    with pytest.raises(TemplateError):
        fill(parse_template(template), BANK, random.Random(1))


def test_e4_bank_too_small():
    header = "% kind letter\n" + "".join(f"@ P{i} f title=גב'\n" for i in range(4))
    with pytest.raises(TemplateError):
        fill(parse_template(header + "כך {P0:full}."), BANK, random.Random(1))


def test_ec18_same_seed_same_document():
    body = "{A:full} פגש את {B:full}."
    assert one(body, seed=7) == one(body, seed=7)
    assert {one(body, seed=seed)[0][0] for seed in range(30)} != {one(body, seed=7)[0][0]}


FORMS = ["full", "given", "surname", "title_surname", "title_full", "initial_surname",
         "title_initial_surname", "group_brothers", "group_family"]
PREFIXES = ["", "ל", "ב", "מ", "ו", "ש", "כ", "ול", "וב", "ומ", "כש", "של", "וש"]
FILLERS = ["ביום ראשון", "נטען כי", "לאחר מכן", "בהתאם לכך", "(להלן:", "–", "\"כך\"", "3.", ";"]


def test_p1_gold_is_exact_on_500_generated_templates():
    rng = random.Random(20261114)
    for case in range(500):
        lines = []
        for _ in range(rng.randint(1, 4)):
            parts = []
            for _ in range(rng.randint(1, 5)):
                if rng.random() < 0.6:
                    person = rng.choice("AB")
                    prefix = rng.choice(PREFIXES)
                    parts.append(f"{{{person}:{rng.choice(FORMS)}{':' + prefix if prefix else ''}}}")
                elif rng.random() < 0.3:
                    parts.append(rng.choice(["{*:cited}", "{*:firm}", "{*:placeholder}"]))
                else:
                    parts.append(rng.choice(FILLERS))
            lines.append(" ".join(parts))
        paragraphs, gold = fill(parse_template(HEADER + "\n".join(lines)), BANK, random.Random(case))
        by_paragraph: dict[int, list] = {}
        for item in gold:
            text = paragraphs[item.paragraph]
            assert 0 <= item.start < item.end <= len(text)
            assert text[item.start : item.end] == item.name
            assert not text[item.start : item.end].startswith(" ") and not text[item.start : item.end].endswith(" ")
            by_paragraph.setdefault(item.paragraph, []).append(item)
        for items in by_paragraph.values():
            items.sort(key=lambda item: item.start)
            assert all(first.end <= second.start for first, second in zip(items, items[1:]))


@pytest.fixture(scope="module")
def committed():
    return corpus(HERE / "templates", HERE / "names.tsv")


def test_c1_forty_documents(committed):
    assert len(committed) == 8 * FILLINGS == 40
    kinds = {}
    for document in committed:
        kinds.setdefault(document.kind, set()).add(document.template)
    assert {kind: len(names) for kind, names in kinds.items()} == {"judgment": 2, "contract": 2, "letter": 2, "medical": 2}
    assert [document.doc_id for document in committed] == [f"doc{number:02d}" for number in range(1, 41)]


def test_c2_c3_enough_mentions_of_every_kind(committed):
    counts = bucket_counts(committed)
    assert counts["all"] >= MIN_COUNTED_MENTIONS == 1000
    promised = set(FORM_BUCKETS.values()) | {"prefixed", "prefix_on_name", "prefix_on_title", "alone", "given_ordinary", "given_plain"}
    assert promised <= set(counts) and "given_also_word" in counts
    assert MIN_PER_BUCKET == 30
    assert {name: counts[name] for name in promised if counts[name] < MIN_PER_BUCKET} == {}


def test_c4_every_gold_position_holds_its_name(committed):
    for document in committed:
        for item in document.gold:
            assert document.paragraphs[item.paragraph][item.start : item.end] == item.name


def test_c5_the_corpus_is_the_same_twice(committed):
    assert corpus(HERE / "templates", HERE / "names.tsv") == committed


def test_bank_file_has_no_name_twice_and_only_known_classes():
    bank = load_bank(HERE / "names.tsv")
    for names in (*bank.given.values(), bank.surnames):
        plain = [name for name, _ in names]
        assert len(plain) == len(set(plain))
        assert all(classes <= {"ordinary", "also_word", "prefix_initial", "arabic", "translit"} for _, classes in names)
