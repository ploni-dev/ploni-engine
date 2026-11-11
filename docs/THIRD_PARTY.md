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
| Ponytail | not recorded | not recorded | MIT per its own docs, unverified | **Unresolved. See below.** |

### Ponytail, unresolved as of 2026-11-11

`CLAUDE.md` requires every session that writes code to invoke the ponytail skill before writing any, and `PROCESS.md` section 7.1 makes it a merge condition. As of today that requirement cannot be met in a cloud session:

- It is not among the account's enabled skills.
- Nothing matching it is in the plugin catalog.
- Achia has a copy he uses locally. Its exact source, version and whether it exposes intensity modes are not recorded, which `PROCESS.md` section 13 items 2 and 3 already list as open.

Until that is resolved, a session that cannot invoke it says so in the PR body rather than skipping it silently or claiming it ran. Resolving it means one of: publishing the local copy as an account-level skill so cloud sessions get it, vendoring it into this repo with its license and commit, or a PR against `CLAUDE.md` and `PROCESS.md` dropping the requirement. The third is a real option; what is not an option is leaving a rule in place that sessions cannot follow.
