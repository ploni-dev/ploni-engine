# E1 pre-registration: baseline Hebrew PERSON recall

Written 2026-11-11, before `dicta-il/dictabert-joint` was loaded for the first time on this
machine and before any of the 10 documents was supplied. The commit that adds this file is the
timestamp. Any change to this file after the run on the real documents is a change after the
fact and must be called that in the findings note.

## Prediction and threshold, from the plan

Quoted from `build-plan.md` section 11, lines 1031 to 1033:

> **E1. Baseline Hebrew NER recall.** `dictabert-joint` on 10 real Hebrew documents (court
> decisions, contracts, a medical summary). Count missed person names by hand.
> Prediction: 85 to 92 percent PERSON recall, errors concentrated in ordinary-word names and
> proclitic forms.
> Threshold: below 80 percent, the architecture needs rethinking before anything else is built.

## The corpus, as Achia set it on 2026-11-12

**Changed on 2026-11-13, before the run: who assembles the corpus and which documents are
in it. See "Amended on 2026-11-13" below. This section is kept as first written.**

Achia assembles the ten documents. The plan's mix (court decisions, contracts, a medical
summary) is replaced, for two reasons Achia gave. Real signed contracts and real medical
records with names are not published, so the honest source for both is court decisions that
quote them. And Supreme Court public-law rulings name judges, senior lawyers and public
figures, who are common in the model's training text, so recall on them would be optimistic
and would not describe a lawyer's document about a private client.

The ten documents are decisions that name private individuals:

- 4 or 5 civil judgments of magistrate or district courts (`ת"א`, `תא"מ`): contract
  disputes, landlord and tenant, road accidents.
- 3 labour court rulings (`סע"ש`, `ד"מ`), which quote employment contracts at length.
- 2 medical malpractice judgments of district courts, which name the plaintiff, the doctors
  and the hospital and describe treatment.

Nothing from family court, minors or sexual offences, and no case captioned `פלוני` or
`אלמוני`. The findings note lists what was actually run, by type and count, not by name.

## Public figures and private parties, an addition to E1

Achia added this on 2026-11-12. It is not in the plan. Recall is counted twice, once for
names of public figures and once for names of private parties, and both are reported beside
the pooled number.

- The plan's prediction and threshold stay on the pooled number. That is the E1 verdict.
- A public figure is a person named in a public role: a judge or registrar, an elected or
  appointed public official, and a lawyer or expert the annotator would expect a reader of
  the news to recognise. Everyone else is a private party, including the parties, witnesses,
  doctors, and the lawyers of record in an ordinary case. **The line between a known lawyer
  and a lawyer of record is Claude's reading of "judges, known lawyers, public officials".**
- No prediction exists for the gap. Achia expects recall on public figures to be higher.
- **Claude's readings, for Achia to amend:** a difference of 10 percentage points or more
  between the two recalls, in either direction, is a finding in itself. It is only read if
  each group has at least 30 mentions, because a judge is named a handful of times per
  decision and a smaller group moves by several points per mention.
- If the private-party recall is below 80 percent while the pooled number is not, the
  findings note says so in its first line. The decision is Achia's.

## What the plan leaves open, and the reading fixed here

The plan gives the numbers but not the unit, the matching rule or the input handling. Each
choice below moves the measured number, so each is fixed now. **These are Claude's readings,
not Achia's decisions. Achia confirms or amends them before the run, in a commit that precedes
the run.** What Achia said on 2026-11-13 is under "Amended on 2026-11-13" below.

