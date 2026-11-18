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
| E4 PERSON recall against planted names | `e4_planted_names/` | not in the plan; Achia asked for it on 2026-11-14. Run on 2026-11-14 in three parts; `docs/findings/2026-11-14-e4-planted-names.md`. The model: `python -I run.py --model-dir <model dir> --list-errors --worksheets-dir <folder outside the repository>`, in the same environment; `--all-documents` writes the span list of every document. A reader's count against the planted names: `python -I reader_check.py --folder <folder>`. The readers' list of hints against the planted names: `python -I list_check.py --folder <folder>`. Every sentence and name in it is generated, so its text is in the repository |
| E5 which way of finding names misses fewest | `e5_methods/` | the first of the experiment series Achia decided on 2026-11-16 (`build-plan.md` section 11). Run on 2026-11-17; `docs/findings/2026-11-17-e5-methods.md`, with the printed tables in `e5_methods/results/`. `detect.py` once per model and corpus, then `evaluate.py`, see its `README.md`. The candidate models are fetched by `scripts/download_e5_models.py`. Every sentence and name in it is generated, so its text is in the repository |
| E6 does what E5 found hold on real documents | `e6_real_documents/` | the real-document test Achia put first on 2026-11-18 (`docs/findings/2026-11-17-e5-methods.md`, `## Decision`). Run on 2026-11-18; `docs/findings/2026-11-18-e6-real-documents.md`, with the printed tables in `e6_real_documents/results/`. Twenty decisions of the Supreme Court in two piles, an answer key made by readers and frozen before any run, E5's methods scored by E5's own code; see its `README.md`. The documents and every file with their text are outside the repository |
