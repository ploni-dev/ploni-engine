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

Option 2, in two steps. In Phase 3, use the segmentation as it is and carry the failing forms in the T1 prefix tests as named cases, so the gap is visible and not forgotten. In Phase 6, add the cross-check.

**Proposed decision, for Achia to confirm or change.** The Decision section below was left empty when this was written: `docs/findings/README.md` gives it to Achia, and line 4 holds a product choice.

1. Option 2. No hand-written rule layer above the model in Phase 3: the count is above the plan's threshold of 85 under every reading of the article forms (93, 94 and 96).
2. The failing forms become named tests in Phase 3. Under the scoring of line 4, four forms are expected to fail: b14, b16, b19 and d04. f03 and f04 become passing cases. The tests also carry the forms the plan names and the 100 did not hold: `שברק`, one form with `וה` and one with `ושה`. Each test marked as an expected failure carries an issue link, as `PROMOTION.md` requires of every such marker, and none of them counts toward Phase 3's gate. That gate is "prefix preservation holds over 1,000 generated forms". If generated `מש`, `וש` or `שמ` forms fail it, that is a finding of its own, and these markers do not cover it.
3. The cross-check against the entity's other mentions is Phase 6 work and is untested. Its test cases need a second mention of the same name without a prefix: the single sentences of this experiment give it nothing to check against. This adds named tests to Phase 3, and one rule with its tests to Phase 6. `build-plan.md` is not edited here.
4. The ה on a surname, in two halves.
   - Scoring: a prefix written `לה` is read as ל on a name that begins with ה, because Hebrew spelling allows nothing else. `להלוי` and `ולהכהן` then count as right. `build-plan.md` Phase 3 lists `לה` among the prefix combinations; changing that list is a change to the plan and is Achia's.
   - The product: open for Achia or Tomer. Until they say, the product replaces what the model marks as the base. That has a cost: one surname can come out two ways in one document. By the outputs above, `הכהן` becomes ה plus the surrogate and `מהכהן` becomes `מה` plus the surrogate, but `ולהכהן` becomes `ול` plus the surrogate, with no ה.
5. No amended E3 run. It would add three forms and move two, and the count would then be 96 to 99 of 103, which is 93.2 to 96.1 percent, whatever the three new forms did; line 1 would not change. `forms.tsv` and the E3 record of 94 stay as pre-registered, and the spelling reading of line 4 applies to Phase 3's tests only. This departs from the paragraph below, which says a changed reading is a new run.

For the article on surnames, Achia or Tomer should say which reading the product wants, because the three readings replace different text. That is a product decision, not a measurement. The table under "Measured result" gives the count under each reading. Choosing a reading other than the pre-registered one changes `forms.tsv`, and that, with `שברק` and the two missing combinations added, is a new run under an amended pre-registration. Under the reading where the ה is always part of the surname, `הכהן` has no prefix at all, so the category sizes in `scoring.py` and in the pre-registration change together with `forms.tsv`.

## Scope requested

None. This is not a waiver request.

## Decision

Achia, 2026-11-13, in the Claude Code session. Claude asked whether to go on without extra hand-written rules for now and to keep the six mistakes as tests that are watched. Achia answered:

> Okay, yes, for now, but remember that we have to strive for maximum accuracy. This is extremely important for later users.

Decided:

1. No hand-written rule layer above the model in Phase 3, for now.
2. The six failing forms (b14, b16, b19, d04, f03, f04) are kept as tests that are watched.
3. Achia: "we have to strive for maximum accuracy. This is extremely important for later users."

As Claude reads "for now": the question of a rule layer comes back when the Phase 3 gate over 1,000 generated forms fails, or when the Phase 5 eval shows prefix errors. Each is then a findings note of its own.

Not decided. These were not put to Achia, and they stay as Claude's proposal in the section above until they are:

- How `לה` on a surname is scored. So f03 and f04 stay watched mistakes, as Achia was told, and do not become passing cases. The plan's list of prefix combinations still has `לה` (`build-plan.md:639`); taking it out is a change to the plan.
- What the product replaces when a surname begins with ה. It is a design question, and it goes to Achia when Phase 3 reaches it. Until then the product replaces what the model marks as the base, which follows from line 1. The proposed decision says "Achia or Tomer". It goes to Achia first.
- The three forms the 100 did not hold (`שברק`, one with `וה`, one with `ושה`), how a test that is expected to fail is marked, and whether such tests count toward Phase 3's gate.
- The cross-check against an entity's other mentions in Phase 6. It adds a rule to Phase 6, so it needs a PR to `build-plan.md`.
- Whether E3 is run again with an amended pre-registration.

