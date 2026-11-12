"""Check that the harness reads the model correctly, on text written for the check.

Why: Phase 3 of the plan names "whether the joint NER head is being read
correctly" as the first thing to suspect if recall is low. That question is
answered here, before the real documents, so a harness fault cannot later be
mistaken for a model result. It also verifies the claim in PREREGISTRATION.md
that running the NER head alone gives the same entities as running every head.

Contract: `python -I smoke.py --model-dir M`. Exits non-zero if an entity's
offsets fall inside a run of letters of the input, if the output with the
syntax head off differs from the output with every head on, or if no person is
found in the first sentence or one is found in the last. Prints the entities, which is allowed here because
every sentence below was invented for this file and names no real person.

Known limits: this is not a measurement. Seven invented sentences say nothing
about recall, and no number printed here belongs in the E1 result.
"""

from __future__ import annotations

import argparse
import gc
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # see run_model.py: `python -I` drops the script folder

from run_model import load_ner_model, window_entities
from worksheet import PERSON_LABEL

# Invented for this check. Chosen to exercise a plain name, a title, attached
# prefixes, ordinary-word names, a geresh name, an organisation and a place.
SENTENCES = [
    'עו"ד מיכל אברהמי הגישה את הבקשה בשם המבקש יעקב שטרן.',
    "המסמך נמסר לרחל ולדוד בן עמי ביום ראשון.",
    "כשברק הגיע למשרד, טל ושחר כבר חיכו לו.",
    "ג'ורג' קליין עובד בבנק הפועלים בתל אביב.",
    "השופטת שרה לביא דחתה את טענות הנתבעת.",
    "ד״ר אור גולן בדק את המטופלת בבית החולים סורוקה.",
    "אין במשפט הזה שום שם של אדם.",
]


def entities_on_token_boundaries(text: str, entities: list[tuple[int, int, str]]) -> bool:
    """Say whether no entity starts or ends inside a run of letters or digits.

    Why: the model labels whole tokens, and its tokenizer splits only at
    whitespace and punctuation, so an offset inside a run of letters means the
    offsets are being read against the wrong string.

    Contract: `entities` are (start, end, label) in characters of `text`. An
    entity may end before a full stop or start after a quote.
    """
    return all(
        0 <= start < end <= len(text)
        and (start == 0 or not text[start - 1].isalnum())
        and (end == len(text) or not text[end].isalnum())
        and not text[start].isspace()
        and not text[end - 1].isspace()
        for start, end, _ in entities
    )


def finds_people_only_where_named(per_sentence: list[list[tuple[int, int, str]]]) -> bool:
    """Say whether the model names a person in the first sentence and none in the last.

    Why: the other two checks are true for empty output, so a wrong label map
    or a head that labels everything `O` would pass them.

    Contract: `per_sentence` is in SENTENCES order. The first sentence names
    two people; the last was written to name nobody.
    """
    labels = [{label for _, _, label in entities} for entities in per_sentence]
    return PERSON_LABEL in labels[0] and PERSON_LABEL not in labels[-1]


def predictions(model_dir: Path, *, all_heads: bool) -> list[list[tuple[int, int, str]]]:
    """Return the entities for every smoke sentence under one head configuration.

    Why: the two configurations are loaded one after the other, not together,
    because the reference laptop cannot hold two copies of the model.

    Contract: one list per sentence, in SENTENCES order. The model is released
    before returning.
    """
    model, tokenizer = load_ner_model(model_dir, all_heads=all_heads)
    result = [window_entities(model, tokenizer, sentence) for sentence in SENTENCES]
    del model
    gc.collect()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-dir", type=Path, required=True)
    model_dir = parser.parse_args().model_dir

    ner_only = predictions(model_dir, all_heads=False)
    for sentence, entities in zip(SENTENCES, ner_only):
        print(sentence)
        for start, end, label in entities:
            print(f"    {label:<6} {start:>3}:{end:<3} {sentence[start:end]}")
    aligned = all(entities_on_token_boundaries(s, e) for s, e in zip(SENTENCES, ner_only))
    same = ner_only == predictions(model_dir, all_heads=True)
    finds = finds_people_only_where_named(ner_only)
    print(f"offsets on token boundaries: {aligned}")
    print(f"syntax-off output equals all-heads output: {same}")
    print(f"a person is found where one is named, and none where none is: {finds}")
    sys.exit(0 if aligned and same and finds else 1)
