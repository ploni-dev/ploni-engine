# E6 pre-registration: does what E5 found hold on real documents

Committed before any of the twenty documents was read for names, before any answer key
existed, and before any detector was run on them. The commit order is the evidence for the
first two. For the third there is no evidence but the author's word and the dates of the
run files.

**Changed on 2026-11-18, after each of the three passes of the review of PR #99 and before
any labelling, the last time after a fifth pass: see the last five sections, which list
every change. No document had been
read for names, no label and no key existed, and no detector had been run when it was
changed.**

**Amended on 2026-11-18, after the two labellers were put side by side and before the third
pass, the freeze and any run: see the last two sections. They add a third labeller, by
another model, name the model of the third pass, and say what had been seen when each was
written. One sentence of "The subject check" above is corrected there.**

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
  judged on the closed pile". No detector is run on it before that list is committed, and
  the harness scores it for no method that the committed list does not name. The
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
(`docs/findings/2026-11-13-e1-hebrew-recall.md`, where his words are quoted). That those
words carry over to E6's key is Claude's reading: he was not asked about E6's key. Two
nearer sources: on 2026-11-13 he decided that Claude counts E1's names
(`experiments/e1_hebrew_recall/PREREGISTRATION.md`, "Who counts"), and `build-plan.md`
section 7 says of real public documents that "their right answers are Claude's labels". A key made
by readers is not that; the two labellers and the count of where they differ are the nearest
thing to it that real documents allow.

**From what.** A worksheet per document, written by the harness from the reader's
paragraphs: every paragraph with its number, every run of characters without white space
with its number. The worksheets do not say which pile a document is in. The readers work
from `LABELLING.md` in this folder, which restates the rules below and is committed with
the harness.

**What a label is.** One line per name: the paragraph, the first and the last numbered run
it stands in, the name exactly as written there, a key for the person, and a kind. The
harness finds the place of the name inside those runs; a line whose name does not stand
there exactly once is refused. A name is marked without its title, without attached
letters and without punctuation around it. The worksheet shows every gap as one space; where
the text holds two spaces, a tab or a line break between two words of a name, the label
is written with one space and the name is taken as it stands in the text.

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

