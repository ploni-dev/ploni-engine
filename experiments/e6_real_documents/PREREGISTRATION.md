# E6 pre-registration: does what E5 found hold on real documents

Committed before any of the twenty documents was read for names, before any answer key
existed, and before any detector was run on them. The commit order is the evidence for the
first two. For the third there is no evidence but the author's word and the dates of the
run files.

## Why this experiment exists

E5 compared ways of finding names on generated text
(`docs/findings/2026-11-17-e5-methods.md`). Its main result for the plan's model: the step
`carry` (a name found anywhere in a document is marked wherever else it stands) took
`dicta-il/dictabert-joint` from 1,482 to 1,587 of 1,595 planted names, for 8 more words
marked for nothing. The same author wrote the text and the steps, so that is an upper bound.

Achia decided four things on 2026-11-18 that this experiment carries out. Each question, the
options and his answer are in that note, under `## Decision`, word for word:

- The carry step goes into the plan "as a thing to build and measure. It is not adopted for
  good until it is measured on real documents."
- The real documents come from the Supreme Court's public site only: "New civil decisions
  with named private parties, not the ten used before."
- "Two piles": "Half of the new real documents I may look at and learn from. The other half
  is kept closed and scored only once, at the end, as the fair judge."
- The order: "First the real-document test with the carry step, because it tells us if the
  experiment's result is true."

**It decides nothing.** The output is a findings note with numbers and a recommendation. The
model of Phase 3 and the place of `carry` in the plan stay as they are until Achia decides.

## The documents

Twenty decisions of the Supreme Court in civil matters, as the site's "save as Word" link
gave them on 2026-11-18, in `C:\Users\Achia\ploni-e6-corpus\docs`, outside the repository.
None is one of E1's ten.

**How they were chosen.** Claude searched `supremedecisions.court.gov.il` with four phrases
(sale of a flat, defamation, tenancy, road accident), read the result lists, and took 24
whose caption names at least one private person and that are 4 to 13 pages long. Achia said
yes to that list before anything was fetched. Three came in the old `.doc` format, which the
reader cannot open, and were deleted on his yes. One was deleted because it is about a claim
of sexual harassment. Twenty are left: 6 on the sale of a flat, 6 defamation, 6 tenancy,
2 road accidents. This was a choice by reading captions and page counts, not a rule that
another person could repeat. It could not follow a detector's output, because none had been
run.

