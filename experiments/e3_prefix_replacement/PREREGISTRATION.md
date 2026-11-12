# E3 pre-registration: prefix-preserving replacement

Committed before the model was run on `forms.tsv`. The commit order is the evidence.

## What the plan says

`build-plan.md` section 11:

> **E3. Prefix-preserving replacement.** 100 hand-written inflected forms (`וליעקב`, `מהכהן`, `שברק`, `כשדוד`, construct state, possessive suffixes). Segment, replace the base, keep the prefix, check agreement.
> Prediction: 90 percent correct, breaking on construct state and possessive suffixes.
> Threshold: below 85 percent, a hand-written rule layer is needed above the model.

"E3 failing grows Phase 3." It does not change the architecture.

## Readings fixed here

The plan leaves these open. **They are Claude's readings, not Achia's decisions.** Achia can amend any of them; an amendment means a new run, recorded as a new run.

| Open point | Reading |
|---|---|
| What a "form" is | One token inside a short invented sentence. The model segments in context, so a bare token would test something Phase 3 never does. |
| "Segment" | `dictabert-joint` at the revision in `docs/THIRD_PARTY.md`, the `seg` field of its JSON output: prefix parts first, base last. Syntax head off, as in E1. |
| "Replace the base, keep the prefix" | The prefix parts joined, then the surrogate. `scoring.replace_base`. |
| "Check agreement" | The replaced token must equal a hand-written expected token, which is the gold prefix plus the surrogate. Each surrogate was chosen by hand with the gender of the name it replaces, so agreement with the surrounding verbs holds by construction and is not measured. |
| "Correct" (headline) | The replaced token equals the expected token **and** the model reports no suffix on the token. Every target is a name, and Phase 3 splits "into prefix, base and suffix", so a name reported as base plus suffix would have only part of itself replaced. |
| Secondary number | The same without the suffix condition ("prefix only"). Reported, not used in the verdict. |
| "90 percent" | 85 to 95 percent inclusive counts as agreeing with the prediction. Above 95 is outside the prediction too, and is reported as such. |
| "Breaking on construct state and possessive suffixes" | More than half of all errors fall in the `construct` and `possessive_like` categories. |
| `מהכהן` | The plan lists `מה` among the proclitic combinations of Phase 3, so the gold prefix is `מה` and the base is `כהן`. |

## The 100 forms

All sentences are invented, in the register of Israeli legal writing, and name no real case. The names are common Israeli given names and surnames; two are public names used as names (`בן גוריון`, `בר אילן`).

| Category | Forms | What it holds |
|---|---|---|
| `single` | 20 | One proclitic letter on a name that does not start with a proclitic letter |
| `chain` | 20 | Two or three proclitic letters: `ול`, `וב`, `ומ`, `כש`, `וכש`, `לכש`, `מש`, `וש`, `של`, `שב`, `שמ`, `ושל` |
| `bare` | 10 | A name that starts with a proclitic letter and carries no prefix: `ברק`, `משה`, `הדר`, `לביא`, `שרה`, `כנרת`, `בן`, `מיכל`, `לירון`, `שירה` |
| `trap` | 15 | A prefix on a name that itself starts with a proclitic letter: `בברק`, `כשמשה`, `לבלהה` |
| `ordinary_word` | 10 | A prefix on a name that is an ordinary Hebrew word, several of them real words with the prefix attached: `לאור`, `משחר`, `מתום` |
| `article` | 5 | A surname written with the definite article: `הכהן`, `מהכהן`, `להלוי` |
| `construct` | 10 | A name of two words whose first word is a noun in construct state, with a prefix on it: `לבני ברק`, `מקרית שמונה`, `לבן גוריון`. The target is the first word; the surrogate is two words. |
| `possessive_like` | 10 | A prefix on a name that is spelled like a noun with a possessive suffix: `לאבי`, `מבני`, `לדודו`, `לעמי`. Where a reader could take it as the noun, a surname follows. |

The last two rows are how "construct state" and "possessive suffixes" were read. Hebrew names do not take a possessive suffix and have no construct form of their own, so the forms are the cases where a name looks like one to a segmenter.

## Decision rule

`scoring.verdict(correct, total)`, integer arithmetic, on the headline count:

- below 85 percent: `threshold_crossed`. Per the plan, a hand-written rule layer is needed above the model.
- 85 to 95 percent: `inside_prediction`.
- above 95 percent: `outside_prediction`.

A form where the model's tokens do not contain the target exactly once stops the run. It is a harness fault and is fixed in the harness, never scored.

## Known limits

- 100 forms: one form is one percentage point. A result within two or three forms of 85 is not distinguishable from 85.
- One person wrote the sentences, the gold prefixes and the scoring rule. The forms show where the model breaks; they are not a sample of how often each form occurs in real documents.
- Legal register only. No medical or accounting sentences.
- Not tested: a surrogate that starts with a consonantal vav (`ורד` after a prefix is written `לוורד`), niqqud, geresh names (`ג'ורג'`), names with a maqaf, Latin-script names.
- The model is the PyTorch FP32 model. A quantized model (E2) is a different model and gets its own run.
