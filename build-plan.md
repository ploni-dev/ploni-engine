# Build Plan v3.0: Local Hebrew-First Document Pseudonymization Tool

Product name: **Ploni** (פלוני). Python package and CLI: `ploni`. Repo: `ploni-engine`. Decided 2026-11-11; trademark check still open with Tomer.
Achia owns engineering. Tomer (lawyer) owns everything legal and regulatory.
Implementer: Claude Code, phase by phase.
Date: 2026-11-01. Supersedes v2.0. Changelog in section 30.

---

## PART I: FRAMING

## 0. Rules of engagement for Claude Code

1. **Engine before UI.** Phases 1 to 10 produce a library plus CLI. No UI code before Phase 12.
2. **A phase is not done until its own gate passes.** Each phase in Part IV lists an explicit gate with numbers. Do not advance on "it looks right".
3. **Never weaken a test to pass a gate.** If a gate cannot be met, stop and report the measured number. The plan changes, not the test.
4. **No network in product code.** Model downloads happen once in `scripts/`. `eval/` may use the network and must never be importable from `ploni/`. Both enforced by tests.
5. **No fabricated numbers.** Where this plan predicts a measurement, it states a disagreement threshold. Measure, print, report. Do not tune until the prediction matches.
6. **Pin everything.** Dependency versions, model revisions by commit hash, thread counts in tests.
7. **English code and logs, Hebrew-first UI through i18n from the first UI commit.**
8. **Document text never reaches a log file or a temp file.** Section 24.
9. **Every commit runs the fast suite. Every phase boundary runs the full suite including metric gates.**

---

## 1. Product definition

An offline Windows desktop application that lets a professional use cloud AI tools on a sensitive document.

**Three jobs:**

**A. Pseudonymize.** Detect identifying information in a document, replace it with consistent realistic surrogates, write out the same format. Output is safe to upload or paste into ChatGPT, Claude or anything else.

**B. Show the user what happened, and make them act on it.** Mandatory review before export: every entity, its occurrences, its replacement, everything uncertain, everything still identifying after replacement. Export is blocked until every open item is explicitly resolved. A per-file report records all of it.

**C. Restore.** Two directions: turn the safe document back into the original, and take the AI's answer about surrogates and give it back with real names, including Hebrew inflected forms.

Primary language Hebrew, including mixed Hebrew/English. Primary user: an Israeli lawyer, accountant or clinician working in Word.

**v1 non-goals:** no anonymity guarantee, no OCR (text inside images is not analyzed and the product says so per document), no layout-preserving PDF output, no cloud, no telemetry, no licensing.

### Where the legal side touches engineering

Tomer owns consent, privilege, professional duties, and all external-facing claims. Four engineering requirements follow from that and only these four:

1. **Claims language lives in i18n keys**, so Tomer can change wording without a code change. The product never says "anonymized", "compliant" or "safe to upload".
2. **The review gate must be substantively real**, because the product's defensibility rests on the user having genuinely reviewed. That is a UX engineering requirement (section 11).
3. **The report is evidence** and must be accurate and honest about its own limits (Phase 11).
4. **Date shifting trades clinical interval fidelity against recognized de-identification rules.** The UI states the trade-off at the point of choice. Tomer writes the words.

---

## 2. The four-hat design review

I ran the plan past four perspectives. Where they disagreed is where the plan changed.

### Software engineer

*"The riskiest component is the offset layer, and v2 had it as an implementation detail rather than an interface."*

If `TextProjection` and anchoring are wrong, every downstream phase inherits the bug and a rewrite cascades. Resolution: the format layer sits behind a `DocumentAdapter` protocol (section 4.2), is the first thing built after types, and gets property-based tests rather than only example tests. A rewrite of DOCX handling must not touch detection, resolution or writing.

*"The single most valuable test in this product is an inverse property, not an example."*

For any document, `restore(apply(analyze(d)))` must equal `d` at text level. That is a property, generated over hundreds of synthetic documents, and it catches whole classes of offset, ordering and encoding bugs that no hand-written example will find. Elevated to a first-class gate (T2, section 7).

### Architect

*"The desktop app is one consumer of the engine. Freeze the engine's public API now or the Word add-in and the gateway become rewrites."*

Resolution: a four-function public contract, frozen at Phase 10 and versioned (section 4.1). Everything else is internal.

*"Determinism is claimed but not actually achievable as specified."*

Surrogate assignment depends on the name banks. If a later release adds names, re-running the same document in the same matter produces different surrogates, silently breaking a two-year-old matter. Resolution: name banks are versioned, and the version is written into the mapping and pinned per matter. New in v3.

*"Nothing stops a user from processing an already-processed file."*

Double-processing produces surrogates of surrogates and a broken mapping chain. Resolution: an idempotency check (section 4.5). Note the honest tension: the cleanest detection is a marker in the output, but a marker reveals that the tool was used. So detection is content-based by default (mapping lookup on the document hash), with an optional marker the user can enable.

### Product designer

*"The scariest screen in the product is 'we found nothing', and v2 had no design for it."*

Zero detections means either a genuinely clean document or total failure, and the user cannot tell which. Resolution: the empty result is treated as suspicious by default. It shows what was searched for, the leftover scan results, and requires an explicit acknowledgement before export. New in v3.

*"Trust is built by showing doubt, not by hiding it."*

The uncertainty queues are not a secondary tab. They are the primary call to action on the review screen.

*"The user sometimes wants to keep a name, and v2 made rejecting harder than accepting."*

Opposing counsel's firm, a public company, a statute, a court. Keeping must be exactly as cheap as replacing: one keystroke, visible, reversible, and remembered per matter.

*"First run asks the user to trust an unknown binary with their most sensitive file. That is the wrong order."*

Resolution: the offline self-test is the **first** screen on first launch, before any file is opened. Prove the claim, then ask for the document.

### Product manager

*"The product is a three-step manual workflow and the failure mode is the user skipping a step."*

Export, upload, paste back. Resolution: time-to-safe-document becomes a measured metric with a target, clipboard export is in v1, and the demo script is an acceptance test (section 8.3).

*"Review burden is the hidden adoption killer and v2 measured it but did not bound the experience."*

A 20-page pleading must be reviewable in minutes, not an hour. Resolution: entity-level review, keyboard navigation from the first UI commit, and a persona acceptance test with a wall-clock budget (T9).

*"We will learn nothing from pilots if the product records nothing, and recording anything covertly would be fatal for a privacy tool."*

Resolution: a **local, visible, user-exportable usage log**. The user can see every line, and sharing it is a deliberate export action. This is the honest answer to wanting usage insight in an offline product: visible by design, never hidden. It also happens to be the foundation any future commercial arrangement would need, without a covert counter. New in v3.

### Where the hats still disagree, and the call

| Tension | Positions | Decision for v1 |
|---|---|---|
| Verification pass (Phase 10) | Engineer: essential, cheap. PM: adds latency and complexity to v1. | Keep it, but it runs **after** export completes and presents findings as a non-blocking follow-up, so it never delays the user's first result. Blocking behavior is a setting. |
| Confidence shown as a number | Designer: a percentage no user can interpret is noise. Engineer: it is real information. | Show three calibrated bands (high, medium, low), not a number. Store the number. |
| Marker in output file | Architect: wants it for idempotency. Designer: reveals tool use. | Off by default, content-hash detection instead, marker available as a setting. |
| OCR | PM: customers will ask immediately. Engineer: unmeasured recall risk. | Out of v1. Mandatory per-document disclosure that images were not analyzed. |

---

## PART II: ARCHITECTURE

## 3. Pipeline

```
 input document
      │
      ▼
 [1] DocumentAdapter.extract()
      → one TextProjection per part (body, headers, footnotes,
        comments, text boxes, metadata, hyperlink targets)
      → each carries exact anchors back into the source structure
      │
      ▼
 [2] Detection, per part, union of independent detectors
      2a deterministic: regex + checksum validators
      2b Hebrew: dictabert-joint (prefix seg, morph, lemma, NER)
      2c multilingual zero-shot: GLiNER2
      2d [post-v1] local LLM risk flagger
      │
      ▼
 [3] Fusion: overlap merge, window-edge resolution, calibration
      │
      ▼
 [4] Entity resolution ACROSS parts
      יעקב / ליעקב / מר כהן / j.cohen@ → one entity
      │
      ▼
 [5] Policy assignment
      surrogates (gender, script, culture, collision-free, keyed)
      numeric policy (default: keep; whitelist of eligible types)
      │
      ▼
 [6] Session: the review contract
      │
      ▼
 [7] REVIEW GATE: human, per-item, mandatory
      │
      ▼
 [8] Writer + scrubber → safe document, clipboard text
      │
      ▼
 [9] Mapping store (encrypted, versioned, per matter)
      │
      ▼
 [10] Verification pass on the exported artifact
      independent re-detection + residue scan + structural check
      │
      ▼
 [11] Report (signed, chained)

 Reverse:  AI answer → Rehydrator (morphology-aware) → real names
           safe doc  → Restorer → original document
```

## 4. Architectural decisions

### 4.1 The public API, frozen at Phase 10

Four functions. Everything else is internal and may change freely. The desktop UI, a future Word add-in, a future gateway and the CLI are all consumers of exactly this.

```python
def analyze(source: Path | bytes, *, matter: MatterRef,
            profile: str) -> Session: ...

def apply(session: Session, *, out_dir: Path) -> Artifacts: ...
    # raises NotApprovedError if any ReviewItem is unresolved

def verify(artifacts: Artifacts, *, session: Session) -> Findings: ...

def rehydrate(text: str, *, matter: MatterRef) -> Rehydrated: ...
```

