"""Test matrix for scoring.py (experiment E3, build-plan.md section 11).

replace_base(seg, surrogate)
  EC1  no prefix                      ("יעקב",) -> surrogate
  EC2  one prefix part                ("ל", "יעקב")
  EC3  several prefix parts           ("ו", "ל", "יעקב") and ("ול", "יעקב")
  EC4  multi-word surrogate           ("ל", "בני") + "קרית גת"
  B1   empty seg                      -> ValueError
  Hebrew axes: name starting with a prefix letter and carrying none (ברק),
  ordinary-word name (אור), prefix letter twice (בברק)
  Invariant, 500 generated cases: result == prefix + surrogate

model_segments(tokens, target)
  EC1  target present once            -> (seg, suffix)
  EC2  suffix reported as a string    -> suffix "PRON" kept
  E1   target absent                  -> LookupError
  E2   target present twice           -> LookupError

is_correct(form, seg, suffix)
  EC1  same prefix, no suffix         -> True
  EC2  prefix split differently but same letters ("ו","ל" vs "ול") -> True
  EC3  model strips a letter of the name (בברק -> בב + רק)        -> False
  EC4  model misses the prefix (לאור kept whole)                    -> False
  EC5  right prefix, suffix reported (לאבי, suffix PRON)            -> False
  Invariant, 500 generated cases: True iff prefixes equal and no suffix

verdict(correct, total)
  B1  84/100 -> threshold_crossed     B2  85/100 -> inside_prediction
  B3  95/100 -> inside_prediction     B4  96/100 -> outside_prediction
  B5  total 0 -> ValueError           B6  849/1000 -> threshold_crossed (no rounding up)

breaks_where_predicted(errors)
  EC1  no errors -> None
  B1   exactly half in construct and possessive_like -> False
  B2   one more than half -> True

load_forms(path)
  EC1  the shipped forms.tsv: 100 rows, the pre-registered count per category
  E1   wrong column count             E2  unknown category
  E3   duplicate id                   E4  target absent from the sentence
  E5   target twice in the sentence   E6  target does not start with the prefix
  E7   prefix is the whole target     E8  empty surrogate
  E9   a prefix holding a letter that is not a prefix letter (לי for ליעקב)
  E10  a row outside `bare` with no prefix    E11  a `bare` row with a prefix
  Adversarial: target next to punctuation still counts once (יעקב, then a full stop)

check_category_sizes(forms)
  EC1  the shipped forms.tsv          -> accepted
  E1   one form missing               -> FormsError naming the category

tally(forms, token_lists)
  EC1  one right form, one wrong prefix, one right prefix with a suffix ->
       strict and prefix-only counts per category, both failures listed, and
       right plus failures equals the number of forms
  E1   fewer or more sentences than forms -> ValueError, nothing dropped silently
  E2   a target the model split differently -> LookupError naming the form id
"""

import random
from collections import Counter
from pathlib import Path

import pytest

import scoring
from scoring import Form, FormsError

HEBREW = "אבגדהוזחטיכלמנסעפצקרשת"
PREFIXES = ["", "ו", "ל", "ב", "מ", "כ", "ש", "ה", "ול", "וב", "ומ", "כש", "וכש", "לכש", "מש", "שה"]
GENERATED_CASES = 500  # CLAUDE.md: invariants get 500 generated cases
SEED = 20261111


def word(rng: random.Random) -> str:
    return "".join(rng.choice(HEBREW) for _ in range(rng.randint(2, 7)))


def form(target="ליעקב", prefix="ל", category="single") -> Form:
    return Form("x01", category, f"המכתב נשלח {target} אתמול.", target, prefix, "נתן")


# replace_base


@pytest.mark.parametrize(
    ("seg", "surrogate", "expected"),
    [
        (("יעקב",), "נתן", "נתן"),
        (("ל", "יעקב"), "נתן", "לנתן"),
        (("ו", "ל", "יעקב"), "דוד", "ולדוד"),
        (("ול", "יעקב"), "דוד", "ולדוד"),
        (("ל", "בני"), "קרית גת", "לקרית גת"),
        (("ברק",), "גדעון", "גדעון"),
        (("ל", "אור"), "דניאל", "לדניאל"),
        (("ב", "ברק"), "גדעון", "בגדעון"),
    ],
)
def test_replace_base_keeps_the_prefix(seg, surrogate, expected):
    assert scoring.replace_base(seg, surrogate) == expected


