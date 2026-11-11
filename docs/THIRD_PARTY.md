# Third party

Everything shipped, executed or relied on, with its source, version and license. `scripts/download_models.py` regenerates the model rows; the rest is maintained by hand.

CI fails if a model present in `models/` is absent from this file (`build-plan.md` Phase 0 gate).

## Models

None yet. Phase 3 adds `dicta-il/dictabert-joint` (CC BY 4.0) and Phase 4 adds `fastino/gliner2-base-v1` (Apache 2.0), each pinned by commit hash.

Two licensing traps, recorded here because they are easy to walk into:

- GLiNER v0 and v1 checkpoints (`gliner_base`, `gliner_multi`, the small/medium/large v1 line) are CC-BY-NC-4.0 and cannot ship in a commercial product. Only the v2.1 generation and the PII models are Apache 2.0. Check every checkpoint individually, community ONNX re-exports included.
- PyMuPDF is AGPL and is banned from product code entirely.

## Development tooling that shapes the shipped code

| Tool | Source | Version | License | Status |
|---|---|---|---|---|
| Ponytail | GitHub `DietrichGebert/ponytail`, installed as the Claude Code plugin `ponytail@ponytail` | 4.7.0, commit `45f7d2f83fb430a65fd512a98ad7b14d79e06636` | MIT, read from the `LICENSE` file of the installed copy | **Available on Achia's laptop. Not available to cloud sessions. See below.** |

### Ponytail, resolved locally and open for cloud sessions as of 2026-11-11

`CLAUDE.md` requires every session that writes code to invoke the ponytail skill before writing any, and `PROCESS.md` section 7.1 makes it a merge condition.

What is installed, read from the copy on Achia's laptop:

- Five skills: `ponytail`, `ponytail-review`, `ponytail-audit`, `ponytail-debt`, `ponytail-help`. The `ponytail` skill has three intensity levels, `lite`, `full` (its default) and `ultra`. That answers `PROCESS.md` section 13 item 2; which level this project uses is still Achia's to write into `CLAUDE.md`.
- Two hooks, on session start and on every prompt, each running a Node script from the plugin.

Where it is enabled: for this project on Achia's laptop, through `.claude/settings.local.json`, which is not in the repository. Until 2026-11-11 it was enabled for a different project only, which is why earlier sessions here did not have it. A session already running when it was enabled has to reload plugins or restart before the skill appears.

What is still open:

- **Cloud sessions do not get it.** A local settings file does not travel with the repository.
- **The version is not pinned.** The marketplace entry names the GitHub repository without a commit, so a plugin update changes what shapes the code. The version and commit above are what was installed on 2026-11-11, not a guarantee.

A session that cannot invoke the skill says so in the PR body rather than skipping it silently or claiming it ran. Closing the cloud gap means one of: enabling the plugin in a checked-in `.claude/settings.json` so every session of this repository loads it, vendoring the skills into this repo with their license and commit, or a PR against `CLAUDE.md` and `PROCESS.md` dropping the requirement. The third is a real option; what is not an option is leaving a rule in place that sessions cannot follow.
