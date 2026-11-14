"""Generate the E4 corpus: invented documents with every name planted at a known place.

Why: E1's count was made by readers and no person checked it. Here a script puts each
name into the text and writes down where it put it, so the right answer is known
exactly and nobody reads in order to count (PREREGISTRATION.md).

A template is a text file. Header lines come first:

    % kind letter
    @ A m title=מר
    @ B f title=עו"ד class=ordinary
    @ C m title=מר surname=A

and every other non-empty line is one paragraph, holding slots such as `{A:full}`,
`{B:title_surname:ל}` or `{*:cited}`. `m` and `f` pick the list the given name is
drawn from, so that the verbs the template writes agree with the name.

Known limits: Hebrew only. A title is one word. The one piece of grammar the generator
knows is that ל, ב and כ swallow the ה of a title or of `האחים`; a template must not
attach a prefix where Hebrew would need more than that.
"""

from __future__ import annotations

import itertools
import random
import re
from collections import Counter
from pathlib import Path
from typing import NamedTuple

# PREREGISTRATION.md, "What is generated": the seed is fixed, five fillings per template.
SEED = "e4-2026-11-14"
FILLINGS = 5
MIN_COUNTED_MENTIONS = 1000
MIN_PER_BUCKET = 30
KINDS = ("judgment", "contract", "letter", "medical")
GENDERS = ("m", "f")
# `ordinary`: a modern name taken from an everyday word (build-plan.md Phase 1: אור, טל).
# `also_word`: a traditional name that is also an everyday word (דוד, מרים).
NAME_CLASSES = frozenset({"ordinary", "also_word", "prefix_initial", "arabic", "translit"})
# A given name is paired with a surname of its own origin; names of neither class are "hebrew".
ORIGINS = ("arabic", "translit")
# PREREGISTRATION.md, second part: the first filling of the first template of each kind.
PART_TWO_DOCUMENTS = ("doc01", "doc11", "doc21", "doc31")
# A filling that repeats a full name of an earlier filling is drawn again, at most this often.
MAX_REDRAWS = 50

PREFIX_LETTERS = "והבלמכש"
# ל, ב and כ merge with the definite article of the word they attach to: לשופט, not להשופט.
ARTICLE_EATERS = "לבכ"
GROUP_WORDS = {"group_brothers": "האחים", "group_family": "משפחת"}
# Every person form, and the bucket the report puts it in.
FORM_BUCKETS = {
    "full": "full",
    "title_full": "full",
    "given": "given",
    "surname": "surname",
    "title_surname": "title_surname",
    "initial_surname": "initial_surname",
    "title_initial_surname": "initial_surname",
    "group_brothers": "group",
    "group_family": "group",
}
TITLE_FORMS = frozenset({"title_surname", "title_full", "title_initial_surname"})
FULL_NAME_FORMS = frozenset({"full", "title_full"})
# The rows of the report beside the form buckets, in the order they are printed.
TRAITS = ("given_ordinary", "given_also_word", "given_plain", "prefixed", "prefix_on_name", "prefix_on_title", "alone")
STAR_FORMS = frozenset({"cited", "firm", "placeholder"})
PLACEHOLDER = "פלוני"

SLOT = re.compile(rf"\{{(\*|[A-Z][0-9]?):([a-z_]+)(?::([{PREFIX_LETTERS}]{{1,3}}))?\}}")
LIST_NUMBER = re.compile(r"\s*(\d+\.\s*)?")

Names = list[tuple[str, frozenset[str]]]


class TemplateError(ValueError):
    """A template, or the name bank, cannot be turned into a document.

    Why: a slot that is silently left in the text, or a name drawn twice, would make
    the gold wrong without looking wrong.
    """


class Bank(NamedTuple):
    """The names a document's people are drawn from.

    Contract: `given` maps `m` and `f` to (name, classes) pairs; `surnames` is one such
    list. Classes are a subset of NAME_CLASSES.
    """

    given: dict[str, Names]
    surnames: Names


