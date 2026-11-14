# experiments/

The week-one experiments from `build-plan.md` section 11. Not product code: nothing here is
imported by `ploni/`, and this directory is outside the layering test and coverage
(`PROCESS.md` section 13, item 5). The output of an experiment is a findings note in
`docs/findings/`, not a module.

What still applies here, because it is about the documents and the numbers and not about
product code:

- Real documents and anything derived from them stay outside the repository. Each harness
  refuses a corpus or output directory inside it.
- Document text and file names never go to stdout. Documents are `doc01`, `doc02`, and so on.
- Downloads live in `scripts/`. The experiment itself runs offline.
- Every dependency and every model revision is pinned.
- The prediction and the threshold are committed before the run.

| Experiment | Directory | Status |
|---|---|---|
| E1 baseline Hebrew NER recall | `e1_hebrew_recall/` | run on 2026-11-13; `docs/findings/2026-11-13-e1-hebrew-recall.md` |
| E2 CPU latency after INT8 | `e2_int8_latency/` | harness and pre-registration committed; `export.py`, then `measure.py` |
| E3 prefix-preserving replacement | `e3_prefix_replacement/` | harness and pre-registration committed; `python -I run.py --model-dir <model dir>`, in the environment of `e1_hebrew_recall/requirements.txt` |
| E4 PERSON recall against planted names | `e4_planted_names/` | not in the plan; Achia asked for it on 2026-11-14. Harness and pre-registration committed; `python -I run.py --model-dir <model dir>`, in the same environment. Every sentence and name in it is generated, so its text is in the repository |