`api_version` is a module constant. A contract test suite (T0) pins the signatures, the exception types and the shape of every returned object. Changing them is a deliberate, versioned act.

### 4.2 The DocumentAdapter protocol

```python
class DocumentAdapter(Protocol):
    suffixes: ClassVar[tuple[str, ...]]
    def extract(self, src: Path) -> list[TextProjection]: ...
    def write(self, src: Path, dst: Path,
              edits: list[Edit], scrub: ScrubPolicy) -> WriteReport: ...
    def inventory(self, src: Path) -> Inventory: ...
        # images, embedded objects, parts present, metadata fields
```

v1 ships `DocxAdapter` and `TxtAdapter`. XLSX, PDF and EML plug in later with zero changes above this line. The adapter conformance suite (T0) runs against every adapter, so a new format inherits the whole test battery.

### 4.3 The Detector protocol

```python
class Detector(Protocol):
    name: ClassVar[str]
    produces: ClassVar[frozenset[str]]       # entity types
    requires_morph: ClassVar[bool]
    def detect(self, proj: TextProjection,
               ctx: DetectContext) -> list[Detection]: ...
```

Fusion knows nothing about individual detectors. Adding a detector means adding a module and a fixture file, not editing fusion. A detector conformance suite (T0) asserts every detector returns in-range spans, declared types only, and confidence in `[0, 1]`.

### 4.4 Determinism contract

Output is byte-identical given the same: input bytes, matter key, model bundle version, **name bank version**, profile, and plan version. All randomness derives from `HMAC(matter_key, entity_id)`. No clock, no `os.urandom` at inference time.

The mapping file records `model_bundle_version` and `name_bank_version`, pinned per matter. A later release that changes either one must either keep the pinned versions for existing matters or require an explicit, warned migration. This is what makes a two-year-old case still produce the same surrogate for the same person.

### 4.5 Idempotency

Before analysis, hash the input and look it up across the matter's mapping store. If the hash matches a previously produced output, refuse with a clear message and offer restore instead. Content-based, so no marker is written into the user's document. An optional setting adds a custom XML marker for environments that prefer explicit tagging.

### 4.6 Process model

Inference runs in a worker process, not a thread. Reasons: real cancellation, memory isolation, a crash in the model layer does not take the UI with it, and thread-count pinning for determinism. The UI talks to the engine over a local IPC channel with streaming progress.

### 4.7 Repo layout

```
ploni/
  api.py              # the four public functions, frozen
  types.py  config.py  profiles.py  session.py  errors.py
  adapters/  base.py docx/ txt/
  detect/
    base.py  windowing.py  fusion.py  calibration.py
    deterministic/  israeli_id.py iban.py credit_card.py phone_il.py
                    email.py plate_il.py case_number_il.py company_il.py
                    gush_helka.py dates.py amounts.py triggers.py
                    placeholders.py
    hebrew_ner.py  gliner_ner.py
    vendored/dictabert/        # reviewed copy of the model's shipped code
  morph/     prefixes.py normalize.py inflect_match.py numwords_he.py
  resolve/   entity_resolution.py
  policy/    surrogates.py name_banks/ numeric.py
  mapping/   store.py crypto.py schema.py migrate.py
  write/     edits.py scrub.py
  verify/    second_pass.py residue_scan.py structural.py
  rehydrate/ document.py ai_answer.py
  report/    audit.py signing.py usage_log.py
  safety/    logging.py tempfiles.py atomic.py
  worker/    host.py protocol.py
  i18n/      he.json en.json
ui/
eval/                 # dev-only; network allowed; never imported by ploni/
  corpus/ generate.py run_eval.py baselines.json
tests/
  t0_contract/ t1_unit/ t2_property/ t3_golden/ t4_integration/
  t5_system/ t6_metrics/ t7_perf/ t8_privacy/ t9_persona/
  fixtures/  golden/
scripts/download_models.py
models/               # gitignored
docs/
```

## 5. Core types

```python
PartId = str   # "body" | "header1" | "footnotes" | "comments" | "docProps" | "textbox3"

@dataclass(frozen=True)
class Span:
    start: int
    end: int

@dataclass(frozen=True)
class Anchor:
    """Run-length entry: projection [proj_start, proj_end) lives in one text node."""
    proj_start: int
    proj_end: int
    node_path: str
    node_offset: int

@dataclass
class TextProjection:
    part: PartId
    text: str
    anchors: list[Anchor]        # sorted, contiguous, covers all of text
    block_breaks: list[int]      # hard sentence boundaries: paragraph,
                                 # table cell, list item, footnote
    table_cells: list[TableCell] # table_id, row, col, span

@dataclass
class Detection:
    detection_id: str            # content-based, see below
    part: PartId
    span: Span
    surface: str
    entity_type: str
    confidence: float            # calibrated
    band: str                    # "high" | "medium" | "low"
    detector: str
    base_span: Span | None       # name without Hebrew proclitic
    prefix: str = ""             # the proclitic present, e.g. "ול"
    suffix: str = ""             # possessive or plural suffix
    lemma: str | None = None
    gender: str | None = None
    at_window_edge: bool = False
    needs_review: bool = False
    review_reason: str | None = None
    metadata: dict = field(default_factory=dict)

@dataclass
class Surrogate:
    value: str
    given: str | None
    surname: str | None
    gender: str | None
    script: str                  # "hebrew" | "latin" | "arabic"
    forms: dict[str, str]        # observed surface -> replacement surface
    translit: list[str]          # Latin spellings, for rehydration

@dataclass
class Entity:
    entity_id: str               # stable hash of canonical + type
    entity_type: str
    canonical: str
    variants: set[str]
    detections: list[Detection]
    gender: str | None
    family_group: str | None
    surrogate: Surrogate | None
    decision: str = "replace"    # "replace" | "keep"
    ambiguous: bool = False

@dataclass
class ReviewItem:
    item_id: str
    kind: str      # "low_confidence" | "type_conflict" | "ambiguous_entity"
                   # | "residual_risk" | "unanalyzed_image" | "empty_result"
                   # | "verification_residue" | "numeric_wordform_unresolved"
    severity: str  # "must_resolve" | "advisory"
    message_key: str
    target: str
    resolved: bool = False
    resolution: str | None = None
```

**Identifiers are content-based, not offset-based.**
`detection_id = sha256(part || type || normalized_surface || ordinal)`.
`entity_id = sha256(canonical || type)`.
The user edits the source and re-runs; offset-based ids would discard every prior decision. Content-based ids let the session reapply "the user already decided this one".

---

## PART III: TEST ARCHITECTURE

## 6. Principles

1. **Every phase has a gate that passes standing alone.** A phase's gate depends only on that phase's deliverable plus already-gated phases. No phase is gated on something built later.
2. **Each test tier answers a different question.** Tiers are additive, not alternatives.
3. **Gates are numbers in a file, not opinions.** `eval/baselines.json` holds every metric gate. A build that regresses a baseline fails. Raising a baseline is a deliberate commit.
4. **Fixtures are a versioned asset.** `tests/fixtures/` has a manifest with a provenance note per file. The corpus is as much a deliverable as the code.
5. **Determinism in tests.** Pin `intra_op_num_threads` and `inter_op_num_threads`, fix all seeds, fix the matter key. A flaky test in an ML pipeline is a test that will be deleted, so do not write one.

## 7. The nine test tiers

| Tier | Name | Question it answers | Runs |
|---|---|---|---|
| **T0** | Contract | Do the interfaces hold? Does every adapter and detector conform? | every commit |
| **T1** | Unit | Does this function do what it says on hand-built examples? | every commit |
| **T2** | Property | Does the invariant hold across generated input? | every commit (reduced), full at phase boundary |
| **T3** | Golden | Did verified output change without us intending it? | every commit |
| **T4** | Integration | Do two or more phases compose correctly? | every commit |
| **T5** | System | Does a full user journey work end to end? | phase boundary |
| **T6** | Metrics | Are recall, precision, burden, consistency and utility at or above baseline? | phase boundary |
| **T7** | Performance | Is it fast enough on the reference machine? | phase boundary |
| **T8** | Privacy and security | Does it leak through network, logs, temp files, metadata or co-location? | every commit |
| **T9** | Persona acceptance | Can the intended user actually do the job, within a time budget? | release candidate |

### T2: the invariants worth generating against

These are the tests that find the bugs examples miss.

| Invariant | Statement |
|---|---|
| **Projection coverage** | Anchors are sorted, contiguous and cover exactly `len(text)`. No gaps, no overlaps. |
| **Identity round trip** | Replacing every character with itself and writing back yields a document whose extraction equals the original extraction. |
| **Inverse property** | `restore(apply(analyze(d))) == d` at text level, for every generated document. |
| **Replacement ordering** | Applying N edits in any valid order yields the same output. |
| **Numeric conservatism** | Any number not positively classified as an eligible type is byte-identical in the output. |
| **Surrogate disjointness** | No assigned surrogate appears anywhere in the source document or anywhere in the matter. |
| **Consistency** | Every occurrence of an entity maps to one surrogate. |
| **Prefix preservation** | For any proclitic P and name N, replacing in `P+N` yields `P+surrogate`, with P unchanged. |
| **Rehydration inverse** | For any surrogate form the morphology generator can produce, the matcher recovers the entity. |
| **Keep means keep** | An entity marked `keep` appears unchanged in the output, in every one of its forms. |
| **Determinism** | Two runs with identical inputs and pinned versions produce identical bytes. |
| **Gate soundness** | `apply()` raises whenever any `must_resolve` item is unresolved, for every generated session state. |