class Person(NamedTuple):
    """One person a template declares.

    Contract: `shares` is the key of the person whose surname this one carries, or "".
    `wanted_class` restricts the given name to a class of NAME_CLASSES, or is "".
    """

    key: str
    gender: str
    title: str
    shares: str
    wanted_class: str


class Template(NamedTuple):
    """A parsed template: its kind, its people in declared order, its paragraphs."""

    kind: str
    persons: dict[str, Person]
    lines: list[str]


class Gold(NamedTuple):
    """One planted name and where it is.

    Why: this is the ground truth the model's output is scored against.

    Contract: `paragraph` counts from 0. `start` inclusive and `end` exclusive, in
    characters of that paragraph, and the text between them is exactly `name`. A title
    and attached prefix letters are outside it. `person` is the template's key, or `*`
    for a name that is not a person of the document. `prefix` holds the attached
    letters, or "". `alone` says the mention is the whole line, after a list number at
    most. `classes` are the classes of the name words inside the span. `counted` is
    False for a name E1's rules leave out: a cited title, a firm, a placeholder.
    """

    paragraph: int
    start: int
    end: int
    name: str
    person: str
    form: str
    prefix: str
    alone: bool
    classes: frozenset[str]
    counted: bool


class Document(NamedTuple):
    """One generated document with its ground truth.

    Contract: `doc_id` is `doc01` onwards in corpus order. `filling` counts from 1.
    `gold` is in reading order.
    """

    doc_id: str
    template: str
    kind: str
    filling: int
    paragraphs: list[str]
    gold: list[Gold]


def load_bank(path: Path) -> Bank:
    """Read the name bank from a tab-separated file.

    Contract: a header line, then `kind`, `gender`, `name`, `classes` per line. `kind`
    is `given` or `surname`; `gender` is `m` or `f` for a given name and `-` for a
    surname; `classes` is empty or comma-separated. Raises TemplateError for any other
    line, an unknown class, or a name listed twice in one list.
    """
    given: dict[str, Names] = {gender: [] for gender in GENDERS}
    surnames: Names = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines()[1:], start=2):
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) != 4:
            raise TemplateError(f"names line {number}: expected four fields")
        kind, gender, name, raw_classes = (field.strip() for field in fields)
        classes = frozenset(filter(None, raw_classes.split(",")))
        if not name or not classes <= NAME_CLASSES:
            raise TemplateError(f"names line {number}: empty name or unknown class")
        if kind == "given" and gender in GENDERS:
            target = given[gender]
        elif kind == "surname" and gender == "-":
            target = surnames
        else:
            raise TemplateError(f"names line {number}: unknown kind or gender")
        if any(name == existing for existing, _ in target):
            raise TemplateError(f"names line {number}: listed twice")
        target.append((name, classes))
    return Bank(given, surnames)


def _parse_kind(line: str) -> str:
    """Read the `% kind X` header line.

    Contract: returns X, one of KINDS. Raises TemplateError for any other `%` line.
    """
    fields = line[1:].split()
    if len(fields) != 2 or fields[0] != "kind" or fields[1] not in KINDS:
        raise TemplateError(f"unknown header line: {line}")
    return fields[1]


def _parse_person(line: str, declared: dict[str, Person]) -> Person:
    """Read one `@ KEY gender option=value ...` header line.

    Contract: `title` is required; `surname` and `class` are optional. `declared` are
    the people read so far. Raises TemplateError for a malformed line, a key declared
    twice, an unknown class, or a shared surname that points at no earlier person.
    """
    fields = line[1:].split()
    options = dict(field.split("=", 1) for field in fields[2:] if "=" in field)
    if len(fields) < 3 or len(options) != len(fields) - 2 or not set(options) <= {"title", "surname", "class"}:
        raise TemplateError(f"bad person line: {line}")
    person = Person(fields[0], fields[1], options.get("title", ""), options.get("surname", ""), options.get("class", ""))
    well_formed = re.fullmatch(r"[A-Z][0-9]?", person.key) and person.gender in GENDERS and person.title
    if not well_formed or (person.wanted_class and person.wanted_class not in NAME_CLASSES):
        raise TemplateError(f"bad person line: {line}")
    if person.key in declared or (person.shares and person.shares not in declared):
        raise TemplateError(f"person declared twice, or shares an unknown surname: {line}")
    return person


