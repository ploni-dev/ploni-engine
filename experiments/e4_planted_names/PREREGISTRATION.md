# E4 pre-registration: PERSON recall against a ground truth that is known by construction

Committed before any template was written and before the model was run on generated text.
The commit order is the evidence.

**Amended on 2026-11-14, before any run: see the last section. It changes the classes of
names, the rows of the report and which prediction each carries, and it fixes the second
part. What stands above it is kept as first written.**

**Amended again on 2026-11-14, after the first two parts were run and reported: a third
part, which measures the readers' cross-check list against the gold. See the section at
the end. Nothing above it is changed.**

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
- Pairing a miss line with a mention. The reader's list of misses has lines of two kinds.
  A line of kind `partial` belongs to the mention that its highlight overlaps, and is not
  paired; it is a reader-only item only if its highlight overlaps no counted mention. A
  line of kind `missed` can be paired with a mention of its own paragraph that no
  highlight marked found or partial overlaps, if the line's text holds the name or lies
  inside it. Each line serves one mention and each mention takes one line. Lines are
  taken in the order of the file, mentions in reading order, and lines whose text is
  exactly the name are paired first. A `missed` line left without a mention is a
  reader-only item.
- For a name that is not counted, the reader agrees if every highlight on it is marked as
  not a person. A miss line is never paired with such a name; a line the reader wrote for
  one is left over, and is a reader-only item.
- A reader-only item is a highlight the reader marks found or partial that overlaps no
  counted mention, or a miss line left over as said above, or a person the reader counts
  through the `extra` column: a highlight marked found stands for one mention plus its
  `extra`, and each of these beyond the counted mentions the highlight overlaps is one
  item. Each reader-only item is a disagreement and each adds one to the denominator.
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

## Amended on 2026-11-14, after the first two parts were reported: the third part

**Why.** The second part was meant to test whether a reader finds a name that the model
left without a highlight. The review of the findings note
(`docs/findings/2026-11-14-e4-planted-names.md`) found that it did not: the four documents
held three such names, and all three were rows of the cross-check list the reader was
given. A reader's unaided search was tested on no case. In E1, 17 of the 18 misses the
readers reported were on that list too, so E1's count leans on it.

The third part asks what can be asked with no reader: **of the names the model misses,
how many does the list point to?** What the list does not hold is what a reader has to
find alone.

**What is known when this is written.** The run of `c05133a`, its 61 errors and their
text. The lists of the four documents of the second part: four rows, three of them on
the three missed mentions. The list of the other 36 documents has not been made, and no
span list of theirs exists.

**The prediction below is not blind.** With the gold and the 61 printed errors, the
place of every one of the 57 missed mentions is known, and so is that the other 1,084
counted mentions carry a `PER` highlight. The name words of the list come from those
highlights, so most of the result could be worked out by hand with no model run.
Claude did not count it. Before predicting, Claude did reason through several of the
errors (a surname after `משפחת`, the given names `שיר` and `מעיין`, `מח'טיב`, a full
name alone on a line) and expects 55 to 57 of the 57 to be on the list. 51 of the 57
are group surnames or everyday-word given names of people the templates name several
times. What the run adds is the count itself and the places that are off the list.

**What is measured.**

- `run.py --worksheets-dir W --all-documents --list-errors` runs the model again and
  writes the span list of every document. `W` is a new, empty folder, so that the files
  of the second part are not written over. That run prints its own pooled number. If it is not part one's
  1084 of 1145, that is said first in the report, and the third part is counted on the
  spans of the new run.
