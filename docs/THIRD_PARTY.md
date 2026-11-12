# Third party

Everything shipped, executed or relied on, with its source, version and license. `scripts/download_models.py` regenerates the model rows; the rest is maintained by hand.

CI fails if a model present in `models/` is absent from this file (`build-plan.md` Phase 0 gate).

## Models

| Model | Revision | License | License source | Used by | Shipped |
|---|---|---|---|---|---|
| `dicta-il/dictabert-joint` | `7b1256fc0846e22d1af431eae299e2dcecee2778` | CC BY 4.0 | `license: cc-by-4.0` in the front matter of `README.md` at that revision | `experiments/e1_hebrew_recall/`, `experiments/e3_prefix_replacement/` and `experiments/e2_int8_latency/` only | no |

That row is written by hand: `scripts/download_e1_model.py` fetches the model for experiment E1 (`build-plan.md` section 11) before the Phase 0 `scripts/download_models.py` exists. The model ships Python that runs under `trust_remote_code`; it was read at this revision before first use and is loaded from the local copy only. For the experiment that Python is vendored, byte for byte, in `experiments/e1_hebrew_recall/vendored/dictabert_joint/` with a notice and pinned hashes, and loaded from there without `trust_remote_code`. Vendoring into the product is Phase 3.

The weights at that revision: `model.safetensors`, 744,080,096 bytes, SHA-256 `c59db02c002b69fd3c072c310e3ba578d036386477248d1c8576d896cc06aa1c`. That is the hash the hub records for the file at the pinned commit, and on 2026-11-12 the downloaded file on Achia's laptop had the same hash. `run_model.py` writes the hash of the file it loaded into `run_meta.json`, so a run can be checked against this line.

Phase 3 adds `dicta-il/dictabert-joint` (CC BY 4.0) to the product and Phase 4 adds `fastino/gliner2-base-v1` (Apache 2.0), each pinned by commit hash.

`experiments/e2_int8_latency/export.py` derives two ONNX files from that model, the encoder and NER head in FP32 and in dynamic INT8. They are written under `models/`, which is not in the repository, carry the same CC BY 4.0 license, and are not shipped.

Python packages for the experiments are pinned in `experiments/e1_hebrew_recall/requirements.txt` and, with the ONNX packages added, in `experiments/e2_int8_latency/requirements.txt`. None is shipped. Licenses of the direct ones, as declared in their installed metadata: torch 2.15.0 (Apache-2.0 and BSD-family, per its SPDX expression), transformers 5.22.2 (Apache 2.0), huggingface_hub 2.4.0 (Apache-2.0), python-docx 1.2.0 (MIT), pytest 9.2.0 (MIT), onnx 1.23.2 (Apache-2.0), onnxruntime 1.31.1 (MIT).

Two licensing traps, recorded here because they are easy to walk into:

- GLiNER v0 and v1 checkpoints (`gliner_base`, `gliner_multi`, the small/medium/large v1 line) are CC-BY-NC-4.0 and cannot ship in a commercial product. Only the v2.1 generation and the PII models are Apache 2.0. Check every checkpoint individually, community ONNX re-exports included.
- PyMuPDF is AGPL and is banned from product code entirely.

## Development tooling that shapes the shipped code

| Tool | Source | Version | License | Status |
|---|---|---|---|---|
| Ponytail | GitHub `DietrichGebert/ponytail`, four skills vendored under `.claude/skills/` | 5.3.3, commit `7801d061243d7b753bad0e0b3c057cd250b11755` (tag `v5.3.3`) | MIT, `.claude/skills/ponytail/LICENSE`, copied from that commit | **Vendored and pinned. See below.** |

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

The `ponytail` skill takes a level as its argument: `lite`, `full` (its default) or `ultra`. That answers `PROCESS.md` section 13 item 2; which level this project uses is still Achia's to write into `CLAUDE.md`.

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