def _check_slots(line: str, persons: dict[str, Person]) -> None:
    """Refuse a paragraph whose slots cannot be filled.

    Why: a brace the pattern does not match would stay in the generated text.

    Contract: raises TemplateError for a brace outside a well-formed slot, an
    undeclared person, an unknown form, or a prefix on a `*` slot.
    """
    if "{" in SLOT.sub("", line) or "}" in SLOT.sub("", line):
        raise TemplateError(f"malformed slot in: {line}")
    for key, form, prefix in SLOT.findall(line):
        if key == "*":
            if form not in STAR_FORMS or prefix:
                raise TemplateError(f"unknown form or prefix on a * slot in: {line}")
        elif key not in persons or form not in FORM_BUCKETS:
            raise TemplateError(f"undeclared person or unknown form in: {line}")


def parse_template(text: str) -> Template:
    """Turn the text of a template file into its kind, people and paragraphs.

    Contract: see the module docstring for the format. Raises TemplateError for an
    unknown header line, a missing kind, a person line `_parse_person` refuses, or a
    paragraph `_check_slots` refuses.
    """
    kind = ""
    persons: dict[str, Person] = {}
    lines = []
    for line in (raw.rstrip() for raw in text.splitlines() if raw.strip()):
        if line.startswith("%"):
            kind = _parse_kind(line)
        elif line.startswith("@"):
            person = _parse_person(line, persons)
            persons[person.key] = person
        else:
            lines.append(line)
    if not kind:
        raise TemplateError("the template names no kind")
    for line in lines:
        _check_slots(line, persons)
    return Template(kind, persons, lines)


def _origin(classes: frozenset[str]) -> str:
    """Name the origin group of a name: `arabic`, `translit`, or `hebrew` for the rest."""
    return next((name for name in ORIGINS if name in classes), "hebrew")


def _draw_people(template: Template, bank: Bank, rng: random.Random) -> dict[str, tuple]:
    """Give every person of a template a given name and a surname.

    Why: a given name paired with a surname of another origin (`מוחמד לוי`) is a name
    real documents do not hold, and it would blur the rows per name class.

    Contract: returns key -> ((given, classes), (surname, classes)). The two names of a
    person share an origin (`_origin`), also when the surname is another person's. No
    two people of a document share a given name; no two share a surname unless the
    template says so. Raises TemplateError when the bank has no unused name that fits.
    """
    people: dict[str, tuple] = {}
    used_given: set[str] = set()
    used_surnames: set[str] = set()
    for person in template.persons.values():
        shared = people[person.shares][1] if person.shares else None
        fitting = [
            entry
            for entry in bank.given[person.gender]
            if entry[0] not in used_given
            and (not person.wanted_class or person.wanted_class in entry[1])
            and (shared is None or _origin(entry[1]) == _origin(shared[1]))
        ]
        if not fitting:
            raise TemplateError(f"the bank has no given name left for {person.key}")
        given = rng.choice(fitting)
        free = [entry for entry in bank.surnames if entry[0] not in used_surnames and _origin(entry[1]) == _origin(given[1])]
        if shared is None and not free:
            raise TemplateError(f"the bank has no surname left for {person.key}")
        surname = shared or rng.choice(free)
        used_given.add(given[0])
        used_surnames.add(surname[0])
        people[person.key] = (given, surname)
    return people


