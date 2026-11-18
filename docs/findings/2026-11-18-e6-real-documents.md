# Finding: E6, on twenty real court decisions: on the closed pile `carry` finds 22 of the 25 names that the plan's model misses, for 3.13 more words per 1,000 marked for nothing, so by the rule written beforehand E5's result holds. Without one long document the closed pile would have been too small to say. The answer key was made by Claude, in three models, and no person checked it. Four of eleven predictions failed

This note is not about a gate that failed. It reports the real-document test that Achia put first on 2026-11-18, with `## Decision` left empty. It decides nothing: the model of Phase 3 and the place of `carry` in the plan stay as they are until he decides.

Read the limits first. They are as much the finding as the numbers.

1. **The answer key is Claude's, and no person checked it.** Every number below is "found, of the names in the key".
   - Two labellers of one model (A and B, sessions of Claude Fable 5.2) marked all twenty documents and agreed on every counted name, 718 of 718. That showed they are one reader twice. The pre-registration was amended, before the third pass, the freeze and any run: a third labeller C (sessions of Claude Opus 5.5) marked every document, and the key is made from A and C. A and C mark the same counted name at the same place for 717 of 728, 98.49 percent. A third pass (sessions of Claude Sonnet 5.5) settled the 32 labels in which they differ, nearly all by rules written down before it began, and by its sessions' reports found no name among the 166 places the two lists gave it. The frozen key holds 1,078 labels, 719 of them counted names; it differs from A in 4 labels.
   - After each pile was scored, the session that ran the experiment read every word that the judged methods marked outside the key, with the text around it: 155 different words in the open pile and 178 in the closed one. **It found no person's name among them that the key lacks as a counted name.** A handful are words inside the name of a company in the title of a cited decision.
   - What nobody can see: a name that no reader and no judged method marked. That no labelling session read another's files rests on the sessions' word.
2. **The pre-registration was changed after data were seen.** Not after any detector output: after the count of how far the labellers agree. Both parts of the amendment are in `experiments/e6_real_documents/PREREGISTRATION.md`, with what had been seen when each was written; an independent reviewer read the first part before the third pass and found it sound and five things unsaid, which the second part says.
3. **One document carries the verdict.** The closed pile holds 477 counted names in ten documents; one document holds 146 of them, and 12 of the 25 names the plan's model misses. `carry` finds all 12. In the other nine documents the model misses 13 and `carry` finds 10. Thirteen is under the 15 the rule asks for, so **without that document the answer for the closed pile would be "too few to say"**, though the share found is of the same kind (10 of 13). The pre-registration asked for this split before any run.
4. **Twenty decisions of one court are a sample of nothing.** They were chosen by reading captions and page counts. The language is that of appeals. `build-plan.md` Phase 5 says of published decisions: "Use them for realism, never as ground truth."
5. **The open pile says little about the plan's model:** it misses 4 of 242 there.
6. **Two readings of Claude's were not put to Achia** and are marked in the pre-registration: that his words of 2026-11-14 about E1's hand check carry over, so that no person checks this key; and that the three models he allowed on 2026-11-17 "for this experiment only", which was E5, may also be run here.

## What was being measured

E5 found on generated text that the step `carry` (a name the detector found anywhere in a document is marked wherever else it stands in that document, also behind attached letters) took the plan's model `dicta-il/dictabert-joint` from 1,482 to 1,587 of 1,595 planted names. The same author wrote that text and the steps. Achia decided on 2026-11-18 that `carry` goes into the plan "as a thing to build and measure. It is not adopted for good until it is measured on real documents", that the real documents come from the Supreme Court's public site only, and that they are used in two piles: "Half of the new real documents I may look at and learn from. The other half is kept closed and scored only once, at the end, as the fair judge." (`docs/findings/2026-11-17-e5-methods.md`, `## Decision`.)

