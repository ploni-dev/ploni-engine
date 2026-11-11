# Finding: E3 prefix-preserving replacement is 94 of 100, and breaks on stacked prefixes, not on construct or possessive forms

## What was being measured

`build-plan.md` section 11, experiment E3: whether `dicta-il/dictabert-joint` segments a prefixed name well enough that replacing the base and keeping the prefix gives the right token.

100 hand-written forms, each one token inside an invented sentence, in eight categories. The forms, the scoring rule and the readings of the plan's open points are in `experiments/e3_prefix_replacement/`, committed as `bb3482b` before the model was run on them.

## Prediction and threshold

As stated before the run (`build-plan.md` section 11, and `experiments/e3_prefix_replacement/PREREGISTRATION.md` at `bb3482b`):

- Prediction: 90 percent correct, read as 85 to 95 inclusive, breaking on construct state and possessive suffixes, read as more than half of the errors falling in those two categories.
- Threshold: below 85 percent, a hand-written rule layer is needed above the model.

## Measured result

One run, 2026-11-11, on Achia's laptop, code at `bb3482b`, model revision `7b1256fc0846e22d1af431eae299e2dcecee2778`, PyTorch FP32, syntax head off. Raw output:

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

The count agrees with the prediction. The place does not: none of the six errors is in `construct` or `possessive_like`, which scored 20 of 20 together.

The six errors are three patterns:

- **A second prefix letter left on the name** (b14, b16, b19). In `מש`, `וש` and `שמ` the model split off the first letter and kept the second as part of the name. The other 17 chains, `ול`, `וב`, `ומ`, `כש`, `וכש`, `לכש`, `של`, `שב` and `ושל` among them, were right.
- **A name eaten by the prefix** (d04). `כשמשה` came back as `כשמש` plus `ה`: the first two letters of `משה` were taken as prefix letters. This is the failure Phase 3 names when it says many real names begin with prefix letters. The other 14 `trap` forms were right, `בברק` and `לבלהה` among them.
- **The definite article on a surname, read two ways** (f03, f04). The model split the article off in `הכהן`, `מהכהן` and `שהלוי` and kept it as part of the name in `להלוי` and `ולהכהן`. The gold prefix followed the plan, which lists `מה` as a prefix combination. Under the other reading, that `הלוי` is the surname, these two are right and the other three are wrong. Either way the model is not consistent across the five.

## What this rules in and what it rules out

Rules in:

- By the plan's threshold, Phase 3 does not need a hand-written rule layer above the model. 94 is nine forms above 85.
- Names that are ordinary words (`לאור`, `משחר`, `מתום`), names spelled like a noun with a possessive suffix (`לאבי`, `מבני`, `לדודו`) and two-word names that start with a construct noun (`לבני ברק`, `לבן גוריון`) were all segmented correctly, and the model reported no suffix on any target.

Rules out:

- The plan's guess about where it breaks.

Does not settle:

- How often these forms occur in real documents. The forms were written to probe, not sampled. A document full of `ש` clauses would do worse than 94 percent; one with plain `ל` and `מ` prefixes would do better.
- Whether "construct state" and "possessive suffixes" were read as the plan meant. `PREREGISTRATION.md` says how they were read and why.
- The quantized model. This is the FP32 model.
- Anything about detection. Every target here was given to the scorer; E1 measures whether the model finds the name at all.

## Options, with the cost of each

1. **Use the model's segmentation as it is in Phase 3.** No extra code. Cost: the three patterns above reach the output as a wrong token (`כשמשאהרון`) until the Phase 10 verification pass or the reviewer catches them.
2. **Use it, and cross-check the base against the entity's other mentions.** When the same entity appears elsewhere without a prefix, the base is known, and the prefix is whatever precedes it. That would have fixed b14, b16, b19 and d04 here. Cost: it needs entity resolution, which is Phase 6, so Phase 3 ships without it and Phase 6 grows by one rule and its tests.
3. **Write the rule layer anyway.** Cost: the plan reserves it for a result below 85, and a prefix-list rule is what Phase 3 warns against, because of names like `משה`.

## Recommendation

Option 2, in two steps. In Phase 3, use the segmentation as it is and add the six failing forms to the T1 prefix tests as named cases that are expected to fail, so the gap is visible and not forgotten. In Phase 6, add the cross-check and turn those cases green.

For the article on surnames, Achia or Tomer should say which reading the product wants, because the two readings replace different text. That is a product decision, not a measurement.

## Scope requested

None. This is not a waiver request.

## Decision

