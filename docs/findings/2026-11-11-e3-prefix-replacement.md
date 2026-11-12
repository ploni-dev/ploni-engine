# Finding: E3 prefix-preserving replacement is 94 of 100, and breaks on stacked prefixes, not on construct or possessive forms

## What was being measured

`build-plan.md` section 11, experiment E3: whether `dicta-il/dictabert-joint` segments a prefixed name well enough that replacing the base and keeping the prefix gives the right token.

100 hand-written forms, each one token inside an invented sentence, in eight categories. The forms, the scoring rule and the readings of the plan's open points are in `experiments/e3_prefix_replacement/`, committed as `bb3482b` before the model was run on them.

## Prediction and threshold

As stated before the run (`build-plan.md` section 11, and `experiments/e3_prefix_replacement/PREREGISTRATION.md` at `bb3482b`):

- Prediction: 90 percent correct, read as 85 to 95 inclusive, breaking on construct state and possessive suffixes, read as more than half of the errors falling in those two categories.
- Threshold: below 85 percent, a hand-written rule layer is needed above the model.

## Measured result

Three runs with the same result. Run 1, 2026-11-11, on Achia's laptop, code at `bb3482b`, model revision `7b1256fc0846e22d1af431eae299e2dcecee2778`, PyTorch FP32, syntax head off. Raw output:

```
E3 prefix-preserving replacement, model revision 7b1256fc0846e22d1af431eae299e2dcecee2778
torch 2.15.0+cpu, threads 4
category          strict  prefix only
single             20/20        20/20
chain              17/20        17/20
bare               10/10        10/10
trap               14/15        14/15
ordinary_word      10/10        10/10
article             3/5          3/5 
construct          10/10        10/10
possessive_like    10/10        10/10
total              94/100       94/100
verdict: inside_prediction
more than half of errors in construct and possessive_like: False
failures (id, category, target, model seg, suffix, produced, expected):
  b14 chain משאריאל מ+שאריאל False מדניאל משדניאל
  b16 chain ושרבקה ו+שרבקה False ואסתר ושאסתר
  b19 chain שמגולדברג ש+מגולדברג False שפרידמן שמפרידמן
  d04 trap כשמשה כשמש+ה False כשמשאהרון כשאהרון
  f03 article להלוי ל+הלוי False לכהן להכהן
  f04 article ולהכהן ול+הכהן False וללוי ולהלוי
```

