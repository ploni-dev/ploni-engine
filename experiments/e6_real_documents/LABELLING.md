# E6 labelling guide

Written before any of the twenty decisions was read for names. The rules are those of
`PREREGISTRATION.md`, "The answer key"; this guide restates them for the readers and settles
the cases a reader meets. Where the two disagree, the pre-registration wins and the reader
reports the disagreement.

There are three passes. Labeller A and labeller B each mark every document alone, from this
guide and the worksheets, and see nothing of each other's work. The third pass settles
where they differ. No pass sees what any detector marked, and no pass is told which pile a
document is in.

## Privacy

The documents are published court decisions with real people's names. Write names and
text only into the files named below, inside the corpus folder. In your final answer give
counts, document ids and line numbers only: no name and no sentence of a document.

## The worksheet

`worksheets/<id>.txt`. Per paragraph a line `¶K`, K from 0, then one line with every run
of characters between spaces, each behind its number in brackets, from 0:

```
¶12
[0]ביום [1]1.1.2020 [2]פנה [3]מר [4]ישראל [5]ישראלי, [6]באמצעות [7]בא-כוחו,
```

The first paragraphs are the caption: the court, the judges, the parties, the lawyers.

## A label

One line per name in `<your folder>/<id>.tsv`, UTF-8. The first line is the header. The
fields are separated by one tab each:

```
paragraph	first	last	text	person	kind
12	4	5	ישראל ישראלי	p3	private
```

- `paragraph`: K of the `¶K` line.
- `first`, `last`: the numbers of the first and the last run the name stands in. For a
  name of one word they are the same number.
- `text`: the name exactly as it stands in those runs, character for character, and
  nothing else: no title, no attached letters before it, no comma, bracket or quote mark
  around it. In run `[5]ישראלי,` the text is `ישראלי`. In a run `ולישראלי` the text is
  `ישראלי`. Between two words of a name write one space, as the worksheet shows it.
- `person`: a key of your own for the person, `p1`, `p2` and so on, the same key for every
  mention of the same person in the document. Two people who share a surname are two
  keys. A surname that stands for several people at once (`האחים ישראלי`) gets a key of
  its own. For a name that is not counted write `-`.
- `kind`: `private`, `public` or `not_counted`.

Every mention gets its own line, also when the same name stands ten times.

## What is one name

- A given name, a surname or a full name of a natural person. A full name written
  together is one label over all its runs, not two.
- An initial with a surname (`י' ישראלי`) is one label; the initial is part of the text.
- Two people joined by "and" are two labels.
- A name with a maqaf or a hyphen in it is one name, written as it stands.
- A name in Latin letters is a name.

## Counted: `private` or `public`

- The parties, lawyers, judges, registrars, witnesses, experts, appraisers, mediators and
  everyone else who is named, in the caption and in the text.
- A dead person named in the name of an estate (`עיזבון המנוח ...`): the person's name.
- A surname that stands for people: after `האחים`, `משפחת`, `בני הזוג` and the like.
- A judge named as the author of a cited opinion (`השופט י' ישראלי` after a citation).
- An author named in the decision's own sentence (`כפי שכתב פרופ' ישראלי`).
- A nickname that is used as the person's name.

`public`: a judge or a registrar, of this case or of any cited opinion; an elected or
appointed public official named in that role; a lawyer or an expert that a reader of the
news would know by name. `private`: everyone else, and every case you are unsure of.
One person has one kind throughout a document.

## Marked as `not_counted`

A detector that marks these is not blamed for it, so they must be labelled too. The `text`
is the person's name only.

- The names in the title of a cited decision: both sides of `ישראלי נ' כהן`, and the name
  in `עניין ישראלי`, `פרשת ישראלי`, `הלכת ישראלי`. The caption of this case itself is not a
  cited decision: its people are counted.
- A person's name inside the name of an organisation, a firm, a company, a street, a
  place, an institution, a statute or a doctrine.
- An author inside a reference to a book or an article (authors, title, page).
- The placeholders `פלוני`, `אלמוני`, `פלונית`, `אלמונית`, and bare initials that stand
  for a hidden name.

## Not labelled at all

Roles and descriptions (`המבקש`, `המשיבה`, `המנוח`, `ב"כ המערער`), titles alone, pronouns,
companies and bodies whose name holds no person's name, courts, places that are not named
after a person, and the word for a judge written with spaces between its letters at the
end of a decision.

## The subject check

If you find that the court below is a family or juvenile court, that a party or a victim
is a minor, that the claim is about a sexual offence, or that a party is captioned
`פלוני` or `אלמוני`, write a line with the document's id and which of the four it is into
`<your folder>/flags.txt`, and label the document all the same. A mention in passing (a
party's children as background, an earlier family-court ruling that the decision relies
on) is not one of the four.

## How to work

1. Read the whole document once, top to bottom, slowly, and label as you go. Look where
   names hide: in the caption; after titles and role words; in lists of lawyers and
   judges; inside brackets; behind attached letters; in the last lines.
2. Then go through your labels person by person, and search the worksheet for each
   person's name words once more.
3. Check your file: `python -I label.py check --corpus <corpus> --a <your folder>`. It
   names every line that does not fit the worksheet, by number. Fix those lines.
4. Write one line per doubt into `<your folder>/<id>_doubts.txt`: the paragraph, the
   runs, what you chose and why you were unsure; `none` if there is none.

## The third pass

For each document, `compare/<id>.tsv` holds a line per label that only one labeller has
or that the two have with another kind (`why` is `differ`), and a line per place that may
hold a name no label marks (`why` is `carry` or `title`). Read each line in its paragraph
in the worksheet and decide it by the rules above. Read the two labellers' doubts for the
document. A line whose `why` is `person` is a place where the two labellers divide the
names among people in another way: one sees one person where the other sees two. Decide
by the text who is who.

Then write `key/<id>.tsv`, a label file as above: every label the two agree on, as it
is; every difference as you decided it; every place that you found to be a name. Where a
listed word is part of a name that both labellers marked too short (an initial before a
surname, a second surname), make that label longer; do not add the word as a label of
its own. Do not join it to a name of another person either. Add no label, and no word
to a label, that is neither in a labeller's file nor on a line of the compare file: the freeze
refuses a key that does, a key that drops, cuts or gives another kind to a label both
labellers have, and a key that puts one label over two labels both have.
Person keys: take labeller A's key for each person. A label that only B has, or that
comes from a listed place, gets A's key for that person, or a new key when A has none.
Write what you decided, line by line, into `key/<id>_decisions.txt`. Check the key with
`python -I label.py check --corpus <corpus> --a <corpus>/key`.

## Your final answer

Counts only, per document: labels by kind; persons; doubts; flags; for the third pass
also how many differences went each way and how many places were names. No name and no
text of a document.