def _render_person(person: Person, form: str, prefix: str, given: tuple, surname: tuple) -> tuple[str, str, frozenset[str]]:
    """Write one mention of a person.

    Contract: returns (text, name, classes). `name` is the part that is the person's
    name and is always the end of `text`; what precedes it is the prefix letters and a
    title or group word, if any.
    """
    initial = f"{given[0][0]}'"
    head = person.title if form in TITLE_FORMS else GROUP_WORDS.get(form, "")
    if form in FULL_NAME_FORMS:
        name, classes = f"{given[0]} {surname[0]}", given[1] | surname[1]
    elif form == "given":
        name, classes = given[0], given[1]
    elif form in ("initial_surname", "title_initial_surname"):
        name, classes = f"{initial} {surname[0]}", surname[1]
    else:
        name, classes = surname[0], surname[1]
    if head and prefix and prefix[-1] in ARTICLE_EATERS and head.startswith("ה"):
        head = head[1:]
    return prefix + (f"{head} " if head else "") + name, name, classes


def _fill_line(index: int, line: str, template: Template, people: dict, spare: Names, rng: random.Random) -> tuple[str, list[Gold]]:
    """Fill the slots of one paragraph and record where each name landed.

    Contract: `spare` are surnames no person of the document carries; cited titles
    and firms draw from them. Returns the paragraph and its gold in reading order.
    """
    slots = list(SLOT.finditer(line))
    alone = len(slots) == 1 and LIST_NUMBER.fullmatch(line[: slots[0].start()]) is not None and not line[slots[0].end() :]
    pieces: list[str] = []
    gold: list[Gold] = []
    cursor = length = 0

    def plant(text: str, names: list[tuple[int, str, frozenset[str]]], key: str, form: str, prefix: str, counted: bool) -> None:
        nonlocal length
        for offset, name, classes in names:
            start = length + offset
            gold.append(Gold(index, start, start + len(name), name, key, form, prefix, alone and counted, classes, counted))
        pieces.append(text)
        length += len(text)

    for slot in slots:
        between = line[cursor : slot.start()]
        pieces.append(between)
        length += len(between)
        cursor = slot.end()
        key, form, prefix = slot.group(1), slot.group(2), slot.group(3) or ""
        if key != "*":
            text, name, classes = _render_person(template.persons[key], form, prefix, *people[key])
            plant(text, [(len(text) - len(name), name, classes)], key, form, prefix, True)
        elif form == "cited":
            (first, first_classes), (second, second_classes) = rng.sample(spare, 2)
            text = f"{first} נ' {second}"
            plant(text, [(0, first, first_classes), (len(text) - len(second), second, second_classes)], key, form, "", False)
        elif form == "firm":
            name, classes = rng.choice(spare)
            plant(f"משרד {name} ושות'", [(len("משרד "), name, classes)], key, form, "", False)
        else:
            plant(PLACEHOLDER, [(0, PLACEHOLDER, frozenset())], key, form, "", False)
    pieces.append(line[cursor:])
    return "".join(pieces), gold


def fill(template: Template, bank: Bank, rng: random.Random) -> tuple[list[str], list[Gold]]:
    """Fill a template once: draw its people, write its paragraphs, record the gold.

    Why: the one place where text and ground truth are made together, so they cannot
    drift apart.

    Contract: returns (paragraphs, gold) with the gold in reading order. The same
    template, bank and state of `rng` give the same result. Raises TemplateError when
    the bank is too small for the document.
    """
    people = _draw_people(template, bank, rng)
    taken = {surname[0] for _, surname in people.values()}
    spare = [entry for entry in bank.surnames if entry[0] not in taken]
    if len(spare) < 2 and any(key == "*" and form != "placeholder" for line in template.lines for key, form, _ in SLOT.findall(line)):
        raise TemplateError("the bank has too few surnames left for a cited title or a firm")
    paragraphs: list[str] = []
    gold: list[Gold] = []
    for index, line in enumerate(template.lines):
        paragraph, line_gold = _fill_line(index, line, template, people, spare, rng)
        paragraphs.append(paragraph)
        gold.extend(line_gold)
    return paragraphs, gold