Use `hypothesis` with custom strategies: a Hebrew-document generator (names with proclitics, split runs, table cells, headers, footnotes), an edit-list generator, and a session-state generator.

### T5: the system journeys

Each is a scripted end-to-end test over a fixed fixture, asserting outcome and side effects.

| # | Journey | Asserts |
|---|---|---|
| S1 | Happy path: pleading in, review, export, verify | safe file opens, zero residue, report present, mapping outside output dir |
| S2 | Restore: take S1's output, restore to original | text-level equality with the source |
| S3 | Rehydrate: paste an AI answer containing inflected, translated, paraphrased and invented names | real names restored, invented names flagged, ambiguity surfaced |
| S4 | Multi-file matter: four documents, same people | identical surrogates across all four, one mapping, one chained report per file |
| S5 | Edit and re-run: modify the source, re-analyze | prior decisions reapplied via content-based ids, no spurious new items |
| S6 | Keep decision: mark an entity keep, export | entity unchanged in every form, recorded in the report |
| S7 | Blocked export: leave one must-resolve item open | `NotApprovedError`, no artifacts written anywhere |
| S8 | Empty result: a document with no detectable identifiers | empty-result review item raised, export blocked until acknowledged |
| S9 | Document with images | unanalyzed-image item raised per image, must be resolved, recorded |
| S10 | Double processing: feed an already-safe file | refused with a restore suggestion, nothing written |
| S11 | Cancellation mid-analysis of a 60-page file | no partial output, no partial mapping, worker exits clean |
| S12 | Crash injection during export | atomic: either complete artifacts or none, mapping consistent |
| S13 | Offline enforcement: run with networking disabled at OS level | full journey S1 completes unchanged |
| S14 | Mapping loss: delete the mapping, re-run the original | keyed determinism reproduces identical surrogates |

### T6: the metric gates

`eval/run_eval.py` prints and compares against `baselines.json`.

| Metric | Why it exists | v1 gate |
|---|---|---|
| Per-type precision, recall, F1 (span and entity level) | model quality | checksum types ≥ 0.98 recall; PERSON reported honestly, baseline frozen after first measurement and never allowed to regress |
| **Pre-review document zero-leak rate** | what the models deliver alone | measured and published internally |
| **Post-review document zero-leak rate** | what the product delivers, with a simulated reviewer resolving all items correctly | the headline number; gate at 1.0 on the eval corpus, because the human gate exists precisely to close this |
| **Review burden: items per page** | low precision kills adoption through a different door than low recall | ≤ 10 per page |
| Consistency | correctness | 1.0 |
| Over-merge count | over-merging silently rewrites the document's facts | 0 |
| Under-merge count | reported and surfaced to the user | reported |
| Verification catch rate | the value Phase 10 adds | reported |
| **Utility preservation** | over-redaction makes the output useless and users quit | 30 QA pairs over the corpus, asked against original and safe version, substantive agreement ≥ 0.9 |
| Numeric conservatism violations | a destroyed contract is worse than a leak-free one nobody can use | 0 |
| Runtime per page, runtime for 60 pages, peak RSS | usability | section 8.2 |

Two zero-leak numbers, never collapsed into one. A single figure would either overstate the models or understate the product.

### T8: what privacy testing actually checks

- AST scan: no networking imports under `ploni/`.
- `eval/` is not importable from `ploni/`.
- Canary test: a document seeded with unique canary strings runs the full pipeline; no canary appears in any log record, any file under the temp directory, or any artifact other than the encrypted mapping.
- Scrub assertions: metadata fields empty, comments gone, tracked-change deletions gone, image EXIF stripped, output filename neutral.
- Co-location: `apply()` refuses to write a mapping into the output directory.
- Mapping file: decrypting with a wrong passphrase fails cleanly; the file reveals no plaintext under `strings`.
- Socket audit: during a full journey, the process opens no outbound socket.

### T9: persona acceptance

Run by a human, scripted, on a release candidate.

| # | Scenario | Budget |
|---|---|---|
| P1 | A lawyer processes a real 20-page pleading: open, review, export | under 6 minutes, zero leaks found on inspection |
| P2 | The ten-minute demo script (section 8.3), start to finish, network cable unplugged | under 10 minutes, no dead ends |
| P3 | An accountant processes a financial statement | amounts scaled consistently, section numbers and percentages untouched, totals still add up |
| P4 | A clinician processes a medical summary | clinical intervals preserved, the date trade-off understood from the UI alone |
| P5 | First run by someone who has never seen it | reaches the offline self-test and understands what it proves, without help |

## 8. Targets

### 8.1 Reference machine

Define it once and record it in `docs/REFERENCE_MACHINE.md`: a mainstream business laptop, 8 cores, 16 GB RAM, no GPU, Windows 11. All performance numbers are on this machine, with pinned thread counts.

### 8.2 Performance budget

| Operation | Target | Fail threshold |
|---|---|---|
| Analysis, one A4 page of Hebrew | 1 to 3 s | > 10 s |
| Analysis, 60-page document | 2 to 6 min | > 12 min |
| Export after approval | < 5 s | > 20 s |
| Rehydrate a 2,000-word answer | < 2 s | > 10 s |
| Cold start to first screen | < 8 s | > 30 s |
| Peak RSS | < 2.5 GB | > 4 GB |

A number below the low end is also a finding: suspect the model is not seeing the full text.

### 8.3 The demo script, as an acceptance test

Ten minutes, on a real-shaped Hebrew pleading, with the network cable visibly unplugged:

1. First launch shows the offline self-test. Point at it.
2. Drag in the pleading. Choose the `כתב טענות` profile.
3. Review: 15 entities, not 400 occurrences. Show the uncertainty queue. Reject one entity to keep opposing counsel's firm name. Add one span the model missed.
4. Export. Copy safe text to clipboard.
5. Paste into ChatGPT or Claude, ask a real question about the case.
6. Copy the answer back. Rehydrate. Real names reappear in correct Hebrew inflection.
7. Show the report.
8. Show the verification pass result.

If any step needs explanation or a workaround, that is a bug. P2 in T9 is this script.

---

## PART IV: THE PHASES

Each phase states: goal, deliverable, tests added, **gate**, and what breaks downstream if it is wrong.

## Phase 0: foundation and safety

**Goal.** A repo that installs, imports, runs a no-op CLI, and cannot leak.

**Deliverable.** Pinned `requirements.txt` and `pyproject.toml`, Python 3.13 (3.11 until 2026-11-13; Achia changed it because the development laptop has 3.13.5 and week-one experiments E2 and E3 had run on it; E1 ran on it the same day). `types.py` and `errors.py` exactly as section 5. CLI stubs: `scan`, `analyze`, `review`, `export`, `verify`, `restore`, `rehydrate`, `report`, `selftest`, `usage`. `safety/logging.py`, `safety/tempfiles.py`, `safety/atomic.py`. `scripts/download_models.py` with pinned revisions, writing `docs/THIRD_PARTY.md` with name, URL, revision hash and license per model. `eval/baselines.json` skeleton. `make check` running the fast suite.

**Tests added.** T0 type contracts. T8 no-network AST scan, eval-isolation, log canary, temp-file canary. T1 atomic-write unit tests including simulated crash between write and rename.

**Gate.** `ploni selftest` prints the model inventory and "offline OK". T0, T1, T8 green. CI fails if a model in `models/` is absent from `THIRD_PARTY.md`.

**If wrong.** Logging and temp-file leaks retrofitted later are found by whoever audits the product, not by you.

---

## Phase 1: deterministic detectors

**Goal.** Checksum-backed and pattern-backed detection of structured identifiers.

**Deliverable.** Every module under `detect/deterministic/`, each with its own fixture file.

Detectors and the specifics that matter:

**Israeli ID.** Nine digits, last is a check digit, Luhn-style.
```python
def israeli_id_checksum_ok(digits: str) -> bool:
    if len(digits) > 9 or not digits.isdigit():
        return False
    d = digits.zfill(9)
    total = 0
    for i, ch in enumerate(d):
        n = int(ch) * (1 if i % 2 == 0 else 2)
        total += n if n < 10 else n - 9
    return total % 10 == 0
```
Separator-tolerant candidate regex, strip, validate. Reject trivial sequences.

**Company and non-profit numbers.** Nine digits, same check digit; companies (ח.פ.) start with `5`, non-profits (ע.ר.) with `58`. Public-registry facts, so default is detect and flag, not replace.

**IBAN.** `IL` plus 2 check digits plus 19 characters, 23 total, mod-97. Plus domestic bank/branch/account triples.

**Credit card.** Luhn plus brand prefix sanity.

**Israeli phone.** Landline `0[23489]`, mobile `05\d`, VoIP `07[2-9]`, `+972` forms, `*NNNN` service numbers.

**Email, URL, IP.** Email stores the local part in metadata so resolution can link `jacob.cohen@` to `יעקב כהן`. Run detection over URL paths and query strings, which carry names and case numbers routinely.

**License plate.** `NN-NNN-NN` and `NNN-NN-NNN`. High false-positive risk, so require separators or a nearby trigger (`רכב`, `מספר רישוי`, `לוחית`).

**Court case numbers.** Net HaMishpat style `<procedure> NNNNN-MM-YY` (`ת"א 12345-01-20`, `תא"מ`, `ק"פ`, `רע"א`) and classic `<procedure> NNNN/NN` (`ע"א 1234/20`, `בג"ץ 1234/21`). Start with the 30 commonest procedure abbreviations. Handle `"` and `״` (U+05F4), `'` and `׳` (U+05F3).

