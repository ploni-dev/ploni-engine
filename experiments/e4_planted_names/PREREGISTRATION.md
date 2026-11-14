# E4 pre-registration: PERSON recall against a ground truth that is known by construction

Committed before any template was written and before the model was run on generated text.
The commit order is the evidence.

**Amended on 2026-11-14, before any run: see the last section. It changes the classes of
names, the rows of the report and which prediction each carries, and it fixes the second
part. What stands above it is kept as first written.**

## Why this experiment exists

It is not in `build-plan.md` section 11, which has three experiments. Achia asked for it on
2026-11-14, after E1: "create a method to verify it and have a ground truth so i dont need
to involve like that".

E1 (`docs/findings/2026-11-13-e1-hebrew-recall.md`) measured 449 of 470 on ten real
judgments. Its count was made by Claude readers, and no person checked it. Two things E1
cannot say follow from that:

- how many names the readers themselves overlooked or counted wrongly;
- what the model does on a contract, a letter or a medical summary, which is what the plan
  first asked for and what E1's corpus does not hold.

E4 answers both with text whose right answer is known exactly, because a script puts every
name in its place and writes down where it put it. Nobody reads anything in order to count.

It is a first, small form of the generator of `build-plan.md` Phase 5 ("Synthetic
generator ... Emits documents plus gold span annotations"). It lives in `experiments/` and
is not that generator.

## What is generated

- **Text.** Eight templates, written by Claude for this experiment, in Hebrew: two trial-court
  judgments (a contract dispute, a road accident), two contracts (a lease, an employment
  agreement), two letters (a lawyer's demand letter, a lawyer's letter to a client), two
  medical documents (a discharge summary, a medical opinion for a court). Everything in them
  is invented. No sentence is taken from a real document.
- **Names.** A name bank in the repository: common Israeli given names and surnames, by
  gender, Hebrew, Arabic and transliterated. No name of a real person is meant. The bank
  marks two classes the plan calls hard: a name that is also an everyday Hebrew word
  (`אור`, `טל`, `שלום`), and a name that begins with a prefix letter and carries none
  (`ברק`, `משה`, `לביא`).
- **Documents.** Each template is filled five times with different people: 40 documents.
  The seed is fixed in the code, so the corpus is the same on every run.
- **Mentions.** A template holds slots. A slot names a person of the document and a form:
  full name; given name alone; surname alone; a title and a surname; an initial and a
  surname; any of these with attached prefix letters; a name alone on a line, as in a
  caption or a signature; a surname in a group term (`האחים`, `משפחת`). At least 1,000
  counted mentions in the 40 documents, and at least 30 of each form.
- **Names that are not counted.** The templates also hold what E1's rules leave out: a name
  in the title of a cited decision, a name inside the name of a firm, a placeholder. The
  script knows these too and marks them as not counted.
- **Gold.** For every mention: the paragraph, the start and end of the name in characters,
  the person, the form, the classes of its name, and whether it is counted. A test checks,
  on every generated document, that the text at each gold position is exactly the name.

## How it is scored

By a script, with E1's strict rule: a counted mention is **found** if `PER` spans of the
model cover every character of the name; **partial** if they cover some of it; **missed**
if none. A title and attached prefix letters are outside the gold span, so covering them or
not changes nothing. A mention under another label is missed, and counted apart, as in E1.
The model, its revision and the input handling are E1's (`PREREGISTRATION.md` there,
"Model and input handling, frozen").

Primary number: found over all counted mentions, pooled over the 40 documents, as an exact
fraction.

## Prediction and threshold, Claude's, stated before any run

Achia set none. These are Claude's.

| What | Prediction | Outside the prediction | Threshold |
|---|---|---|---|
| Strict recall, pooled | 90 to 96 percent | below 90, or above 96 | below 80 percent: the same line the plan draws for E1. Stop, findings note, the decision is Achia's |
| Against E1 | within 10 points of E1's 95.53 | | more than 10 points under E1 (below 85.53): E1's number does not carry over to this text. Said in the first line of the findings note |
| A surname in a group term | under 50 percent found (E1: 1 of 14) | 50 or more | none |
| A given name alone that is an everyday word | 60 to 90 percent | outside that | none |
| Every other form | 90 percent or more, each | under 90 | none |
| Document kind | no prediction. Reported: judgments, contracts, letters, medical | | |