The first three go to Achia before Phase 3 writes its prefix tests.

### Decided on 2026-11-16

Achia, 2026-11-16, in the Claude Code session. He asked to go through what waited on him one point at a time. Each question below is given as Claude asked it, word for word, and each answer as he wrote it.

**How `לה` on a surname is scored** (first open point above). Claude asked:

> Decided: lonely names are their own hard case from the start. I've also recorded your guiding principle: when in doubt, think of the purpose, because one wrong name can change how the whole document is understood.
>
> **Question 5: a Hebrew spelling point from the prefix test (E3).**
>
> Background: the product must keep prefixes like ל, ב, ו when it replaces a name. In the test, the word "להלוי" was scored as a mistake. The plan expected it to be read as the prefix "לה" plus the name "לוי". The model read it as "ל" plus the name "הלוי".
>
> In standard Hebrew spelling, ל together with "the" is written just ל, never "לה". So "להלוי" can only be ל plus a surname that starts with ה.
>
> **How should the test read "להלוי"?**
>
> 1. **As ל + הלוי.** The model was right, those two cases count as correct, and I correct the plan's list of prefixes in a small PR. I recommend this: it follows Hebrew spelling.
> 2. **As לה + לוי,** as the plan says now. The two cases stay as known mistakes.

Achia answered:

> specifically -  in this case it was not a mistake: it could be or ללוי if the name is לוי, or הלוי again for ךוי as a name, but here the model recognized correctly the name is הלוי and the for - ל+ הלוי is the right decision

He chose no number and answered in his own words, and of `להלוי` only. So `להלוי` is read as ל on the surname `הלוי`, and f03 counts as right in Phase 3's tests. The other word of "those two cases", `ולהכהן` (f04), was not shown to him. His reason covers it, since a name `כהן` with ל would be written `לכהן`, but it stays a watched mistake until he is asked that in one plain question. Line 4 of the proposed decision, which reads every `לה` this way, is decided for f03 and not yet for the rule. The E3 record of 94 of 100 stays as pre-registered. The plan's list of prefix combinations still has `לה`; taking it out is a PR to `build-plan.md`, not written yet.

**A surname that begins with ה, and the forms that still fail** (second and third open points above). Claude asked:

> Decided: "להלוי" is read as ל + הלוי, the model was right there, and I'll correct the plan's prefix list in a small PR.
>
> **Question 6: the two remaining prefix points from E3.**
>
> Background: both are about how the product treats a surname that starts with ה.
> - The same surname can come out two ways in one document. For example "הכהן" was read as "the" + כהן in one place, and as the surname הכהן in another.
> - Six prefix forms still fail or were never tested (like "כשמשה", where part of the name משה was taken for a prefix).
>
> Both depend on which method we end up with, and prefix handling is exactly the kind of "other method" the experiment series will compare.
>
> 1. **Move both into the experiment series.** I test the ways of handling them and bring them back to you with numbers. I recommend this: deciding now would be a guess.
> 2. **Decide them now,** before any experiment.

Achia answered:

> just like הלוי - which could be its own name or ה+לוי - the same for הכהן

He chose neither answer and stated the principle: either reading can be right, for `הכהן` as for `הלוי`. Claude put that back to him as a rule and asked:

> Agreed: "הכהן", like "הלוי", can be a surname of its own or "the" + כהן. Neither reading is wrong in general; it depends on what that person's name really is.
>
> So I take this as the rule: the product must work out the real name from the rest of the document (for example, how the same person is written elsewhere), and then treat every mention of that person the same way.
>
> **Shall I put that into the experiment series, testing how well each method works out the real name, and bring you the numbers?**
>
> 1. **Yes.** I recommend this. It also covers the six prefix forms that still fail.
> 2. **No,** you want to set a fixed rule now (for example: always treat ה as part of the name).

Achia answered:

> 1 - but a good model should recognize it from the context (especially when the name appears more than once)

So no fixed rule is set for the letter ה. The product has to work out the real name from the rest of the document and treat every mention of that person alike, and the experiment series measures how well each method does that, with his expectation that a good model recognizes it from the context, above all where the name stands more than once. The forms that still fail (b14, b16, b19, d04) and the three the 100 did not hold go into the same series. The questions above say "six" prefix forms; the count is these four that still fail and three that were never held, and f04 while it stays watched. The series is decided in `docs/findings/2026-11-14-e4-planted-names.md`, "Decided on 2026-11-16". How a test that is expected to fail is marked, and whether such tests count toward Phase 3's gate, was not asked and stays open. So do the last two points above: the cross-check in Phase 6, and whether E3 is run again.
