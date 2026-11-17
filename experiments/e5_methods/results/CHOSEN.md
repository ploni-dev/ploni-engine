# E5: the methods chosen on selection, written down before the held-out corpus is scored

Committed on 2026-11-17 after the three scoring runs on selection (`e4` and `select`,
1,595 planted names) and before any scoring of `heldout`. The commit order is the evidence.
The tables are in `selection_no_list.md`, `selection_given_all.md` and
`selection_given_top200.md`, as `evaluate.py` printed them at commit `fe9573d`.

The winners, by the rules of `PREREGISTRATION.md` and its two amendments:

| Part | Winner on selection | Found | Recall |
|---|---|---|---|
| Detector alone (with whole words) | `golem + whole words` | 1,519 of 1,595 | 95.24% |
| Step (a single step on the baseline) | `joint + carry` | 1,587 of 1,595 | 99.50% |
| Together (a union without a stack) | `golem or joint or large or seter_fast` | 1,588 of 1,595 | 99.56% |
| Of all | `golem at 0.03 + titles, carry` | 1,593 of 1,595 | 99.87% |

The cheapest method within half a point of the winner of all, by the rule of point 11 of
the first amendment (least seconds of its detectors, then fewer extra words without titles,
then fewer steps, then the name): `golem + titles, carry`, 1,590 of 1,595, 99.69%.

So the five methods that are scored on `heldout`, once, are:

1. `joint + whole words` (the baseline alone)
2. `golem + whole words` (the winning detector alone)
3. `joint + titles, carry` (the baseline with `titles` and `carry`)
4. `golem at 0.03 + titles, carry` (the winner of all)
5. `golem + titles, carry` (the cheapest within half a point)

No method with the `list` step is among them: with the list of every name the best such
method finds 1,592 of 1,595 and marks 1,550 extra words; with the 200 most common names of
each table, 1,591 and 755.

## Corrected on 2026-11-17, after the review of the findings note

What stands above is kept as it was committed before the held-out corpus was scored. Two
of its sentences say more than is so.

- **"The commit order is the evidence."** The commit shows that this file was written
  before the held-out table and its record lines were written (10:02:54 against 10:03:06).
  It cannot show that nothing was scored to the screen before: all four detectors had been
  run on `heldout` by 09:51. That no such scoring was made is the author's word.
- **The rule for the cheapest method** is quoted above as ending "then the name". Point 11
  of the first amendment ends with "then fewer steps". Three methods tie on its rules:
  `golem + titles, carry`, `golem + titles, carry strong` and
  `golem at 0.5 + titles, carry`, each with 1,590 names, 173 seconds, 45 extra words and
  two steps on top (the third also has a threshold; counted as a step, two tie). The tie was broken by the name, as point 10 does for the tables. That step
  was added here, at the choosing.