| Open point | Reading fixed here | Why this one |
|---|---|---|
| Unit of recall | One mention: each occurrence of a person name in the text counts once. | A missed occurrence is a leak whether or not the same name was caught elsewhere. Phase 3 calls the same number "entity-level", which in NER evaluation means span-level, not token-level. |
| Pooling | Micro: all mentions of all 10 documents in one fraction. Per-document and macro are reported beside it. | "Count missed person names" describes one count. Macro is reported because one long document can dominate a pooled figure. |
| Match rule (primary, strict) | Found only if `PER` highlights cover every name token of the mention. Part of the name covered is `partial` and counts as not found. | Half a name left in the output is still a leak. |
| Attached prefix letters | A proclitic (ו ה ב ל מ כ ש and combinations) may fall inside or outside the highlight. | The model labels whole whitespace words, so it cannot separate them. Separation is E3's question. |
| Titles | `עו"ד`, `ד"ר`, `השופט`, `מר`, `גב'` are not part of the name. Their absence from a highlight is not a miss. | The model has a separate `TTL` label. |
| Wrong label | A person name fully covered by a non-`PER` highlight is a miss in the primary number, and is counted separately so an any-label figure can be reported. | The plan says PERSON recall. The any-label figure matters to the decision, so it is recorded, not substituted. |
| "Errors concentrated in" | More than half of all errors (missed plus partial) fall in the ordinary-word, proclitic, or both categories. | The plan gives no number. Half is the weakest reading of "concentrated". |
| Between 80 and 85, or above 92 | Reported as outside the prediction with the threshold not crossed. | The plan defines only the two regions. |

## What counts as a person name

Counted:
- Given name, surname or full name of a natural person, every occurrence, with or without an
  attached prefix. Judges, lawyers, doctors, witnesses and parties all count.
- An initial with a surname (`א' כהן`) counts as one mention.

Not counted:
- Placeholders and anonymised forms: `פלוני`, `אלמוני`, bare initials (`א.ב.`, `ר' ש'`).
- Roles and descriptions: `המבקש`, `התובעת`, `המנוח`, pronouns.
- A person's name inside the name of an organisation, a firm, a street, a statute or a cited
  precedent (`משרד כהן ושות'`, `רחוב ז'בוטינסקי`, `הלכת אפרופים`).
- Anything not in the worksheet text. The count is over the text the model was given, so text
  the extraction dropped (headers, footers, footnotes, text boxes) is outside this number.

A doubtful case is decided once, written into the findings note, and applied the same way to
every document.

## Error categories

Every missed or partial mention gets exactly one:
- `ordinary_word`: a name token is also a common Hebrew word (`ברק`, `שלום`, `אור`, `טל`).
- `proclitic`: the mention carries an attached prefix (`ולמשה`, `שברק` counts as `both`).
- `both`.
- `other`.

## Model and input handling, frozen

- Model: `dicta-il/dictabert-joint` at commit `7b1256fc0846e22d1af431eae299e2dcecee2778`.
  Weights from `models/dictabert-joint/<commit>/model.safetensors`, offline. The model's
  Python is the copy vendored in `vendored/dictabert_joint/`, byte for byte the files of that
  commit; nothing is fetched or executed from the hub, and `trust_remote_code` is not used.
- The syntax head is switched off, which skips the dependency-tree decoding E1 has no use for.
  The heads read the same encoder output and do not feed the NER classifier
  (`BertForJointParsing.py:163-169` at the pinned commit), and tokenization is the same either
  way (`BertForPrefixMarking.py:239`). `smoke.py` asserts the NER output is identical with all
  heads on. The other heads stay on because the model's shipped code fails without them under
  transformers 5.22.2 (the two errors are recorded in `run_model.py`).
- Labels read as the argmax per word, grouped by the model's own `aggregate_ner_tokens`. No
  score threshold, no post-processing, no dictionary, no retry.
- Unit of input: one paragraph or table cell. A paragraph longer than 510 wordpieces (512
  positions minus `[CLS]` and `[SEP]`) is cut after the last sentence-final punctuation that
  fits, or before the first word that does not fit when there is none. Windows do not overlap.
  The run prints how many paragraphs were cut and how many cuts were not at a sentence end.
- Text extraction: `.txt` as UTF-8; `.docx` body paragraphs and table cells in document order,
  each with the text of the content controls inside it (added on 2026-11-13, see below).
