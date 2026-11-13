# E4 pre-registration: PERSON recall against a ground truth that is known by construction

Committed before any template was written and before the model was run on generated text.
The commit order is the evidence.

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
