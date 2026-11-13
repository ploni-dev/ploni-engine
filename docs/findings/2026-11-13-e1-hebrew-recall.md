# Finding: E1 Hebrew PERSON recall is 95.5 percent (449 of 470 mentions) on ten Supreme Court civil judgments, above the predicted 85 to 92; counted by Claude, not yet checked by Achia

## What was being measured

`build-plan.md` section 11, experiment E1: how many person-name mentions `dicta-il/dictabert-joint` labels as a person in ten real Hebrew documents. The plan calls it the measurement that decides whether the architecture stands.

What was run, as `experiments/e1_hebrew_recall/PREREGISTRATION.md` fixes it, including its amendment of 2026-11-13, which was merged before the run (#50):

- **Corpus:** ten judgments of the Supreme Court in civil appeals (`ע"א`), 8 to 20 pages each, dated 22 July to 18 October 2026, chosen by one search and a rule on the captions. 224,355 characters in 843 paragraphs. This is not the mix the plan names (court decisions, contracts, a medical summary), and not the mix of 2026-11-12 (trial-court civil, labour and medical malpractice judgments).
- **Model:** commit `7b1256fc0846e22d1af431eae299e2dcecee2778`, weights SHA-256 `c59db02c…06aa1c`, vendored model code, offline, one paragraph per call, no threshold and no post-processing.
- **Count:** by Claude, not by hand. One reader per document, each a fresh Claude session working from one written guide. Achia checks `doc06` afterwards. That check is not done yet, so by the pre-registration **this number is unchecked**.

## Prediction and threshold

As stated before the run, `build-plan.md` lines 1031 to 1033:

> Prediction: 85 to 92 percent PERSON recall, errors concentrated in ordinary-word names and proclitic forms.
> Threshold: below 80 percent, the architecture needs rethinking before anything else is built.

Primary number: strict mention-level recall, pooled over the ten documents. A mention is found only if `PER` highlights cover every token of the name.

## Measured result

**449 of 470 mentions found: 95.53 percent. Outside the prediction, on the high side. The threshold is not crossed.**

| | Found | Mentions | Recall |
|---|---|---|---|
| All | 449 | 470 | 95.53% |
| Public figures (judges, registrars, officials) | 175 | 176 | 99.43% |
| Private parties | 274 | 294 | 93.20% |

The errors are not where the plan predicted. 21 errors: 3 partial, 18 missed. 6 are ordinary-word names, 1 carries an attached prefix, 14 are neither. 13 of the 21 are one surname in one document.

### The run

```
experiments/.venv/Scripts/python.exe -I -X utf8 experiments/e1_hebrew_recall/run_model.py \
  --corpus-dir /c/Users/Achia/ploni-e1-corpus --out-dir /c/Users/Achia/ploni-e1-out \
  --model-dir models/dictabert-joint/7b1256fc0846e22d1af431eae299e2dcecee2778
```

```
doc01 {"paragraphs": 106, "windows": 108, "cut_paragraphs": 2, "hard_cuts": 0, "unknown_pieces": 0, "unread_chars": 0, "per_highlights": 136, "placeholders": 2, "placeholder_highlights": 2, "all_entities": 501, "seconds": 158.1}
doc02 {"paragraphs": 94, "windows": 94, "cut_paragraphs": 0, "hard_cuts": 0, "unknown_pieces": 0, "unread_chars": 0, "per_highlights": 81, "placeholders": 3, "placeholder_highlights": 0, "all_entities": 414, "seconds": 117.2}
doc03 {"paragraphs": 75, "windows": 75, "cut_paragraphs": 0, "hard_cuts": 0, "unknown_pieces": 0, "unread_chars": 0, "per_highlights": 57, "placeholders": 0, "placeholder_highlights": 0, "all_entities": 248, "seconds": 83.4}
doc04 {"paragraphs": 84, "windows": 84, "cut_paragraphs": 0, "hard_cuts": 0, "unknown_pieces": 0, "unread_chars": 0, "per_highlights": 44, "placeholders": 0, "placeholder_highlights": 0, "all_entities": 146, "seconds": 71.4}
doc05 {"paragraphs": 66, "windows": 66, "cut_paragraphs": 0, "hard_cuts": 0, "unknown_pieces": 0, "unread_chars": 0, "per_highlights": 61, "placeholders": 5, "placeholder_highlights": 2, "all_entities": 212, "seconds": 67.8}
doc06 {"paragraphs": 56, "windows": 56, "cut_paragraphs": 0, "hard_cuts": 0, "unknown_pieces": 1, "unread_chars": 0, "per_highlights": 34, "placeholders": 1, "placeholder_highlights": 0, "all_entities": 172, "seconds": 61.1}
doc07 {"paragraphs": 112, "windows": 112, "cut_paragraphs": 0, "hard_cuts": 0, "unknown_pieces": 0, "unread_chars": 0, "per_highlights": 97, "placeholders": 0, "placeholder_highlights": 0, "all_entities": 355, "seconds": 118.9}
doc08 {"paragraphs": 122, "windows": 122, "cut_paragraphs": 0, "hard_cuts": 0, "unknown_pieces": 0, "unread_chars": 0, "per_highlights": 51, "placeholders": 0, "placeholder_highlights": 0, "all_entities": 258, "seconds": 138.4}
doc09 {"paragraphs": 68, "windows": 68, "cut_paragraphs": 0, "hard_cuts": 0, "unknown_pieces": 0, "unread_chars": 0, "per_highlights": 41, "placeholders": 2, "placeholder_highlights": 1, "all_entities": 178, "seconds": 56.4}
doc10 {"paragraphs": 60, "windows": 61, "cut_paragraphs": 1, "hard_cuts": 0, "unknown_pieces": 0, "unread_chars": 0, "per_highlights": 120, "placeholders": 0, "placeholder_highlights": 0, "all_entities": 309, "seconds": 85.7}
{"model_dir": "7b1256fc0846e22d1af431eae299e2dcecee2778", "model_sha256": {"model.safetensors": "c59db02c002b69fd3c072c310e3ba578d036386477248d1c8576d896cc06aa1c", "config.json": "507f247f97ccaed18308054d58b5f063dd2cc01e69204d13218703dc2512932c", "tokenizer.json": "4e520fd9025a2fd5f2dce1d04df5922954c8ff050cc3e67d4bc54a7347eccb32"}, "torch": "2.15.0+cpu", "transformers": "5.22.2", "torch_threads": 4, "code": {"commit": "40981d489e407a898e90aaf4a77052d23a0ebcf3", "dirty": false}}
```

- The code commit `40981d4` is `main` after #47 (the reader change) and #50 (the amendment), as the amendment requires.
- `unread_chars` is 0 in all ten. Three paragraphs were cut, all at a sentence end. One `[UNK]` piece in `doc06`.
- A first attempt, minutes earlier, was stopped by Claude Code for low memory before any document was finished. It left only `index.csv`, which was deleted. Nothing from it is used.
- The run took 958 seconds for the ten documents, on mains power, on a laptop with 1.2 GB of free memory at the start. It is recorded here as a timing and is not read as a result (decision in the E2 note).

### The tally

`tally.csv`, as written from the readers' files. It holds highlight numbers and counts only.

```
doc_id,per_highlights,not_person_ids,partial_ids,public_ids,found_adjust,missed,missed_other_label,err_ordinary_word,err_proclitic,err_both,err_other,found_adjust_public,missed_public
doc01,136,21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 45 46 47 48 49 50 53 54 55 56 57 58 59 60 61 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 95 96 97 98 99 102 103 104 105 106 107 108 109 116 117 118 126 128 130,4,1 2 3 10 15 16 41 42 43 44 51 52 62 63 93 94 100 101 119 120 121 122 123 124 125 127 129 131 132 133 134 135 136,0,1,0,2,0,0,0,0,0
doc02,81,6 7 8 9 10 11 20 21 22 23 24 25 26 27 28 31 32 33 34 35 37 38 39 41 43 44 45 46 47 48 49 50 51 52 53 54 55 59 61 62 63 70 71,,1 2 3 12 16 17 36 40 42 56 57 58 60 64 65 66 67 68 69 72 73 74 75 76 77 78 79 80 81,0,0,0,0,0,0,0,0,0
doc03,57,29 31 33 34 35 36 37 38 39 40 41 44 45 47 48 49 50 51 52 53 54,16,1 2 3 17 22 23 24 28 30 32 42 43 46 55 56 57,0,0,0,1,0,0,0,0,0
doc04,44,14 15 16 17 18 19 20 21 22 23 24 25 28 29 30 34 35,,1 2 3 7 11 12 26 31 33 36 37 38 39 40 41 42 43 44,-2,2,0,2,0,0,0,0,0
doc05,61,50 52 53 54 58,,1 2 3 7 10 11 32 59 60 61,0,0,0,0,0,0,0,0,0
doc06,34,20 21 22 23 24 25 27 28 30 32 33,,1 16 18 19 26 31 34,0,1,0,1,0,0,0,0,0
doc07,97,18 19 20 21 22 23 24 25 26 27 28 29 30 32 33 34 35 37 38 39 40 42 43 44 45 46 48 49 53 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 78 79 80 81 82 83 84 85 86 88,77,1 2 3 7 13 14 17 31 36 41 47 50 51 52 54 77 87 89 90 91 92 93 94 95 96 97,0,0,0,0,0,0,1,0,0
doc08,51,39 40 41 42,,1 2 3 10 15 16 43 44 45 46 47 48 49 50 51,0,0,0,0,0,0,0,0,0
doc09,41,13 17 25 26 27 28 29 30 31 32 33 34 35 37,,1 2 3 6 9 11 23 24 39 40 41,0,0,0,0,0,0,0,0,0
doc10,120,78 79 80 81 82 83 84 85 110 111,,1 2 3 7 10 11 46 77 118 119 120,0,14,13,0,1,0,13,0,0
```

### The report

```
experiments/.venv/Scripts/python.exe -I experiments/e1_hebrew_recall/tally.py /c/Users/Achia/ploni-e1-out/tally.csv
```

```
documents: 10
strict PERSON recall, pooled: 449/470 = 95.53%
verdict: outside_prediction (prediction 85 to 92 percent, threshold below 80 percent)
lenient recall (partial counted as found): 452/470 = 96.17%
any-label recall (found, or missed but under another label): 462/470 = 98.30%
public figures: 175/176 = 99.43%
private parties: 274/294 = 93.20%
gap between the two: small_gap (large is 10 points or more, with at least 30 mentions in each group)
private-party recall below 80 percent while pooled recall is not: no
macro mean of per-document strict recall: 96.79% over 10 documents with at least one mention
PER highlight precision: 454/722 = 62.88%
errors: 21 (partial 3, missed 18); ordinary_word 6, proclitic 1, both 0, other 14
errors concentrated in ordinary-word and proclitic forms: no
per document (strict recall, partial, missed):
  doc01  53/55 = 96.36%  partial 1  missed 1
  doc02  38/38 = 100.00%  partial 0  missed 0
  doc03  35/36 = 97.22%  partial 1  missed 0
  doc04  25/27 = 92.59%  partial 0  missed 2
  doc05  56/56 = 100.00%  partial 0  missed 0
  doc06  23/24 = 95.83%  partial 0  missed 1
  doc07  35/36 = 97.22%  partial 1  missed 0
  doc08  47/47 = 100.00%  partial 0  missed 0
  doc09  27/27 = 100.00%  partial 0  missed 0
  doc10  110/124 = 88.71%  partial 0  missed 14
```

### Per document

| Document | Highlights | Not a counted mention | Found | Partial | Missed | Public found of total | Private found of total |
|---|---|---|---|---|---|---|---|
| doc01 | 136 | 82 | 53 | 1 | 1 | 33 of 33 | 20 of 22 |
| doc02 | 81 | 43 | 38 | 0 | 0 | 29 of 29 | 9 of 9 |
| doc03 | 57 | 21 | 35 | 1 | 0 | 16 of 16 | 19 of 20 |
| doc04 | 44 | 17 | 25 | 0 | 2 | 18 of 18 | 7 of 9 |
| doc05 | 61 | 5 | 56 | 0 | 0 | 10 of 10 | 46 of 46 |
| doc06 | 34 | 11 | 23 | 0 | 1 | 7 of 7 | 16 of 17 |
| doc07 | 97 | 61 | 35 | 1 | 0 | 25 of 26 | 10 of 10 |
| doc08 | 51 | 4 | 47 | 0 | 0 | 15 of 15 | 32 of 32 |
| doc09 | 41 | 14 | 27 | 0 | 0 | 11 of 11 | 16 of 16 |
| doc10 | 120 | 10 | 110 | 0 | 14 | 11 of 11 | 99 of 113 |
| All | 722 | 268 | 449 | 3 | 18 | 175 of 176 | 274 of 294 |

In `doc04` two highlights are a second highlight on a name already counted (a judge's initial and surname highlighted apart), so `found_adjust` is -2.

### The 21 errors, by kind

No name is written here. `misses.csv` in the private output folder has one line per error.

| Kind | Count | Where | Label the model gave |
|---|---|---|---|
| A surname in a group term ("the brothers" and the surname) for two parties | 13 | doc10 | ORG 12 times, no label once. The same term is found once. |
| A given name with an attached ל | 1 | doc10 | LOC. The name is also a region. |
| A short given name inside a quoted handwritten note, also an everyday word | 2 | doc04 | none |
| A party line in the caption, given name and surname | 1 | doc06 | none |
| A surname in the name of a decision about a party of this case | 1 | doc01 | none. The same phrase is found four times. |
| A party line in the caption, only part of the name highlighted | 2 | doc01, doc03 | PER on part of the name |
| A judge after a citation, the initial left outside the highlight | 1 | doc07 | PER on the surname |

So 3 of the 21 are in a caption line, where a name stands with little around it. The amendment expected the caption to be the hard part. With 3 errors in ten captions it was not.

### The 268 highlights that are not counted mentions

`PER highlight precision: 62.88%` does not mean the model is wrong in 37 of 100 highlights. Nearly all of the 268 are real person names that the counting rules leave out: party names in the titles of cited decisions, and authors inside references to books and articles. These judgments cite a great deal. The readers' notes name only a few that are not a person's name at all (a company suffix, a company name).

### The cross-check

As the amendment asks, per document: places listed by the throwaway script, and how many of them were errors.

| Document | Name word outside a highlight | Word after a title | Of these, errors |
|---|---|---|---|
| doc01 | 76 | 4 | 1 miss, and 2 rows on the uncovered part of the partial |
| doc02 | 40 | 3 | 0 |
| doc03 | 32 | 0 | 0 |
| doc04 | 16 | 0 | 2 |
| doc05 | 6 | 0 | 0 |
| doc06 | 6 | 7 | 0 |
| doc07 | 34 | 7 | 1 row on the uncovered part of the partial |
| doc08 | 16 | 1 | 0 |
| doc09 | 15 | 0 | 0 |
| doc10 | 18 | 0 | 14 |

281 places, 17 of the 18 misses among them. The one miss that was on neither list is the caption line in `doc06`; the reader found it by reading. One detail the amendment does not give: a highlighted word with its own prefix letters taken off was searched only if at least three letters were left.

### Doubtful cases, each decided once and applied to every document

The guide the readers worked from was written before the run. It settled two cases ahead of the count that the pre-registration does not name: a dead person named in "the estate of the late X" as a party of this case is counted, and a party named in the caption of this case is counted. The rest came up during the count:

| Case | Decision | What the other reading would do |
|---|---|---|
| A surname in a group term for two natural persons (doc10) | Counted: it is the surname of people, and a product has to replace it | 448 of 456, 98.2% |
| A surname in the name of a decision about a party of this case (doc01) | Counted: it is not a cited precedent | 4 found and 1 missed drop out |
| The bare initials of the writing judge or registrar in editorial brackets (doc05, doc06, doc09: 11 places, 4 of them highlighted) | Not counted: the pre-registration lists bare initials as not counted | 453 of 481, 94.2% |
| An author's surname used as the short name of a cited book or article (at least 27 highlights in doc01, doc02, doc07, doc09) | Not counted: the name of a cited work | all are found, so recall goes up |
| A dead person's name in "estate of the late X" inside the title of a cited decision | Not counted: the title of a cited decision | a few more found |
| A person's name inside the name of a company that is a party (doc02) | Not counted: a name inside an organisation | a few more found |
| A judge's initial outside the highlight on the surname (doc07) | Partial: an initial with a surname is one mention | 450 of 470 |
| A professor or a known lawyer named in the judgment's own sentence | Counted. Public only when the person also held a public office the readers were sure of; private when unsure | moves mentions between the two groups, not the pooled number |

No reading of these cases brings the pooled number under 94 percent.

### What was added to the pre-registered procedure

A second reading. Four documents (doc01, doc07, doc08, doc10: 120,753 of the 224,355 characters, and 17 of the 21 errors) were read again by a second Claude session that did not see the first reader's files, looking only for names with no highlight or a partial one. It listed the same errors as the first reader in all four and no new one. This step is not in the pre-registration. It could only have added misses.

### What is not done

- **Achia's check of `doc06`.** Until it is done the number is unchecked, as the amendment says. If the check changes a line, all ten are counted again and the second tally is the E1 number.
- No human has read any of the ten documents against a worksheet.

## What this rules in and what it rules out

Rules in:

- The threshold is not crossed, by a wide margin: 95.5 percent against 80. As far as E1 can say, the architecture stands and the plan goes on.
- Achia's concern of 2026-11-12 is visible but small here: 99.4 percent on public figures, 93.2 percent on private parties. Both groups have far more than 30 mentions. Private-party recall alone is also far above 80.
- The model's main failure in these documents is a wrong label, not a blind spot: 13 of 18 misses sit under ORG or LOC, and any-label recall is 98.3 percent. The 13 are one surname whose full names are highlighted elsewhere in the same document. Phase 6 links a lone surname to a full-name entity and groups a family by a shared surname. Whether that reaches a span the model labelled ORG is not in the plan; option 3 makes it a test.
- Reading the caption mattered. Before #47 the reader skipped it. It holds 3 of the 21 errors.

Rules out, or does not show:

- **Nothing about a lawyer's own documents.** These are Supreme Court judgments: formal language, and names introduced with a role and a title. Achia's concern, recorded in the pre-registration, is that such text is close to what the model was trained on. A contract, a letter or a medical summary may behave differently. `build-plan.md:687` says published decisions are for realism, "never as ground truth". Above the prediction is a reason for caution, not for comfort.
- **Nothing about trial-court judgments**, which quote contracts and testimony at length and were the corpus Achia first asked for.
- **Not a sample.** Ten documents by one rule on one search. One document carries 14 of the 21 errors, and one surname 13 of them.
- **The count is a model's.** A name that neither the model under test nor the reader recognises is counted by neither. Two independent readings agreed on four documents, which says the readers are consistent with each other, not that they are right. The one check by a person is still to come.
- **Recall only.** What the product does with the 268 names in citations and references is not measured here; the counting rules leave them out.
- **The prediction about where the errors fall did not hold.** 7 of 21 are ordinary-word or prefix cases. E1 does not show that those two are the hard cases; it shows too few of them to say.

## Options, with the cost of each

1. **Take E1 as not crossing the threshold and go on to Phase 0, once Achia has checked `doc06`.** Cost: Achia's time for one document of 8 pages. The number then stands for Supreme Court civil judgments and for nothing else.
2. **Run E1 again on the documents the product is for** (trial-court judgments that quote contracts, or real contracts and letters) before Phase 3 records its first baseline. Cost: the source has to be settled first (issue #4: the trial-court decisions sit on Net HaMishpat), then a run and a count like this one. The Phase 3 gate asks for PERSON recall "on the 10 real Hebrew documents", so this decides which ten those are.
3. **Carry the 13 wrong-label misses into Phase 6 as a named test:** a lone surname under a non-person label, with the full name highlighted elsewhere in the document, is linked to that person. Cost: one test case in Phase 6, and a rule the plan does not have yet if the test fails.
4. **Have a person count more than one document.** Cost: several hours of careful reading per document. It measures the annotation error that this note cannot.

## Recommendation

**Proposed decision, for Achia to confirm or change.**

1. Option 1. E1 does not cross the threshold. The architecture stands and Phase 0 starts. The number is recorded as 95.5 percent on ten Supreme Court civil judgments, counted by Claude.
2. Option 3. The wrong-label surname goes into Phase 6 as a named test.
3. Option 2, before Phase 3's baseline and not before Phase 0. Phases 0 to 2 do not use the Hebrew model, so nothing waits on it. Which documents, and from where, is Achia's to say.
4. Not option 4 for now. Achia's check of `doc06` is the pre-registered human check. If it finds a wrong line, the amendment already says what follows.

## Scope requested

None. This is not a waiver request.

## Decision