A number above the prediction is a finding too: text written by a language model may be
easier for a language model than a person's text.

## The second part: are Claude's readers right?

E1's count rests on readers. Here their count can be compared with the truth.

- Four documents, the first filling of one template of each kind, are counted by a Claude
  reader in the way E1's documents were: from the worksheet with the model's highlights,
  with the guide printed in the E1 findings note, without the gold.
- The reader's result is compared with the script's, mention by mention: for a counted
  mention, found, partial or missed; for a name that is not counted, that the reader did
  not count it.
- **Agreement** is the share of gold items, counted and not counted, on which the reader
  and the script say the same. A mention the reader lists and the gold does not have is
  also a disagreement.

| What | Prediction | Threshold |
|---|---|---|
| Reader against gold, over the four documents | 98 percent agreement or more | below 95 percent: E1's count is not supported by this check, and the E1 findings note is amended to say so |

## What this cannot show, stated before the run

- The text is written by a language model. Its sentences may be more regular than a
  person's, and names may sit in more predictable places. Recall here says what the model
  does on such text, not on a client's document.
- The names come from a bank. A real document has names no bank holds.
- Five fillings of one template share every sentence. Mentions in them are not independent:
  a slot the model cannot read is missed five times. The report is also given per template.
- The readers' check covers four documents written to be read, shorter and cleaner than a
  judgment of twenty pages.
- No person checks this either. What replaces the person is that the right answer is
  written down by the script before the model runs.

## Decision rule

- Pooled strict recall below 80 percent: threshold crossed. Stop; findings note.
- 90 to 96 percent: inside the prediction.
- Anything else: outside the prediction, threshold not crossed.

No number is rounded before it is compared. The findings note gives the report as printed,
per form, per kind of document and per template, and leaves `## Decision` empty.

## Amended on 2026-11-14, after the review of the harness and before any run

The model has not been run on generated text. A fresh review of the harness, in two passes,
found no fault in the gold or in the scorer, and asked for the changes below. The prediction
for the pooled number, the two thresholds and the decision rule are unchanged.

**The names.** A person's given name and surname now come from one origin: Arabic with
Arabic, transliterated with transliterated, the rest with the rest. Before the change a
quarter of the people mixed them, which real documents do not.

**Two kinds of name that is also a word.** The bank now marks them apart. The marking is
Claude's judgement, made before the run; the list is `names.tsv`.

- `ordinary`: a modern name taken from an everyday word, the kind the plan lists in Phase 1
  (`אור`, `טל`, `שחר`). The prediction "a given name alone that is an everyday word, 60 to
  90 percent" is about this class and no other. Its row is `given_ordinary`.
- `also_word`: a traditional name that is also an everyday word (`דוד`, `מרים`, `אריה`,
  `חיים`, `יצחק`). Its row is `given_also_word`. It carries no prediction.

**Which rows "every other form, 90 percent or more" means.** The rows of the report used to
overlap, so a miss that one prediction expects could pull another row under 90. Now:

| Row | What is in it | Prediction |
|---|---|---|
| `group` | a surname after `האחים` or `משפחת`, with or without prefix letters | under 50 percent |
| `given_ordinary` | a given name alone, of class `ordinary`, with or without prefix letters | 60 to 90 percent |
| `full`, `surname`, `title_surname`, `initial_surname` | the form | 90 percent or more, each |
| `given_plain` | a given name alone, of neither word class | 90 percent or more |
| `prefix_on_name` | prefix letters attached to the name itself; a given name alone of class `ordinary` is not in this row | 90 percent or more |
| `prefix_on_title` | prefix letters attached to the title before the name | 90 percent or more |
| `alone` | a name that is the whole line | 90 percent or more |
| `given`, `given_also_word`, `prefixed` | all given names alone; the `also_word` ones; every mention with prefix letters, whatever they are attached to | none, reported |