**The subject check.** E1's exclusions are kept: nothing from a family or juvenile court,
no party or victim who is a minor, no claim about a sexual offence, no party captioned
`פלוני` or `אלמוני`. On 2026-11-18 every hit of E1's list of words, and of the two
placeholders, was read in its sentence: 31 hits. None of the twenty fails. Two touch the
subjects in passing (`r03`: two minor children of a party are mentioned as background;
`r19`: the decision relies on a family-court ruling in the tenants' divorce). Achia was
asked about those two and chose "Keep both (Recommended)". A labeller who finds that a
document does fail says so; the document is then deleted, with its labels, before any
detector is run, and Achia is told. It is not replaced: there is no spare. No document is
dropped after the first detector run, for any reason.

**What had been seen of them when this was written.** The captions in the result lists of
the search. Counts of the exclusion words. The 31 sentences of the subject check; a few
hold names. The sizes below, from a script that prints counts only. No file was opened to
look for names.

**Sizes**, as E1's reader (`experiments/e1_hebrew_recall/corpus.py`) reads them: 993
paragraphs, 244,069 characters, 43,209 words between spaces. The reader returns all of the
body text of each of the twenty (`unread_chars` is 0). E1's ten held 224,355 characters and
470 counted mentions, so about 500 counted mentions are expected here, about 250 per pile.

## The two piles

Drawn by a rule that looks at nothing in the files. Within each topic the ids are put in
the order of the SHA-256 of `e6-2026-11-18:<id>`, as a hexadecimal string; the first half
is the open pile, the second half the closed one. The result, with the SHA-256 of each
file:

| id | topic | pile | SHA-256 of the file |
|---|---|---|---|
| `r01` | sale | closed | `deaf7f557772809af9822a6c99a038b1ae2c4734f91ce8ffff56d6c4de4a2dbb` |
| `r02` | sale | open | `ddee0f33b3f5c3f6d3dd48ec408bdfeab011a83a5c74d0d21565792ae989cbb1` |
| `r03` | sale | open | `54816a17717a7ed9729b64f0dd0a1b67ea493aae4213cd270217351ef776631a` |
| `r04` | sale | closed | `e2a01694e133444aa0ece79b56f881341d6075dc6894b5074d605362af22f90e` |
| `r05` | sale | open | `bb698634ca515ba51365ee66f67ecb28f8d157bb179ed5f6b4b91bb0e0881340` |
| `r06` | sale | closed | `ae132d11ac0a1ceef88402c93a6a46661962e464f07da2bb217f0dbcab8bdd02` |
| `r08` | defamation | open | `d6194391d7f47b1e5f5b87d396792dc946b2df576c0674017111b5e370d2a986` |
| `r10` | defamation | closed | `dd027d9b4615d6922365579d0e3829cb237705f216789c2206bc4f3d32241aa4` |
| `r11` | defamation | open | `33e5f914bcc3557a6e872a9badce13a42ad07d5177eb47b7aa7c024a1a197511` |
| `r12` | defamation | closed | `283278209ebf4cb5ca0ff63add36f79c421cdc94da55201d7f38d1348da10d19` |
| `r13` | defamation | open | `9aed3fd2497d46057f9bfe74292f51d2b29b82c13f6023648c1fd59ecdb5ab5c` |
| `r14` | defamation | closed | `db3b394ffc1eabf2ba3730048e965a08d4eceb3c2b32eba2a8d9178ccc601cb0` |
| `r15` | tenancy | open | `50d5bb6f0b1b8d24528c2a41cbba15de322817855c2eb6781a4e77e92c8bcf89` |
| `r16` | tenancy | closed | `9102dfe61a806fc15b51ebbc960ed45b0d3e9b1b9cb90edcbd6c6e1bddd419a4` |
| `r17` | tenancy | open | `8d9e6ea6e6311bde9694b2b63143eb352b1d3a81544fc10ed35c9361f9098056` |
| `r18` | tenancy | closed | `22438eabad6906d09c007074230ebe8d1a1f52704d4a3203e7fc619c734a3401` |
| `r19` | tenancy | open | `4c46bfa9517007424da33bff36b6545804d36c0b670726b0e8a27dc092248795` |
| `r20` | tenancy | closed | `7f70750c9078e85fc60911eb0d780fef7c19a1ad31fd738e203a97143c6d3405` |
| `r21` | accident | closed | `225c379235ee5ae426e94f82b95a437b05a63f230ec520fd5c0cba0c28a3d730` |
| `r23` | accident | open | `28b71ff258eb36dc745fc3edfac4ce368fce86599ee81c0508e82c350418001c` |

The open pile holds 20,964 words between spaces, the closed pile 22,245. The table is a
constant of the harness, and a test holds it to the rule. The harness refuses a file whose
hash is not the one above. A document that is deleted later leaves its pile; the draw is
not made again.

- **The open pile** may be scored as often as wanted, and its errors may be read.
- **The closed pile** is scored once, at the end, for the methods named under "What is
  judged on the closed pile". No detector is run on it before that list is committed. The
  session that runs the experiment opens no document, worksheet, label or key of the closed
  pile before that one scoring; it sees counts only. No method, list or rule is changed
  after a closed number is seen. If one must be, the note says so and the number is
  reported as seen.

## The answer key

No script knows where the names of a real document are. The key is made by readers, before
any detector is run on any of the twenty, and none of its makers sees a detector's output.

**Who.** Three passes by Claude, each by sessions that share nothing but the files named
here. Two labellers, A and B, each mark every document alone. A third pass settles where
they differ. **No person checks the key.** Achia said of E1's hand check on 2026-11-14 that
he does not want to read documents, and asked for a method that checks itself
(`docs/findings/2026-11-13-e1-hebrew-recall.md`, where his words are quoted). A key made
by readers is not that; the two labellers and the count of where they differ are the nearest
thing to it that real documents allow.

**From what.** A worksheet per document, written by the harness from the reader's
paragraphs: every paragraph with its number, every run of characters without white space
with its number. The worksheets do not say which pile a document is in.

**What a label is.** One line per name: the paragraph, the first and the last numbered run
it stands in, the name exactly as written there, a key for the person, and a kind. The
harness finds the place of the name inside those runs; a line whose name does not stand
there exactly once is refused. A name is marked without its title, without attached
letters and without punctuation around it.

**What counts** is E1's rule (`experiments/e1_hebrew_recall/PREREGISTRATION.md`, "What
counts as a person name" and "Names in citations"), with the cases E1's readers' guide
settled (`docs/findings/2026-11-13-e1-hebrew-recall.md`, "E1 annotation guide"):

- Counted: a given name, a surname or a full name of a natural person, every time it
  stands. A full name written together is one mention. An initial with a surname is one
  mention, the initial being part of it. Two people joined by "and" are two mentions.
  Judges, lawyers, parties, witnesses and experts all count, in the caption and in the
  text. A dead person named in the name of an estate counts. A surname that stands for
  people (`האחים` or `משפחת` and the surname) counts. A judge named as the author of a
  cited opinion counts. An author named in the decision's own sentence counts.
- Not counted, and marked as such so that a detector that marks them is not blamed for it:
  a person's name inside the name of an organisation, a firm, a street, a place, a statute
  or a doctrine; the names in the title of a cited decision (`כהן נ' לוי`, `עניין כהן`);
  an author inside a reference to a book or an article; the placeholders `פלוני` and
  `אלמוני` and bare initials.
- Not a name at all, and not marked: roles and descriptions (`המבקש`, `המנוח`), titles
  alone, companies, courts, pronouns.

**The kind** of a counted name is `public` or `private`, by E1's line: public is a judge
or a registrar, an elected or appointed official named in that role, and a lawyer or
expert that a reader of the news would know by name. Everyone else is private, and so is
every unsure case.

**How the two are put together.** The harness lists, per document, every label that only
one labeller has or that the two have with another kind, and two lists of places to look
at, as in E1: every other place where a word of a labelled name stands in the document,
also behind attached letters; and every word that stands right after a title. Those two
lists are made by the functions of E5's `carry` and `titles` steps, run on the labels and
on no detector's output. The third pass decides each difference and each such place by the
rules above and writes the key. It adds nothing of its own beyond those places.

**Frozen.** The SHA-256 of every key file is committed to the repository before any
detector is run on any of the twenty. The harness refuses a key file with another hash.

**What the key cannot be trusted for.** A name that both labellers miss, that stands after
no title and whose words stand nowhere else in a label, is not in the key. A detector that
marks it is charged with a word marked for nothing, and a detector that misses it is not
charged. So recall is flattered for every method alike, and the key is most complete
exactly where `carry` and `titles` reach. To bound this: after a pile is scored, every
word that the methods judged on the closed pile marked outside the key is read in that
pile. A person's name among them that the key lacks is counted, and the pile's numbers
are given a second time with those names added. The numbers by the frozen key stay the
ones the predictions are held to.

## What is run

**Detectors**, the four that are on the laptop since E5, each at the commit and with the
weights hash of `docs/THIRD_PARTY.md`, in this order as time allows; one that was not run
is reported as not run: `joint` (`dicta-il/dictabert-joint`, the plan's model), `golem`
(`CordwainerSmith/GolemPII-v2-small`), `seter_fast` (`shoresh-labs/seter-pii-he-ar-fast`),
`large` (`dicta-il/dictabert-large-ner`). Nothing is downloaded. The three models Achia
allowed on 2026-11-18 come after this experiment, in the order he chose.

**Methods**, on the open pile: every method of E5's grid for those detectors, built and
scored by E5's own code (`experiments/e5_methods/evaluate.py` and `layers.py`), unchanged:
each detector as it is, with whole words, with each stack of steps, at each threshold, and
the unions. The `list` step is left out: E5 found that it marks 751 to 1,547 words for
nothing and finds fewer names than `carry`.

**The model's input** is as in E1 and E5: one paragraph at a time, cut at sentence ends
where it is longer than the model takes, read by E1's reader.

## How it is scored

- **Recall** by E4's strict rule, as in E5: a counted name is found when what is marked
  covers every character of it that is not white space.
- **Rows**, beside the pooled number: `private`; `public`; `one_word` (the name is one
  word); `prefixed` (letters are attached before it); `alone` (nothing else on its line but
  digits and punctuation); `lonely` (the person is named once in the document); and
  `no_trigger` (the `titles` step, run on the document with nothing marked, does not touch
  the name). A row is read only when it holds 30 mentions or more.
- **Words marked for nothing**: Hebrew words that a method marks and that lie in no name of
  the key, counted or not, as in E5; titles and initials are counted apart.
- **Time and memory**: seconds inside the detector and the most memory the process held,
  measured and recorded, not a gate.

## Predictions and thresholds

Written before any labelling and any run. On the open pile unless it says otherwise. "Per
1,000" is per 1,000 Hebrew words of the pile's text.

| # | Prediction | It is wrong when |
|---|---|---|
| 1 | `joint + whole words` finds 92.5 to 98 percent (E1: 95.53 percent on ten decisions of the same court) | outside that range |
| 2 | `joint + carry` finds 1 to 3.5 points more than `joint + whole words` | less than 1, or more than 3.5 |
| 3 | `joint + carry` finds 97 to 99.6 percent | outside that range |
| 4 | `joint + carry` marks fewer than 5 more words per 1,000 for nothing than `joint + whole words` (titles left out) | 5 or more |
| 5 | `joint + titles, carry` marks more than 5 more per 1,000 than `joint + whole words`: in a real decision a title is often followed by a word that is no name (`השופט קבע`), the step marks it, and `carry` spreads it | 5 or fewer |
| 6 | `golem + whole words` finds fewer names than `joint + whole words`: the order of E5 turns around on real text | as many or more |
| 7 | For `joint + whole words`, `public` is 0 to 8 points over `private` (E1: 99.43 against 93.20) | outside that range; not read unless each row holds 30 or more |
| 8 | For `joint + carry`, `lonely` is the lowest in percent of the rows that hold 30 or more | another row is lower |
| 9 | On the closed pile `joint + carry` is within 2.5 points of its open number, either way | further away |
| 10 | The two labellers mark the same counted name, at the same place, for at least 90 percent of the counted names that either marks | under 90 percent: the key is weak, and the note says so in its first lines |
| 11 | `joint` takes 20 to 60 seconds per 1,000 (E5: 602 seconds for 16,871) | outside that range |

A prediction that fails is reported as failed, with the number.

## What "holds on real documents" means

Decided on the closed pile, for the plan's model, by the frozen key. `errors` are the
counted names that `joint + whole words` does not find.

- **Holds:** `joint + carry` finds at least one third of those errors, and marks fewer than
  5 more words per 1,000 for nothing than `joint + whole words`.
- **Does not hold:** it finds fewer than one in six of them, or marks 10 or more per 1,000.
- **In between** otherwise, reported as that.
- **Too few to say** when there are fewer than 15 such errors on the closed pile. The note
  then gives the open and the closed pile together, named as a number that is not blind.

No fraction is rounded before it is compared.

## What may be fitted on the open pile

After the open pile is scored its errors are read, and steps may be changed: the list of
titles, what `carry` takes as a name, a threshold. A changed step is a new function with a
new name in this folder, with its tests; E5's functions stay as they are. Its open number
measures how well it was fitted and nothing else. It is judged by the closed pile. At most
three fitted methods go there.

## What is judged on the closed pile

Once, after the file `results/CHOSEN.md` is committed, which names them:

1. `joint + whole words`
2. `joint + carry`
3. `joint + titles, carry`
4. `golem + whole words`
5. `golem + carry`
6. `golem at 0.03 + titles, carry`, E5's winner of all
7. the open pile's method with the highest recall, by E5's order (then fewer words marked
   for nothing without titles, then fewer seconds, then the name), if it is not above
8. the open pile's method with the highest recall among those that mark fewer than 5 more
   words per 1,000 for nothing than their detector with whole words, if it is not above
9. up to three fitted methods

## What stays out of the repository, the PR and the chat

Every name and every sentence of the twenty. The documents, worksheets, labels, key, run
files and lists of errors are in two folders outside the repository
(`C:\Users\Achia\ploni-e6-corpus`, `C:\Users\Achia\ploni-e6-out`). The harness prints
counts and ids only, and refuses to write a list of errors inside the repository. A record
line holds numbers and labels. The repository gets the harness, the hashes of the key, the
printed tables and the note. The labellers answer with counts only.

## Known limits, stated before the run

- Twenty decisions of one court, chosen by reading captions, are a sample of nothing. The
  numbers describe these twenty. `build-plan.md` Phase 5 says of published decisions: "Use
  them for realism, never as ground truth." Nothing here becomes a gate.
- The language is that of appeals, less like a law firm's everyday documents; Achia was
  told so with the option he chose.
- The key is made by one model in three passes, and no person checks it. The two labellers
  can share a blind spot. "What the key cannot be trusted for" says where that bends the
  numbers.
- Ten documents and about 250 names per pile: one document with one hard name moves a
  pooled number by several points. E1 had such a document (13 of its 21 errors).
- Mentions inside one document are not independent.
- The steps were written on generated text. What may be fitted is fitted on ten documents.
- One run per detector, on the laptop of `docs/REFERENCE_MACHINE.md`, with whatever else
  was running.

## What is not in it

- The three models Achia allowed on 2026-11-18, Stanza, a language model: later parts of
  the series.
- The prefix forms of E3 and the real name behind a surname that begins with ה.
- Anything of the product: no file under `ploni/` is touched. In which phase `carry` is
  built was not asked and is not settled here.
- Whether the closed pile becomes the real part of the plan's held-out batch
  (`build-plan.md` section 7): not asked, not settled here.
