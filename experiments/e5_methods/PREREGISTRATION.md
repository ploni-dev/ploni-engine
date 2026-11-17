# E5 pre-registration: which way of finding names misses fewest

Committed before any candidate was downloaded and before any detector was run on E5's own
text. The commit order is the evidence.

**Amended on 2026-11-17, after the first review of the harness and after the first runs:
see the last section. It says what had been run and seen by then, narrows the candidates
to those already on the laptop, and settles the points this text left open. What stands
above it is kept as first written.**

**Amended a second time on 2026-11-17, before any scoring with the amended harness: the
full account of what had been seen, a correction about the row `no_trigger`, and three
more points of "the winner". See the section after the first amendment.**

## Why this experiment exists

Achia decided on 2026-11-16 that a series of experiments comes before the tests demand
anything for the kinds of names the model is weak on (`build-plan.md` section 11, "The
experiment series, once the merge gate works"): "a series of experiments to get the best
most fit tools". On 2026-11-17, in chat, he asked for it to be run overnight:

> Make sure to do a great research and look for relevant tools ( maybe even not the obvious
> tools like just another model, but different kinds) take your time to have a deep vast
> research. Create a short list of great candidates per each part relevant and run a series
> of experiments to see who are the winners.

E4 measured the model of the plan at 1,084 of 1,145 planted names, 94.67 percent, with 51
of its 61 errors in two kinds of mention: a surname after a group word (22 of 55 found) and
a given name alone that is an everyday word (`docs/findings/2026-11-14-e4-planted-names.md`).
E5 asks what gets closer to every name: another model, several models together, or steps
that are no model at all.

**It decides nothing.** The model of Phase 3 stands until Achia decides otherwise. The
output is a findings note with numbers and a recommendation.

## What a download means here

The plan says "Every model needs his yes before it is downloaded". Claude reads his message
of 2026-11-17 ("run a series of experiments to see who are the winners", "dont stop to ask
questions") as that yes for the candidates listed below, for the experiment only. That is
Claude's reading and it is named as such in the findings note. Every candidate is listed
here with its size and licence before it is fetched. Nothing is added to the product, and a
candidate folder under `models/`, which is not in the repository, can be deleted.

## The data

Three generated corpora, each with its ground truth, all from E4's generator
(`experiments/e4_planted_names/generate.py`): a script puts every name in its place and
writes down where. Nothing in them is a real document.

| Corpus | What it is | Used for |
|---|---|---|
| `e4` | E4's 40 documents, 1,145 counted mentions, unchanged | choosing |
| `select` | 20 new documents from 4 new templates (a partnership contract, a labour-court judgment, a letter from a personnel department, a medical referral) and a new name bank; 450 counted mentions, 55 of a person named once | choosing |
| `heldout` | 20 more documents from 4 other new templates (a loan contract, a tenancy judgment, a letter from an insurer, a nursing report) and a third name bank; 425 counted mentions, 55 of a person named once | judging, once |

- A method is **chosen** on `e4` and `select` together, 1,595 mentions.
- `heldout` is measured **once**, after the choosing, and only for the methods named in
  "What is measured on the held-out corpus". No method, list, threshold or rule is changed
  after its `heldout` number is seen. If one must be, the note says so and the number is
  reported as seen.
- The steps that are no model were written by Claude after reading E4's errors. So `e4` is
  text they were fitted to, and the `e4` number of a step flatters it. `select` was written
  before the steps were run on anything, `heldout` too.
- The name banks of the three corpora are different files and share no name
  (`build_banks.py` leaves out a name that another bank holds).
- `heldout` is E5's own. It is not the held-out batch of `build-plan.md` section 7, which
  holds real documents and starts with Phase 3.

The ten real judgments of E1 are not used: no script knows where their names are, and a
count by readers would take a night of its own.

## The candidates

### Detectors: a model that marks names

Run in this order, one at a time, as long as the night lasts. One that was not run is
reported as not run.

| Name | Model | Revision | Size | Licence | Why it is on the list |
|---|---|---|---|---|---|
| `joint` | `dicta-il/dictabert-joint` | `7b1256fc0846e22d1af431eae299e2dcecee2778` | 0.7 GB | CC BY 4.0 | the model of the plan; the baseline; already on the laptop |
| `golem` | `CordwainerSmith/GolemPII-v2-small` | `fbaf0f7a9092c50c9ecc27e3d33ba1352ac40883` | 0.5 GB | MIT | trained to find personal data in Hebrew; its authors claim 0.956 recall of persons on NEMO |
| `large` | `dicta-il/dictabert-large-ner` | `ac70130828d5a6811c2dc451e2255424c96f0eb0` | 1.7 GB | CC BY 4.0 | the large model of the same family as the baseline |
| `seter_fast` | `shoresh-labs/seter-pii-he-ar-fast` | `2744c393718de9a911d9db3478341984a99a7cdb` | 1.2 GB | MIT | trained to find personal data in Hebrew and Arabic; the smaller of two |
| `seter` | `shoresh-labs/seter-pii-he-ar` | `280425059728cd9bba14a4c3c0cd1f57c5278c00` | 2.2 GB | MIT | the larger of the two |
| `seter_fast_int8` | the same `-fast` model as an 8-bit ONNX file | `2744c393718de9a911d9db3478341984a99a7cdb` | 0.3 GB | MIT | what the small model loses when it is made four times smaller |

Each revision and the hash of each weights file were read from the hub on 2026-11-17
(`scripts/download_e5_models.py`), and each goes into `docs/THIRD_PARTY.md` before the
candidate is run. The licence is the one the model's card declares at that commit. A
candidate whose weights do not have the recorded hash is not run. A candidate that needs
code of its own to load (`trust_remote_code`) is not run, except the baseline, whose code is
vendored and was read. All five new ones load with the transformers and onnxruntime
packages that the experiments already pin.

**Three more are on the short list and are not run tonight**, because each needs a Python
package that the experiments do not have, and adding a package is a decision of Achia's
(`CLAUDE.md`, "Merging"). They go to him with the findings note:

| Name | Model | Size | Licence | Package it needs | Why it is on the list |
|---|---|---|---|---|---|
| `gliner` | `urchade/gliner_multi-v2.1`, commit `443d26d654e0324125a96bebd8e796c14ff2efe6` | 1.2 GB | Apache 2.0 | `gliner` | another kind of model: it is given the labels in words, with no training for Hebrew names. Not a v0 or v1 checkpoint |
| `stanza` | Stanza's Hebrew NER model | 0.2 GB | Apache 2.0 | `stanza` | another family: not a fine-tune of the same data |
| `llm` | `dicta-il/DictaLM-3.0-1.7B-Instruct` as a GGUF file | about 1.2 GB | Apache 2.0 | `llama-cpp-python` | another kind of tool: a small language model asked to list the names of a paragraph |

**Which labels are a person.** A label of a model counts as a person when its name, without
its B- or I- mark and in capitals, is one of `PER`, `PERSON`, `PRIVATE_PERSON`,
`FIRST_NAME`, `LAST_NAME`. Every run prints all labels of the model beside the ones that
were counted.

### Steps that are no model

Each takes what is marked so far in one document and adds to it. None removes anything.

| Step | What it does |
|---|---|
| whole words | widens every span to the whole of each word it touches |
| a lower threshold | takes every token whose chance of being a person is at least 0.5, 0.3, 0.1 or 0.03, in place of the model's own choice |
| `group` | marks the word after `משפחת`, `האחים`, `האחיות`, also behind attached letters |
| `titles` | `group`, and the word after a personal title (`מר`, `גב'`, `ד"ר`, `עו"ד`, `השופט` and so on), with an initial before it |
| `carry` | every word that stands inside a marked name is marked wherever else it stands in the same document, also behind attached letters |
| `carry strong` | `carry`, but only for a word that was marked twice or inside a name of two words |
| `list` | marks every word that is on a list of given names from outside this repository, also behind attached letters. The list: the given-name tables of `alumag/hebrew-names` (MIT, commit `e9055afea4c4bd0bb8d55102d543ee106f26041c`), every name in them; and a second, shorter form of it, the 200 most common names of each table. The name banks of the corpora are never the list |

### Together

Every pair of detectors that were run, and all of them, what any one marks being marked;
each alone and with `titles` and `carry` on top.

## How it is scored

- **Recall** by E4's strict rule (`experiments/e4_planted_names/score.py`): a planted name
  is found when what is marked covers every character of it that is not white space.
- **Rows.** Beside the pooled number: a surname after a group word; a given name alone that
  is an everyday word, modern and traditional; a mention with attached letters; a name
  alone on a line; **a person named once in the document**; Arabic names; transliterated
  names; each kind of document.
- **Words marked for nothing.** Hebrew words that a method marks and that lie in no planted
  name, as a count and as a share of the words it marks. Titles and group words are counted
  apart: hiding `מר` with the name is no error for the reader.
- **Time and memory.** Seconds for the corpus and the most memory the process held, on the
  laptop of `docs/REFERENCE_MACHINE.md`, measured, not a gate.

## Predictions and thresholds

Written before any run. "Selection" is `e4` and `select` together.

| # | Prediction | It is wrong when |
|---|---|---|
| 1 | The baseline alone finds 90 to 96 percent of `select` | outside that range |
| 2 | No detector alone reaches 99 percent on selection; the best one is between 94 and 98.5 | a detector alone reaches 99, or the best is under 94 |
| 3 | `titles` and `carry` on the baseline add 2 to 5 points on selection, and lift the group row from under half to over 90 percent | less than 2 points, or the group row stays under 90 percent |
| 4 | The best pair of detectors is 0.5 to 3 points over the better of the two | no gain, or more than 3 points |
| 5 | The best method of all finds 97.5 to 99.7 percent on selection | outside that range |
| 6 | The best method's `heldout` number is no more than 2 points under its selection number | more than 2 points under: the method was fitted to the selection text |
| 7 | A person named once stays the weakest row of the best method, under 97 percent | it is not the weakest, or it is 97 or more |
| 8 | `titles` and `carry` mark fewer than 2 extra words per 1,000 words of text; a threshold of 0.03 and the `list` step each mark more than 5 | either side is off |
| 9 | `large` and `seter` each take 2 to 5 times the baseline's seconds | outside that range |
| 10 | The 8-bit `seter_fast_int8` is within 1 point of `seter_fast` on selection, and takes under half its seconds | more than 1 point under, or not twice as fast |

A prediction that fails is reported as failed, with the number.

## What "the winner" means

Per part, on selection:

- **Detector:** the highest pooled recall of a detector alone, with whole words.
- **Step:** the step that adds most to the baseline.
- **Together:** the highest pooled recall of a pair or of all.
- **Of all:** the highest pooled recall of any method tried.

Ties go to fewer extra words, then to less time. Beside each winner the note names the
cheapest method within half a point of it, by time. Recall is what Achia ranked first
("accuracy is the top priority"); what a winner costs in extra words, time and memory is
printed beside it and no limit is set here: that is his to set.

## What is measured on the held-out corpus

After the choosing, once: the baseline alone; the winning detector alone; the baseline with
`titles` and `carry`; the winner of all; and the cheapest method within half a point of it.

## What is not in it

- The prefix forms of E3 that still fail and the real name behind a surname that begins
  with ה (`build-plan.md` section 11 lists them for the series). They need E3's harness and
  are a second part.
- Fine-tuning a model on generated text. It is on the research list and needs more than a
  night.
- Real documents.
- The three candidates that need a new package.
- Anything of the product: no file under `ploni/` is touched.

## Amended on 2026-11-17, after the first review of the harness

What stands above is kept as first written. An independent review of the harness
(PR #92, first pass, 18 findings) came back after the first runs had begun. This section
says what had been run and seen by then, what the review changed, and how each point the
text above left open is settled. It is committed before any run with the amended harness
and before any scoring with it.

### What was run and seen before this amendment

- **Before the first commit of this file.** The scoring code was tried with made-up
  detectors that mark planted names by construction. Files were made for all three corpora;
  tables were printed for `e4` and `select` only. Nothing of `heldout` was scored. After
  that dry run the lists of trigger words were tightened against words that only look like
  a title (`שמר`, `מרב`, `רב`, `רשם`, `שופט`, `אחים`). The tightening came from thinking of
  such words, not from a number, but it came after the dry run, and the commit order cannot
  show that.
- **After the harness was committed.** Run with the first version of `detect.py`: `joint`,
  `golem` and `seter_fast` on all three corpora, and `large` on `select`.
- **Scored once:** `joint` on `select`, with every method that needs only `joint`. Seen:
  `joint` 398 of 450 (88.44 percent), a surname after a group word 1 of 30;
  `joint + titles` 428; `joint + carry` and `joint + titles, carry` 446 (99.11 percent);
  `joint + carry strong` 443, with the fault of finding 1 in it. No other detector and no
  other corpus was scored. **No file of `heldout` was scored, by any method.**
- Every run file made before this amendment is thrown away. Each detector is run again with
  the amended harness, whose run files carry a digest of the text they were made on.

So the points settled below were settled by someone who had seen those five numbers. Where
a number that was seen bears on a prediction, it is said at the prediction.

### What the review found about fairness, and what it means for the numbers

- **The titles and group words are one closed list.** Every title that any template uses,
  11 of 11, is on the list of the `titles` step, and two of them, `הרשם` and `המהנדס`,
  stand only in the held-out templates. The generator writes only `משפחת` and `האחים`,
  which are the group words of the `group` step. The same author wrote the steps and all
  three corpora. Measured by the reviewer with no model at all, on the first version of the
  steps: `group` finds 55 of 55 and 30 of 30 surnames after a group word in `e4` and
  `select`; `titles, carry` alone finds 873 of 1,145 and 255 of 450.
- **So:** what the `group` and `titles` steps gain on these corpora is an upper bound. On
  text with a title that is not on the list, or with a word between the title and the
  name, they gain less, and E5 cannot say how much less. The held-out corpus does not judge
  these two steps independently: prediction 6 cannot fail because of them. It can still
  catch a model, a threshold or the `carry` step that fits the selection text.
- **A new row, `no_trigger`:** the mentions with no title and no group word before the
  name. It is printed in every table. It is the part of each corpus that the trigger steps
  cannot reach by construction, and the row to read for what a method does without them.

### What the review changed in the methods

- `carry strong` now does what the text above says. In the first version "inside a name of
  two words" never held once spans were widened to whole words. A word now counts when it
  stands next to another marked word of a name with only white space between.
- The trigger steps mark the word after a trigger only when nothing but white space lies
  between them. The form without the article is taken only behind ל, and only for
  `השופט`, `השופטת`, `הרשם`, `הרשמת`, `המהנדס`, `המהנדסת`, `האחים`, `האחיות`: `למנוחה`,
  `לרב`, `לאחות` and `כשופט` are ordinary words. This was changed after the five numbers
  above were seen. It can only make the steps mark less.
- Stated as limits: a name found only behind attached letters (`לכהן`) is not carried to
  its bare form; a maqaf or a hyphen ends a word.
- A run file is tied to its text by a digest, and `evaluate.py` refuses a file made on
  another text. The held-out corpus is scored only by itself and only for methods named on
  the command line. The weights of a candidate are hashed and compared before it is loaded.

### The candidates, after the review

The reviewer found that Achia's message of 2026-11-17 is a fair reading of a yes to the
downloads but is not the yes that `build-plan.md` section 11 asks for per model. The
question goes to him. When that finding arrived, three candidates and the list of names had
been fetched on that reading: `golem`, `large`, `seter_fast`, and the given-name tables of
`alumag/hebrew-names`. **Nothing more is fetched.** `seter` and `seter_fast_int8` are not
downloaded and not run. The detectors of E5 are therefore `joint`, `golem`, `large` and
`seter_fast`. If Achia's answer is no, the three folders and the list are deleted, and
every number that rests on them is marked as such in the findings note.

Of the three candidates that wait for a package: Stanza's Hebrew NER weights are `.pt`
files on the hub, which are pickles, and rule 2 of this experiment's PR fetches no pickle;
it would need a safe form of the weights first. The GGUF file of the small language model
has no pinned source yet. Both facts go to him with the list.

### The points the text above left open, settled

1. **"Alone"** in predictions 1, 2, 4 and 10 and in "the winner" of the detectors means the
   row `<detector> + whole words`.
2. **Prediction 1** is already known to have failed: 88.44 percent on `select`, under 90.
3. **Prediction 2:** the best `<detector> + whole words` on selection is between 94 and
   98.5 percent, and none reaches 99.
4. **Prediction 3:** the pooled recall on selection of `joint + titles, carry` minus that
   of `joint + whole words`, in points. Right when it is between 2 and 5 and the group row
   of `joint + titles, carry` is 90 percent or more; wrong otherwise, also when the gain is
   over 5. On `select` alone the gain seen was 10.67 points, so it is likely to be wrong on
   the side of "more than predicted".
5. **Prediction 4:** the best union of two detectors, without steps, against the better of
   its two with whole words. Right when the gain is between 0.5 and 3 points.
6. **Prediction 7:** the row `lonely` of the winner of all is under 97 percent, and is the
   lowest in percent of the rows of WEAK_ROWS that hold 30 mentions or more.
7. **Prediction 8:** extra words are the count without titles, added by the method over
   `<detector> + whole words`, per 1,000 Hebrew words of the selection text.
   `joint + titles, carry` adds fewer than 2. `joint + list`, with the list of every name,
   adds more than 5. The winning detector at a threshold of 0.03 adds more than 5; if that
   detector's file holds no chances, the best detector whose file does.
8. **Prediction 9:** the seconds of `large` on selection are 2 to 5 times those of `joint`.
   `seter` is not run.
9. **Prediction 10** cannot be tested: `seter_fast_int8` is not fetched.
10. **Ties** between methods of the same recall go to fewer extra words without titles,
    then to fewer seconds, then to the name. The table is sorted in that order.
11. **"The cheapest method within half a point":** among the methods whose pooled recall on
    selection is within half a point of the winner of all, the one whose detectors' seconds
    add up to least; then fewer extra words without titles; then fewer steps. The time of
    the steps themselves is a fraction of a second and is not what decides.
12. **Labels.** The mark of position that is taken off a label is one of B-, I-, E-, S-,
    L-, U-. If a run prints a label that is not on the list and that the model's card
    describes as a person's name, the run is thrown away, the list is amended here with a
    date, and the model is run again, before any of its numbers is scored.
13. **Each kind of document** is a column of every table.
14. **The two lists of names** are two scoring runs. Every table and every record line of a
    method with the `list` step says which list it used: file name, number of names, and
    the first 16 characters of the file's SHA-256.
15. **A detector that was not run on every corpus asked for** is named above the tables.

## Amended a second time on 2026-11-17, after the second review, before any scoring with the amended harness

The second review pass found that the first amendment's account of what had been seen was
not complete, that one sentence about the row `no_trigger` was too strong, and that three
points of "the winner" were still open. This section corrects that. When it was committed,
every detector had been run again with the amended harness and **nothing had been scored
with it**; no file of `heldout` had been scored by any version.

### What was seen before the first amendment, in full

The first amendment spoke of "five numbers". More was on the screen.

**The one scoring.** `evaluate.py` of the first harness printed one table for `select`, of
which these eight rows were read, every column of them:

```
| method | recall | found | group | given_ordinary | given_also_word | prefixed | alone | lonely | arabic | translit | extra words | with titles | marked in a name | seconds | peak MB |
| joint + carry | 99.11% | 446/450 | 30/30 | 65/65 | 7/7 | 90/90 | 59/60 | 52/55 | 20/20 | 64/64 | 17 | 18 | 97.3% | 197 | 1173 |
| joint + titles, carry | 99.11% | 446/450 | 30/30 | 65/65 | 7/7 | 90/90 | 59/60 | 52/55 | 20/20 | 64/64 | 17 | 18 | 97.3% | 197 | 1173 |
| joint + carry strong | 98.44% | 443/450 | 30/30 | 63/65 | 7/7 | 90/90 | 58/60 | 52/55 | 20/20 | 64/64 | 17 | 18 | 97.3% | 197 | 1173 |
| joint + titles, carry strong | 98.44% | 443/450 | 30/30 | 63/65 | 7/7 | 90/90 | 58/60 | 52/55 | 20/20 | 64/64 | 17 | 18 | 97.3% | 197 | 1173 |
| joint + titles | 95.11% | 428/450 | 30/30 | 59/65 | 5/7 | 77/90 | 58/60 | 52/55 | 20/20 | 64/64 | 16 | 17 | 97.4% | 197 | 1173 |
| joint + group | 94.89% | 427/450 | 30/30 | 59/65 | 5/7 | 77/90 | 58/60 | 52/55 | 20/20 | 64/64 | 16 | 17 | 97.4% | 197 | 1173 |
| joint | 88.44% | 398/450 | 1/30 | 59/65 | 5/7 | 67/90 | 58/60 | 52/55 | 20/20 | 58/64 | 16 | 17 | 97.3% | 197 | 1173 |
| joint + whole words | 88.44% | 398/450 | 1/30 | 59/65 | 5/7 | 67/90 | 58/60 | 52/55 | 20/20 | 58/64 | 16 | 17 | 97.3% | 197 | 1173 |
```

So `joint + whole words`, the row that "alone" means, was 398 of 450, the same as `joint`.

**The detector runs.** Each run printed its seconds, its peak memory, the model's labels and
the number of rows it wrote, on `heldout` too. For `joint` a row is one name the model
marked. Seen, with the first harness: `joint` 197.2 s and 422 rows on `select`, 420.9 s and
1,138 rows on `e4`, 203.3 s and 402 rows on `heldout`, about 1,180 MB; `golem` 56.5, 119.3
and 55.0 s, about 850 MB; `seter_fast` 98.7, 207.0 and 100.5 s, about 1,900 MB; `large`
164.3 s on `select`, 2,053 MB. The runs with the amended harness printed the same kind of
lines again, with times within a few seconds of these. A row count says how much a model
marked, not how much of it is right; no recall on `heldout` was computed or seen.

### Which predictions were therefore not made blind

- **Prediction 1:** failed, known since the first scoring (88.44 percent on `select`).
- **Prediction 3:** the gain on `select` was in view (10.67 points); said in the first
  amendment.
- **Prediction 5** (the best method of all finds 97.5 to 99.7 percent on selection): 99.11
  percent for `joint + carry` on `select` was in view when the first amendment was written.
  The range itself was written before any run and was not changed.
- **Prediction 7** (the row `lonely`): 52 of 55 for every `joint` method on `select` was in
  view when point 6 of the first amendment settled how the prediction is read.
- **Prediction 8** (extra words): 16 and 17 extra words of the `joint` methods on `select`
  were in view when point 7 settled how they are counted.
- **Prediction 9** (the seconds of `large` against `joint`): 164.3 against 197.2 seconds on
  `select` were in view when point 8 named `large` alone. On that corpus the ratio was
  under 1, so the prediction is likely to be wrong.
- **Predictions 2, 4 and 6** rest on numbers that had not been computed: no detector but
  `joint` was scored, no union, and nothing on `heldout`.

The findings note counts predictions 1, 3, 5, 7, 8 and 9 as partly after the fact.

### The row `no_trigger`, corrected

The first amendment called it "the part of each corpus that the trigger steps cannot reach
by construction, and the row to read for what a method does without them". That is true of
`group` and `titles` alone. It is not true of a stack with `carry` after them: a trigger
gives the name, and `carry` takes it to the bare mention. Measured by the reviewer with no
model: `titles` alone finds 0 of 620 and 0 of 275 mentions of that row in `e4` and
`select`; `titles, carry` finds 390 of 620 and 110 of 275. So for `titles, carry` the row
still holds names that the closed list gave. The rows that owe the list nothing are those
of `<detector> + whole words`, `<detector> + carry`, `<detector> + list`, the thresholds
without a stack, and the unions without a stack.

### Three points of "the winner", settled

16. **"Step: the step that adds most to the baseline"** compares the single steps on
    `joint`: `group`, `titles`, `carry`, `carry strong`, and `list` once with each of its
    two lists. A stack of two or more steps is not a step.
17. **"Together"** compares the unions of detectors without a stack. A union with
    `titles, carry` on top can be the winner of all, not the winner of "together".
18. **On the held-out corpus** "the baseline alone" is `joint + whole words`, and "the
    winning detector alone" is that detector `+ whole words`.

Point 14 of the first amendment said every table names its list. The name of the list now
stands in the title of each table of a run that uses one.