- Characters the tokenizer cannot represent: every Unicode space separator becomes a plain
  space, and every format character (zero-width space, soft hyphen, byte order mark,
  direction marks) is removed, before the text reaches the model and the worksheet. Measured
  on the tokenizer at the pinned commit, `משה`, a no-break space, `כהן` becomes one `[UNK]`
  piece, which would hide both words from the model. Phase 3 normalizes whitespace too.
- Two counts are printed per document so that lost text is never silent: `unknown_pieces`,
  the `[UNK]` pieces left after that rewriting, and `unread_chars`, the characters of `.docx`
  body text the extraction did not return (tracked insertions, content controls around
  whole paragraphs, fields, text boxes). A document with `unread_chars` above 0 is fixed in Word and run again.
- Placeholders: every mention of `פלוני` or `אלמוני` (feminine or plural, with attached
  prefix letters, adjacent ones such as `פלוני אלמוני` as one mention) is counted per document
  and printed as `placeholders`. A `PER` highlight that holds only such a word is counted as
  `placeholder_highlights`, and its number is written into `not_person_ids` before the hand
  count starts. A placeholder is neither a found name nor a missed one, as "What counts as a
  person name" says. Bare initials and blanks are not detected and stay with the hand count.

## Decision rule

Primary number: strict mention-level PERSON recall, pooled over the documents, as an exact
fraction `found / (found + partial + missed)`.

- `found * 100 < 80 * total`: threshold crossed. Stop; the findings note says so.
- `85 * total <= found * 100 <= 92 * total`: inside the prediction.
- Anything else: outside the prediction, threshold not crossed.

No number is rounded before it is compared.

## Amended on 2026-11-11, before any real document was run

On 2026-11-12, also before any real document was run: the corpus section and the public and
private section above were added at Achia's instruction, the model's Python was vendored,
and each document now also gets a list of its PERSON spans with offsets. The prediction, the
threshold, the counting rules and the decision rule on the pooled number are unchanged.

Also on 2026-11-12, before any real document was run, after the brief in issue #4: the
placeholder bullet above was added. The rule is unchanged, placeholders were already not
counted; what changed is that the run counts them and lists their highlights, so they are
reported apart and not typed by hand. The issue reports that the Supreme Court's medical
malpractice decisions are mostly captioned `פלוני`, and leaves the source of the corpus to
Achia. "No case captioned `פלוני` or `אלמוני`" in the corpus section stands until Achia
changes it; if such a document is run, the findings note gives its `placeholders` count and
says which party is unnamed.

Also on 2026-11-12, before any real document was run, a second Ponytail review of the whole
harness (pasted in PR #11) led to these changes. A paragraph is no longer cut after two
initials written with full stops (`י.ח. לוי`), which the cut rule had read as a sentence end.
The tally is refused if a document appears twice in it or its columns were changed. The
report prints whether private-party recall alone is below 80 percent, the comparison the
public and private section above already asks for. `run_meta.json` records the SHA-256 of
the model files. The prediction, the threshold, the counting rules and the decision rule
are unchanged.

The Ponytail review of the harness found three ways the number could be wrong for a reason
that is not the model. The two input-handling bullets above about characters and counts were
added in answer. The prediction, the threshold, the counting rules and the decision rule are
unchanged. `README.md` now also says how to record a name the model split into two partial
highlights, and that a highlight on a name that does not count is listed in
`not_person_ids`; both follow from the rules above and change none of them.

## Amended on 2026-11-13, before any real document was run

No document had been given to the model when this was committed. The prediction, the
threshold and the decision rule are unchanged. The counting rules are unchanged, with one
doubtful case settled ahead of the count (judges named in citations, below).

Achia decided three things in the session of 2026-11-13: Claude collects the documents, they
come from the Supreme Court's public search, and Claude does the count. Everything else
below is Claude's choice and is marked as such.

**Who assembles the corpus.** Achia asked Claude to collect the ten documents. Until now this
file said Achia assembles them.

**Which documents.** Ten judgments of the Supreme Court in civil appeals (`ע"א`), from the
court's public search. The mix of 2026-11-12 (magistrate and district civil judgments, labour
rulings, district medical malpractice judgments) is dropped. Issue #4 reports that those sit
on Net HaMishpat, and Achia chose the Supreme Court's public search. The two exclusions
stand: nothing from family court, minors or sexual offences, and no case captioned `פלוני`
or `אלמוני`.