**Gush / Helka.** `גוש`, `חלקה`, `תת-חלקה`.

**Dates.** Gregorian numeric, Hebrew month names, Hebrew-calendar dates (`כ"ה בכסלו תשפ"ו`), parsed to values for consistent shifting.

**Amounts.** `₪`, `ש"ח`, `שקל`, `NIS`, `$`, `€`, plus written-out Hebrew numbers. Capture the value.

**Addresses.** Street lexicon followed by a number, plus city lexicon. NER-assisted in Phase 3.

**Trigger words.** `מר`, `גב'`, `עו"ד`, `ד"ר`, `פרופ'`, `רו"ח`, `התובע`, `הנתבע`, `המבקש`, `המשיב`, `העד`, `כב' השופט`, `ב"כ`. A trigger followed by a Hebrew token is high-precision PERSON evidence, and it is the main defense against names that are ordinary Hebrew words: אור, שחר, רון, ברק, יונה, שרון, עדן, טל, גל, שקד, ים, תום, עומר, נועם, דקל, חן, שירה. There is no capitalization to lean on, so lexicon membership raises confidence but never creates a PERSON detection alone.

**Already-anonymized placeholders.** `פלוני`, `אלמוני`, `פלונית`, `א.ב.`, `ח.ד.`, `___`. Detected and **excluded from surrogate assignment**, because turning a placeholder into a realistic name makes the document look more identifying than it was.

**Low-confidence pattern-only.** Health fund member numbers, military IDs, passport numbers. Always `needs_review`.

**Tests added.** T1 per detector: ≥ 40 positive and ≥ 40 negative examples each, in Hebrew context, with separator and gershayim variants. T0 detector conformance. T2 property: every returned span lies inside the projection and every returned type is declared.

**Gate.** Checksum-backed types ≥ 0.98 recall and ≥ 0.98 precision on fixtures. Pattern-only types report their numbers; `IL_PLATE` and `ADDRESS` precision is expected around 0.7 to 0.85 and is recorded, not gated.
**Prediction and threshold.** If a checksum-backed detector lands below 0.98 recall, the candidate regex is too narrow. Widen the regex. Never weaken the checksum.

**If wrong.** These are the identifiers that cause actual damage. A gap here is not a quality issue, it is the product failing at its core job.

---

## Phase 2: the DOCX adapter

**Goal.** Exact, reversible extraction and writing of real Word documents.

**Deliverable.** `adapters/docx/`, implementing `DocumentAdapter`.

**Parts extracted.** `word/document.xml`, every header and footer, `footnotes.xml`, `endnotes.xml`, `comments.xml`, every `w:txbxContent`, `docProps/core.xml`, `docProps/app.xml`, any `customXml`, and hyperlink targets from the rels.

**One projection per part, not one concatenated string.** Concatenating means the NER model reads from the end of a page header straight into the body, producing phantom entities across a boundary that does not exist in the document. Entity resolution unifies across parts later; extraction must not pretend parts are contiguous.

**Block breaks.** Record an offset at every paragraph, table cell, list item and footnote boundary. Model windows never cross one.

**Tracked changes.** `w:ins` holds inserted text, `w:del` holds deleted text in `w:delText`. Both contain real content and both leak. Both enter the projection, labelled.

**Run splitting.** Word splits runs when formatting, spellcheck state or language attributes change mid-word, so `יעקב` can be `יע` plus `קב` in two `w:r` elements. The projection joins run text transparently; the writer must replace spans crossing run boundaries by writing the full replacement into the first run and emptying the rest, preserving the first run's properties.

**Tables.** Capture `table_id`, row and column. Column-type inference is post-v1, but the structural metadata must exist now or it is expensive to add.

**Direction.** Hebrew to Hebrew is safe. Cross-script replacement changes directionality and needs an explicit `w:rtl` fix plus a warning.

**Fixture corpus, at least 15 files**, each with a provenance note: tracked changes, footnotes, comments, text box, RTL with embedded English, a wide table, an embedded image, per-page headers, multi-section with different headers, a hyperlink carrying a name, a name split across runs, a document with 60 pages, a document with an embedded spreadsheet, a document with `docProps` populated, a scanned-page-as-image document.

**Tests added.** T2 projection coverage, identity round trip, replacement ordering. T0 adapter conformance. T3 golden extraction output per fixture. T1 run-splitting units.

**Gate.** Identity round trip passes on all 15 fixtures: extraction equality, opens in Word with no repair prompt, formatting run count within tolerance. T2 coverage invariant holds over 500 generated documents.
**Prediction and threshold.** Simple files pass immediately; text boxes and tracked changes fail first. If more than 2 of 15 still fail after the first implementation pass, stop and decide between going deeper into OOXML or pre-normalizing documents (accept changes, drop comments) before processing.

**If wrong.** Every phase downstream inherits the bug, and the failure the user sees is "the tool broke my document", which is unrecoverable trust damage.

---

## Phase 3: Hebrew NER, morphology, windowing

**Goal.** Detect names, places and organizations in real Hebrew, with morphological awareness.

**Deliverable.** `detect/hebrew_ner.py`, `detect/windowing.py`, `morph/prefixes.py`, `morph/normalize.py`, `detect/vendored/dictabert/`.

**Model.** `dicta-il/dictabert-joint` gives prefix segmentation, morphological disambiguation, lemma, syntax and NER in one pass, with heads toggled via `do_lex`, `do_syntax`, `do_ner`, `do_prefix`, `do_morph`. License CC BY 4.0, so commercial use is fine with attribution.

It requires `trust_remote_code=True`, meaning it ships executable Python. **Vendor that code into the repo, read it, load it from the local path.** Do not execute hub code at runtime in an offline product. Do this now.

Fallback if the joint ONNX export fights back: `onnx-community/dictabert-ner-ONNX` for the NER head, with prefix segmentation on the PyTorch path temporarily.

**Windowing, specified exactly**, because vague windowing is where recall dies silently:
- Max 512 tokens, stride 128, so 384 new tokens per window.
- Windows never cross a `block_break`.
- A detection touching the first or last 32 tokens is `at_window_edge=True`.
- Fusion prefers the version of an edge detection produced by a window where it is not at the edge. If no such window exists, keep it and set `needs_review`.

**Proclitics.** Letters ו ה ב ל מ כ ש and combinations `ול`, `וב`, `ומ`, `וה`, `ושה`, `כש`, `לכש`, `מה`, `שה`, `וכש`, `מש`, `לה`. Use the model's segmentation, not a regex over a prefix list, because many real names begin with those letters: ברק, משה, הדר, לביא, שרה, כנרת, בן, מיכל, לירון, שירה. Split into prefix, base and suffix; replacement rewrites the base only, so `וליעקב` becomes `ולדוד`.

**Normalization.** Strip niqqud, normalize final letters (ך ם ן ף ץ), normalize gershayim and geresh variants, fold ktiv male and haser (`יוסף`/`יסף`, `דוד`/`דויד`) under a configurable rule set, normalize maqaf and whitespace. Handle geresh inside transliterated names: `ג'ון`, `צ'רלי`, `ז'אק`, `ג'ורג'`, which break naive tokenizers.

**Tests added.** T1 prefix and normalization units. T2 prefix preservation over generated proclitic forms. T1 windowing: a fixture with the same name deliberately placed at window boundaries, asserting one detection per occurrence with no duplicates and no drops. T3 golden detection output per fixture.

**Gate.** The windowing test passes exactly. Prefix preservation holds over 1,000 generated forms. PERSON recall measured and printed on the 10 real Hebrew documents, and the number is recorded as the first baseline.
**Prediction and threshold.** 85 to 92 percent entity-level PERSON recall, errors concentrated in ordinary-word names and proclitic forms; near 1.0 on checksum types. **Below 80 percent PERSON recall, stop: do not proceed to any UI work.** Revisit windowing, the vendored code path, and whether the joint NER head is being read correctly.

**If wrong.** This number determines whether the product is viable at all. It is the one measurement worth taking before anything else gets built.

---

## Phase 4: multilingual detection and fusion

**Goal.** English and mixed-language coverage, custom categories, and one coherent detection list.

**Deliverable.** `detect/gliner_ner.py`, `detect/fusion.py`, `detect/calibration.py`.

**GLiNER2.** `fastino/gliner2-base-v1`, 205M parameters, Apache 2.0, CPU-first, one forward pass, labels supplied at request time. This is what delivers the "realm of activity" option with no training. Absolute zero-shot quality is moderate, so run it at a low threshold as a recall booster, never as the primary Hebrew detector. Labels come from the active profile, for example `["person name", "organization", "job title", "medical condition", "location", "industry or field of activity"]`.

**Licensing trap, memorize it.** GLiNER v0 and v1 (`gliner_base`, `gliner_multi`, the small/medium/large v1 line) are **CC-BY-NC-4.0, non-commercial**. Only the v2.1 generation and the PII models are Apache 2.0. Pulling the most popular GLiNER checkpoint builds a product that cannot be sold. Fine-tunes can also be re-licensed more restrictively than their base because of training data, so check every checkpoint individually, including community ONNX re-exports. And PyMuPDF is AGPL, so it is banned from product code entirely.

**Fusion rules.**
1. Collect all detections from all detectors, per part.
2. Overlapping spans: same type merges and raises confidence; different type keeps the more sensitive type and sets `needs_review` with reason `type_conflict`.
3. Longest span wins when one contains another, except that a checksum-backed detector's shorter span wins (a validated ID inside a longer NER span is the real answer).
4. Resolve `at_window_edge` per Phase 3.
5. Confidence below the profile threshold sets `needs_review` with reason `low_confidence`.