A mention is in its form row and in every other row that fits it, so one miss can show in
two rows. No mention of the two rows with a lower prediction, `group` and `given_ordinary`,
is in a row that predicts 90 or more, except the form row `given`, which predicts nothing.

**The corpus as it is now generated.** 40 documents, 1,035 paragraphs, 67,145 characters,
1,145 counted mentions, 55 names that are not counted (30 in cited titles, 20 in firms, 5
placeholders).

| Row | Mentions |
|---|---|
| `full` | 410 |
| `given` | 290: `given_ordinary` 169, `given_also_word` 25, `given_plain` 96 |
| `surname` | 120 |
| `title_surname` | 205 |
| `initial_surname` | 65 |
| `group` | 55 |
| `prefixed` | 230: `prefix_on_name` 64, `prefix_on_title` 95, on a group word 25, on a given name alone of class `ordinary` 46 |
| `alone` | 135 |

People: 250, of them 29 with Arabic names and 37 with transliterated ones.

**The second part, fixed before the run.**

- The four documents are `doc01`, `doc11`, `doc21` and `doc31`: the first filling of the
  first template of each kind, in the order of the file names. They hold 116 counted
  mentions and 7 names that are not counted.
- `run.py --worksheets-dir` writes their worksheets and span lists from the same run that
  gives the E4 number, in E1's formats. No file it writes holds a gold position.
- The reader works as E1's readers did: one fresh Claude session per document, the guide
  printed in the E1 findings note, the plain-text worksheet and the cross-check lists made
  by the same throwaway scripts, and the same three output files.
- The reader must not see the gold, and the gold is in this repository: a template shows
  every slot. The reader's brief names only the folder of worksheets, which is outside the
  repository, and tells the reader not to open `experiments/e4_planted_names/`. Nothing
  enforces that. So a high agreement shows that a reader can count, and cannot show that
  this reader did not look.
- The comparison, item by item. For a counted mention the script's verdict is found,
  partial or missed. The reader's verdict is read from the reader's files: partial if a
  highlight that overlaps the name is marked partial; else found if one is marked found;
  else missed if a line of the reader's list of misses is paired with the mention. If none
  of these, the reader did not see the mention, which is a disagreement.
- Pairing a miss line with a mention. A line can be paired with a mention of its own
  paragraph that no highlight marked found or partial covers, if the line's text holds the
  name or lies inside it. Each line serves one mention and each mention takes one line.
  They are paired in reading order, lines whose text is exactly the name first. A line
  left without a mention is a reader-only item.
- For a name that is not counted, the reader agrees if every highlight on it is marked as
  not a person. A miss line is never paired with such a name; a line the reader wrote for
  one is left over, and is a reader-only item.
- A reader-only item is a highlight the reader marks found or partial that overlaps no
  counted mention, or a miss line left over. Each is a disagreement and each adds one to
  the denominator.
- Agreement is the agreeing items over all gold items of the four documents plus the
  reader-only items. The script that computes it is committed, with tests, before any
  reader's file is compared.

**What else this cannot show**, added to the list above:

- A given name alone is a quarter of the mentions here (290 of 1,145). A formal document
  uses it far less, mostly where two people share a surname.
- The 169 `given_ordinary` mentions come from 22 names; the most frequent stands 19 times.
- Prefix letters: ל 140 times, ו 30, ול 20, ש 20, מ 10, וכש 5, ב 5. None with ה, and כ
  only inside `וכש`.
- An initial stands after a title in 60 of the 65 initial forms.
- 45 mentions hold a surname of two words.
- A person who shares a surname with another person of the document is never named by the
  surname alone, with or without a title. The templates were changed so, because such a
  sentence does not say who is meant.
- Where the line between `ordinary` and `also_word` runs is a judgement. A reader who
  draws it elsewhere moves a few mentions between `given_ordinary`, `given_also_word` and
  `given_plain`.
