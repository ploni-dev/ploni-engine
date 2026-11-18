"""The real decisions of experiment E6, with their answer key, in the shape E5's scorer reads.

Why: E5 measured its methods on generated text, where a script knows where every name is.
E6 measures the same methods on twenty real decisions, where readers mark the names
(PREREGISTRATION.md). This module is where the two meet: it reads a real document and its
labels into the `Document` and `Gold` of E4's generator, so that E5's code scores them
unchanged.

Contract: the documents and every file with their text are outside the repository, in a
corpus folder given by the caller: `docs/<id>.docx`, and `key/<id>.tsv` for the key. This
module holds, as constants, which documents there are, which pile each is in and the
SHA-256 of each file. It prints nothing, and an error names a document's id and line
numbers only, never a word of a document.

Known limits: a label is taken at its word. Nothing here can tell a name that was labelled
wrongly from one that was labelled well, or see a name that no label marks.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# `python -I` drops the script folder. E1's reader, E4's shapes and E5's steps are reused, not copied.
sys.path[:0] = [str(HERE), *(str(HERE.parent / name) for name in ("e5_methods", "e4_planted_names", "e1_hebrew_recall"))]

import corpus
import generate

import layers

# CLAUDE.md, Hard constraints: no real document in the repository, in any form.
REPOSITORY = HERE.parents[1]
# PREREGISTRATION.md, "The two piles": the draw orders the ids of a topic by the SHA-256 of `<SEED>:<id>`.
SEED = "e6-2026-11-18"
OPEN = "open"
CLOSED = "closed"
# id -> (topic, pile, SHA-256 of the file), as PREREGISTRATION.md lists them. The piles are
# what `draw` gives for these ids and topics; a test holds the table to it.
DOCUMENTS = {
    "r01": ("sale", CLOSED, "deaf7f557772809af9822a6c99a038b1ae2c4734f91ce8ffff56d6c4de4a2dbb"),
    "r02": ("sale", OPEN, "ddee0f33b3f5c3f6d3dd48ec408bdfeab011a83a5c74d0d21565792ae989cbb1"),
    "r03": ("sale", OPEN, "54816a17717a7ed9729b64f0dd0a1b67ea493aae4213cd270217351ef776631a"),
    "r04": ("sale", CLOSED, "e2a01694e133444aa0ece79b56f881341d6075dc6894b5074d605362af22f90e"),
    "r05": ("sale", OPEN, "bb698634ca515ba51365ee66f67ecb28f8d157bb179ed5f6b4b91bb0e0881340"),
    "r06": ("sale", CLOSED, "ae132d11ac0a1ceef88402c93a6a46661962e464f07da2bb217f0dbcab8bdd02"),
    "r08": ("defamation", OPEN, "d6194391d7f47b1e5f5b87d396792dc946b2df576c0674017111b5e370d2a986"),
    "r10": ("defamation", CLOSED, "dd027d9b4615d6922365579d0e3829cb237705f216789c2206bc4f3d32241aa4"),
    "r11": ("defamation", OPEN, "33e5f914bcc3557a6e872a9badce13a42ad07d5177eb47b7aa7c024a1a197511"),
    "r12": ("defamation", CLOSED, "283278209ebf4cb5ca0ff63add36f79c421cdc94da55201d7f38d1348da10d19"),
    "r13": ("defamation", OPEN, "9aed3fd2497d46057f9bfe74292f51d2b29b82c13f6023648c1fd59ecdb5ab5c"),
    "r14": ("defamation", CLOSED, "db3b394ffc1eabf2ba3730048e965a08d4eceb3c2b32eba2a8d9178ccc601cb0"),
    "r15": ("tenancy", OPEN, "50d5bb6f0b1b8d24528c2a41cbba15de322817855c2eb6781a4e77e92c8bcf89"),
    "r16": ("tenancy", CLOSED, "9102dfe61a806fc15b51ebbc960ed45b0d3e9b1b9cb90edcbd6c6e1bddd419a4"),
    "r17": ("tenancy", OPEN, "8d9e6ea6e6311bde9694b2b63143eb352b1d3a81544fc10ed35c9361f9098056"),
    "r18": ("tenancy", CLOSED, "22438eabad6906d09c007074230ebe8d1a1f52704d4a3203e7fc619c734a3401"),
    "r19": ("tenancy", OPEN, "4c46bfa9517007424da33bff36b6545804d36c0b670726b0e8a27dc092248795"),
    "r20": ("tenancy", CLOSED, "7f70750c9078e85fc60911eb0d780fef7c19a1ad31fd738e203a97143c6d3405"),
    "r21": ("accident", CLOSED, "225c379235ee5ae426e94f82b95a437b05a63f230ec520fd5c0cba0c28a3d730"),
    "r23": ("accident", OPEN, "28b71ff258eb36dc745fc3edfac4ce368fce86599ee81c0508e82c350418001c"),
}
# A document that a labeller found to fail the subject check is deleted and named here, so
# that a file gone for any other reason stops the run (PREREGISTRATION.md, "The subject check").
DELETED: frozenset[str] = frozenset()
# The SHA-256 of every key file, committed before any detector is run (PREREGISTRATION.md, "Frozen").
FROZEN = HERE / "key_sha256.tsv"
# The methods that are judged on the closed pile, committed before that pile is touched.
CHOSEN = HERE / "results" / "CHOSEN.md"
COUNTED_KINDS = ("private", "public")
NOT_COUNTED = "not_counted"
HEADER = ["paragraph", "first", "last", "text", "person", "kind"]
RUN = re.compile(r"\S+")
LETTERS_AT_THE_END = re.compile(r"[א-ת]*$")
# E4's form for a name that is neither after a group word nor a given name alone. A real
# label does not say which form a name has; E6 has rows of its own (score_real.ROWS).
FORM = "full"


class LabelError(ValueError):
    """A label file that cannot be taken as it is.

    Why: a label in the wrong place would be scored as a name the detectors missed.
    Contract: the message names the document and line numbers with a reason each, and
    holds no word of the file.
    """


class CorpusError(ValueError):
    """The corpus folder is not what the pre-registration describes.

    Contract: the message names a document's id or a folder, never a word of a document.
    """


def draw(topics: dict[str, str], seed: str = SEED) -> dict[str, str]:
    """Put every document into the open or the closed pile.

    Why: which documents may be learned from must not follow anything in them, so the
    draw looks at ids only (PREREGISTRATION.md, "The two piles").

    Contract: `topics` maps an id to its topic. Within a topic the ids are ordered by the
    SHA-256 of `<seed>:<id>` as a hexadecimal string; the first half is open, the rest
    closed, so the odd document of a topic is closed. Returns id -> pile.
    """
    piles = {}
    for topic in set(topics.values()):
        ordered = sorted(
            (doc_id for doc_id, name in topics.items() if name == topic),
            key=lambda doc_id: hashlib.sha256(f"{seed}:{doc_id}".encode()).hexdigest(),
        )
        piles.update({doc_id: OPEN if position < len(ordered) // 2 else CLOSED for position, doc_id in enumerate(ordered)})
    return piles


def runs(paragraph: str) -> list[tuple[int, int]]:
    """Return the place of every run of characters without white space, as (start, end).

    Why: the worksheet numbers these runs and a label names them, so both must cut a
    paragraph in the same way.
    """
    return [(match.start(), match.end()) for match in RUN.finditer(paragraph)]


def worksheet(paragraphs: list[str]) -> str:
    """Write the text a labeller reads: every paragraph and every run with its number.

    Why: a label names a place by numbers that stand in the worksheet, so that nobody
    counts characters by hand.

    Contract: per paragraph a line `¶K`, K from 0, then one line with every run behind
    its number in brackets, from 0. It says nothing about the pile.
    """
    lines = []
    for index, paragraph in enumerate(paragraphs):
        numbered = " ".join(f"[{number}]{paragraph[start:end]}" for number, (start, end) in enumerate(runs(paragraph)))
        lines += [f"¶{index}", numbered]
    return "".join(line + "\n" for line in lines)


def _place(fields: list[str], paragraphs: list[str]) -> tuple[int, int, int]:
    """Find where the name of one label stands.

    Why: the worksheet shows every gap as one space, and the text may hold two spaces,
    a tab or a line break there. A label copied from the worksheet must still fit.

    Contract: the first three fields are the paragraph, the first run and the last run,
    the fourth is the name, its words separated by one space each. In the text any
    white space may stand between two words of the name. Returns (paragraph, start,
    end). Raises ValueError, with a reason that holds none of the fields, when a
    number is no number or names nothing, when the name is empty or has white space
    around it, when it does not stand exactly once inside those runs, or when it
    leaves the first or the last run untouched.
    """
    try:
        paragraph, first, last = (int(field) for field in fields[:3])
    except ValueError:
        raise ValueError("a place that is not a number") from None
    if not 0 <= paragraph < len(paragraphs):
        raise ValueError("no such paragraph")
    found = runs(paragraphs[paragraph])
    if not 0 <= first <= last < len(found):
        raise ValueError("no such runs")
    low, high = found[first][0], found[last][1]
    if not fields[3] or fields[3] != fields[3].strip():
        raise ValueError("the name is empty or has white space around it")
    pattern = r"\s+".join(re.escape(word) for word in fields[3].split())
    matches = list(re.finditer(pattern, paragraphs[paragraph][low:high]))
    if len(matches) != 1:
        raise ValueError("the name does not stand exactly once in its runs")
    start, end = low + matches[0].start(), low + matches[0].end()
    if start >= found[first][1] or end <= found[last][0]:
        raise ValueError("the runs reach further than the name")
    return paragraph, start, end


def _attached(paragraph: str, start: int, end: int) -> str:
    """Return the letters attached before a name.

    Why: a name cut out of the middle of a word (`לוי` out of `לוין`) is a slip of the
    labeller, and it would be scored as a name.

    Contract: the Hebrew letters that stand right before the name. Raises ValueError when
    one of them is no attached letter (ו ה ב ל מ כ ש), or when a Hebrew letter follows
    the name.

    Known limits: a name cut after letters that could be attached (`רק` out of `ברק`)
    passes.
    """
    before = LETTERS_AT_THE_END.search(paragraph[:start]).group()
    if set(before) - set(layers.PREFIX_LETTERS):
        raise ValueError("the name begins inside a word")
    if end < len(paragraph) and "א" <= paragraph[end] <= "ת":
        raise ValueError("the name ends inside a word")
    return before


def _gold(fields: list[str], paragraphs: list[str]) -> generate.Gold:
    """Turn one label line into a name of the key.

    Contract: six fields as in HEADER. The name is taken as it stands in the text, with
    the white space it has there. A counted name (`private` or `public`) carries
    its person and its kind as its one class; one that is `not_counted` has the person
    `*`, as in E4. `alone` says that nothing else on the line is a letter. Raises
    ValueError with a reason that holds none of the fields.
    """
    if len(fields) != len(HEADER):
        raise ValueError("not six columns")
    paragraph, start, end = _place(fields, paragraphs)
    person, kind = fields[4], fields[5]
    if kind not in (*COUNTED_KINDS, NOT_COUNTED):
        raise ValueError("no such kind")
    counted = kind != NOT_COUNTED
    if counted and person in ("", "-"):
        raise ValueError("a counted name with no person")
    text = paragraphs[paragraph]
    alone = not any(character.isalpha() for character in text[:start] + text[end:])
    classes = frozenset({kind}) if counted else frozenset()
    return generate.Gold(paragraph, start, end, text[start:end], person if counted else "*", FORM, _attached(text, start, end), alone, classes, counted)


def _clashes(gold: dict[int, generate.Gold]) -> dict[int, str]:
    """Find the lines that cannot stand beside an earlier line.

    Contract: `gold` maps a line number to its name. Returns line number -> reason for a
    name that shares a character with any name that begins before it, and for a person
    who has another kind than on an earlier line.
    """
    bad = {}
    kinds: dict[str, frozenset[str]] = {}
    for number, item in gold.items():
        if item.counted and kinds.setdefault(item.person, item.classes) != item.classes:
            bad[number] = "this person has another kind on an earlier line"
    ordered = sorted(gold.items(), key=lambda pair: (pair[1].paragraph, pair[1].start, pair[1].end))
    paragraph, furthest = -1, 0
    for number, item in ordered:
        if item.paragraph != paragraph:
            paragraph, furthest = item.paragraph, 0
        if item.start < furthest:
            bad[number] = "shares characters with another label"
        furthest = max(furthest, item.end)
    return bad


def parse_labels(doc_id: str, text: str, paragraphs: list[str]) -> list[generate.Gold]:
    """Read the labels of one document against its paragraphs.

    Why: the labels are typed by a reader. Each is checked against the text before it
    becomes part of the key, and all bad lines are named at once.

    Contract: `text` is a file with the header HEADER and one label per line, the fields
    separated by tabs: paragraph, first run, last run (as the worksheet numbers them), the
    name as it stands there, a key for the person, and `private`, `public` or
    `not_counted`. Returns the names in reading order. Raises LabelError naming `doc_id`
    and every bad line by its number in the file, with a reason.
    """
    lines = text.splitlines()
    if not lines or lines[0].split("\t") != HEADER:
        raise LabelError(f"{doc_id}: the first line is not the header")
    gold: dict[int, generate.Gold] = {}
    bad: dict[int, str] = {}
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        try:
            gold[number] = _gold(line.split("\t"), paragraphs)
        except ValueError as error:
            bad[number] = str(error)
    bad.update(_clashes(gold))
    if bad:
        raise LabelError(f"{doc_id}: bad lines " + ", ".join(f"{number} ({reason})" for number, reason in sorted(bad.items())))
    return sorted(gold.values(), key=lambda item: (item.paragraph, item.start))


def ids(pile: str | None = None) -> list[str]:
    """Return the ids of the documents that are still in the corpus, in order.

    Why: every command goes through the documents in the same order and leaves out
    the same deleted ones.

    Contract: of one pile, or of both when `pile` is None. Raises ValueError for a pile
    that does not exist.
    """
    if pile not in (None, OPEN, CLOSED):
        raise ValueError(f"no such pile: {pile}")
    return sorted(doc_id for doc_id, (_, of, _) in DOCUMENTS.items() if doc_id not in DELETED and pile in (None, of))


def read_document(corpus_dir: Path, doc_id: str) -> list[str]:
    """Read one decision into its paragraphs, by E1's reader.

    Why: every place in a label and in a run file is counted in these paragraphs, so the
    file must be the one that was fetched.

    Contract: reads `docs/<doc_id>.docx`. Raises CorpusError when the corpus folder lies
    inside the repository, when the file is missing or its SHA-256 is not the one in
    DOCUMENTS, and `corpus.DocumentReadError` as E1's reader does.
    """
    if corpus.is_inside(corpus_dir, REPOSITORY):
        raise CorpusError("the corpus folder lies inside the repository")
    path = corpus_dir / "docs" / f"{doc_id}.docx"
    if not path.is_file():
        raise CorpusError(f"{doc_id}: the file is missing and is not listed as deleted")
    if hashlib.sha256(path.read_bytes()).hexdigest() != DOCUMENTS[doc_id][2]:
        raise CorpusError(f"{doc_id}: the file is not the one that was fetched")
    return corpus.read_checked(doc_id, path)


def frozen_hashes() -> dict[str, str]:
    """Return the committed SHA-256 of every key file, by document.

    Why: a key is the frozen one when its hash is the one that was committed before
    the first run, not when a file by its name is in the folder.

    Contract: FROZEN holds a line per document, the id and the hash separated by white
    space. Raises CorpusError when the file does not exist.
    """
    if not FROZEN.is_file():
        raise CorpusError(f"the key is not frozen yet: {FROZEN.name} is missing")
    return dict(line.split() for line in FROZEN.read_text(encoding="utf-8").splitlines() if line.strip())


def read_labels(folder: Path, doc_id: str, paragraphs: list[str], expected: str | None = None) -> list[generate.Gold]:
    """Read the label file of one document from a folder.

    Why: the two labellers' files and the key are the same kind of file, read and
    checked by the same code.

    Contract: reads `<folder>/<doc_id>.tsv`, UTF-8. With `expected`, the SHA-256 of the
    file must be that. Raises CorpusError when the file is missing or has another hash,
    and LabelError as `parse_labels` does.
    """
    path = folder / f"{doc_id}.tsv"
    if not path.is_file():
        raise CorpusError(f"{doc_id}: no label file in {folder.name}")
    raw = path.read_bytes()
    if expected is not None and hashlib.sha256(raw).hexdigest() != expected:
        raise CorpusError(f"{doc_id}: the key file is not the frozen one")
    return parse_labels(doc_id, raw.decode("utf-8-sig"), paragraphs)


def load(corpus_dir: Path, pile: str, key_dir: Path | None = None, frozen: bool = True) -> list[generate.Document]:
    """Read the documents of one pile with their key.

    Why: the one way a real document reaches a detector or the scorer, so that both see
    the same text and no run is made before the key exists.

    Contract: the documents of `pile` in id order, each as E4's `Document`: the id, the
    topic as its template, the kind `judgment`, the paragraphs, and the key as `gold`.
    The key is read from `key_dir`, or from `key/` in the corpus folder. With `frozen`
    every key file must have the hash that is committed in FROZEN. Raises ValueError for
    a pile that does not exist, and CorpusError and LabelError as the readers do.
    """
    expected = frozen_hashes() if frozen else {}
    documents = []
    for doc_id in ids(pile):
        paragraphs = read_document(corpus_dir, doc_id)
        # A document with no line in the frozen table has a hash that no file can have.
        want = expected.get(doc_id, "") if frozen else None
        gold = read_labels(key_dir or corpus_dir / "key", doc_id, paragraphs, want)
        documents.append(generate.Document(doc_id, DOCUMENTS[doc_id][0], "judgment", 1, paragraphs, gold))
    return documents


def check_closed(pile: str) -> None:
    """Refuse the closed pile before the methods to be judged on it are written down.

    Why: the closed pile is the fair judge only while nothing that was run or scored on
    it could have shaped the choice (PREREGISTRATION.md, "The two piles").

    Contract: raises ValueError for the closed pile while CHOSEN does not exist.

    Known limits: the file must also be committed, and that is not checked here.
    """
    if pile == CLOSED and not CHOSEN.is_file():
        raise ValueError(f"the closed pile is not touched before {CHOSEN.name} is committed")