**Calibration.** Raw model scores are not probabilities. Fit a reliability curve on the eval set, binning predicted score against observed correctness, and store it in config. Map calibrated confidence to three bands, and show the user bands rather than numbers, because a percentage no user can interpret is noise that looks like information.

**Tests added.** T1 fusion units for every rule, including adversarial overlaps. T2 property: fusion output has no overlapping spans and is order-independent with respect to detector execution order. T4 integration: adapter plus all detectors plus fusion over the fixture corpus. T6 first full metrics run.

**Gate.** No overlapping spans in any fusion output. Order independence holds. Calibration curve produced and stored. Metrics table prints and `baselines.json` is populated.

---

## Phase 5: the eval harness, pulled forward

**Goal.** The measuring instrument, built before the things it measures.

**Deliverable.** `eval/generate.py`, `eval/run_eval.py`, `eval/corpus/`, `eval/baselines.json`.

**Synthetic generator.** Templates for pleadings, contracts, medical summaries, emails, HR letters and financial statements, filled from name banks, city and street lists, generated identifiers, realistic case numbers and amounts. Emits documents plus gold span annotations. At least 200 documents, wide variation in formatting, inflection, proclitic usage and language mixing.

Deliberately include the hard cases: names that are ordinary Hebrew words; one person in six surface forms; two people sharing a surname; a name inside an email address; a name in a header; a name in a footnote; a name inside a tracked deletion; a name split across runs; a name at a window boundary; a document already partly anonymized with `פלוני`; a document dense with `סעיף` numbers, percentages and statute years; a document with zero identifiers.

**Real documents.** Published Israeli court decisions are useful for format and language realism, but they are often already partly anonymized, which biases recall measurement. Use them for realism, never as ground truth. Real client documents are measured only on the pilot firm's own machine, by a script that prints metrics and copies no content anywhere.

**Utility benchmark.** 30 question-answer pairs over the corpus. Ask each against the original and against the safe version, score substantive agreement. This is the counterweight to chasing recall: a tool that redacts everything scores perfectly on leaks and is useless.

**Tests added.** T6 the full metric suite. T1 generator units (gold annotations match the generated text exactly).

**Gate.** `run_eval.py` prints the complete metrics table and writes baselines. The generator's gold annotations are verified exact on 100 percent of generated documents, because a benchmark with wrong labels is worse than no benchmark.

---

## Phase 6: entity resolution

**Goal.** Detections across all parts become a small set of entities.

**Deliverable.** `resolve/entity_resolution.py`.

No usable Hebrew coreference exists off the shelf, so this is ordered heuristics:

1. Exact normalized match after normalization and lemma folding.
2. Name decomposition into given and surname via lexicons.
3. Partial match linking: a lone surname links to the full-name entity when exactly one candidate exists. With two candidates (`יעקב כהן` and `רחל כהן`) it becomes `ambiguous` and **the user decides**. Never guess.
4. Initials and abbreviations: `י. כהן`, `י.כ.`, `יעקב כ'`.
5. Title stripping, retaining the title as a gender and role signal.
6. Email linking via a Hebrew-to-Latin transliteration table (`כהן` ↔ cohen/kohen/coen, `יעקב` ↔ yaakov/jacob/yakov, `חיים` ↔ chaim/haim/hayim).
7. Fuzzy match: normalized edit distance, same type only, last resort, always `needs_review`.
8. Family grouping by shared surname plus nearby relation words (`אשתו`, `בנו`, `אחיו`, `אביו`).
9. Gender inference from the given-name lexicon, the title, and the morphological features the joint model already returns for agreeing verbs and adjectives.

**Over-merging is worse than under-merging.** Merging two people silently rewrites the document's facts, and the AI then reasons about a person who does not exist. Under-merging costs the user a click and is surfaced as a "these might be the same person" item.

**Tests added.** T1 resolution on hand-built documents with known correct clustering. T2 property: an entity's detections all share the entity's type; no detection belongs to two entities. T6 cluster purity, over-merge and under-merge counts.

**Gate.** **Zero over-merges** on the resolution test set and on the 200-document corpus. Under-merges reported. Ambiguity correctly raised for every shared-surname case in the corpus.

---

## Phase 7: surrogate and numeric policy

**Goal.** Replacements that keep the document meaningful and the analysis valid.

**Deliverable.** `policy/surrogates.py`, `policy/name_banks/` (versioned), `policy/numeric.py`.

### Surrogates

Name banks as versioned JSON in the repo, auditable: Hebrew male and female given names and surnames, Arabic, Russian-origin surnames common in Israel, English, plus company-name components, street names and city names.

Rules:
1. **Gender match.** A female entity gets a female surrogate. Mismatched gender breaks Hebrew agreement in surrounding verbs and adjectives, which both confuses the AI and signals that substitution happened.
2. **Script match.** Hebrew to Hebrew. Cross-script changes directionality and breaks RTL layout; explicit, warned option only.
3. **Cultural origin match**, as a profile setting with a one-line explanation. It preserves the document's substance but also preserves demographic signal, and some users will want origin flattened deliberately.
4. **Collision avoidance.** Never a surrogate that appears in the source document, anywhere else in the matter, or in a blocklist of judges, public figures and the user's own firm.
5. **Family consistency.** Shared `family_group` means shared surrogate surname.
6. **Form generation.** Fill `Surrogate.forms` for full name, lone surname, lone given name, initials, email local part at a surrogate domain, and prefix-carrying forms. Fill `translit` for rehydration.
7. **Per-matter persistence** so the same person gets the same surrogate across 40 files and across sessions two years apart.
8. **Keyed determinism** from `HMAC(matter_key, entity_id)`, with the name bank version pinned per matter (section 4.4).

### Fake identifiers must not be real identifiers

A generated nine-digit value that passes the Israeli ID checksum **belongs to an actual living person**. Replacing one person's identifier with another person's identifier is not acceptable. Policy:

- `IL_ID`: default to a clearly marked pseudo-identifier such as `ת.ז. [מזהה-1]`. Checksum-valid output in a documented non-issued range is opt-in only, with a warning, for users whose downstream tooling validates IDs.
- `PHONE`: a reserved-for-fiction prefix convention, documented in the UI, never a dialable real number.
- `CREDIT_CARD`: standard reserved test numbers.
- `IBAN` and bank accounts: structurally and checksum valid, with an unassigned bank code.
- **Surrogate names** have a weaker version of the same problem: `דוד מילר` is somebody. It cannot be eliminated. Keep the matter blocklist and state the residual issue in the report rather than pretending it is solved.

### The numeric policy

A legal or financial document is mostly numbers that must never be touched. **Default is keep.** Only positively classified eligible types may be transformed.

**Never transform:** section and clause numbers (`סעיף 12`, `ס"ק 3(ב)`), page and paragraph numbers, years inside citations, percentages (`17%` VAT, interest rates), statute numbers (`חוק X, התשמ"ד-1984`), item counts, footnote markers, ordinals, standard-form numbers, court procedure numbers, ages when age mode is keep, and any number inside a placeholder.

**Written-out numbers must move with their digits.** Hebrew legal text writes `100,000 ש"ח (מאה אלף שקלים חדשים)`. Scaling the digits and leaving the words creates a contradiction the AI will notice and reason about wrongly. `morph/numwords_he.py` converts both directions; the amount transformer rewrites both representations together or transforms neither. If the word form cannot be regenerated confidently, fall back to keep for that amount and raise a `numeric_wordform_unresolved` item.

| Type | Modes | Notes |
|---|---|---|
| DATE | keep / shift by matter constant / month-year / year | One offset derived from the matter key, preserving intervals and optionally weekday. UI states the trade-off at the point of choice. |
| AMOUNT | keep / scale by matter factor / bucket / mask | Scaling preserves ratios and totals, which is what keeps financial analysis working. |
| AGE | keep / 5-year bucket / generalize above 89 | |

**Tests added.** T1 surrogate units: gender, script, family, collision, form generation. T2 surrogate disjointness, consistency, keep-means-keep, numeric conservatism. T1 numeric policy on a real-shaped contract and pleading fixture asserting section numbers, percentages and statute years survive byte-identical. T1 `numwords_he` round trip. T6 numeric conservatism violations.

**Gate.** Numeric conservatism violations: **0**. Surrogate disjointness and consistency hold over the full corpus. No generated identifier is a dialable or issuable real-world value, asserted by test. Gender preserved in 100 percent of cases where gender is known.

**If wrong.** A destroyed contract is a worse product than a leaky one, because the user discovers it immediately and never comes back.

---

## Phase 8: session and the review contract

**Goal.** The API the UI will drive, with the gate enforced in code rather than in the interface.

**Deliverable.** `session.py`.

```python
review_queue()                      # open items, grouped, counted, by severity
entities(filter=...)                # grouped, with occurrence counts
reject(detection_id) / reject_entity(entity_id)
keep_entity(entity_id)              # as cheap as replacing
merge_entities(a, b) / split_entity(entity_id, detection_ids)
add_span(part, start, end, entity_type)
override_surrogate(entity_id, value)
set_mode(entity_type, mode)
resolve_item(item_id, resolution)
approve()                           # raises if any must_resolve item is open
```

`apply()` raises `NotApprovedError` unless `approve()` has succeeded.

