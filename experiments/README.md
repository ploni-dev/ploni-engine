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
| E1 baseline Hebrew NER recall | `e1_hebrew_recall/` | harness ready, run pending |
| E2 CPU latency after INT8 | not started | |
| E3 prefix-preserving replacement | not started | |