- `list_check.py --folder W` makes the cross-check list of every document, by the rule
  of the throwaway script that made the lists of E1 and of the second part. The rule is
  now in the repository, with tests:
  - A *name word* is a word of any `PER` highlight of the document, cut at white space
    and hyphens, with punctuation taken off its edges, of two letters or more; and also
    that word with one, two or three leading prefix letters (`והבלמכש`) taken off, if
    three letters or more are left.
  - The list holds every place where a name word stands with at most three prefix
    letters before it, no Hebrew letter on either side, and no `PER` highlight on any of
    its characters.
  - It also holds the word after a title: the whole run of characters up to the next
    white space, so a comma at its end is inside the row (`מר`, `גב'`, `גברת`, `עו"ד`, `ד"ר`, `פרופ'`,
    `השופט`, `השופטת`, `הנשיא`, `הנשיאה`, `הרשם`, `הרשמת`, `כב'`, with at most two
    prefix letters before the title, and no Hebrew letter before those), if that word,
    with punctuation taken off its edges, is not itself a title with or without prefix
    letters, and no `PER` highlight is on it. Where a title follows a title (`כב' השופט`), the search goes on
    after the second one, so the word after it is not listed by this rule. The
    throwaway behaves so, and it is kept.
- **An item** is a counted mention that the scorer calls missed, from the span lists: 57
  in part one. A partial mention is not an item: a highlight sits on it, in front of
  the reader.
- **A missed mention under another label is an item.** 12 of the 57 are such. The
  worksheet shows a highlight of another label in grey, so a reader is pointed to those
  places with or without the list. The number and the threshold are read on all items,
  those 12 included. The findings note also gives, from the error list of the same run,
  how many items have no highlight of any label, and how many of those are on the list.
  An item with no highlight of any label that is off the list is what a reader has to
  find alone, and each such item is printed.
- An item is **on the list** if a row of the list shares at least one character with the
  planted name.
- **The number**: items on the list over all items, pooled over the 40 documents, as an
  exact fraction.
- Also reported: the same by kind of mention (a surname after `משפחת`, a surname after
  `האחים`, a given name alone that is an everyday word, the rest); how many rows the
  lists have and how many of them lie on an item, which is what a reader has to look
  through; and every item that is off the list, with its text. One place can give two
  rows (a name word, and the same word with a comma as the word after a title), so the
  rows on items can outnumber the items.
- The port is checked once against the throwaway: the rows `list_check.py` makes for
  `doc01`, `doc11`, `doc21` and `doc31` are compared with the four files the readers
  had. Those files are outside the repository, so this is reported in the findings note
  and is not a test. The throwaway itself is not in the repository either: its one long
  function is over the size limit of `CLAUDE.md`, and split up it would no longer be the
  script that made the lists. A copy is kept beside the output of the run, SHA-256
  `bd02b49f2668a5f733f82c6982404e39c4e0aa26504137826a2bfdc9f83d9d51`. The reviewer of
  the port compared the two on made-up highlights; the count of that comparison is in
  the pull request.

**Prediction and threshold, Claude's, stated before the list of the 36 is made.**

| What | Prediction | Threshold |
|---|---|---|
| Missed mentions that are on the list, pooled | 90 percent or more | below 80 percent: the E1 findings note is amended to say that a fifth or more of the misses of the kinds seen here are not on the readers' list |

From 80 to under 90 percent the result is outside the prediction and does not cross the
threshold: the findings note says so in its first line, and the E1 note is not amended.

The reason for the prediction: most names missed in part one belong to a person whose
name is highlighted somewhere else in the same document, and E1's figure was 17 of 18.

**What the number is used for.** One estimate, given as arithmetic and named as resting
on an assumption: if a share `c` of misses is on the list, and a reader found none of
the others, then E1's 17 misses from the list stand for about `17 / c` misses in all.
The assumption is that the share carries over from this text to a judgment. Nothing
shows that it does.

**What the third part cannot show.**

- The 57 items are not independent draws: five fillings of a template share every
  sentence, so a place that is off the list is likely off it five times.
- The templates name every person several times, so a missed name usually has a
  highlighted twin in the same document. A person named once in a real document, and
  missed, is on no list. The share measured here is therefore more likely too high than
  too low for real text.
- Whether a reader takes every miss from the list. The second part saw three of three.
- Whether a reader finds a miss that is off the list. That needs a reader, on the
  documents where the third part finds such a miss. It is not part of this amendment.
