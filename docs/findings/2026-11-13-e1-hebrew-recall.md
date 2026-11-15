# Finding: E1 Hebrew PERSON recall is 95.5 percent (449 of 470 mentions) on ten Supreme Court civil judgments, above the predicted 85 to 92; counted by Claude, not checked by a person

## What was being measured

`build-plan.md` section 11, experiment E1: how many person-name mentions `dicta-il/dictabert-joint` labels as a person in ten real Hebrew documents. The plan calls it the measurement that decides whether the architecture stands.

What was run, as `experiments/e1_hebrew_recall/PREREGISTRATION.md` fixes it, including its amendment of 2026-11-13, which was merged before the run (#50):

- **Corpus:** ten judgments of the Supreme Court in civil appeals (`ע"א`), 8 to 20 pages each, dated 22 July to 18 October 2026, chosen by one search and a rule on the captions. 224,355 characters in 843 paragraphs. This is not the mix the plan names (court decisions, contracts, a medical summary), and not the mix of 2026-11-12 (trial-court civil, labour and medical malpractice judgments).
- **Model:** commit `7b1256fc0846e22d1af431eae299e2dcecee2778`, weights SHA-256 `c59db02c…06aa1c`, vendored model code, offline, one paragraph per call, no threshold and no post-processing.
- **Count:** by Claude, not by hand. One reader per document, each a fresh Claude session working from one written guide. Achia checks `doc06` afterwards. That check is not done yet, so by the pre-registration **this number is unchecked**. (Added on 2026-11-14: that check will not be done. See "What is not done".)

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

Under the reading taken of one doubtful case (the first row of the table of doubtful cases below), the errors are not where the plan predicted. 21 errors: 3 partial, 18 missed. 6 are ordinary-word names, 1 carries an attached prefix, 14 are neither. 13 of the 21 are one surname in one document. Under the other reading of that case, the prediction about where the errors fall holds.

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
- `unread_chars` is 0 in all ten. Three paragraphs were cut, all at a sentence end.
- One `[UNK]` piece in `doc06`. The reviewer of this note checked with the tokenizer alone, no model: it is in paragraph 44, on a section sign with a number written against it, inside a book reference. It is not in a name.
- `placeholders`: 13 in five documents. The reviewer of this note read all 13: each is in the title of a cited decision, and none stands for a party of these ten cases. The 5 that the model highlighted are in `not_person_ids`.
- A first attempt, minutes earlier, was stopped by Claude Code for low memory before any document was finished. It left only `index.csv`, which was deleted. Nothing from it is used.
- The run took 958 seconds for the ten documents, on mains power, on a laptop with 1.2 GB of free memory at the start. It is recorded here as a timing and is not read as a result (decision in the E2 note).

### The tally

`tally.csv`, as written from the readers' files. It holds highlight numbers and counts only. SHA-256 of `tally.csv`: `49d27a6ff9b6033049bee05b08df4da3abad511f2555785fbcc5b43b4da33e57`. Of `misses.csv`: `1ba80e510bd9f823783d9361cacba956449c97e885bafd13c84efecbbeefcd8b`.

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

So 3 of the 21 are in a caption line, where a name stands with little around it. The amendment expected the caption to be the hard part. By the count of the reviewer of this note, the captions hold 122 mentions, 119 of them found (97.5 percent), against 330 of 348 (94.8 percent) in the rest of the text. Under the other reading of the group term the rest is 329 of 334 (98.5 percent), and the caption is then the weaker part.

### The 268 highlights that are not counted mentions

`PER highlight precision: 62.88%` does not mean the model is wrong in 37 of 100 highlights. By the reasons the readers wrote in the ten `docNN_marks.csv` files, as the reviewer of this note counted them:

| Why the highlight is not a counted mention | Highlights |
|---|---|
| A party name in the title of a cited decision | 122 |
| An author, or an author's surname as the short name of a cited work | 94 |
| A person's name inside the name of a company | 4 |
| A placeholder | 5 |
| Bare initials | 4 |
| Not a person's name: a company or part of its name, a company suffix, an organisation, a village, an ordinary word | 39 |

So 220 of the 268 are names of people that the counting rules leave out; these judgments cite a great deal. About 39 of the 722 highlights are on something that is not a person.

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

The guide the readers worked from was written before the run and is printed in full at the end of this section. It settled cases ahead of the count that the pre-registration does not name: a dead person named in "the estate of the late X" as a party of this case is counted; a party named in the caption of this case is counted; mediators, arbitrators, appraisers and lawyers of record are private; an unsure call between public and private is private. The rest came up during the count:

| Case | Decision | What the other reading would do |
|---|---|---|
| A surname in a group term for natural persons: "the brothers" and the surname in doc10 (14 places, 1 found), and family surnames used for a group of clients in doc08 (highlights 29 to 34, all found) | Counted: it is the surname of people, and a product has to replace it | doc10 alone: 448 of 456, 98.2%; private 273 of 280; "errors concentrated" becomes yes (7 of 8). Both: 442 of 450 |
| A surname in the name of a decision about a party of this case (doc01) | Counted: it is not a cited precedent | 4 found and 1 missed drop out |
| The bare initials of the writing judge or registrar in editorial brackets (doc05, doc06, doc09: 11 places, 4 of them highlighted) | Not counted: the pre-registration lists bare initials as not counted. The guide's wording is narrower. The three readers saw the difference, wrote it down and followed the pre-registration, as the guide tells them to | 453 of 481, 94.2% |
| An author's surname used as the short name of a cited book or article (47 highlights: doc01 19, doc02 7, doc04 2, doc07 17, doc09 2) | Not counted: the name of a cited work | all are found, so recall goes up |
| A dead person's name in "estate of the late X" inside the title of a cited decision | Not counted: the title of a cited decision | a few more found |
| A person's name inside the name of a company that is a party (doc02) | Not counted: a name inside an organisation | about 5 more found and at least 2 more missed, by the reviewer's count |
| A judge's initial outside the highlight on the surname (doc07) | Partial: an initial with a surname is one mention | 450 of 470 |
| A professor or a known lawyer named in the judgment's own sentence, and a party who may be known from public life (doc06, highlight 9) | Counted. Public only when the person also held a public office the readers were sure of; private when unsure | moves mentions between the two groups, not the pooled number |
| The category of an error. The readers marked 5 of the 6 ordinary-word calls as unsure (doc01 paragraph 43, doc03 paragraph 22, doc04 twice, doc06 paragraph 18) | Ordinary word, as the readers chose | Under the reading taken, "errors concentrated" stays no whatever the category (7 of 21 at most). Under the other reading of the group term it is yes, or no (4 of 8) if the three weakest calls go to `other` |

Taken one at a time, the lowest reading is 453 of 481, 94.18 percent (bare initials counted). Two readings together, bare initials and names inside company names, give 458 of 488, 93.85 percent, by the reviewer's count. Both go against the pre-registration's own list of what is not counted, so the E1 number does not move.

### What was added to the pre-registered procedure

- **A second reading.** Four documents (doc01, doc07, doc08, doc10: 120,753 of the 224,355 characters, and 17 of the 21 errors) were read again by a second Claude session that was told not to open the first reader's files, looking only for names with no highlight or a partial one. It listed the same errors as the first reader in all four and no new one. This step is not in the pre-registration. It could only have added misses.
- **Plain-text worksheets.** The readers read `docNN_compact.txt`, not the page `docNN.html` the amendment names. A throwaway script outside the repository makes the one from the other. The reviewer of this note compared them: the same text and the same highlights in all 843 paragraphs.
- **One more column in `misses.csv`:** `highlight`, the number of the highlight for a partial.

### What is not done

- **Achia's check of `doc06`.** Until it is done the number is unchecked, as the amendment says. If the check changes a line, all ten are counted again and the second tally is the E1 number. (Added on 2026-11-14: it will not be done. See below.)
- No human has read any of the ten documents against a worksheet.

**Added on 2026-11-14, after the run.** This departs from the amendment, and is said here as that.

- Achia looked at the first page of `doc06` and confirmed the one miss Claude listed: "line 11 no yellow". Achia did not read the rest, and said: "i didnt read it all - u domit slowly for me. i domt want to have to read all of it - read it carefully and check urself and even better - create a method to verify it and have a ground truth so i dont need to involve like that".
- So the check by a person that the amendment registered is not done and will not be. **The number stays unchecked by a person.**
- What was done in its place: the session that wrote this note read `doc06` whole on 2026-11-14, every paragraph. It is the third full reading of `doc06`: the document's reader; then the reviewer of this note, whose reading is recorded in the body of PR #52 (it "read one document, `doc06`, against its text, with the same count as the reader (24 mentions, 23 found, 1 missed, 7 public)"); then this one. Same count: 24 mentions, 23 found, 1 missed, 7 public; 11 highlights not counted. This reading wrote no file, and the session knew the first count before it read. All three readings are by the same model, so this does not measure what a person's check would have.
- What comes next is a check against a ground truth, experiment E4: text written for the purpose, with the names planted by a script, so that the right answer is known exactly and nobody has to read to count. Its second part compares a Claude reader's count with that ground truth. It was pre-registered on 2026-11-14 in `experiments/e4_planted_names/`, on a branch of its own when this was written.

### The readers' guide, as written before the run

Printed here because the count cannot be repeated or checked without it. The path to the pre-registration is shortened, and two examples are replaced by invented ones, because the guide's own examples there were names that also stand in the documents: an initial with a surname, and the authors in a book reference. Nothing else is changed. So the readers of doc01, doc02, doc04 and doc09 had a guide example that was also in their document. The rule they applied to those names is the pre-registration's either way.

The guide differs from the pre-registration in two places. It leaves out bare initials only when they "stand for a hidden name"; the pre-registration leaves out bare initials with no such limit, and the readers followed the pre-registration (third row of the table above). And it gives a prefix on an ordinary-word name as an example of `proclitic`, where the pre-registration calls that `both`; no error in this count is of that kind.

````text
# E1 annotation guide (written before the model was run on any document)

You are the annotator for ONE document of experiment E1. E1 measures how many person-name
mentions the Hebrew model `dictabert-joint` finds. You read the worksheet of your document and
record, for every highlight and every person-name mention, what happened.

The source of the rules is `experiments/e1_hebrew_recall/PREREGISTRATION.md`
(sections "What counts as a person name", "What the plan leaves open", "Public figures and
private parties", "Error categories", and "Amended on 2026-11-13": "Names in citations").
Read those sections first. This guide restates them and settles the cases they leave open.
Where this guide and that file disagree, that file wins and you report the disagreement.

## Privacy

The document is a published court judgment with real people's names. Write names only into
the output files named below, inside the private output folder. In your final answer to the
caller give counts and highlight numbers only: no names, no sentences from the document.

## The worksheet format

`docNN_compact.txt`: one line per paragraph, `¶K: text`. K counts from 0.
- `⟦N:text⟧` is a yellow highlight: the model labelled `text` as a person (PER). N is its number.
- `⟨LABEL:text⟩` is a grey highlight: the model gave `text` another label (for example ORG, GPE, LOC, TTL, FAC, DUC, EVE, WOA, ANG, MISC, TIMEX).
- Everything else is text the model did not label.
The first lines are the caption: the court, the panel of judges, the parties, the lawyers.

## What is one mention

- A given name, a surname or a full name of a natural person. Every occurrence is one mention.
  A full name written together (`יעקב כהן`, `ד"ר יעקב בן דוד כהן`) is ONE mention, not two.
- An initial with a surname (`א' כהן`, `ב' לוי`) is one mention.
- Attached prefix letters (ו ה ב ל מ כ ש and combinations) do not matter for counting: `ולכהן` is a mention of `כהן`.
- Two different people joined by "and" (`כהן ולוי`, `השופטים א' לוי וב' כהן`) are two mentions.
- The same person named twice in a sentence is two mentions.

## What is NOT a mention (never counted, whether highlighted or not)

- Placeholders: `פלוני`, `אלמוני`, bare initials that stand for a hidden name (`א.ב.`, `ר' ש'`).
- Roles and descriptions: `המערער`, `המשיבה`, `התובע`, `המנוח`, `השופט` alone, `ב"כ המערער`, pronouns.
- Titles are not part of the name: `עו"ד`, `ד"ר`, `פרופ'`, `השופט`, `השופטת`, `הנשיא`, `מר`, `גב'`, `כב'`.
- A person's name inside the name of an organisation, a firm, a street, a place, a statute or a doctrine
  (`משרד כהן ושות'`, `רחוב ז'בוטינסקי`, `הלכת אפרופים`, `קרן רוטשילד`, `בית חולים שיבא`).
- The title of a CITED decision: the party names in a citation such as `ע"א 123/45 כהן נ' לוי, פ"ד ...`
  or `עניין כהן`, `פרשת לוי`, `הלכת כהן`. These name a precedent.
- An author named INSIDE a reference to a book or an article (authors, title, edition, page), e.g.
  `לוי וכהן, דיני חיובים, בעמ' 100`. That names a cited work.

## What IS a mention even though it sits near a citation or a title

- A judge named as the author of a cited opinion: `(פסקה 5 לפסק דינו של השופט א' לוי)`,
  `(השופטת ב' כהן)`. Counted, public figure.
- An author named in the judgment's own sentence (`כפי שכתב פרופ' כהן בספרו`). Counted.
- The parties, lawyers and judges of THIS case, in the caption and in the text. Counted. The
  caption line `X נ' Y` of this case is not a cited precedent: its natural persons are counted.
- A dead person named in `עיזבון המנוח X` or `המנוח X ז"ל`: the name X is counted (the party is
  an estate, the name is a natural person's).
- A company, a kibbutz, a ministry, a bank, a court: not a person, not counted.

## Found, partial, missed (the strict rule)

- FOUND: yellow highlights cover every name token of the mention. Extra covered text (a title,
  a prefix letter, a comma) does not matter.
- PARTIAL: yellow covers only part of the name tokens (`⟦7:יעקב⟧ כהן` where the mention is `יעקב כהן`).
- MISSED: no yellow on the mention at all. If the whole name sits inside ONE grey highlight,
  it is still missed, with `other_label = yes`.
- Only the title is yellow (`⟦9:עו"ד⟧ כהן`): the highlight is not a person, and the name is missed.

## Verdict for every yellow highlight

Give each yellow highlight N exactly one verdict:

- `found`: it (alone or with the adjacent highlight(s) listed as `surplus`) fully covers one counted mention.
- `partial`: it covers only part of a counted mention.
- `surplus`: it is a second (third...) highlight on a mention that another highlight already
  stands for. Example: `⟦5:יעקב⟧ ⟦6:כהן⟧` for the one mention `יעקב כהן`: 5 is `found`, 6 is `surplus`.
  If two highlights each cover part of one name and a name token is left uncovered, one is
  `partial` and the other `surplus`.
- `not_person`: it is not a counted mention: a placeholder, a role, a title alone, a company or
  place, a name inside an organisation/street/statute/doctrine, a party name in the title of a
  cited decision, an author inside a book reference, or not a name at all.
- For a highlight that holds MORE than one counted mention (`⟦4:כהן ולוי⟧`): verdict `found`
  and put the number of extra persons in the `extra` column (1 for two people).

`group` for found / partial / surplus: `public` or `private` (see below). For `not_person`: `-`.

## Public figure or private party

- `public`: a judge or a registrar (of this case or of any cited opinion); an elected or
  appointed public official named in that role (a minister, the Attorney General, a mayor);
  a lawyer or an expert that a reader of the news would recognise by name.
- `private`: everyone else: the parties, witnesses, doctors, experts, appraisers, mediators,
  arbitrators, and the lawyers of record of this case and of other cases.
- Unsure: choose `private` and write the highlight or the miss into the doubts file.

## Misses and partials

For every MISSED mention and every PARTIAL mention write one line (columns below). For a
partial, `text` is the whole name as it should have been covered.
`category`:
- `proclitic`: the mention carries an attached prefix letter (`ולכהן`, `שברק`... only if the prefix is attached to a name token).
- `ordinary_word`: a name token is also an everyday Hebrew word (`ברק`, `שלום`, `אור`, `טל`, `חיים`, `שחר`, `רון`, `יונה`, `גל`, `חן`, `דקל`, `נועם`).
- `both`: both of the above.
- `other`: neither.
If you are unsure whether a token is an everyday word, pick what you think and add a doubt line.

## How to work

1. Read the whole document once, top to bottom, slowly. For each paragraph, go through every
   yellow highlight and give it a verdict, and look for person names with no yellow on them:
   after titles and role words, in lists of lawyers and judges, in signatures at the end
   (`ניתן היום ... ש ו פ ט`), inside parentheses, and names with attached prefix letters.
   Names written with spaces between letters are not names (they are the word "judge" etc.).
2. Read `docNN_spans.csv` to make sure you gave a verdict to EVERY highlight number from 1 to
   the last one, each exactly once.
3. Go through `crosscheck_docNN.csv`: each row is a place that may hold a missed name (a word
   the model highlighted elsewhere, found outside a highlight; or the word after a title).
   Look at each row. Most are not misses (a name inside a citation title, a common word). Any
   that is a counted mention with no yellow on it must be in your misses.
4. Write the three output files.

## Output files (write them into the private output folder, UTF-8, comma-separated, with header)

`docNN_marks.csv` — one row per yellow highlight, in order:
`highlight,verdict,group,extra,note`
- `highlight`: the number. `verdict`: found | partial | surplus | not_person. `group`: public | private | -.
- `extra`: 0, or the number of extra persons inside this one highlight.
- `note`: a few words only when the verdict is not `found` (why), else empty. No commas inside it.

`docNN_misses.csv` — one row per missed or partial mention:
`doc_id,paragraph,text,kind,group,other_label,category,highlight`
- `kind`: missed | partial. `other_label`: yes | no (only a missed mention can be yes).
- `highlight`: for a partial, the number of the yellow highlight listed as `partial`; empty for a miss.
- Put `text` in double quotes if it holds a comma.

`docNN_doubts.txt` — free text, one doubt per line: the paragraph number, the highlight number
or the words, what you decided and why you were unsure. Write "none" if there is none.

## Your final answer to the caller

Counts only: number of highlights; how many found / partial / surplus / not_person; how many
public and private among found; how many misses and partials, by category and by group; how
many crosscheck rows you looked at and how many of them were misses; how many doubt lines.
No names and no text from the document.
````

## What this rules in and what it rules out

Rules in:

- The threshold is not crossed, by a wide margin: 95.5 percent against 80. As far as E1 can say, the architecture stands and the plan goes on.
- Achia's concern of 2026-11-12 is visible but small here: 99.4 percent on public figures, 93.2 percent on private parties. Both groups have far more than 30 mentions. Private-party recall alone is also far above 80.
- In `doc10` the model's main failure is a wrong label, not a blind spot. 12 of the 18 misses are one surname under ORG. One more is a given name under LOC. One more place of that surname has no label. Any-label recall is 98.3 percent. Outside `doc10`, none of the 4 misses sits under another label.
- The full names of the people who carry that surname are highlighted elsewhere in `doc10`. Phase 6 links a lone surname to a full-name entity only "when exactly one candidate exists" (`build-plan.md:707`), and groups a family by a shared surname (`build-plan.md:712`). At least three people carry the surname here, so the plan's answer is `ambiguous`, not a link. And `build-plan.md:717` has all detections of one entity share one type, so a span labelled ORG cannot join a person as the plan stands.
- Reading the caption mattered. Before #47 the reader skipped it. It holds 3 of the 21 errors.

Rules out, or does not show:

- **Nothing about a lawyer's own documents.** These are Supreme Court judgments: formal language, and names introduced with a role and a title. Achia's concern, recorded in the pre-registration, is that such text is close to what the model was trained on. A contract, a letter or a medical summary may behave differently. `build-plan.md:687` says published decisions are for realism, "never as ground truth". Above the prediction is a reason for caution, not for comfort.
- **Nothing about trial-court judgments**, which quote contracts and testimony at length and were the corpus Achia first asked for.
- **Not a sample.** Ten documents by one rule on one search. One document carries 14 of the 21 errors, and one surname 13 of them.
- **The count is a model's.** A name that neither the model under test nor the reader recognises is counted by neither. Two separate readings agreed on four documents, which says the readers are consistent with each other, not that they are right. Both had the same guide, and the second reader was told not to open the first reader's files; nothing enforced it. The one check by a person that was registered will not be done (addition of 2026-11-14 under "What is not done").
- **Recall only.** What the product does with the names in citations and references, 216 of them highlighted, is not measured here; the counting rules leave them out.
- **Where the errors fall depends on one reading.** Under the reading taken, 7 of 21 errors are ordinary-word or prefix cases, and the prediction did not hold. Under the other reading of the group term it holds (7 of 8). Prefix forms were not rare: by the reviewer's mechanical count at least 33 counted highlights begin with an attached prefix letter, 23 of them in `doc10`, against 1 missed.

## Options, with the cost of each

1. **Take E1 as not crossing the threshold and go on to Phase 0.** As first written, this waited for Achia's check of `doc06`. Since 2026-11-14 that check will not be done, so the cost is that the number is taken with no check by a person. It stands for Supreme Court civil judgments and for nothing else.
2. **Run E1 again on the documents the product is for** (trial-court judgments that quote contracts, or real contracts and letters) before Phase 3 records its first baseline. Cost: the source has to be settled first (issue #4: the trial-court decisions sit on Net HaMishpat), then a run and a count like this one. The Phase 3 gate asks for PERSON recall "on the 10 real Hebrew documents" (`build-plan.md:645`), so this decides which ten those are.
3. **Carry the `doc10` surname into Phase 6 as a named test:** a surname shared by several people, standing under a wrong label (12 places) or under no label (1 place), does not stay in the output. It is raised as `ambiguous` or grouped as a family, as `build-plan.md:707` and `:712` have it. It is not linked to one person. Cost: one test case in Phase 6, and a change to the plan if the test shows that a span labelled ORG cannot reach a person (`build-plan.md:717`).
4. **Have a person count more than one document.** Cost: several hours of careful reading per document. It measures the annotation error that this note cannot.

## Recommendation

**Proposed decision, for Achia to confirm or change.**

1. Option 1. E1 does not cross the threshold. The architecture stands and Phase 0 starts. The number is recorded as 95.5 percent on ten Supreme Court civil judgments, counted by Claude and not checked by a person.
2. Option 3. The shared surname of `doc10` goes into Phase 6 as a named test, in the wording of option 3.
3. Option 2, before Phase 3's baseline and not before Phase 0. Phases 0 to 2 do not use the Hebrew model (`build-plan.md:517` to `:620`; Hebrew NER starts at `:621`), so nothing waits on it. Which documents, and from where, is Achia's to say.
4. Not option 4. As first written, this point rested on Achia's check of `doc06`. Since 2026-11-14 no person checks the count. What stands in for it is the second part of experiment E4: a Claude reader's count is compared with a ground truth on generated documents. If that check falls below its threshold, this note is amended to say that E1's count is not supported.

## Scope requested

None. This is not a waiver request.

## Decision

Achia, 2026-11-15, in the Claude Code session. Claude asked, word for word:

> One decision of yours stands between us and Phase 0: **is the model good enough at finding names to start building?**
>
> - **E1, real court judgments:** 449 of 470 names found (95.5%). I counted these, and no person checked the count.
> - **E4, generated text where a script knows every name:** 1,084 of 1,145 found (94.7%), as predicted.
> - **The bar in the plan:** below 80% means rethink the architecture. Both results are well above it.
> - **Known weak spots:** a surname after a group word such as `משפחת`, and a first name alone that is also an everyday word. Both would become named test cases.
>
> I recommend yes. If you say yes, I write your decision into the two findings notes as a PR for you to approve, and then start Phase 0 with the merge gate.
>
> **Start Phase 0: yes or no?**

Achia answered:

> Yes

What follows from it, as Claude reads it:

1. Option 1. E1 is taken as not crossing the threshold. The architecture stands and Phase 0 starts. The number stays recorded as it is: 449 of 470, 95.5 percent, on ten Supreme Court civil judgments, counted by Claude and not checked by a person. It stands for Supreme Court civil judgments and for nothing else.
2. Not option 4 now: Phase 0 does not wait for a person's count. The question said that no person checked the count, and the answer was yes. Achia chose on 2026-11-14 not to spend that reading time ("What is not done", above). What E4 is taken as is in its own note (`docs/findings/2026-11-14-e4-planted-names.md`, Decision, point 1).
3. A surname after a group word becomes a named test case. The shared surname of `doc10` is the case of it in E1, and option 3 proposes Phase 6 for it. Where the test sits in the plan and what it asserts is a PR to `build-plan.md`, which needs Achia's decision. That PR is not written yet, and nothing in Phase 0 waits on it. The other weak kind the question named, a given name alone that is an everyday word, is in the E4 note (Decision, point 2).
4. Not decided here: option 2, running E1 again on documents closer to the ones the product is for, before Phase 3 records its baseline. The question did not ask it. Which documents, and from where, stays Achia's to say (issue #4). Nothing before Phase 3 waits on it.
