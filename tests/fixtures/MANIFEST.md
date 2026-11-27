# Fixtures manifest

Every file under `tests/fixtures/` has a row here: its path from this folder, in backquotes, and where it came from (`build-plan.md` section 7, principle 4). `tests/t0_contract/test_fixtures_manifest.py` fails on a file with no row, or with an empty provenance.

Rules:

- No real client documents, in any form (`CLAUDE.md`, Hard constraints; `PROCESS.md` section 2). A fixture is invented, or written for this project.
- Real public documents, such as the court decisions of the experiments, stay outside the repository (`build-plan.md` section 7, "The held-out batch"). They are never a fixture.
- A fixture is never removed or made to ask less without Achia's decision (`CLAUDE.md`, Merging).

| Path | Provenance | Added in |
|---|---|---|
| `detect/il_id.json` | Invented for this project: Hebrew sentences written by hand, with a slot for each number; `tests/invented_numbers.py` fills the slots when the tests run, with numbers made from a fixed seed (its `SEED`, 32) by the checksum of `build-plan.md` Phase 1 (valid ones, near misses with another check digit, company, non-profit, landline and case-number shapes), so that no number that passes the checksum is stored (Achia, 2026-11-27, issue #32, "Make them fresh too (Recommended)"); the trivial sequences the detector refuses (such as `000000000`) are written as they are; no real document | issue #32 |
| `detect/company_number.json` | Invented for this project: Hebrew sentences written by hand, with a slot for each number and the type each found slot must get; `tests/invented_numbers.py` fills the slots when the tests run, with numbers made from a fixed seed (its `SEED`, 32) by the checksum of `build-plan.md` Phase 1 (company numbers 51 to 54, non-profit numbers 58, IDs, near misses written by a slot's shape), so that no number that passes the checksum is stored (Achia, 2026-11-27, issue #32, "Make them fresh too (Recommended)"); the literals it holds fail the checksum (`555555555`, `512345678`) or are no nine-digit number; no real document | issue #33 |