**How the two are put together.** The harness lists, per document: every label that only
one labeller has or that the two have with another kind; every place where the two divide
the names among people in another way; and two lists of places to look at, after E1's:
every other place where a word of a labelled name stands in the document, bare or behind
attached letters; and every word that stands right after a title. The first list is made
from the words of the labels' own text, looked for by E5's `layers.from_list`. The second
is made by E5's `layers.after_triggers`, with three titles added that E1's list held and
E5's lacks (`הנשיא`, `הנשיאה`, `כב'`). Both are made from the labels and from no
detector's output. The third pass decides each difference and each such place by the rules
above and writes the key. It adds nothing of its own beyond those places, and the harness
holds it to that before the freeze. These stop the freeze: a label of the key that
touches no label of either labeller and no listed place; a label both labellers have that
the key lacks, cuts, has with another kind, or makes longer by a word that is in neither
labeller's file and at no listed place; one label of the key over two labels that both
have. A label of the key at a listed place, or at a label only one labeller has, takes
the whole name as the rules above ask ("a full name written together is one mention"),
also where the list or that label holds only a part of it. Where a listed word turns out to be part of a name that both
labellers marked too short (an initial before a surname, a second surname), the third
pass makes that label longer; it does not add the word as a name of its own. Where the
name ends is the guide's rule alone: the harness cannot tell such a word, added as a
label of its own, from a real second name; nor a listed word, or a label only one
labeller has, that was wrongly joined to the name before it.

**Whose person keys.** The key takes labeller A's key for each person. A label that only
B has, or that comes from a listed place, gets A's key for that person, or a new key when
A has none. Where the two divide the names among people in another way, the third pass
decides by the text. The harness does not check the person keys of the key.

**Frozen.** The SHA-256 of every key file is committed to the repository before any
detector is run on any of the twenty. The harness refuses a key file with another hash.
The freeze is made once: the harness does not write the table when it is already there.

**What the key cannot be trusted for.** A name that both labellers miss, that stands after
no listed title and whose words stand nowhere in a label, is not in the key. A detector
that marks it is charged with a word marked for nothing, and a detector that misses it is
not charged. So recall is flattered for every method. It is not flattered alike. A name
both labellers miss gets into the key only where the two lists reach, and those are the
places `carry` and `titles` reach. So the share of `joint`'s errors that `carry` finds,
which the verdict below rests on, is an upper bound.

To bound this on the open pile: after it is scored, every word that the methods of "What
is judged on the closed pile" marked outside the key is read. A person's name among them
that the key lacks is counted, and the open pile's numbers are given a second time with
those names added, beside the numbers by the frozen key. The note says in its first lines
when a prediction comes out differently by the two. On the closed pile there is no second
scoring: Achia's words are "scored only once". After its one scoring the same words are
read there, and the names the key lacks are counted, apart for those `joint + carry`
marked and those it did not; the two counts are given beside the verdict. Neither reading
can see a name that no judged method marked. The numbers by the frozen key are the ones
the predictions and the verdict are held to.

## What is run

**Detectors**, the four that are on the laptop since E5, each at the commit and with the
weights hash of `docs/THIRD_PARTY.md`, in this order as time allows; one that was not run
is reported as not run: `joint` (`dicta-il/dictabert-joint`, the plan's model), `golem`
(`CordwainerSmith/GolemPII-v2-small`), `seter_fast` (`shoresh-labs/seter-pii-he-ar-fast`),
`large` (`dicta-il/dictabert-large-ner`). Nothing is downloaded. The three models Achia
allowed on 2026-11-18 come after this experiment, in the order he chose. His yes of
2026-11-17 to the three models fetched for E5 was "for this experiment only"
(`docs/THIRD_PARTY.md`, "On whose word they were fetched"). That they may also be run in
E6, the next experiment of the same series, is Claude's reading; it adds no download and
no use in the product.

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
  the name). A row is read only when it holds 30 mentions or more. A surname that stands
  for several people (`האחים` and the surname) is a person of its own in the key, so one
  that stands once is in `lonely`; E5's `lonely` left group names out, so the row is not
  the same as E5's in this.
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
| 5 | `joint + titles, carry` marks more than 5 more per 1,000 than `joint + whole words` (titles left out): in a real decision a title is often followed by a word that is no name (`השופט קבע`), the step marks it, and `carry` spreads it | 5 or fewer |
| 6 | `golem + whole words` finds fewer names than `joint + whole words`: the order of E5 turns around on real text | as many or more |
| 7 | For `joint + whole words`, `public` is 0 to 8 points over `private` (E1: 99.43 against 93.20) | outside that range; not read unless each row holds 30 or more |
| 8 | For `joint + carry`, `lonely` is the lowest in percent of the rows that hold 30 or more | another row is lower |
| 9 | On the closed pile `joint + carry` is within 2.5 points of its open number, either way | further away |
| 10 | Over all twenty documents, the two labellers mark the same counted name, at the same place, for at least 90 percent of the counted names that either marks | under 90 percent: the key is weak, and the note says so in its first lines |
| 11 | `joint` takes 20 to 60 seconds per 1,000 (E5: 602 seconds for 16,871) | outside that range |

A prediction that fails is reported as failed, with the number.

## What "holds on real documents" means

Decided on the closed pile, for the plan's model, by the frozen key. `errors` are the
counted names that `joint + whole words` does not find. "More words" is the number of
words `joint + carry` marks for nothing, titles left out, minus that of
`joint + whole words`, per 1,000 Hebrew words of the text.

- **Too few to say** comes first: when there are fewer than 15 such errors on the closed
  pile, none of the three answers below is given for it.
- **Holds:** `joint + carry` finds at least one third of those errors, and marks fewer than
  5 more words per 1,000.
- **Does not hold:** it finds fewer than one in six of them, or marks 10 or more words
  more per 1,000.
- **In between** otherwise, reported as that.

**"Too few to say" is the likely answer for the closed pile alone.** At E1's 95.53 percent,
about 250 names give about 11 errors, under 15. The same rules are then applied to the
open and the closed pile together, in the same order, with the same limits, and the answer
is named as one that is not blind: `joint + carry` is E5's function, unchanged, but the
open pile's errors were read before the closed pile was scored. If the two piles together
hold fewer than 15 such errors, the answer is "too few to say" and no other. Achia chose
two piles to have a fair judge; he is told before the labelling starts that the closed
pile alone will most likely be too small to give this answer.

No fraction is rounded before it is compared.

## What may be fitted on the open pile

After the open pile is scored its errors are read, and steps may be changed: the list of
titles, what `carry` takes as a name, a threshold. A changed step is a new function with a
new name in this folder, with its tests; E5's functions stay as they are. Its open number
measures how well it was fitted and nothing else. It is judged by the closed pile. At most
three fitted methods go there.

## What is judged on the closed pile

Once, after the file `results/CHOSEN.md` is committed, which names them. That file puts
between backticks the methods that are judged and nothing else: the harness scores the
closed pile for a name it finds there between backticks.

1. `joint + whole words`
2. `joint + carry`
3. `joint + titles, carry`
4. `golem + whole words`
5. `golem + carry`
6. `golem at 0.03 + titles, carry`, E5's winner of all
7. the open pile's method with the highest recall, by E5's order (then fewer words marked
   for nothing without titles, then fewer seconds, then the name), if it is not above
8. the open pile's method with the highest recall among those that mark fewer than 5 more
   words per 1,000 for nothing, titles left out, than their base row, if it is not above.
   The base row of a method of one detector, at any threshold, is `<detector> + whole
   words`; of a union of detectors, that union with whole words and no step
9. up to three fitted methods

## What stays out of the repository, the PR and the chat

Every name and every sentence of the twenty. The documents, worksheets, labels, key, run
files and lists of errors are in two folders outside the repository
(`C:\Users\Achia\ploni-e6-corpus`, `C:\Users\Achia\ploni-e6-out`). The harness prints
counts, ids and line numbers only, and refuses to write a list of errors inside the repository. A record
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
- The harness holds the order by files: no run without a frozen key, no closed pile
  without `results/CHOSEN.md`, and then only for the methods it names. It cannot see that
  those files were committed before the runs, that the closed pile is scored once, that
  the session that runs the experiment opened nothing of the closed pile, or that no
  labeller saw a detector's output. Those rest on the author's word.
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

## Changed on 2026-11-18, after the first review, before any labelling

An independent review of the pre-registration and the harness (PR #99, first pass, 16
findings, all taken) came back before any document was read for names. This file was
changed in place; the first version is commit `de5db48`. What changed:

1. **"Holds on real documents".** The first version said "marks 10 or more per 1,000" for
   "does not hold", which could be true together with "holds". Both limits are now on the
   words `joint + carry` marks more than `joint + whole words`, titles left out. "Too few to
   say" comes first; it is said to be the likely answer for the closed pile alone, and the
   rule for the two piles together is written down.
2. **The closed pile is scored once.** The first version gave the closed pile's numbers a
   second time with a changed key. That is a second scoring, which is more than Achia's
   words. On the closed pile the names the key lacks are now only counted.
3. **The lists the third pass looks at.** The first is made from the words of the labels'
   own text, so that a name labelled only behind attached letters gives its bare form; the
   first version used E5's `carry` function, which takes the whole word. The second has
   three titles more, from E1's list. The text now says that the share of errors `carry`
   finds is an upper bound, and why.
4. **The third pass is checked.** The freeze refuses a key that adds a label of its own or
   drops or changes a label both labellers have, and is made once.
5. **Person keys.** The key takes labeller A's; places where the two divide the names among
   people in another way are listed for the third pass.
6. **White space inside a name.** A label is written with one space where the text holds
   two, a tab or a line break.
7. **Three rules name their number:** prediction 5 and item 8 of the closed list (titles
   left out; the base row of a union and of a threshold), prediction 10 (all twenty).
8. **The closed pile is scored only for methods `CHOSEN.md` names**, held by the harness.
9. **Two readings are marked as readings:** that Achia's words about E1's check carry over
   to E6's key, and that the models fetched for E5 may be run in E6. What rests on the
   author's word is listed under the known limits.
10. `LABELLING.md`, the readers' guide, is named and committed with the harness.

## Changed on 2026-11-18, after the second review, before any labelling

The second pass of the review (6 findings, all taken) found that the first round of
changes left four things to say. Nothing had been read for names, labelled or run.

1. **The third pass may make a label longer.** The check before the freeze, as first
   changed, refused a key in which a label both labellers have was made longer by a listed
   word (`י'` before a surname, a second surname), and passed the key that added the word
   as a name of its own, which is two names where the rules say one. An agreed label now
   counts as kept when a label of the key of the same kind covers all of it.