Run 2, 2026-11-12, same laptop, code at `4576cc4`, after the Ponytail review of the harness (PR #9). The harness now loads the model through the vendored copy of its code and not the Python in the download folder, refuses a weights file that is not the recorded one, and counts in a tested function. No form and no scoring rule changed. Raw output:

```
E3 prefix-preserving replacement, model revision 7b1256fc0846e22d1af431eae299e2dcecee2778
model.safetensors sha256 c59db02c002b69fd3c072c310e3ba578d036386477248d1c8576d896cc06aa1c
code 4576cc4ebd27ae5a1d4ed3fae875625b5aef1472
torch 2.15.0+cpu, transformers 5.22.2, threads 4
category          strict  prefix only
single             20/20        20/20
chain              17/20        17/20
bare               10/10        10/10
trap               14/15        14/15
ordinary_word      10/10        10/10
article             3/5          3/5 
construct          10/10        10/10
possessive_like    10/10        10/10
total              94/100       94/100
verdict: inside_prediction
more than half of errors in construct and possessive_like: False
failures (id, category, target, model seg, suffix, produced, expected):
  b14 chain משאריאל מ+שאריאל False מדניאל משדניאל
  b16 chain ושרבקה ו+שרבקה False ואסתר ושאסתר
  b19 chain שמגולדברג ש+מגולדברג False שפרידמן שמפרידמן
  d04 trap כשמשה כשמש+ה False כשמשאהרון כשאהרון
  f03 article להלוי ל+הלוי False לכהן להכהן
  f04 article ולהכהן ול+הכהן False וללוי ולהלוי
```

The counts and the six failures are the same in both runs. The weights hash is the one the hub records for the pinned commit (`docs/THIRD_PARTY.md`).

Run 3, 2026-11-12, same laptop, code at `d90c815`, after the second review pass: the harness now also prints the hashes of the config and the tokenizer, and takes its weights check from E1. The first lines of its output:

```
E3 prefix-preserving replacement, model revision 7b1256fc0846e22d1af431eae299e2dcecee2778
model.safetensors sha256 c59db02c002b69fd3c072c310e3ba578d036386477248d1c8576d896cc06aa1c
config.json sha256 507f247f97ccaed18308054d58b5f063dd2cc01e69204d13218703dc2512932c
tokenizer.json sha256 4e520fd9025a2fd5f2dce1d04df5922954c8ff050cc3e67d4bc54a7347eccb32
code d90c815b103f30f81cf91094fee540ade91fa601
torch 2.15.0+cpu, transformers 5.22.2, threads 4
```

From `category` to the last failure line, its output is the same as run 2, line for line: 94 of 100 and the same six failures.

The count agrees with the prediction. The place does not: none of the six errors is in `construct` or `possessive_like`, which scored 20 of 20 together.

The six errors are three patterns:

- **A second prefix letter left on the name** (b14, b16, b19). In `מש`, `וש` and `שמ` the model split off the first letter and kept the second as part of the name. `מש` and `שמ` have one form each. `וש` has two, and the other one, b15 `ושיוסף`, was right. The other 17 chains, `ול`, `וב`, `ומ`, `כש`, `וכש`, `לכש`, `של`, `שב` and `ושל` among them, were right.
- **A name eaten by the prefix** (d04). `כשמשה` came back as `כשמש` plus `ה`: the first two letters of `משה` were taken as prefix letters. This is the failure Phase 3 names when it says many real names begin with prefix letters. The other 14 `trap` forms were right, `בברק` and `לבלהה` among them.
- **The definite article on a surname, read two ways** (f03, f04). The model split the article off in `הכהן`, `מהכהן` and `שהלוי` and kept it as part of the name in `להלוי` and `ולהכהן`. The gold prefix followed the plan, which lists `מה` as a prefix combination. Under the other reading, that `הלוי` is the surname, these two are right and the other three are wrong. Under these two readings the model is not consistent across the five; under the third reading, below, it is.

The review of the harness (PR #9, finding 1) adds a third reading of the article forms. In standard spelling ל with the article is written `ל`, never `לה`. So `להלוי` and `ולהכהן` can only be a prefix on a surname that begins with ה, which is how the model read them. The gold prefix `לה` followed `build-plan.md` Phase 3, which lists `לה` among the prefix combinations. The three readings give three counts:

| Reading of the ה | `הכהן` | `מהכהן` | `להלוי` | `ולהכהן` | `שהלוי` | Count |
|---|---|---|---|---|---|---|
| Always the article (as pre-registered) | right | right | wrong | wrong | right | 94, inside the prediction |
| The article, except after ל where spelling rules it out | right | right | right | right | right | 96, above the predicted range |
| Always part of the surname | wrong | wrong | right | right | wrong | 93, inside the prediction |

Only the first row was run. The other two are worked out from the model's output on these five forms, which the two runs give. The threshold of 85 is not crossed under any of the three.

## What this rules in and what it rules out

Rules in:

- By the plan's threshold, Phase 3 does not need a hand-written rule layer above the model. 94 is nine forms above 85.
- Names that are ordinary words (`לאור`, `משחר`, `מתום`), and names spelled like a noun with a possessive suffix (`לאבי`, `מבני`, `לדודו`) were all segmented correctly. So was the prefix on the first word of two-word names that start with a construct noun (`לבני ברק`, `לבן גוריון`); the second word of those names was not scored. The model reported no suffix on any target.

Rules out:

- The plan's guess about where it breaks.

Does not settle:

- How often these forms occur in real documents. The forms were written to probe, not sampled. What was measured is the split inside the 100: of the 24 forms with `ש` in the gold prefix, 20 were right; of the 76 without, 74. No document was scored.
- Whether "construct state" and "possessive suffixes" were read as the plan meant. `PREREGISTRATION.md` says how they were read and why.
- Three things the plan names that the 100 forms do not hold: the form `שברק`, which section 11 gives as an example, and the prefix combinations `וה` and `ושה` of Phase 3. The failures here are in `ש` chains and in a name eaten by its prefix, and `שברק` would be both, so it is untested. The six forms whose gold prefix is `ש` alone were all right. Found by the review of the harness (PR #9, finding 3).
- The quantized model. This is the FP32 model.
- Anything about detection. Every target here was given to the scorer; E1 measures whether the model finds the name at all.

## Options, with the cost of each

1. **Use the model's segmentation as it is in Phase 3.** No extra code. Cost: the three patterns above reach the output as a wrong token (`כשמשאהרון`) until the Phase 10 verification pass or the reviewer catches them.
2. **Use it, and cross-check the base against the entity's other mentions.** When the same entity appears elsewhere without a prefix, the base is known, and the prefix is whatever precedes it. It is designed for failures like b14, b16, b19 and d04. It was not tested here and could not be: each of these sentences holds its name once, so there is no other mention to check against. Cost: it needs entity resolution, which is Phase 6, so Phase 3 ships without it and Phase 6 grows by one rule and its tests.
3. **Write the rule layer anyway.** Cost: the plan reserves it for a result below 85, and a prefix-list rule is what Phase 3 warns against, because of names like `משה`.

## Recommendation

Option 2, in two steps. In Phase 3, use the segmentation as it is and add the six failing forms to the T1 prefix tests as named cases that are expected to fail, so the gap is visible and not forgotten. In Phase 6, add the cross-check and turn those cases green.

For the article on surnames, Achia or Tomer should say which reading the product wants, because the three readings replace different text. That is a product decision, not a measurement. The table under "Measured result" gives the count under each reading. Choosing a reading other than the pre-registered one changes `forms.tsv`, and that, with `שברק` and the two missing combinations added, is a new run under an amended pre-registration. Under the reading where the ה is always part of the surname, `הכהן` has no prefix at all, so the category sizes in `scoring.py` and in the pre-registration change together with `forms.tsv`.

## Scope requested

None. This is not a waiver request.

## Decision

