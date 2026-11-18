# E6: does what E5 found hold on real documents

Not product code. Read `PREREGISTRATION.md` first: it says which documents, how the two
piles were drawn, how the answer key is made, what is scored and what was predicted, and it
was committed before any document was read for names.

## What is here

| File | What it does |
|---|---|
| `PREREGISTRATION.md` | the plan of the experiment, with the predictions |
| `real.py` | which documents there are, their piles and hashes; reads a document and its labels into the shape E5's scorer reads |
| `label.py` | writes the labellers' worksheets, puts two labellers side by side, freezes the key |
| `detect_real.py` | runs one model over one pile, by E5's runner |
| `score_real.py` | scores E5's methods on one pile against the key; loads no model |
| `key_sha256.tsv` | the hash of every key file; added by the commit that freezes the key, before any run |
| `results/CHOSEN.md` | the methods judged on the closed pile; added before that pile is touched |
| `tests/` | the tests of all of the above, on made-up sentences |

No name and no sentence of the twenty decisions is in this folder. The documents, the
worksheets, the labels, the key, the run files and the lists of errors are in two folders
outside the repository, `<corpus>` and `<out>`.

## How it is run

In the environment of `experiments/e2_int8_latency/requirements.txt`, offline, from this
folder, in this order. `<models>` is the `models/` folder of the repository.

```
python -I label.py worksheets --corpus <corpus>
    # two labellers each write <corpus>/labels_a/<id>.tsv and <corpus>/labels_b/<id>.tsv
python -I label.py compare --corpus <corpus> --a <corpus>/labels_a --b <corpus>/labels_b
    # a third pass decides every line of <corpus>/compare/<id>.tsv and writes <corpus>/key/<id>.tsv
python -I label.py freeze --corpus <corpus>          # writes key_sha256.tsv here; commit it
python -I detect_real.py --corpus <corpus> --pile open --detector joint --model-dir <models>/dictabert-joint/<revision> --out <out>/runs/joint.e6-open.json
python -I detect_real.py --corpus <corpus> --pile open --detector hf --model-dir <models>/golem/<revision> --sha256 <hash of its weights, from docs/THIRD_PARTY.md> --out <out>/runs/golem.e6-open.json
python -I score_real.py --corpus <corpus> --runs-dir <out>/runs --pile open --record results/record.jsonl --lists-to <out>/open_lists.txt
    # write and commit results/CHOSEN.md; only then:
python -I detect_real.py --corpus <corpus> --pile closed ... --out <out>/runs/joint.e6-closed.json
python -I score_real.py --corpus <corpus> --runs-dir <out>/runs --pile closed --only "joint + whole words" "joint + carry" ...
python -m pytest tests
```

On a machine with little memory free, add `--budget-seconds 420` to a `detect_real.py`
command and give the same command again until it says that every document is done.

A label file has a header and one line per name, the fields separated by tabs:
`paragraph`, `first`, `last` (the numbers of the paragraph and of the first and last run
the name stands in, as the worksheet prints them), `text` (the name as it stands there,
without title, attached letters or punctuation), `person` (a key of the labeller's own,
the same for every mention of one person in the document; `-` for a name that is not
counted) and `kind` (`private`, `public` or `not_counted`).

## What it does not do

It changes nothing under `ploni/` and decides nothing. Its output is a findings note in
`docs/findings/`.