def test_b1_replace_base_rejects_empty_seg():
    with pytest.raises(ValueError):
        scoring.replace_base((), "נתן")


def test_invariant_replace_base_is_prefix_plus_surrogate():
    rng = random.Random(SEED)  # noqa: S311 seeded on purpose, so the same input is drawn on every run
    for _ in range(GENERATED_CASES):
        prefix, base, surrogate = rng.choice(PREFIXES), word(rng), word(rng)
        seg = (*prefix, base) if rng.random() < 0.5 else tuple(filter(None, (prefix, base)))
        assert scoring.replace_base(seg, surrogate) == prefix + surrogate


# model_segments


def token(text, seg, suffix=False):
    return {"token": text, "seg": list(seg), "morph": {"suffix": suffix}}


def test_ec1_model_segments_finds_the_target():
    tokens = [token("המכתב", ["ה", "מכתב"]), token("ליעקב", ["ל", "יעקב"])]
    assert scoring.model_segments(tokens, "ליעקב") == (("ל", "יעקב"), False)


def test_ec2_model_segments_keeps_a_reported_suffix():
    assert scoring.model_segments([token("לאבי", ["ל", "אבי"], "PRON")], "לאבי") == (("ל", "אבי"), "PRON")


@pytest.mark.parametrize("texts", [["המכתב"], ["ליעקב", "ליעקב"]])
def test_e1_e2_model_segments_needs_exactly_one_match(texts):
    with pytest.raises(LookupError):
        scoring.model_segments([token(t, [t]) for t in texts], "ליעקב")


# is_correct


@pytest.mark.parametrize(
    ("target", "prefix", "seg", "suffix", "expected"),
    [
        ("ליעקב", "ל", ("ל", "יעקב"), False, True),
        ("וליעקב", "ול", ("ו", "ל", "יעקב"), False, True),
        ("בברק", "ב", ("בב", "רק"), False, False),
        ("לאור", "ל", ("לאור",), False, False),
        ("לאבי", "ל", ("ל", "אבי"), "PRON", False),
    ],
)
def test_is_correct(target, prefix, seg, suffix, expected):
    assert scoring.is_correct(form(target, prefix), seg, suffix) is expected


def test_invariant_is_correct_iff_same_prefix_and_no_suffix():
    rng = random.Random(SEED)  # noqa: S311 seeded on purpose, so the same input is drawn on every run
    for _ in range(GENERATED_CASES):
        gold, guess, base = rng.choice(PREFIXES), rng.choice(PREFIXES), word(rng)
        suffix = rng.choice([False, False, "PRON"])
        seg = tuple(filter(None, (guess, (gold + base)[len(guess):] or base)))
        assert scoring.is_correct(form(gold + base, gold), seg, suffix) is (guess == gold and not suffix)


# verdict


@pytest.mark.parametrize(
    ("correct", "total", "expected"),
    [
        (84, 100, "threshold_crossed"),
        (85, 100, "inside_prediction"),
        (95, 100, "inside_prediction"),
        (96, 100, "outside_prediction"),
        (849, 1000, "threshold_crossed"),
    ],
)
def test_verdict_boundaries(correct, total, expected):
    assert scoring.verdict(correct, total) == expected


def test_b5_verdict_rejects_an_empty_run():
    with pytest.raises(ValueError):
        scoring.verdict(0, 0)


# Tests of breaks_where_predicted.


@pytest.mark.parametrize(
    ("errors", "expected"),
    [
        ({}, None),
        ({"construct": 1, "possessive_like": 1, "trap": 2}, False),
        ({"construct": 2, "possessive_like": 1, "trap": 2}, True),
    ],
)
def test_breaks_where_predicted(errors, expected):
    assert scoring.breaks_where_predicted(errors) is expected


# load_forms