**Review burden scales with entities, not occurrences.** A 60-page pleading has maybe 15 people and 400 name occurrences. A UI asking for 400 approvals gets clicked through blindly and the review becomes theater. So the default unit of review is the entity with an occurrence count and an expander. Only three things are ever per-occurrence: low-confidence detections, type conflicts, and ambiguous-entity occurrences.

**The gate is per-item resolution.** Not "the user visited a tab", which is two clicks and no substance. This is what makes the report's central claim true.

**Decision reapplication.** Content-based ids let a re-run of an edited document restore prior decisions. The session records which decisions were reapplied and shows the user.

**Severity.** `must_resolve` blocks export. `advisory` does not. Residual risks and unanalyzed images are `must_resolve`; the leftover scan is advisory.

**Tests added.** T1 every session operation. T2 gate soundness over generated session states: `apply()` raises whenever any `must_resolve` item is open, with no exceptions. T4 integration: analyze, decide, approve, apply.

**Gate.** Gate soundness holds over 1,000 generated session states. Every operation has a unit test including its failure modes.

---

## Phase 9: writer, scrubber, and clipboard

**Goal.** A safe artifact, with nothing left behind.

**Deliverable.** `write/edits.py`, `write/scrub.py`, clipboard export in the CLI.

Writing: apply edits per part, sorted descending by offset. Spans crossing run boundaries write into the first run and empty the rest, preserving the first run's properties.

Scrub defaults, all on:
- Accept all tracked changes: drop `w:del` content, unwrap `w:ins`.
- Delete `comments.xml` and all references.
- Blank `docProps/core.xml`: creator, lastModifiedBy, title, subject, keywords, description, category; reset revision and timestamps.
- Strip `docProps/app.xml` company and manager.
- Strip EXIF from images in `word/media/`.
- Remove embedded objects, with a loud warning rather than a silent drop. An embedded spreadsheet inside a Word file is a real leak path.
- Run detection over hyperlink targets; rewrite or remove ones carrying identifiers.
- **Neutral output filename.** `Cohen_v_Levi_draft3.docx` is itself a disclosure. Default to `<matter_id>_safe_<n>.docx`; show the original name only locally.
- **Clipboard export in v1.** Many users paste rather than upload, and a "copy safe text" action removes a whole class of error, namely the user hand-copying from the original by mistake.

**Tests added.** T3 golden output per fixture, frozen once verified. T8 scrub assertions, canary residue scan. T2 inverse property (`restore(apply(analyze(d))) == d`) over the generated corpus. T4 end-to-end library integration.

**Gate.** Golden outputs frozen. Inverse property holds over 500 generated documents. Residue scan finds zero original surfaces anywhere in any artifact, metadata included. All T8 scrub assertions pass.

---

## Phase 10: mapping, restore, rehydration, verification

**Goal.** The reverse direction, and a closed loop.

**Deliverable.** `mapping/`, `rehydrate/`, `verify/`. The public API is frozen at the end of this phase.

### Mapping store

One encrypted file per matter, `<matter_id>.ploni`.
- **Schema version in the header**, with `migrate.py` from day one. A matter lives two years and the app will change. Retrofitting a version field means breaking every existing matter.
- Argon2id key derivation with parameters in the header; AES-256-GCM or XChaCha20-Poly1305, AEAD over the whole payload, per-record nonces. On Windows, optionally wrap the key with DPAPI so the user is not prompted every time; passphrase-only mode for portability.
- Contents: matter id, timestamps, schema version, `model_bundle_version`, `name_bank_version`, entity records, surrogate records with forms and transliterations, number modes, the matter date offset and amount factor, source document hashes, and a session hash chain.
- Stored in a dedicated app data directory. **`apply()` refuses to write a mapping into the output directory**, because the worst user error is emailing both together.
- Optional per-matter expiry. Backup export action. The UI states plainly that losing the mapping means the safe document cannot be restored, and that keyed determinism means re-running the original regenerates the same surrogates.

### Rehydrating the AI's answer

The feature users will love, with a trap nobody has solved. Naive string replacement fails because:

1. **The AI inflects Hebrew surrogates.** You injected `דוד`; the answer has `לדוד`, `של דוד`, `ודוד`. Match the surrogate base with any legal proclitic and possessive suffix, substitute the real name, keep the prefix. This is Phase 3's machinery in reverse.
2. **The AI paraphrases.** `מר מילר` for `דוד מילר`. Match surname-only and given-only forms.
3. **The AI translates.** `דוד מילר` becomes `David Miller` in an English answer. Match on `translit`.
4. **The AI invents names** never in the mapping. Leave them untouched and **flag them visibly**, because the user must know those are not real parties.
5. **Plurals and possessives.** `מילרים`, `מילר's`. Longest-match-first; never replace inside a longer token that is not a known form.
6. **Ambiguity.** A family group sharing a surrogate surname makes a lone surname ambiguous. Mark both candidates or ask. Never pick silently.
7. **Partial paste.** The user pastes a fragment; rehydration must work without the whole answer.

### Verification pass

`leak_test` only proves we removed what we found. It says nothing about what we never detected. So after the artifact exists, run an independent check with a **different configuration**, so it is not the same blind spot twice: GLiNER2 at a lower threshold, full lexicon, trigger-word detection, plus Hebrew NER. Then the residue scan, the consistency check, and a structural check that the scrub list was applied.

Findings become `verification_residue` items. Per the design review, verification runs after export completes and presents findings as a non-blocking follow-up, so it never delays the user's first result; blocking is a setting.

**Tests added.** T1 crypto units, wrong-passphrase behavior, migration from a v0 fixture file. T2 rehydration inverse property. T1 at least 50 hand-written Hebrew answer snippets covering all seven cases above. T5 journeys S2, S3, S4, S14. T8 mapping plaintext audit and co-location refusal. T6 verification catch rate.

**Gate.** Rehydration recovers ≥ 90 percent of mentions on the 50-snippet set, with unmapped names flagged in 100 percent of cases. Restore round trip exact over the full corpus. Mapping co-location refused. Migration from a v0 fixture succeeds.
**Prediction and threshold.** Naive matching recovers 50 to 70 percent; morphology-aware should exceed 95. Below 90 percent, prefix handling is wrong and the feature does not ship.

---

## Phase 11: the report and the usage log

**Goal.** Evidence, and honest self-knowledge.

**Deliverable.** `report/audit.py`, `report/signing.py`, `report/usage_log.py`.

Report, JSON plus PDF (via `reportlab`, not PyMuPDF), per export:
- Timestamp, app version, model names, versions and hashes, name bank version.
- Source filename and SHA-256, output filename and SHA-256, mapping hash.
- Matter id, profile.
- Per entity type: detected, replaced, kept, rejected by user, added by user.
- Every review item and how the user resolved it.
- Verification pass results.
- Unanalyzed image count.
- An explicit statement of what the tool does and does not claim, from i18n keys Tomer owns.
- Ed25519 signature over canonical JSON, chained to the previous report's hash for that matter.

**Be honest about what the signature proves.** A per-install keypair is self-generated, so it does not prove authorship to a third party. What it provides is **tamper evidence over a chain**: a report cannot be altered or silently removed from the sequence. Offline, the timestamp is the local clock and is not a trusted timestamp. Say both in the report itself. Overclaiming here is what destroys trust when someone technical reads it. Trusted timestamping is a paid item.

**Usage log.** Local, visible, user-exportable: one line per operation with document hash, entity counts, timestamp, profile. The user can read every line and sharing it is a deliberate export. This is the honest way to have usage insight in an offline privacy product: visible by design, never hidden.

**Tests added.** T1 report completeness against a schema, signature verification, chain continuity, chain-break detection. T8 the report contains no document content beyond counts and hashes.

**Gate.** Every field populated on every export. Chain break detected by test. Report contains zero document surfaces.

---

## Phase 12: the application

**Goal.** A professional can do the whole job without reading a manual.

**Deliverable.** `ui/`, plus `worker/` per section 4.6.

Stack: engine in a worker process, FastAPI on `127.0.0.1` with a random port and a per-launch token, static HTML/CSS/JS front end. Zero license cost, fastest path, keeps the engine shell-agnostic for a native wrapper later.

### Screens

1. **First run: the offline self-test, before any file.** Lists the process's open sockets, shows zero outbound connections since launch, offers a run-with-network-disabled check. Prove the claim, then ask for the document. This is a sales tool as much as a feature.
2. **Open.** Drag a file. Pick or create a matter. Pick a profile.
3. **Profiles, not levels.** Never "censorship level 2"; a lawyer cannot answer that. Named presets over entity types and number modes:
   - `כתב טענות`: names, IDs, addresses, phones, case numbers replaced; amounts kept; dates kept.
   - `בדיקת חוזה`: party and company names replaced; amounts scaled; dates kept.
   - `סיכום רפואי`: names, IDs, institutions replaced; dates shifted preserving intervals; ages bucketed.
   - `דוח כספי`: names and company names replaced; amounts scaled by one factor; dates kept.
   - `מותאם אישית`: the full matrix.
   Each shows one line on what the AI will and will not be able to do with the result.