2. **A group surname in `lonely`.** Said under the rows.
3. **What `CHOSEN.md` holds between backticks.** Only the methods that are judged.
4. The harness also prints line numbers; the sentence that said "counts and ids only" is
   corrected.

## Changed on 2026-11-18, after the third review, before any labelling

The third pass of the review (2 findings, both taken) found that the check before the
freeze held less than the text said. Nothing had been read for names, labelled or run.

1. **What the check holds.** As changed after the second review it let a label both
   labellers have grow by any words, and let one label of the key stand over two that both
   have. It now refuses a key label that holds a word which is in neither labeller's file
   and at no listed place, and a key label over two labels that both have.
2. **What it cannot hold** is said where the rule stands: a listed word added as a name of
   its own instead of making the name before it longer.

## Changed on 2026-11-18, after the fourth review, before any labelling

The fourth pass of the review (3 findings, all taken) found that the stricter check of the
round before refused two right keys, and that the text named one of three things the check
cannot hold. Nothing had been read for names, labelled or run.

1. **An initial or a name particle after one of the three added titles.** The list held
   only the word right after such a title, so the key could not take `א' ברק` after
   `הנשיא` when both labellers had missed it. The word after an initial or a particle is
   listed too, as E5's function does for its own titles.
2. **A hyphen that stands by itself inside a name** no longer stops the freeze.
3. **What the check cannot hold** is said in full: where one name ends and the next begins.

