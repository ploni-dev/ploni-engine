# Third party

Everything shipped, executed or relied on, with its source, version and license. `scripts/download_models.py` regenerates the model rows; the rest is maintained by hand.

The fast suite fails if a model present in `models/` is absent from this file (`tests/t0_contract/test_third_party.py`; `build-plan.md` Phase 0 gate). It bites on the machine that holds the models: `models/` is not in git, so on GitHub the check has nothing to look at, and the gate's words "CI fails" are not met there.

## Models

| Model | Revision | License | License source | Used by | Shipped |
|---|---|---|---|---|---|
| `dicta-il/dictabert-joint` | `7b1256fc0846e22d1af431eae299e2dcecee2778` | CC BY 4.0 | `license: cc-by-4.0` in the front matter of `README.md` at that revision | `experiments/e1_hebrew_recall/`, `experiments/e3_prefix_replacement/`, `experiments/e2_int8_latency/`, `experiments/e4_planted_names/`, `experiments/e5_methods/` and `experiments/e6_real_documents/` only | no |
| `CordwainerSmith/GolemPII-v2-small` | `fbaf0f7a9092c50c9ecc27e3d33ba1352ac40883` | MIT | `license: mit` in the front matter of `README.md` at that revision, and its `LICENSE` file | `experiments/e5_methods/` and `experiments/e6_real_documents/` only | no |
| `dicta-il/dictabert-large-ner` | `ac70130828d5a6811c2dc451e2255424c96f0eb0` | CC BY 4.0 | `license: cc-by-4.0` in the front matter of `README.md` at that revision | `experiments/e5_methods/` and `experiments/e6_real_documents/` only | no |
| `shoresh-labs/seter-pii-he-ar-fast` | `2744c393718de9a911d9db3478341984a99a7cdb` | MIT | `license: mit` in the front matter of `README.md` at that revision | `experiments/e5_methods/` and `experiments/e6_real_documents/` only | no |

The first row is written by hand: `scripts/download_e1_model.py` fetches the model for experiment E1 (`build-plan.md` section 11) before the Phase 0 `scripts/download_models.py` exists. The model ships Python that runs under `trust_remote_code`; it was read at this revision before first use and is loaded from the local copy only. For the experiment that Python is vendored, byte for byte, in `experiments/e1_hebrew_recall/vendored/dictabert_joint/` with a notice and pinned hashes, and loaded from there without `trust_remote_code`. Vendoring into the product is Phase 3.

The weights at that revision: `model.safetensors`, 744,080,096 bytes, SHA-256 `c59db02c002b69fd3c072c310e3ba578d036386477248d1c8576d896cc06aa1c`. That is the hash the hub records for the file at the pinned commit, and on 2026-11-12 the downloaded file on Achia's laptop had the same hash. `run_model.py` writes the hash of the file it loaded into `run_meta.json`, so a run can be checked against this line.

The three rows below the first are the candidates of experiment E5 (`experiments/e5_methods/PREREGISTRATION.md`) that are on the laptop, fetched on 2026-11-17 by `scripts/download_e5_models.py`, which pins each commit and refuses weights whose SHA-256 is not the one the hub records for it: `GolemPII-v2-small` `model.safetensors` 501,697,020 bytes, `e94e31a5bbe17c4fbfbd12ef5ffef2ea16209f03975ce8e1bac876e3660f8c47`; `dictabert-large-ner` `model.safetensors` 1,735,796,812 bytes, `763e556ec1c0dd676f48c9b306aec90bb11322f682f0c3d0de9574c01ba10272`; `seter-pii-he-ar-fast` `model.safetensors` 1,230,169,116 bytes, `803221b925bc4e7e4be590e08ea9795ef9104585cbbadbfd6078457801b06fe0`. Each downloaded file had the recorded hash. None needs code of its own to load: no Python file is fetched, and no pickle of the weights. They are for experiments only (E5, and E6 on his yes of 2026-11-18) and are not shipped.