4. **Review.** Three panes: original on the right (RTL), preview on the left, entity list in the middle grouped by entity with occurrence counts. Clicking an entity highlights all occurrences in both panes. The uncertainty queues are the primary call to action, not a secondary tab, each with a live unresolved count. Keep is one keystroke, same as replace. Select-text-and-mark for misses. Keyboard navigation (`j`, `k`, `x`, `k` for keep, `Enter`) from the first UI commit, because reviewing 60 pages with a mouse is miserable.
5. **Leftover scan panel**, advisory. After replacement, scan for tokens that look like names and were not detected: lexicon members, Latin-script capitalized tokens, tokens following triggers, rare tokens appearing once or twice. Most will be noise. The one that is not is the one that saves the user.
6. **Empty result state.** Zero detections is treated as suspicious, not as success: show what was searched for, show the leftover scan, require explicit acknowledgement before export.
7. **Export.** Shows exactly what will be written: output path, neutral filename, mapping location, report location, the scrub checklist. Plus "copy safe text".
8. **Rehydrate.** Paste box, output box, substitution list, unmapped-name warnings.
9. **Accuracy page.** The current measured per-type recall, shipped with the build. Publishing your own numbers, including the unflattering ones, is both honest and a differentiator against competitors who publish nothing.
10. **Licenses**, generated from `THIRD_PARTY.md`.
11. **Usage log viewer** with an export action.

**Residual risk warnings**, each a Hebrew sentence pointing at a span, each a `must_resolve` item: a small locality plus a person or job title; a unique or near-unique job title (`מנכ"ל`, `ראש העיר`, `המנהל הרפואי של`); uniqueness language (`היחיד`, `הראשון ש`, `היחידה בישראל`); a rare condition from a configurable list; a date plus a named institution; a distinctive exact amount that survived with mode keep.

**Tests added.** T5 journeys S1, S5 to S13 driven through the UI layer. T7 cold start. T9 personas P1 to P5.

**Gate.** All system journeys green. P2, the demo script, completes in under 10 minutes with the network unplugged and with no workaround needed at any step.

---

## Phase 13: performance and packaging

**Goal.** Fast enough, installable, offline-provable.

### Quantization

This is where the product can be meaningfully better than a competitor calling `transformers` on a laptop.

1. Export `dictabert-joint` to ONNX. If the joint export fights back, start from the ONNX NER head and keep segmentation on PyTorch.
2. Dynamic INT8 first, per-channel. Then static or QDQ if dynamic costs accuracy.
3. **Re-run the full eval after every quantization change.** Quantization that costs 2 points of recall is not acceptable here even if it doubles speed. Record both numbers side by side.
4. Batch the document's windows into one inference call instead of looping.
5. Tune `intra_op_num_threads` and `inter_op_num_threads`, with a measured default per core count.
6. OpenVINO on Intel, DirectML or QNN on Copilot+ NPUs: explicitly post-v1. Tempting, and a distraction now.

### Long documents

A 60-page file is roughly 120 windows plus verification. Requirements: streaming progress with a per-stage breakdown, cancellation that leaves no partial output and no partial mapping, and detection results streamed to the UI as parts complete rather than a frozen spinner.

### Packaging

- Windows first. PyInstaller one-folder, not one-file, which unpacks to temp on every launch and trips antivirus more often.
- Models ship as a data directory beside the executable, not inside the binary.
- MSI or MSIX so IT can deploy with Intune or SCCM. An installer that works only by double-clicking from a USB stick fails at exactly the security-conscious customers worth having.
- Unsigned builds trigger SmartScreen and antivirus heuristics. Signing is a paid item. Until then publish SHA-256 hashes and accept the friction in pilots.
- **Offline update path:** a signed bundle (software plus models) verified against an embedded public key and installed from local disk. This is where a USB stick genuinely makes sense: transport for updates into air-gapped environments, not the runtime.

**Tests added.** T7 the full performance budget on the reference machine. T6 post-quantization eval, both numbers recorded. T5 S13 on the packaged build. Install and uninstall on a clean Windows 11 VM.

**Gate.** Every number in section 8.2 met. Post-quantization recall regression under 1 point, or the quantization is rejected. Installer installs and uninstalls cleanly on a fresh VM.

---

## PART V: CLOSING

## 9. Release gate for v1.0

v1.0 ships when all of the following are true and measured:

**Correctness**
1. All phase gates green.
2. T0 through T8 green on the release candidate.
3. Identity round trip on all 15 DOCX fixtures.
4. Inverse property over 500 generated documents.
5. Numeric conservatism violations: 0.
6. Over-merges: 0.
7. Consistency: 1.0.
8. No generated identifier is a dialable or issuable real-world value.

**Quality**
9. Checksum-backed detectors ≥ 0.98 recall.
10. PERSON recall measured, baselined, and published on the in-app accuracy page.
11. Post-review zero-leak rate 1.0 on the eval corpus; pre-review rate measured and recorded.
12. Review burden ≤ 10 items per page.
13. Utility preservation ≥ 0.9.
14. Rehydration ≥ 90 percent with unmapped names flagged.

**Privacy**
15. Offline journey S13 passes with networking disabled at OS level.
16. No document text in any log file or temp file, asserted by canary test.
17. Mapping encrypted, versioned, co-location refused.
18. Scrub assertions all pass.

**Product**
19. Personas P1 to P5 pass within budget.
20. Demo script under 10 minutes, no workarounds.
21. Performance budget met on the reference machine.
22. Installer verified on a clean VM.
23. `THIRD_PARTY.md` complete, every license verified.

## 10. Build order

| # | Phase | Sessions | Gate in one line |
|---|---|---|---|
| 1 | 0 Foundation and safety | 1 to 2 | selftest, no-network, no-leak |
| 2 | 1 Deterministic detectors | 3 to 4 | checksum types 0.98 recall |
| 3 | 2 DOCX adapter | 4 to 6 | identity round trip, 15 fixtures |
| 4 | 3 Hebrew NER and morphology | 4 to 6 | **the first honest recall number** |
| 5 | 4 Multilingual and fusion | 2 to 3 | no overlaps, order-independent, calibrated |
| 6 | 5 Eval harness | 2 to 3 | metrics table, gold labels exact |
| 7 | 6 Entity resolution | 3 to 4 | zero over-merges |
| 8 | 7 Surrogate and numeric policy | 4 to 5 | numeric violations 0, disjointness holds |
| 9 | 8 Session and review contract | 1 to 2 | gate soundness over 1,000 states |
| 10 | 9 Writer, scrubber, clipboard | 3 to 4 | golden frozen, inverse property, zero residue |
| 11 | 10 Mapping, restore, rehydrate, verify | 4 to 5 | 90 percent rehydration, exact restore |
| 12 | 11 Report and usage log | 2 | complete, chained, chain-break detected |
| 13 | 12 Application | 5 to 8 | all journeys, demo under 10 minutes |
| 14 | 13 Performance and packaging | 3 to 5 | budget met, installer clean |

## 11. Week one: three experiments before any product code

Each with a prediction and a disagreement threshold. Run them, paste the raw numbers, then commit to the architecture.

**E1. Baseline Hebrew NER recall.** `dictabert-joint` on 10 real Hebrew documents (court decisions, contracts, a medical summary). Count missed person names by hand.
Prediction: 85 to 92 percent PERSON recall, errors concentrated in ordinary-word names and proclitic forms.
Threshold: below 80 percent, the architecture needs rethinking before anything else is built.

**E2. CPU latency after INT8.** Export to ONNX, quantize dynamic INT8, measure wall clock on one A4 page of Hebrew on the reference machine.
Prediction: 1 to 3 seconds per page.
Threshold: above 10 seconds per page, quantization or batching is wrong.

**E3. Prefix-preserving replacement.** 100 hand-written inflected forms (`וליעקב`, `מהכהן`, `שברק`, `כשדוד`, construct state, possessive suffixes). Segment, replace the base, keep the prefix, check agreement.
Prediction: 90 percent correct, breaking on construct state and possessive suffixes.
Threshold: below 85 percent, a hand-written rule layer is needed above the model.

E1 or E2 failing changes the plan. E3 failing grows Phase 3.

## 12. Risk register

| # | Risk | Severity | Mitigation, and where |
|---|---|---|---|
| 1 | A missed identifier causes a real leak | critical | Union fusion at low thresholds; per-item human gate enforced in `apply()`; Phase 10 verification pass; leftover scan; residue scan on every build; published measured recall; copy that never claims anonymity |
| 2 | Hebrew recall insufficient | critical | E1 decides this in week one; HalleluBERT fine-tune held in reserve (section 13) |
| 3 | Precision so low that review becomes theater | high | Review burden is a gated metric; entity-level review; keyboard navigation |
| 4 | Numeric transformation destroys the document | high | Default-keep policy with an explicit whitelist; contract and pleading fixtures gate it at zero violations |
| 5 | DOCX fidelity breaks real documents | high | Identity round trip gates everything downstream; golden regression; adapter isolated behind a protocol |
| 6 | Over-merging rewrites the document's facts | high | Zero-over-merge gate; ambiguity goes to the user, never guessed |
| 7 | Rehydration misses inflected forms | medium-high | Morphology-aware reverse matching; 50-snippet set; 90 percent gate |
| 8 | Over-redaction kills utility | medium-high | Utility metric gated at 0.9; profiles instead of levels; public entities kept |
| 9 | Text inside images never analyzed | medium-high | Mandatory per-document disclosure; OCR in tier 2 with measurement first |
| 10 | Mapping compromise, or user emails mapping with the document | medium-high | Argon2id plus AEAD; stored outside output dir; co-location refused; schema versioned |
| 11 | Document text leaks into logs or temp files | medium | Redacting logger and secure temp from Phase 0; canary tests on every commit |
| 12 | Quantization quietly costs accuracy | medium | Full eval re-run after every quantization change; both numbers recorded; 1-point regression limit |
| 13 | Name bank drift breaks old matters | medium | Name bank version pinned per matter in the mapping (section 4.4) |
| 14 | Double processing corrupts a matter | medium | Content-hash idempotency check (section 4.5); journey S10 |
| 15 | Licensing mistake in a shipped model | medium | Generated `THIRD_PARTY.md` with CI check; GLiNER generation trap documented; PyMuPDF banned |
| 16 | Antivirus or IT blocks the installer | medium | MSI/MSIX; one-folder PyInstaller; signing planned |