## Changed on 2026-11-18, after the fifth review, before any labelling

The fifth pass of the review (1 finding, taken) found that the check of the third round
was applied wider than it should be. Nothing had been read for names, labelled or run.

1. **The whole name at a listed place.** The check asked of every label of the key that
   each of its words be in a labeller's file or at a listed place. A list often gives one
   word of a name (the given name after `עו"ד`), and the key then could not take the whole
   name that both labellers had missed. The word-by-word rule now holds only for a label of
   the key that covers a label both labellers have; any other label of the key must touch a
   labeller's label or a listed place, and takes the whole name.

## Amended on 2026-11-18, after the two labellers were compared, before the third pass

What stands above is kept as it was merged (#99). This section is committed before the
third pass, before the freeze and before any detector is run on any of the twenty.

### What had been done and seen

- The worksheets of the twenty were written. Labellers A and B, each four sessions with
  five documents, marked every document from `LABELLING.md`. No session raised a flag of
  the subject check, so no document is deleted.
- The session that runs the experiment saw the counts each labelling session reported
  (labels by kind, persons, doubts, per document) and what `label.py compare` printed. It
  opened no worksheet, label file, doubts file or compare file, of either pile.
- **The two agree on every counted name: 718 of 718, at the same place, over all twenty.**
  A holds 1,076 labels and B 1,069. They differ in 14 labels, in four documents, none of
  them a counted name that only one has. No place where they divide the names among
  people in another way. The two lists hold 166 places to look at.
- By A's and B's labels the open pile holds 241 counted names and the closed pile 477, of
  which one document holds 146.

### What that means

Prediction 10 holds, and it says nothing. Two sessions of one model, with one guide and
one worksheet, are one reader twice: they find the same names and miss the same names.
The second labeller was in the plan to catch what the first misses, and caught nothing.
So the key would rest on one reading and on the two lists, and a name that this model
does not see, standing where no list reaches, would be in no key. For the closed pile
nothing can mend that afterwards: it is scored once.

### What changes

1. **A third labeller, C, by another model.** Four sessions of Claude Opus, where A and B
   were sessions of the model that runs the experiment, mark every document alone from the
   same guide and the same worksheets, into `labels_c`. They see nothing of A, of B or of
   any detector, and are not told which pile a document is in.
2. **The key is made from A and C**, by the procedure above, unchanged: `compare` on A
   and C, the third pass on its differences and its two lists, the check before the freeze
   against A and C. The third pass also gets the 14 labels in which B differs from A and
   decides them by the same rules. One limit follows from the check as it is built: a
   label that only B has can go into the key only where it touches a label of A or of C
   or a listed place.
3. **Two numbers of agreement are reported.** A against B is prediction 10 as written:
   718 of 718. A against C is given beside it and is the one that says something about
   the key. No range was predicted for it. If A and C mark the same counted name at the
   same place for fewer than 90 percent of the counted names that either marks, the note
   says in its first lines that the key is weak, as prediction 10 says for A and B.
4. Nothing else changes: the rules for what counts, the third pass, the freeze, what is
   run, how it is scored, the predictions, what "holds" means, what is judged on the
   closed pile.

### What this cannot do

C is another model of the same family, trained in part on the same kind of text. It is
less like A than B is, and it is not a person. No person checks the key. That this
amendment was written after the agreement of A and B was seen, and not before, is the
reason it is here: the plan should have said that two sessions of one model are not two
readers.

## Added on 2026-11-18, after the review of the amendment, before the third pass

An independent review of the section above (5 findings, 29 to 33, all taken) found it sound
and found five things unsaid. This section says them. It is committed before the third
pass, the freeze and any detector run.

### What had been done and seen by now

- Labeller C finished: four sessions of Claude Opus 5.5 (`claude-opus-5-5`). A and B were
  sessions of Claude Fable 5.2 (`claude-fable-5-2`), the model that runs the experiment.
  No session of C raised a flag of the subject check.
- The session that runs the experiment saw the counts C's sessions reported and, from a
  script that prints numbers only and writes nothing, how far A and C agree: **the same
  counted name at the same place for 717 of 728, 98.49 percent**; 240 of 246 in the open
  pile and 477 of 482 in the closed one. They differ in 32 labels, 10 of them in the kind
  only; no person split. It also saw, in the sessions' reports, the kinds of case the guide
  does not settle (a judge's own initials beside an insertion, a typist's initials after
  the file name, a party who holds an office, a second surname in brackets), with
  paragraph numbers and no text. It opened no worksheet, label file, doubts file or
  compare file.
- That no labelling session read another's files rests on the sessions' word: all three
  label folders lie in the one corpus folder. What can be seen from outside fits it. A and
  B wrote their files in the same four minutes (11:00 to 11:04), C began at 11:08, after
  the commit of the section above (11:07); 16 of the 20 files of A and B are the same
  byte for byte, and 16 of C's 20 differ in size from A's.

### The model of the third pass (finding 31)

The third pass is made by sessions of Claude Sonnet 5.5 (`claude-sonnet-5-5`): neither
A's model nor C's, so that no difference between the two is judged by the twin of one of
them. This is chosen after the count of how far A and C agree was seen, and before any
of their differences was. It could not be chosen for a result: no detector has been run.

### The way of B's 14 labels, and what stands (finding 30)

Before `compare` runs on A and C, the folder `compare`, which holds A against B, is
renamed `compare_ab`. The third pass reads, per document: `compare/<id>.tsv` (A against
C, with the two lists), the lines of `compare_ab/<id>.tsv` whose `why` is `differ`, and
the doubts files of all three labellers. Where A and C have the same label, that label
stands, whatever B has: the check before the freeze holds the key to A and C. A label
that only B has can go into the key only where it touches a label of A or of C or a
listed place. `LABELLING.md` says the same to the third pass, and settles the four kinds
of case named above by the rules of this file, so that they are decided alike in every
document: bare initials are not counted, whoever they stand for; a second surname in
brackets is a label of its own; a party who holds an office is `public` only where the
decision gives the office beside the name; a word of which it is unsure that it is a
person's name, inside the name of a company or a place, is `not_counted`.

### What 477 names in the closed pile mean (finding 29)

"What 'holds on real documents' means" says that "too few to say" is the likely answer
for the closed pile alone, from about 250 names a pile. The closed pile holds about 477
by the labels, which at E1's 95.53 percent is about 21 errors, over the 15 the rule asks
for. So the closed pile alone will most likely give the answer. The rule is unchanged.
The open pile holds about 241: one name there is 0.4 points, and some rows may hold fewer
than 30. Achia was told before the labelling that the closed pile would likely be too
small; he is told this too.

### One document holds 146 of the closed pile's names (finding 32)

The verdict stays on all ten documents of the closed pile. Beside it the note gives, for
that document and for the other nine apart: the errors of `joint + whole words`, and how
many of them `joint + carry` finds. If the verdict would be another one without that
document, the note says so in its first lines. This is written before any run, so that
the split is not chosen after the result.

### "The subject check", corrected

The text above says that "every hit" of the list of words was read in its sentence: 31
hits. The script that wrote those sentences dropped a sentence whose only hit stood
inside one of eleven patterns of everyday words, and the review of PR #100 found that
four of the patterns could also hide a word that matters (`הקטינים`, `ילדות`, `מנער`,
the pair `פלוני אלמוני`). A second script counted what the first had dropped, printing
numbers only: 13 sentence hits by pattern, all of them `נערך` and `נערכ` ("was held"),
`מינימ`, `זמינ`, `ימיני` and one surname; no dropped sentence matches one of the four.
So the 31 are every hit but for those, and none of the twelve labelling sessions, which
read every document whole, raised a flag.