E6 is that measurement. Twenty decisions in civil matters, 4 to 13 pages each, 6 on the sale of a flat, 6 defamation, 6 tenancy, 2 road accidents; none is one of E1's ten. Ten are the open pile and ten the closed one, drawn by a rule that looks at ids only. The methods are E5's, built and scored by E5's own code: a detector, alone or with steps on top. Recall is E4's strict rule: a counted name is found when what is marked covers every character of it. Beside it, the Hebrew words a method marks that lie in no name of the key, per 1,000 words of text.

**The order, by commits on `feat/e6-key-and-runs`.** The pre-registration and the harness merged first (#99, `4939bc6`). Then: the amendment (`9aec880`, `7f78e1d`); the hashes of the frozen key (`f34fbf3`); the open pile's table (`3ac0d77`); the one fitted method (`ad9cd65` tests, then the code); the list of what is judged on the closed pile (`375f327`); the closed pile's table (`1a933a6`). The commit order shows which file came before which. That no detector was run on a document before its key was frozen, or on the closed pile before the list was committed, rests on the author's word and on the dates of the run files.

## Prediction and threshold

Written before any labelling and any run (`PREREGISTRATION.md`, "Predictions and thresholds"). On the open pile unless it says otherwise; "per 1,000" is per 1,000 Hebrew words of the pile, titles left out.

| # | Prediction | Measured | Verdict |
|---|---|---|---|
| 1 | `joint + whole words` finds 92.5 to 98 percent | 238 of 242, 98.35% | **failed**, over |
| 2 | `joint + carry` finds 1 to 3.5 points more than `joint + whole words` | 240 against 238, 0.83 points | **failed**, less: there were 4 errors to find |
| 3 | `joint + carry` finds 97 to 99.6 percent | 99.17% | held |
| 4 | `joint + carry` marks fewer than 5 more words per 1,000 for nothing | 90 against 14 words in 20,349: 3.73 more | held |
| 5 | `joint + titles, carry` marks more than 5 more per 1,000 | 141 against 14: 6.24 more | held |
| 6 | `golem + whole words` finds fewer names than `joint + whole words` | 233 against 238 | held on the open pile; on the closed pile it is the other way round, 462 against 452 |
| 7 | For `joint + whole words`, `public` is 0 to 8 points over `private` | public 102 of 105, 97.14%; private 136 of 137, 99.27% | **failed**: public is 2.13 points under |
| 8 | For `joint + carry`, `lonely` is the lowest row of 30 or more | `lonely` 54 of 54; the lowest is `public`, 103 of 105 | **failed** |
| 9 | On the closed pile `joint + carry` is within 2.5 points of its open number | 99.37% against 99.17% | held |
| 10 | The two labellers mark the same counted name for at least 90 percent | A and B: 718 of 718 | held, and it says nothing (limit 1); A and C: 717 of 728 |
| 11 | `joint` takes 20 to 60 seconds per 1,000 words | 531.2 s for 20,349 words: 26.1; closed 556.1 s for 21,431: 25.9 | held |

**Four of the eleven failed: 1, 2, 7 and 8.** All four are about the open pile, where the plan's model left 4 errors; with so few, one name is 0.4 points and the rows cannot be told apart.

## Measured result

### The verdict

"What 'holds on real documents' means" was written before any run and corrected, before any labelling, after the first review. On the closed pile, by the frozen key:

- `joint + whole words` does not find 25 of 477 counted names. That is 15 or more, so the rule gives an answer for the closed pile alone.
- `joint + carry` finds 22 of the 25, which is more than one third.
- `joint + carry` marks 84 words for nothing against 17: 67 more in 21,431 words, 3.13 per 1,000, under 5.

**So the answer is "holds".** After the one scoring the words marked outside the key were read: no name that the key lacks was found, among those `joint + carry` marked or among the others (limit 1). The split of limit 3: 12 of 12 in the one long document, 10 of 13 in the other nine.

### The two piles

Scored by the frozen key. "Extra" is the number of Hebrew words marked that lie in no name of the key; no judged method marked a title, so the count with titles is the same.

| Method | Open: found of 242 | Open: extra, per 1,000 | Closed: found of 477 | Closed: extra, per 1,000 |
|---|---|---|---|---|
| `joint + whole words` (the plan's model alone) | 238, 98.35% | 14, 0.69 | 452, 94.76% | 17, 0.79 |
| `joint + carry` | 240, 99.17% | 90, 4.42 | 474, 99.37% | 84, 3.92 |
| `joint + titles, carry` | 242, 100% | 141, 6.93 | 474, 99.37% | 151, 7.05 |
| `joint + titles, carry strong` (the open pile's best by E5's order) | 242, 100% | 62, 3.05 | 474, 99.37% | 104, 4.85 |
| `joint + carry strong, titles` (fitted on the open pile) | 242, 100% | 57, 2.80 | 474, 99.37% | 95, 4.43 |
| `golem + whole words` | 233, 96.28% | 8, 0.39 | 462, 96.86% | 5, 0.23 |
| `golem + carry` | 233, 96.28% | 39, 1.92 | 472, 98.95% | 41, 1.91 |
| `golem at 0.03 + titles, carry` (E5's winner of all) | 241, 99.59% | 135, 6.63 | 477, 100% | 133, 6.21 |

The closed pile was scored once, for these eight, which `results/CHOSEN.md` names. The open numbers of the fitted method say how well it was fitted and nothing else. The tables as printed are `experiments/e6_real_documents/results/open.md` (70 methods), `open_fitted.md` and `closed.md`.

### Where the plan's model fails on real decisions

The 25 names of the closed pile that `joint + whole words` does not find, by kind. No name is written here; the listing is in a folder outside the repository.

| Kind | Names | `carry` finds |
|---|---|---|
| A name that is also an everyday word: one surname 9 times and one given name twice in one document, one surname 5 times in another, the first word of a full name once | 17 | 16 |
| One surname, three times, where it stands for a couple | 3 | 3 |
| A name behind an attached letter, no everyday word | 1 | 1 |
| An initial before a surname, after "and" with a hyphen | 2 | 0 |
| A full name of four words on a line of its own, found in part | 1 | 1 |
| A foreign surname, once | 1 | 1 |

Eleven of the 25 stand behind attached letters. These are the kinds E4 named on generated text: a name that is an everyday word, and a name behind attached letters. The three that `carry` leaves are found only in part: the two initials, and a full name whose first word is an everyday word that the model marks nowhere in the document.

In the open pile the four are: two initials of judges before a surname the model marked, one surname alone, and half of a full name on a line of its own. `carry` finds the last two; `titles` finds the two initials.

### What `carry` marks for nothing

On the closed pile `joint + carry` marks 67 words more than the model alone, in 21,431. Almost all of them are a few everyday words, each spread through one document:

- the word for "the company", in its forms, which the model once marked inside a company's name in the title of a cited decision: about 20 times, most of them in one document;
- two everyday words in one document, one of them a relative word that is also a given name: about 22 times, also behind attached letters;
- the company suffix `בע"מ`, marked once inside a cited title: about 15 times in two documents;
- an everyday word that is also a short name, bare or cut out from behind attached letters by the step: a handful per document.

In the open pile it is the same picture: one role word that the model marked once inside the title of a cited decision is spread about 35 times through one document. With `carry strong`, which carries only a word that was marked twice or beside another marked word, that one is gone, and the open pile's count falls from 90 to 50 at the same recall. `carry strong` alone was not among the methods judged on the closed pile.

### `titles` on real text

The step marks the word after a title "whatever it is" (E5's own stated limit). On real decisions that word is often no name. In the stack `titles, carry` it is then spread: in one closed document the word `כי` after `עו"ד` about 35 times, in another the word `מיום` after `בד"ר`, an abbreviation for a rabbinical court that the step reads as the title `ד"ר`; in one open document the word `על` about 40 times. On the closed pile `joint + titles, carry` finds the same 474 names as `joint + carry` and marks 67 words more. On the open pile it finds 2 names more, the two initials. The fitted order, `carry strong` before `titles`, does not spread the title's word; it is 5 to 9 words better than the other order and finds the same names.

### The detectors alone, on the open pile

All four that are on the laptop were run on the open pile; only `joint` and `golem` were needed for the closed one.

| Detector, with whole words | Found of 242 | Private, of 137 | Public, of 105 | Extra | Seconds | Peak memory |
|---|---|---|---|---|---|---|
| `joint` (the plan's model) | 238, 98.35% | 136 | 102 | 14 | 531 | 1,601 MB |
| `golem` | 233, 96.28% | 136 | 97 | 8 | 110 | 879 MB |
| `large` | 217, 89.67% | 131 | 86 | 83 | 346 | 2,060 MB |
| `seter_fast` | 178, 73.55% | 134 | 44 | 129 | 232 | 1,923 MB |

`seter_fast` finds 44 of 105 public names: it was trained to find private persons, and most public names here are judges. What `golem` misses are mostly judges' names found in part: an initial with a surname, or a surname with a hyphen. On the closed pile `golem + whole words` finds 462 of 477 and `joint + whole words` 452, so which of the two is better alone depends on the pile: `golem` does not lose the everyday-word surnames that cost `joint` 17 names there.

### Time and memory

Seconds are the time inside the detector, model loading left out, 4 threads, one run each, on the laptop of `docs/REFERENCE_MACHINE.md` with other programs running and 1.2 GB of 7.72 GB free before the first run. `joint`: 531.2 s for the open pile and 556.1 s for the closed one, each in two parts of at most seven minutes; 26 seconds per 1,000 Hebrew words; peak 1,601 and 1,889 MB. `golem`: 110.1 and 115.5 s, 5.4 seconds per 1,000; peak 879 and 881 MB. E5 measured `joint` at 602 s for 16,871 words of generated text, 35.7 per 1,000; the two are not the same text, and nothing here says why they differ. No time is a gate.

### The key, in numbers

| | |
|---|---|
| Documents, paragraphs, words between spaces | 20; 993; 43,209 |
| Labels of A, B, C | 1,076; 1,069; 1,060 |
| A against B: the same counted name at the same place | 718 of 718; 14 labels differ, none a counted name only one has |
| A against C | 717 of 728, 98.49%; 32 labels differ, 10 in the kind only |
| Places the two lists gave the third pass | 166; by its reports, none a name |
| The key | 1,078 labels, 719 counted (242 open, 477 closed); 4 labels differ from A |
| The check before the freeze | no label of the key without ground, none of A and C not kept, in all twenty |
| Flags of the subject check, by twelve labelling sessions | none |
| Words marked outside the key by the judged methods, read after scoring | 155 open, 178 closed; no counted name the key lacks |

### The runs

- Harness: as merged in #99, with the one fitted method added on the branch (`score_real.FITTED`), and E5's scorer taking methods beyond its grid.
- Run files: in `C:\Users\Achia\ploni-e6-out\runs`, outside the repository, each carrying the digest of the text it was made on: open `a2bdfd53...`, closed `b07568fe...`.
- Weights, checked by the runner before each run: `joint` `c59db02c...` (E1's pin), `golem` `e94e31a5...`, `seter_fast` `803221b9...`, `large` `763e556e...`; full hashes in `docs/THIRD_PARTY.md`.
- Record: `experiments/e6_real_documents/results/record.jsonl`, 78 lines, one per method and pile; numbers and method names only.
- Nothing of a document is in the repository: no name, no sentence. The words quoted in this note (`כי`, `מיום`, `על`, `בע"מ`, `בד"ר`) and the two titles beside them are everyday words, titles and abbreviations, not names.

## What this rules in and what it rules out

Rules in:

- On these twenty decisions the weak kinds of E4 are real: where the plan's model fails on real text, it fails on a name that is an everyday word and on a name behind attached letters, and one such surname in one document costs a dozen names.
- `carry` finds those names, because the model does find the same name elsewhere in the document. On the closed pile it leaves 3 of 477, all three found in part.
- The price of `carry` on real text is a few everyday words spread through a document, 3 to 4 per 1,000 words here. Most of it starts from a word the model marked wrongly once, inside a company's name or a cited title.
- `titles` as E5 wrote it is not worth its price on real decisions: it adds the two initials on the open pile and nothing on the closed one, and it marks the word after a title also where that word is no name.

Rules out, or does not show:

- Not that any method finds every name: the key cannot show a name nobody marked (limit 1).
- Not which model is better. `joint` is ahead on the open pile and `golem` on the closed one when each stands alone; with `carry` on top `joint` is ahead on both, 99.17 and 99.37 percent against 96.28 and 98.95. `golem` at its low threshold with `titles` and `carry` finds all 477 of the closed pile and 241 of 242 of the open one, and marks 6 to 7 words per 1,000 for nothing.
- Not what happens on a law firm's own documents, or on text that is not a court decision.
- Not whether `carry strong` is the better form: it was better on the open pile and was not judged alone on the closed one.
- Not that the product can afford the price: a word marked for nothing is replaced in the output, and whether 3 to 4 everyday words per 1,000 is acceptable is Achia's to say.

## Options, with the cost of each

1. **Adopt `carry` as a step of the product**, after detection, on whatever model Phase 3 uses. E5's code is a few dozen lines with no model and no dependency. Its cost on real text is now measured here: 3 to 4 everyday words per 1,000. In which phase it is built, and how it sits with Phase 6, was not asked on 2026-11-18 and is still open.
2. **Leave `titles` out, and measure one narrow rule in its place:** an initial that stands right before a marked surname belongs to the name. That is 4 of the 5 names `joint + carry` leaves over both piles. It is not built and not measured.
3. **Make `carry` cheaper before it is built:** do not carry a word that the model marked only inside the name of a company or a cited title; do not cut attached letters off an everyday word to find a short name. Neither is built or measured. `carry strong` is built and was measured on the open pile only.
4. **Decide the model of Phase 3.** `joint` with `carry`: 99.2 and 99.4 percent here, 26 seconds per 1,000 words, up to 1,889 MB. `golem` with `carry`: 96.3 and 99.0 percent, 5.4 seconds per 1,000, 881 MB; at a low threshold with `titles` and `carry`, 99.6 and 100 percent at about twice the words marked for nothing. A new model in the product is a decision of its own: its licence (MIT) and its card read by Achia. Using both models together was not judged on the closed pile.
5. **Run the three models he allowed on 2026-11-18** (`seter`, the 8-bit `seter_fast`, GLiNER multi v2.1) on the same twenty documents before deciding 4. The key and the harness exist; the closed pile has now been scored once, so a number from it for a new method is no longer blind and would be named so.
6. **More real documents, or a person's check of the key.** The verdict rests on one long document (limit 3) and on a key no person checked (limit 1). Either would make it firmer; both cost time, and the second is his own time, which he declined for E1.

## Recommendation

Option 1, with option 3 measured when it is built; option 2 as a small measurement; option 4 after option 5.

What the numbers carry: on real decisions `carry` does what E5 saw on generated text. It finds the names the plan's model misses where they are an everyday word or stand behind attached letters, and its price is small and of one kind. The rule written before the runs says "holds", and the reading of everything the methods marked outside the key found no name that would change it.

What they do not carry: a number near 100 percent that a person has checked. The key is three models of one family agreeing with each other. And the verdict needed one document to reach the 15 errors the rule asks for.

On the model: the two are close enough here that the choice turns on time and memory as much as on names, and on whether the product may mark 6 words per 1,000 for nothing to find the last few. That is his to weigh, and the three models he allowed may still change the picture.

## Scope requested

None. This is not a waiver request.

## Decision
