# E5: which way of finding names misses fewest

Not product code. Read `PREREGISTRATION.md` first: it says what is compared, on which text,
how it is scored and what was predicted, and it was committed before anything was run.

## What is here

| File | What it does |
|---|---|
| `PREREGISTRATION.md` | the plan of the experiment, with the predictions |
| `templates_select/`, `names_select.tsv` | the second corpus on which methods are chosen (the first is E4's) |
| `templates_heldout/`, `names_heldout.tsv` | the corpus on which the chosen methods are judged, once |
| `data.py` | generates the three corpora with E4's generator |
| `detect.py` | runs one model over one corpus and writes what it marked, with time and memory |
| `layers.py` | the steps that are no model: group words, titles, carrying a name through the document, a list |
| `evaluate.py` | scores every method from the files `detect.py` wrote; loads no model |
| `build_banks.py` | wrote the two name banks; kept so that they can be written again |
| `tests/` | the tests of all of the above |

Everything in the templates and the name banks is invented. No sentence and no name is taken
from a real document.

## How it is run

In the environment of `experiments/e2_int8_latency/requirements.txt`, offline, from this
folder. `<models>` is the `models/` folder of the repository, `<runs>` a folder outside it.

```
python ../../scripts/download_e5_models.py golem          # the only step that uses the network
python -I detect.py --detector joint --model-dir <models>/dictabert-joint/<revision> --dataset select --out <runs>/joint.select.json
python -I detect.py --detector hf --model-dir <models>/golem/<revision> --dataset select --out <runs>/golem.select.json
python -I detect.py --detector onnx --model-dir <models>/seter_fast_int8/<revision> --onnx-file <models>/seter_fast_int8/<revision>/onnx/model_quantized.onnx --dataset select --out <runs>/seter_fast_int8.select.json
python -I evaluate.py --runs-dir <runs> --datasets e4 select --record results/record.jsonl
python -I evaluate.py --runs-dir <runs> --datasets heldout --only "joint + whole words" ...
python -m pytest
```

On a machine with little memory free, add `--budget-seconds 420` to a `detect.py` command and give the
same command again until it says that every document is done: the run is then made in parts,
and no command is longer than a few minutes.

The name of a detector in the tables is the first part of its file's name. `results/` holds
what the runs printed and one line per method and corpus in `record.jsonl`, in the form the
analytics record of `build-plan.md` section 7 asks of an experiment.

## What it does not do

It changes nothing under `ploni/` and decides nothing: the output is
`docs/findings/2026-11-17-e5-methods.md`.
