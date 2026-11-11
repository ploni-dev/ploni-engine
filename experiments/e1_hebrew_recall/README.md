# E1: baseline Hebrew PERSON recall

`build-plan.md` section 11. Prediction, threshold and counting rules: `PREREGISTRATION.md`,
committed before the run. Read that first; this file is only the steps.

All commands run from the repository root, in Git Bash.

## Once

```bash
python -m venv experiments/.venv
experiments/.venv/Scripts/python.exe -m pip install -r experiments/e1_hebrew_recall/requirements.txt
experiments/.venv/Scripts/python.exe -I scripts/download_e1_model.py
```

The download is about 750 MB into `models/dictabert-joint/<commit>/` and prints a SHA-256 per
file. Then check the harness reads the model correctly, on invented sentences:

```bash
M=models/dictabert-joint/7b1256fc0846e22d1af431eae299e2dcecee2778
experiments/.venv/Scripts/python.exe -I -X utf8 experiments/e1_hebrew_recall/smoke.py --model-dir $M
```

It must end with two `True` lines. The tests for the harness logic:

```bash
cd experiments/e1_hebrew_recall && ../.venv/Scripts/python.exe -m pytest -q
```

## The run

1. Put the ten documents, `.docx` or UTF-8 `.txt`, in a folder **outside the repository**, with
   nothing else in it. A PDF or a legacy `.doc` stops the run; convert it to `.docx` in Word
   first, and say so in the findings note, because the conversion is then part of what was
   measured. In a `.txt`, one line is one paragraph: unwrap a file that has line breaks
   inside sentences, or supply it as `.docx`.
2. Run the model. The output folder must be new and also outside the repository.

   ```bash
   experiments/.venv/Scripts/python.exe -I -X utf8 experiments/e1_hebrew_recall/run_model.py \
     --corpus-dir /c/path/to/e1_corpus --out-dir /c/path/to/e1_out --model-dir $M
   ```

   It prints one line of counts per document and nothing from the documents. Roughly five
   seconds per full window on this laptop, so a few minutes for a long decision.

   Two of the counts must be looked at before any counting by hand:

   - `unread_chars` above 0: the `.docx` holds body text the worksheet does not show, such
     as tracked insertions, content controls, fields or text boxes. Accept all changes in
     Word, save, run again in a new output folder, and say so in the findings note.
   - `unknown_pieces` above 0: the text holds characters the model cannot read, and each
     one hides a word from it. Report the count in the findings note.

   If a document cannot be read, the error names it as `docNN`; `index.csv` in the output
   folder says which file that is.
3. `e1_out/doc01_spans.csv` lists every PERSON span the model found in that document: its
   number on the worksheet, the paragraph (counted from 0), the start and end offsets in
   characters of that paragraph, and the text. Use it to check the spans against the original.

   Then open `e1_out/doc01.html` in a browser, and `e1_out/tally.csv` beside it. Read the document
   once, top to bottom, and fill in the row:

   | Column | What goes in it |
   |---|---|
   | `not_person_ids` | Numbers of yellow highlights that are not a counted mention under "What counts as a person name" in `PREREGISTRATION.md`: not a person, a placeholder, or a name inside an organisation, street, statute or cited precedent. Space-separated. |
   | `partial_ids` | Numbers of yellow highlights that cover only part of a name. |
   | `found_adjust` | Usually `0`. `+1` for each extra person inside one highlight that holds two names; `-1` for each surplus highlight when two adjacent ones cover a single name. If two highlights each cover only part of the same name, list one of them in `partial_ids` and add `-1` here, so the name counts as one error and not two. |
   | `public_ids` | Numbers of yellow highlights that are the name of a public figure, as `PREREGISTRATION.md` defines one. Leave empty if there is none. |
   | `missed` | Person-name mentions with no yellow highlight on them at all. |
   | `missed_other_label` | How many of those misses sit fully inside a grey highlight. |
   | `err_ordinary_word`, `err_proclitic`, `err_both`, `err_other` | Each missed or partial mention goes in exactly one. They must add up to `missed` plus the number of `partial_ids`. |
   | `found_adjust_public` | The part of `found_adjust` that concerns public figures. Usually `0`. |
   | `missed_public` | How many of the `missed` mentions are names of public figures. |

   A blank cell means "not counted yet" and stops the report. Write `0` for zero. The three
   id-list columns may stay empty.
4. Print the result:

   ```bash
   experiments/.venv/Scripts/python.exe -I experiments/e1_hebrew_recall/tally.py /c/path/to/e1_out/tally.csv
   ```

5. The report, the per-document lines from step 2 and `run_meta.json` go into
   `docs/findings/2026-11-NN-e1-hebrew-recall.md`, in a PR of its own, with `## Decision` empty.
   `tally.csv` holds numbers only and may be pasted. The worksheets and `index.csv` never leave
   the output folder.
