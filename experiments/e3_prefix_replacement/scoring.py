"""Score prefix-preserving replacement against hand-written forms (experiment E3).

Why: build-plan.md section 11, E3. Phase 3 replaces a name by rewriting the
base the model segments out and keeping the prefix. This module holds the
hand-written forms, the replacement step and the pre-registered decision rule,
with no model in it, so every rule can be tested without one.

Known limits: see PREREGISTRATION.md. The gold prefix of each form is one
person's reading of the sentence.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path
from typing import NamedTuple

# build-plan.md section 11, E3: "Threshold: below 85 percent".
THRESHOLD_PERCENT = 85
# The plan predicts "90 percent"; PREREGISTRATION.md reads that as 85 to 95.
PREDICTED_HIGH_PERCENT = 95

# PREREGISTRATION.md: how many forms each category holds.
FORMS_PER_CATEGORY = {
    "single": 20,
    "chain": 20,
    "bare": 10,
    "trap": 15,
    "ordinary_word": 10,
    "article": 5,
    "construct": 10,
    "possessive_like": 10,
}
# build-plan.md section 11, E3: "breaking on construct state and possessive suffixes".
PREDICTED_BREAKING = ("construct", "possessive_like")
# build-plan.md Phase 3: the proclitic letters. A gold prefix holds nothing else.
PREFIX_LETTERS = frozenset("והבלמכש")
# PREREGISTRATION.md: the one category whose forms carry no prefix.
NO_PREFIX_CATEGORY = "bare"

WORD = re.compile(r"\w+")


class FormsError(ValueError):
    """A row of the forms file is malformed.

    Why: the forms are written by hand, and a typo in one would be scored as a
    model error. Raised by load_forms with the line number.
    """


class Form(NamedTuple):
    """One hand-written form: a sentence, the token under test, its gold prefix.

    Why: one row of forms.tsv. `target` is a single token of `sentence`;
    `prefix` is the leading part of `target` that replacement must keep, empty
    when there is none; `surrogate` replaces the rest.
    """

    id: str
    category: str
    sentence: str
    target: str
    prefix: str
    surrogate: str


def _checked(row: list[str], seen: set[str]) -> Form:
    """Turn one row into a Form, or raise FormsError naming what is wrong.

    Contract: `seen` holds the ids of earlier rows.
    """
    if len(row) != len(Form._fields):
        raise FormsError(f"expected {len(Form._fields)} columns, found {len(row)}")
    form = Form(*row)
    if form.category not in FORMS_PER_CATEGORY:
        raise FormsError(f"unknown category {form.category!r}")
    if form.id in seen:
        raise FormsError(f"duplicate id {form.id!r}")
    if WORD.findall(form.sentence).count(form.target) != 1:
        raise FormsError("the target must be exactly one token of the sentence")
    if not form.target.startswith(form.prefix) or form.target == form.prefix:
        raise FormsError("the target must be the prefix followed by a base")
    if not set(form.prefix) <= PREFIX_LETTERS:
        raise FormsError("the prefix holds a letter that is not a prefix letter")
    if (form.category == NO_PREFIX_CATEGORY) != (form.prefix == ""):
        raise FormsError(f"only a {NO_PREFIX_CATEGORY!r} form has no prefix, and it must have none")
    if not form.surrogate:
        raise FormsError("empty surrogate")
    return form


def load_forms(path: Path) -> list[Form]:
    """Read and validate the hand-written forms.

    Why: every row is checked before the model runs, so a malformed row stops
    the run and is never counted as a miss.

    Contract: `path` is a UTF-8 tab-separated file with no header and the
    columns of Form. Raises FormsError with the line number on the first bad
    row.
    """
    forms: list[Form] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for line, row in enumerate(csv.reader(handle, delimiter="\t", quoting=csv.QUOTE_NONE), 1):
            try:
                forms.append(_checked(row, {form.id for form in forms}))
            except FormsError as error:
                raise FormsError(f"line {line}: {error}") from None
    return forms


def replace_base(seg: tuple[str, ...], surrogate: str) -> str:
    """Rewrite the base of a segmented token, keeping its prefix.

    Why: this is the replacement Phase 3 specifies, "replacement rewrites the
    base only, so וליעקב becomes ולדוד".

    Contract: `seg` is the model's segmentation, prefix parts first and the
    base last. Returns the prefix parts joined, then `surrogate`. Raises
    ValueError for an empty `seg`.
    """
    if not seg:
        raise ValueError("a token has at least a base")
    return "".join(seg[:-1]) + surrogate


def model_segments(tokens: list[dict], target: str) -> tuple[tuple[str, ...], str | bool]:
    """Return the model's segmentation and suffix flag for the token `target`.

    Why: the model is given a whole sentence; this picks out the one token the
    form is about.

    Contract: `tokens` is the `tokens` list of the model's JSON output. Returns
    `(seg, suffix)`, where `suffix` is False or the model's suffix tag. Raises
    LookupError unless exactly one token equals `target`, which means the
    model split the sentence differently from load_forms: a harness fault, not
    a model error.
    """
    matches = [token for token in tokens if token["token"] == target]
    if len(matches) != 1:
        raise LookupError(f"{len(matches)} model tokens equal the target")
    return tuple(matches[0]["seg"]), matches[0]["morph"]["suffix"]


def is_correct(form: Form, seg: tuple[str, ...], suffix: str | bool) -> bool:
    """Say whether replacing the model's base gives the hand-written result.

    Why: the headline rule of PREREGISTRATION.md.

    Contract: True when the replaced token equals gold prefix plus surrogate
    and the model reports no suffix on the token. A reported suffix fails
    because every target is a name, and a name split into base and suffix
    would have only part of itself replaced.

    Known limits: the surrogate is on both sides of the comparison, so the
    rule comes to "the model's prefix letters equal the gold prefix letters,
    and no suffix". Nothing about the surrogate itself is measured: not its
    gender, and not how it is spelled after a prefix.
    """
    return replace_base(seg, form.surrogate) == form.prefix + form.surrogate and not suffix


def check_category_sizes(forms: list[Form]) -> None:
    """Refuse a set of forms whose categories are not the pre-registered sizes.

    Why: the report prints each category out of its pre-registered size, so a
    row deleted or moved to another category would lower a score without a
    model error behind it.

    Contract: raises FormsError naming the first category whose number of
    forms differs from FORMS_PER_CATEGORY.
    """
    for category, size in FORMS_PER_CATEGORY.items():
        found = sum(form.category == category for form in forms)
        if found != size:
            raise FormsError(f"category {category!r} holds {found} forms, pre-registered {size}")


def tally(
    forms: list[Form], token_lists: list[list[dict]]
) -> tuple[Counter[str], Counter[str], list[tuple[Form, tuple[str, ...], str | bool, str]]]:
    """Score every form against the model's tokens for its sentence.

    Why: the headline count is made here, apart from the model call, so it can
    be tested without a model.

    Contract: `token_lists[i]` is the model's token list for `forms[i]`.
    Returns `(strict, prefix_only, failures)`: the forms right under the
    headline rule and under the prefix-only rule, counted per category, and
    for every form that fails the headline rule `(form, seg, suffix,
    produced)`. Every form is in `strict` or in `failures`. Raises ValueError
    if the two lists differ in length, and LookupError naming the form id if
    its target is not exactly one of the model's tokens.
    """
    strict: Counter[str] = Counter()
    prefix_only: Counter[str] = Counter()
    failures = []
    for form, tokens in zip(forms, token_lists, strict=True):
        try:
            seg, suffix = model_segments(tokens, form.target)
        except LookupError as error:
            raise LookupError(f"{form.id}: {error}") from None
        produced = replace_base(seg, form.surrogate)
        if produced == form.prefix + form.surrogate:
            prefix_only[form.category] += 1
        if is_correct(form, seg, suffix):
            strict[form.category] += 1
        else:
            failures.append((form, seg, suffix, produced))
    return strict, prefix_only, failures


def verdict(correct: int, total: int) -> str:
    """Place `correct / total` against the plan's prediction.

    Why: the pre-registered decision rule, in code so it cannot drift once the
    number is known.

    Contract: "threshold_crossed" below 85 percent, "inside_prediction" from 85
    to 95 percent inclusive, otherwise "outside_prediction". Integer
    comparison, so nothing is rounded. Raises ValueError when `total` is not
    positive.
    """
    if total <= 0:
        raise ValueError("no form was scored")
    if correct * 100 < THRESHOLD_PERCENT * total:
        return "threshold_crossed"
    if correct * 100 <= PREDICTED_HIGH_PERCENT * total:
        return "inside_prediction"
    return "outside_prediction"


def breaks_where_predicted(errors: dict[str, int]) -> bool | None:
    """Say whether the errors fall where the plan predicts.

    Contract: `errors` maps a category to its error count. True when more than
    half of all errors are in the construct and possessive_like categories;
    None when there are no errors.
    """
    total = sum(errors.values())
    if total == 0:
        return None
    return sum(errors.get(category, 0) for category in PREDICTED_BREAKING) * 2 > total