## 13. Post-v1 backlog

### Tier 1: reach more users
1. **Word add-in.** Lawyers live in Word; process the open document in place. Highest-value single addition after v1, and the frozen public API is what makes it cheap.
2. **XLSX and CSV.** Column-type inference, sheet names, hidden sheets and columns, comments, formulas referencing sensitive cells.
3. **Email (EML/MSG).** Headers are names and addresses; signatures, quoted threads and attachments all leak.
4. **PDF text input.** `pypdf` and `pdfplumber`, output DOCX or TXT. If PDF output is ever needed, generate a clean PDF from scratch; never draw black boxes over text, which leaves the text recoverable underneath.
5. **Batch and folder processing.** One matter, one mapping, chained reports across 40 files.
6. **Fine-tuned Hebrew NER.** Fine-tune HalleluBERT (MIT, base scores BMC 93.33 and NEMO 87.06 micro-F1) on your own annotated legal and medical data. This is what takes PERSON recall from the low 90s toward the high 90s, and the hardest thing for a competitor to copy, because it needs the dataset rather than the model.
7. **Clipboard live mode.** Watch a field, pseudonymize outbound, rehydrate inbound.

### Tier 2: depth
8. **Local LLM risk flagger.** `DictaLM-3.0-1.7B-Instruct` (Apache 2.0, from Qwen3-1.7B-Base, Q4 GGUF around 1.05 to 1.11 GB) via llama.cpp, as an optional deep mode that flags quasi-identifiers and realm-of-activity spans. Flags only, never rewrites, so output stays deterministic.
9. **Better residual-risk analysis.** Document-level k-anonymity-style reasoning, configurable rare-condition and rare-occupation lists, plain-Hebrew explanations.
10. **OCR for scanned Hebrew.** Tesseract 5 with `heb` reaches roughly 92 to 96 percent on clean modern Hebrew print and drops to 60 to 80 percent on 19th-century rabbinical print; PaddleOCR and Surya handle complex layouts better but are heavier. An OCR error means a name is never detected, so OCR output must be marked lower-trust and reviewed harder. Measure before shipping.
11. **Coreference for pronouns and definite descriptions** (`הוא`, `המבקש`, `אותו אדם`).
12. **Format-preserving encryption (FF1/FF3-1)** for structured identifiers, deterministic and reversible without a mapping lookup.
13. **Cross-matter blocklist** of judges, public figures and firm staff.
14. **Firm server mode.** Shared matter dictionaries, central mapping with access control, batch processing, shared blocklist.
15. **Local privacy gateway.** The strongest long-term shape: sit between the user and ChatGPT, Claude or a local model, pseudonymize every outgoing prompt and attachment, rehydrate every response. The frozen API makes this an interface swap, not a rewrite.
16. **MCP server** so agents can call pseudonymize and rehydrate as tools.
17. **macOS build.**
18. **Arabic.** Adjacent RTL language, overlapping customer base, natural second market.

### Tier 3: polish
19. Undo and redo in review.
20. Custom dictionaries: the firm's clients, matters and staff, always caught.
21. Diff view with change bars.
22. Hebrew UI polish, RTL edge cases, accessibility.
23. Per-matter statistics from the usage log.

## 14. Paid tools, deferred

Nothing here is needed for v1.

| Item | Rough cost | Buys | When |
|---|---|---|---|
| Code signing certificate (OV or EV) | a few hundred USD per year | Removes SmartScreen warnings and most antivirus false positives; many IT departments will not deploy unsigned binaries | Before the first customer deployment |
| Apple Developer Program | 99 USD per year | Notarized macOS build | When macOS is on the roadmap |
| RFC 3161 trusted timestamping | low | Makes the report timestamp provable instead of local-clock | When a customer's security team asks |
| Licensing or entitlement library (Keygen, Cryptlex, Wibu CodeMeter) | subscription or per-dongle | Signed expiring licenses, offline activation | When you start charging |
| Third-party penetration test | low thousands USD | The letter that satisfies an institutional security review | Before selling to institutions |
| Transkribus or commercial Hebrew OCR | per page or subscription | Historical and handwritten Hebrew that open engines handle poorly | Only if a customer needs it |
| Annotation labor for the Hebrew corpus | hourly | Better ground truth than doing it yourself | When synthetic data stops improving recall |
| SOC 2 or ISO 27001 | tens of thousands USD | Enterprise procurement checkbox | Defer; processing zero customer data on your servers is the stronger story |

## 15. Open decisions for Achia

1. **First format after DOCX:** XLSX (accountants) or PDF-in (lawyers)? This picks the second customer segment.
2. **Cross-script surrogate policy.** Same-script and same-origin by default? Preserves utility and RTL layout, also preserves demographic signal.
3. **Public entity policy.** Keep courts, laws, ministries and precedents by default? Recommended yes; confirm with Tomer and a pilot lawyer.
4. **Identifier surrogate style.** Marked pseudo-identifiers (`[מזהה-1]`) by default, or checksum-valid non-issued values?
5. **Passphrase or OS keystore** as the mapping default. Portability against friction.
6. ~~**Product name.**~~ Decided 2026-11-11: **Ploni** (פלוני), the word Israeli legal writing already uses for an unnamed party. Package and CLI `ploni`, repo `ploni-engine`. Still open and owned by Tomer: a trademark check, and whether the name's association with anonymity conflicts with the rule in section 1 that the product never claims anonymity.
7. **Pilot users.** Who are the first three who will let you measure recall on their documents, on their machines?

## 16. First instruction to Claude Code

Phase 0 only. Create the repo skeleton per section 4.7, `types.py` and `errors.py` exactly as section 5, the CLI stubs, `safety/logging.py`, `safety/tempfiles.py`, `safety/atomic.py`, `scripts/download_models.py` with pinned revisions and license capture, `eval/baselines.json` skeleton, and the T0 and T8 suites.

Do not implement any detector. Report back with the repo tree, the model inventory output, and the test results.

Then Phase 1, one detector per commit, each with its fixture file and its measured numbers printed.

## 17. Changelog from v2.0

**Restructured.** Five parts: framing, architecture, test architecture, phases, closing. Each phase now states goal, deliverable, tests added, a numeric gate, and what breaks downstream if it is wrong.

**Added: the four-hat design review (section 2)**, including the four tensions where the hats disagreed and the explicit call made on each.

**Added: a frozen public API (4.1)** of four functions, with contract tests. Without this, the Word add-in and the gateway become rewrites rather than consumers.

**Added: the DocumentAdapter and Detector protocols (4.2, 4.3)** with conformance suites, so a new format or detector inherits the whole test battery and fusion never changes.

**Added: name bank versioning (4.4).** The v2 determinism claim was not actually achievable: surrogate assignment depends on the name banks, so adding names in a later release would silently change surrogates in a two-year-old matter.

**Added: idempotency (4.5).** Nothing in v2 stopped a user from processing an already-processed file, which produces surrogates of surrogates and a broken mapping chain. Detection is content-based so no marker is written into the user's document.

**Added: worker process model (4.6)** for real cancellation, memory isolation and deterministic thread counts.

**Added: a nine-tier test architecture (section 7)**, with T2 property-based testing as a first-class tier. The inverse property `restore(apply(analyze(d))) == d` is the single most valuable test in the product and v2 did not have it.

**Added: 14 system journeys (T5)** including cancellation, crash injection, double processing, mapping loss and OS-level network disablement.

**Added: the empty-result state.** Zero detections is the scariest screen in the product and v2 had no design for it. It is now suspicious by default and blocks export until acknowledged.

**Added: keep as a first-class decision.** v2 made rejecting harder than accepting; keeping a name is now one keystroke, visible and remembered per matter.

**Added: offline self-test as the first screen on first launch.** Asking a user to trust an unknown binary with their most sensitive file before proving the offline claim is the wrong order.

**Added: the local, visible, user-exportable usage log (Phase 11).** The honest answer to wanting usage insight in an offline privacy product.

**Added: a reference machine and an explicit performance budget (8.1, 8.2)**, including a 60-page number, cold start and peak RSS.

**Added: the demo script as acceptance test P2 (8.3)**, with a ten-minute budget and the rule that any step needing explanation is a bug.

**Added: persona acceptance tier T9** with wall-clock budgets, because review burden is the hidden adoption killer.

**Changed: confidence is shown as three calibrated bands, not a number.** A percentage no user can interpret is noise that looks like information.

**Changed: verification runs after export as a non-blocking follow-up** by default, so it never delays the user's first result. Blocking is a setting.

**Changed: build order.** Fusion and calibration split out as their own phase; the eval harness stays pulled forward at position 6 so the measuring instrument exists before the things it measures.

**Changed: gates are numbers in `eval/baselines.json`**, with regression failing the build, instead of prose targets.

**Carried forward unchanged from v2**, because they were right: per-part projections, content-based ids, default-keep numeric policy, written-number consistency, non-real generated identifiers, per-item review gating, the two separate zero-leak numbers, the honest signature claim, the verification pass, the leftover scan, unanalyzed-image disclosure, exact windowing rules, placeholder detection, review burden as a gated metric, mapping schema versioning, logging and temp-file hygiene, clipboard export in v1, golden-file regression, and vendoring the model's shipped Python.
