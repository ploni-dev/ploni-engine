# E5 pre-registration: which way of finding names misses fewest

Committed before any candidate was downloaded and before any detector was run on E5's own
text. The commit order is the evidence.

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