def test_ec1_shipped_forms_match_the_preregistered_counts():
    forms = scoring.load_forms(Path(scoring.__file__).with_name("forms.tsv"))
    counts = {c: sum(f.category == c for f in forms) for c in scoring.FORMS_PER_CATEGORY}
    assert counts == scoring.FORMS_PER_CATEGORY
    assert len(forms) == 100


GOOD = "a01\tsingle\tהמכתב נשלח ליעקב.\tליעקב\tל\tנתן"


@pytest.mark.parametrize(
    "rows",
    [
        ["a01\tsingle\tהמכתב נשלח ליעקב.\tליעקב\tל"],
        [GOOD.replace("single", "simple")],
        [GOOD, GOOD],
        [GOOD.replace("נשלח ליעקב", "נשלח לדוד")],
        [GOOD.replace("המכתב", "ליעקב")],
        [GOOD.replace("\tל\t", "\tמ\t")],
        [GOOD.replace("\tל\t", "\tליעקב\t")],
        [GOOD.replace("\tנתן", "\t")],
        [GOOD.replace("\tל\t", "\tלי\t")],
        [GOOD.replace("\tל\t", "\t\t")],
        [GOOD.replace("single", "bare")],
    ],
    ids=[
        "columns", "category", "duplicate_id", "absent", "twice", "prefix", "whole_target", "surrogate",
        "prefix_letter", "missing_prefix", "bare_with_prefix",
    ],
)
def test_load_forms_rejects_a_bad_row(tmp_path, rows):
    path = tmp_path / "forms.tsv"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(FormsError):
        scoring.load_forms(path)


def test_adversarial_target_next_to_punctuation_counts_once(tmp_path):
    path = tmp_path / "forms.tsv"
    path.write_text(GOOD + "\n", encoding="utf-8")
    assert scoring.load_forms(path) == [Form("a01", "single", "המכתב נשלח ליעקב.", "ליעקב", "ל", "נתן")]


# check_category_sizes


def test_ec1_shipped_forms_have_the_preregistered_sizes():
    scoring.check_category_sizes(scoring.load_forms(Path(scoring.__file__).with_name("forms.tsv")))


def test_e1_a_missing_form_is_named_by_its_category():
    forms = scoring.load_forms(Path(scoring.__file__).with_name("forms.tsv"))
    without_one_trap = [f for f in forms if f.id != next(f.id for f in forms if f.category == "trap")]
    with pytest.raises(FormsError, match="trap"):
        scoring.check_category_sizes(without_one_trap)


# tally


TALLY_FORMS = [
    Form("a01", "single", "המכתב נשלח ליעקב אתמול.", "ליעקב", "ל", "נתן"),
    Form("d01", "trap", "פגשנו בברק אתמול.", "בברק", "ב", "דוד"),
    Form("h01", "possessive_like", "מסרנו לאבי את המכתב.", "לאבי", "ל", "יוסי"),
]
TALLY_TOKENS = [
    [token("המכתב", ["ה", "מכתב"]), token("ליעקב", ["ל", "יעקב"])],
    [token("בברק", ["בב", "רק"])],
    [token("לאבי", ["ל", "אבי"], "PRON")],
]


def test_ec1_tally_counts_each_rule_and_lists_every_failure():
    strict, prefix_only, failures = scoring.tally(TALLY_FORMS, TALLY_TOKENS)
    assert strict == Counter(single=1)
    assert prefix_only == Counter(single=1, possessive_like=1)
    assert failures == [
        (TALLY_FORMS[1], ("בב", "רק"), False, "בבדוד"),
        (TALLY_FORMS[2], ("ל", "אבי"), "PRON", "ליוסי"),
    ]
    assert sum(strict.values()) + len(failures) == len(TALLY_FORMS)


@pytest.mark.parametrize("token_lists", [TALLY_TOKENS[:2], [*TALLY_TOKENS, TALLY_TOKENS[0]]])
def test_e1_tally_refuses_a_different_number_of_sentences(token_lists):
    with pytest.raises(ValueError):
        scoring.tally(TALLY_FORMS, token_lists)


def test_e2_tally_names_the_form_whose_target_the_model_split():
    with pytest.raises(LookupError, match="d01"):
        scoring.tally(TALLY_FORMS, [TALLY_TOKENS[0], TALLY_TOKENS[0], TALLY_TOKENS[2]])