The same script fetched the given-name tables of `alumag/hebrew-names` (GitHub, commit `e9055afea4c4bd0bb8d55102d543ee106f26041c`): ten data files, each checked against its git blob id, for the `list` step of E5. Its licence: `LICENSE.txt` at that commit is the MIT licence text, read through the GitHub API on 2026-11-17, with a copyright line of the project's author and one of the author of the project it is based on; GitHub's own licence field for the repository says "Other". The script lists the licence file too since `6eec6ee`, but nothing was fetched after that, so the file itself is not on the laptop. Data, not code: the project's Python is not fetched. Not shipped.

**On whose word they were fetched.** `build-plan.md` section 11 says "Every model needs his yes before it is downloaded". The three models and the list of names were fetched on Claude's reading of Achia's message of 2026-11-17 ("run a series of experiments to see who are the winners", "dont stop to ask questions"). The independent review of PR #92 found that this is a fair reading and is not his decision. He was asked afterwards, in chat on 2026-11-17: "I took your message as a yes to download three models (GolemPII small 0.5 GB, MIT; DictaBERT large NER 1.7 GB, CC BY 4.0; Seter fast 1.2 GB, MIT) and one public list of first names, for this experiment only. Is it a yes?" He answered: "Yes". That yes came after the download, not before it, and covers these three models and this list for the experiment only. Nothing more was fetched after that finding: `shoresh-labs/seter-pii-he-ar` (commit `280425059728cd9bba14a4c3c0cd1f57c5278c00`, MIT, 2.2 GB) and the 8-bit ONNX file of `seter-pii-he-ar-fast` are pinned in the script and are not on the laptop.

**Their use in E6.** His yes of 2026-11-17 was for E5 only. Experiment E6 (`experiments/e6_real_documents/`) ran the same three models on real court decisions on Claude's reading, which its pre-registration marks as one; nothing was downloaded for it. On 2026-11-18, after the runs, he was asked through the session's question dialog: "The real-document test is finished. Besides your planned model, it also ran the three extra models from the last experiment (GolemPII small, DictaBERT large, Seter fast). They were already on the laptop; nothing was downloaded. Your yes on 2026-11-17 was for that experiment only. Is it a yes for the real-document test too?" Of "Yes, for this test too (Recommended)" and "No, take them out" he chose the first, described to him as: "Their numbers stay in the report, for experiments only. Nothing goes into the product. It lets you compare your planned model with GolemPII on real documents." The other option was described as: "I remove every number that rests on those three models from the report. The main result, for your planned model with the carry step, does not depend on them and stays." That yes came after the runs, not before them, and covers these three models in E6, for experiments only. It does not cover another experiment or any use in the product.

Phase 3 adds `dicta-il/dictabert-joint` (CC BY 4.0) to the product and Phase 4 adds `fastino/gliner2-base-v1` (Apache 2.0), each pinned by commit hash.

`experiments/e2_int8_latency/export.py` derives two ONNX files from that model, the encoder and NER head in FP32 and in dynamic INT8. They are written under `models/`, which is not in the repository, carry the same CC BY 4.0 license, and are not shipped. On the laptop they are in `models/e2_onnx/` (written 2026-11-11) and `models/e2_onnx_run3/` (2026-11-12): `ner_fp32.onnx`, 735,322,572 bytes, SHA-256 `e686ac235181498b9bef5c3f660db18e42c0120dc21e0a5cead5950c4151d760`, and `ner_int8.onnx`, 184,958,516 bytes, SHA-256 `b12eaf9283bbc40ae7473461a93e4b8872b44478503af9ad51e7fb0922b83b05`, the same two files in both folders (measured 2026-11-19).

Python packages for the experiments are pinned in `experiments/e1_hebrew_recall/requirements.txt` and, with the ONNX packages added, in `experiments/e2_int8_latency/requirements.txt`. None is shipped. Licenses of the direct ones, as declared in their installed metadata: torch 2.15.0 (Apache-2.0 and BSD-family, per its SPDX expression), transformers 5.22.2 (Apache 2.0), huggingface_hub 2.4.0 (Apache-2.0), python-docx 1.2.0 (MIT), pytest 9.2.0 (MIT), onnx 1.23.2 (Apache-2.0), onnxruntime 1.31.1 (MIT).

Two licensing traps, recorded here because they are easy to walk into:

- GLiNER v0 and v1 checkpoints (`gliner_base`, `gliner_multi`, the small/medium/large v1 line) are CC-BY-NC-4.0 and cannot ship in a commercial product. Only the v2.1 generation and the PII models are Apache 2.0. Check every checkpoint individually, community ONNX re-exports included.
- PyMuPDF is AGPL and is banned from product code entirely.

## Development tooling that shapes the shipped code

| Tool | Source | Version | License | Status |
|---|---|---|---|---|
| Ponytail | GitHub `DietrichGebert/ponytail`, four skills vendored under `.claude/skills/` | 5.3.3, commit `7801d061243d7b753bad0e0b3c057cd250b11755` (tag `v5.3.3`) | MIT, `.claude/skills/ponytail/LICENSE`, copied from that commit | **Vendored and pinned. See below.** |
| Modern Web Guidance | GitHub `GoogleChrome/modern-web-guidance`, the 209 guides of `skills/modern-web-guidance/guides/` vendored under `.claude/skills/modern-web-guidance/guides/` | commit `4dd968349e54ca45a05dd5c818fb035c9054b022` of 2026-11-10 (tag `v1.0.0`, skill version `2026_11_09-5bcc021b`, plugin version 1.0.0) | Guides CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), software Apache 2.0, per the "License" section of `README.md` at that commit; `.claude/skills/modern-web-guidance/LICENSE` is the Apache text, copied from that commit | **Guides vendored and pinned; the source's program is not used. See below.** |

### Ponytail, vendored at a pinned commit as of 2026-11-11

`CLAUDE.md` requires every session that writes code to invoke the ponytail skill before writing any, and `PROCESS.md` section 7.1 makes it a merge condition. It is used as a skill invoked by name, which is what the vendored copy is.

What is in the repository, each file identical to upstream at the commit above (git blob id, the same on both sides):

| File | Blob id |
|---|---|
| `.claude/skills/ponytail/SKILL.md` | `d64edd32265ba21cbf5270158f04e97d96925f27` |
| `.claude/skills/ponytail-review/SKILL.md` | `a50e3ac6ded6fccc9edae34ce37877bbce11e3fa` |
| `.claude/skills/ponytail-audit/SKILL.md` | `ff9a95480700600fe2664d2d0906a4d750b2da0b` |
| `.claude/skills/ponytail-debt/SKILL.md` | `3124f520a65d2a4fa75a2f5db6225c38ebdb8620` |
| `.claude/skills/ponytail/LICENSE` | `715d483338cea4365f0d91a27799cf61226d6bcf` |

To check a file, compare `git rev-parse HEAD:<file>` here with `git rev-parse 7801d061:skills/<name>/SKILL.md` in a clone of the source.

The `ponytail` skill takes a level as its argument: `lite`, `full` (its default) or `ultra`. That answers `PROCESS.md` section 13 item 2; this project uses `ultra`, decided by Achia on 2026-11-15 and written in `CLAUDE.md`.

Why vendored files and not the Claude Code plugin the same repository offers:

- A plugin marketplace declared in `.claude/settings.json` can be pinned to a branch or a tag, not to a commit (`ref` is "Branch or tag", https://code.claude.com/docs/en/plugins/marketplace-reference.md#marketplace-sources). A tag can be moved, so it does not meet the pin-by-commit rule.
- A cloud session does not install plugins a repository declares, and does load `.claude/skills/` because it is part of the clone (https://code.claude.com/docs/en/cloud-environments.md#what-carries-over-from-your-setup).

What was left out, on purpose:

- `ponytail-help` and `ponytail-gain`: a reference card for the plugin's own commands and a benchmark scoreboard. Neither is used by `PROCESS.md` section 7.1.
- Every hook. At 5.3.3 the plugin's hooks switch the mode on at session start, inject the rules into subagents, and run a "band" that after every turn writes a row per task to `~/.config/ponytail/band/<project>.csv`, including the session title or the first 60 characters of the first prompt, and can post that row to a webhook (`hooks/band/register.tsx` lines 155 to 181 and 245 to 249 at that commit). None of that is installed here.

What follows from having no hooks:

- Nothing activates on its own. A session invokes the skill by name, as section 7.1 already says.
- A subagent does not get the rules unless the session that spawns it passes them on.

Known limits:

- A cloud thread inside a Claude project does not load a repository's `.claude/skills/` (https://code.claude.com/docs/en/skills.md). A session there still says so in the PR body rather than skipping the review silently or claiming it ran.
- Until 2026-11-11 Achia's laptop had the plugin at 4.7.0 (commit `45f7d2f83fb430a65fd512a98ad7b14d79e06636`), enabled for another project and briefly for this one. It is disabled for this project so that one version applies.

Updating is a PR of its own: replace the files from a newer commit, read the diff of the rules, and update the commit and blob ids here.

### Modern Web Guidance, guides vendored at a pinned commit as of 2026-11-15

Achia asked on 2026-11-15 for this to be a guideline for the project's code, "like ponytail". It is guidance for HTML, CSS and browser JavaScript, so it applies to web code only: `CLAUDE.md`, "Web code". It does not apply to Python.

What is in the repository:

| Path here | What | Check |
|---|---|---|
| `.claude/skills/modern-web-guidance/guides/` | 209 Markdown files in 17 folders, each identical to the source at the commit above | git tree id `19d5b8598e4af3f3da0b94d110ffe3e464b93d05`, the same on both sides |
| `.claude/skills/modern-web-guidance/LICENSE` | The source's `LICENSE` (Apache 2.0) | git blob id `d645695673349e3947e8e5ae42332d0ac3164cd7`, the same on both sides |
| `.claude/skills/modern-web-guidance/SKILL.md` | Written for this project. Not the source's file | none; it is ours |

To check the guides, compare `git rev-parse HEAD:.claude/skills/modern-web-guidance/guides` here with `git rev-parse 4dd96834:skills/modern-web-guidance/guides` in a clone of the source. One id covers all 209 files.

Why the guides are vendored and the source's way of working is not used:

- The source's `SKILL.md` (blob `fdab1a72680427bcbe179c1b4bc344c6621ef001` at that commit) tells the agent to run `npx -y modern-web-guidance@latest` for every search. `@latest` is not a pin: npm is asked for the newest version on every run. That does not meet the pin rule of `CLAUDE.md`.
- That program is not in the source repository. `package.json` names it as `skills/modern-web-guidance/modern-web.mjs`, and no such file is in the tree at that commit. It is built from another repository, `GoogleChrome/modern-web-guidance-src`, which the README links. So the pinned commit does not cover the program, and the file npm serves was not read.
- The source's `README.md`, "Telemetry & Privacy", says the program reports to Google the name of the calling agent, the ids of the guides retrieved and the search words the agent wrote, unless `DISABLE_TELEMETRY=1` is set. A search word written by an agent can say what the project is.
- A file under `.claude/skills/` is part of the clone, so every session has it, with no network.

What was left out, on purpose:

- The source's `SKILL.md` and its program, for the reasons above. The project's `SKILL.md` says how to find and read a guide with the tools a session already has.
- The `chrome-extensions` skill of the same repository. Ploni is not a browser extension.
- The plugin files for the various agents, and the source's `README.md`.

Known limits:

- The source's program finds guides by meaning. Here a guide is found by its file name and by searching the text, which can miss a guide whose name does not say what it is about.
- The source's program holds back guides for features in an Origin Trial and for features one browser engine shipped in the last three months or that are still stabilizing, until the developer agrees (`README.md`, "Safe Adoption of Modern Features"). The guide files carry no mark for that, so here nothing holds them back. The project's `SKILL.md` sets a rule in words, and it is stricter than the source: a feature that only one engine has is not used, with or without a fallback, until the browser for the Phase 12 screens is decided. That strictness is Claude's choice, for Achia to change.
- The source's program has a `legacy-scan` command that searches a codebase for old patterns (source `SKILL.md`, "Alternative flow"). It is part of the program, so it is not used. Existing web code is reviewed by reading it against the guides (project `SKILL.md`, section 4).
- The guides are written for websites on the open internet. Some name a CDN (`unpkg.com`, `esm.sh`, `cdn.jsdelivr.net`, `esm.run`) or ask for `npm install`, and some are about sending data out. `CLAUDE.md` and the project's `SKILL.md` say none of that is used here. That is a rule in words, not a check; the no-network test of Phase 0 covers `ploni/` and not yet a `ui/` folder.
- The guides were not read in full before vendoring. They were searched for commands, for the hosts they name and for text aimed at an agent: 198 pointers to `npx -y modern-web-guidance@latest retrieve`, 16 lines with `npm install` in 13 files, and the four CDN hosts above. Examples in the guides also name `img.youtube.com`, `www.youtube-nocookie.com`, `x.com` and `raw.githubusercontent.com`. The guides are written to an agent. No instruction to do anything other than write web code was found, other than those commands.
- Code copied from a guide into the product carries the CC BY 4.0 attribution. No such code exists yet.

Updating is a PR of its own: replace `guides/` from a newer commit, and update the commit and the tree id here.

## Tools of the fast suite

None is shipped. They come from PyPI, pip's default index. They run on the laptop and in the GitHub workflow, and once the workflow is on `main`, a PR merges only when their run on its last commit is green (`CLAUDE.md`, Merging). Each is pinned to one version in `requirements-dev.txt`, with the SHA-256 of its Windows and of its Linux wheel for CPython 3.13, and is installed with `pip install --require-hashes`, which refuses any other file. `requirements-dev.txt` and the workflow come with the PR of issues #17 and #22.

Where they come from: Achia asked on 2026-11-15 for tests on every merge, "like a pytest and jenkins (but whatever fits here)". ruff and mypy are named in `PROCESS.md` section 4.5.

| Package | Version | License, as the package declares it | Why it is there |
|---|---|---|---|
| pytest | 9.2.0 | MIT | named by Achia: runs the tests |
| ruff | 0.17.5 | MIT | named in `PROCESS.md` section 4.5: the linter |
| mypy | 2.4.1 | MIT | named in `PROCESS.md` section 4.5: the type check |
| ast-serialize | 0.13.1 | MIT | needed by mypy |
| librt | 0.16.0 | MIT | needed by mypy |
| mypy-extensions | 1.2.0 | MIT | needed by mypy |
| pathspec | 1.1.1 | MPL 2.0 | needed by mypy |
| typing-extensions | 4.16.0 | PSF-2.0 | needed by mypy |
| colorama | 0.4.6 | BSD | needed by pytest, on Windows only |
| iniconfig | 2.3.1 | MIT | needed by pytest |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | needed by pytest |
| pluggy | 1.7.0 | MIT | needed by pytest |
| pygments | 2.21.0 | BSD-2-Clause | needed by pytest |

None declares GPL or AGPL. pathspec declares MPL 2.0; it is used as published and is not shipped.

The workflow uses two GitHub actions, each pinned by commit:

| Action | Version | Commit | License |
|---|---|---|---|
| `actions/checkout` | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | MIT |
| `actions/setup-python` | v7.1.0 | `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` | MIT |

Known limits:

- The licenses are what each package declares in its installed metadata, read on 2026-11-16 (for colorama and pathspec a classifier, for pluggy the `License` field, for the other ten `License-Expression`), and what GitHub reports for the two action repositories. No license text was read.
- The workflow runs on GitHub's `ubuntu-24.04` image. That is a name, not a pin: GitHub changes what the image holds.
- `actions/setup-python` installs Python 3.13.5 and pip. In the run of 2026-11-16 it first upgraded to the newest pip (26.3) and used that once to install the pinned pip 25.1.1; the twelve packages above that Linux needs were then installed by 25.1.1 with hash checking. Nothing in the workflow asks for that upgrade; the install script inside the Python download does it, and the action runs that script.
- Python and pip are not in the hashed set. `actions/setup-python` downloads Python 3.13.5 at run time from the repository `actions/python-versions`, found by version through a list on that repository's `main` branch; the log shows no hash check. pip 25.1.1 comes from PyPI by version, and the newest pip (26.3 in that run) with no version at all; neither with a hash. So the tool that checks the hashes is itself not hashed.
- The two actions run their own code, with what they bundle, at the pinned commit. That code was not read.