def _fill_fresh(template: Template, bank: Bank, seed: str, taken: set[str]) -> tuple[list[str], list[Gold]]:
    """Fill a template so that no person carries a full name in `taken`.

    Why: the pre-registration says each template is filled five times with different
    people, and two draws from one bank can land on the same full name.

    Contract: tries `seed`, then `seed:1`, `seed:2` and so on, and returns the first
    filling whose full names (FULL_NAME_FORMS) are all outside `taken`. Raises
    TemplateError after MAX_REDRAWS tries.
    """
    for attempt in itertools.islice(itertools.count(), MAX_REDRAWS):
        paragraphs, gold = fill(template, bank, random.Random(f"{seed}:{attempt}" if attempt else seed))
        if not taken & {item.name for item in gold if item.counted and item.form in FULL_NAME_FORMS}:
            return paragraphs, gold
    raise TemplateError(f"no filling with new people after {MAX_REDRAWS} tries: {seed}")


def corpus(templates_dir: Path, bank_path: Path) -> list[Document]:
    """Generate the whole corpus: every template, FILLINGS times.

    Contract: templates are the `.txt` files of `templates_dir` in name order; documents
    come in template order, then filling order, and are named `doc01` onwards. Each
    document is seeded from SEED, its template's name and its filling number, so the
    corpus is the same on every run and adding a template does not change the others.
    The fillings of one template share no full name. Raises TemplateError as
    `parse_template`, `load_bank`, `fill` and `_fill_fresh` do.
    """
    bank = load_bank(bank_path)
    documents = []
    for path in sorted(templates_dir.glob("*.txt")):
        template = parse_template(path.read_text(encoding="utf-8"))
        taken: set[str] = set()
        for filling in range(1, FILLINGS + 1):
            paragraphs, gold = _fill_fresh(template, bank, f"{SEED}:{path.stem}:{filling}", taken)
            taken |= {item.name for item in gold if item.counted and item.form in FULL_NAME_FORMS}
            documents.append(Document(f"doc{len(documents) + 1:02d}", path.stem, template.kind, filling, paragraphs, gold))
    return documents


def buckets_of(gold: Gold) -> list[str]:
    """Name every report row one counted mention belongs to.

    Why: the pre-registration makes a prediction per row, so the rows that carry one
    must not overlap in a way that hides which mentions failed.

    Contract: first the form's bucket from FORM_BUCKETS. A given name alone is then
    exactly one of `given_ordinary`, `given_also_word`, `given_plain`. A mention with
    prefix letters is `prefixed`, and also `prefix_on_name` or `prefix_on_title` by
    what the letters are attached to; on a group word it is `prefixed` only, because
    the group row already carries its own prediction. Last, `alone`.
    """
    names = [FORM_BUCKETS[gold.form]]
    if gold.form == "given":
        kind = next((name for name in ("ordinary", "also_word") if name in gold.classes), "plain")
        names.append(f"given_{kind}")
    if gold.prefix:
        names.append("prefixed")
        if gold.form in TITLE_FORMS:
            names.append("prefix_on_title")
        elif gold.form not in GROUP_WORDS:
            names.append("prefix_on_name")
    if gold.alone:
        names.append("alone")
    return names


def bucket_counts(documents: list[Document]) -> Counter[str]:
    """Count the counted mentions of a corpus, in all and per row of the report.

    Why: the pre-registration promises at least MIN_COUNTED_MENTIONS in all and
    MIN_PER_BUCKET per row that carries a prediction; a test holds the committed
    templates to it.

    Contract: key `all`, every form bucket and every name in TRAITS, present even at 0.
    """
    counts: Counter[str] = Counter({name: 0 for name in (*FORM_BUCKETS.values(), *TRAITS, "all")})
    for document in documents:
        for gold in document.gold:
            if gold.counted:
                counts["all"] += 1
                counts.update(buckets_of(gold))
    return counts