**How the ten were chosen** (Claude's rule), so that the choice cannot follow the model's
output. One search on 2026-11-13 at `supremedecisions.court.gov.il`: section `אזרחי`,
procedure `ע"א-ערעור אזרחי`, document type `פסק-דין`, substantive documents only, 8 to 25
pages, document date in the last year (13/11/2025 to 13/11/2026), newest first. It returned
42 documents. Taken in the listed order: the first ten whose caption names a natural person,
by name, as a party. Passed over on the way: three captioned `פלוני` (results 2, 4 and 9)
and one between two companies (result 12). The ten are results 1, 3, 5, 6, 7, 8, 10, 11, 13
and 14. Only the captions were read before the choice. The page range is Claude's choice: a
judgment under 8 pages holds few names, and ten judgments over 25 pages are more than one
annotator reads with care.

**The subject check, done before the run.** A document is dropped if the court below is a
family or juvenile court, if a party or a victim is a minor, or if the claim is about a
sexual offence. Checked on 2026-11-13 by searching the text of each document for the words
for family court, minor and sexual offence, and reading each hit in its sentence. No
document names a family or juvenile court. One document says, as background, that a party
came to the country with a son who was then a minor; the son is not a party. Every other
hit is the phrase `מיני רבים` before a list of citations. So none of the ten is dropped. No
document is dropped after the run, for its subject or for anything else.

**The files.** `.docx`, as the site's "save as Word" link gives them, not re-saved.
Downloaded one at a time in Achia's browser, on Achia's decision after hearing what the
site's terms of use say. The run names them `doc01` to `doc10` in the order of their file
names. SHA-256 of each, in that order:

```
doc01  af94dd559248e1bc2a5fda5c4431fd4ccf53cfe01c628d1dd505462a895347e8
doc02  a19885b48cb0e4d2abc9e8fa6015cb3f3e1ce543dbb34df47f95415eff7efeae
doc03  6cf959fda1a87692f604f8625ab762a65c4f348cb0ee1d18683d830fb1b53378
doc04  adb6bf21a0a1d113fd7c983d2ed874291faec28cafdcfc901558b30fe8d5db77
doc05  d88d88343ff7a4c4346117edab676b362719e6a7da420334beb11402b9be4de5
doc06  e89f499d0988c8929eb2005b90e44433efd220e51824e94e1b9d4db5711eb902
doc07  993b26324976e29421b6d6fa055b48c9d4bf1e35ab63d2eb961ae22b7ebe706f
doc08  d736d885d336ce3cfc6178b5d97d5c19d91c7ea98a335d7f2760063a808ffdbf
doc09  319e4d67d873c00c954956ffbd013bc1d2e6d97db71ad738b7dfc8ec2ba82ef0
doc10  a25246e20d590b1871989ae46cbc8481967b62253c2fbc59da2d4eefcbf33639
```

**The caption, and a change to the reader.** These files keep their caption (the panel, the
parties and the lawyers) in content controls inside paragraphs: 16 to 41 per file, 126 to
492 characters per file, 2,227 in all. The reader skipped them. The review of this
amendment found it, before the run. The reader now reads a content control that sits inside
a paragraph (branch `fix/e1-read-content-controls`, tests first). A content control around
whole paragraphs is still not read and still counted. Measured with the reader alone, no
model: `unread_chars` is 0 in all ten, and 224,355 characters are read, 13,752 to 36,551
per document. The headers hold 1 or 2 characters per document, and no footer, footnote or
endnote holds text. A caption line is a name with little around it, which is where a model
that reads context may do worst. That is a reason to count it, not to leave it out.

**What this does to the number.** It describes Supreme Court civil appeals, not a lawyer's
document about a private client. Each judgment names its judges, and Achia's concern of
2026-11-12 holds: such names are common in the model's training text. The public and
private split above exists for this, and its rules are unchanged. Appellate judgments also
quote fewer contracts and medical records than trial judgments do. `build-plan.md:687` says
published decisions are for realism, "never as ground truth".

**Judges named in citations** (Claude's reading, fixed before the count). These judgments
cite many decisions. The title of a cited decision (`כהן נ' לוי`) is the name of a
precedent and is not counted, as "What counts as a person name" already says. A judge named
as the author of a cited opinion (`השופט פלוני` after a citation) is a person named in a
public role: it is counted, as a public figure.

**Who counts.** Claude reads the worksheets and fills in the tally. The plan says "count
missed person names by hand", and until now the count was Achia's, with Claude beside. A
count by a language model departs from the plan. Achia decided it on 2026-11-13. Two steps
are added for this run. They are not in `README.md`.

- Every missed or partial mention gets a line in `misses.csv` in the private output folder,
  with these columns: `doc_id`; `paragraph`, counted from 0 as in `docNN_spans.csv`; `text`,
  the mention; `kind`, `missed` or `partial`; `group`, `public` or `private`;
  `other_label`, `yes` if a missed mention sits fully inside a grey highlight; `category`,
  the error category. Each number in the tally's error and miss columns can then be counted
  again from this file. The file holds names and never leaves the folder.
- A mechanical cross-check. Every word the model highlighted as part of a person name
  somewhere in a document is searched for in the rest of that document: as a whole word, and
  with one to three of the letters ו ה ב ל מ כ ש in front of it. Each occurrence outside a
  highlight is looked at. The script that lists them is a throwaway outside the repository.
  It is not tested and it decides nothing: it gives places to look at. The findings note
  says, per document, how many places it listed and how many of them were misses.

**Achia's check.** Achia checks `doc06`, the document with the least text (13,752
characters), after Claude's count: the worksheet `doc06.html` against the `doc06` lines of
the tally and of `misses.csv`. The findings note says whether the check was done and gives
both counts for `doc06`. If they differ on any mention, Claude counts all ten again with
what the difference showed, and the note gives the first tally and the second.

Limits this adds. The annotator is a language model. It can share a blind spot with the
model under test: a name that neither recognises is counted by neither, which makes recall
look higher than it is. One document checked by a person is the only human check.

**The readings.** Achia was shown five of Claude's readings in plain words and confirmed
them: one mention is one unit, a name is found only if the whole name is highlighted, titles
are not part of the name, judges are counted and also reported apart from private people,
and below 80 percent the threshold is crossed. For the others (micro pooling, attached
prefix letters inside or outside a highlight, a wrong label as a miss, "concentrated" as
more than half, between 80 and 85 or above 92 as outside the prediction, the 10-point gap
read only with 30 mentions in each group, a lawyer of record as a private party) Achia
said: "for these kinda decisions u dont need me, Just go on". They stand as Claude's
readings.

## Known limits, stated before the run

- Ten documents chosen by a rule on one search are not a sample of anything. The number
  describes these ten.
- Mentions inside one document are not independent: one name the model cannot see, repeated
  fifty times, moves the pooled figure by fifty. The per-document table exists to show that.
- One annotator, one pass. Since 2026-11-13 the annotator is Claude and Achia checks one
  document afterwards. Annotation error is not measured beyond that check.
- Non-overlapping windows can cut a name in two in a long paragraph. Phase 3 windowing
  (stride 128) is not implemented here; the cut counts bound how often this can have happened.
- The number is recall only. Precision of `PER` highlights is reported because it falls out of
  the same count, but nothing is predicted about it.
