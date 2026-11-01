---
name: new-detector
description: Add or change an entity detector in the Tomer pipeline, with its fixture corpus, conformance tests and measured precision and recall printed. Use when adding or modifying a detector under tomer/detect/.
---

# Adding a detector

One detector per commit. One detector per PR when it is non-trivial. Never bundle three detectors into one change: when the measured numbers disagree with the prediction you will not know which detector is responsible.

## 1. The contract

Every detector implements this protocol and nothing more:

```python
class Detector(Protocol):
    name: ClassVar[str]
    produces: ClassVar[frozenset[str]]       # entity types it may emit
    requires_morph: ClassVar[bool]
    def detect(self, proj: TextProjection,
               ctx: DetectContext) -> list[Detection]: ...
```

Rules that follow from the architecture:

- **Never edit `fusion.py` to accommodate a detector.** Fusion knows nothing about individual detectors. If a detector seems to need a fusion change, that is a design discussion, not a code change: stop and raise it.
- Emit only types listed in `produces`.
- Spans must lie inside the projection. Confidence in `[0, 1]`.
- Set `needs_review=True` with a `review_reason` for anything pattern-only or ambiguous. A silent low-confidence guess is the failure mode this product cannot afford.
- A detector does not decide whether something gets replaced. That is policy. Detect and report.

## 2. Recall beats precision, with a floor

A miss is a client data leak. A false positive is one click for the user. So prefer the wider pattern and let fusion and the human gate sort it out.

But precision has a floor: if the detector produces enough noise to push the document over roughly 10 review items per page, it fails adoption through a different door. Measure both, report both.

## 3. The fixture corpus

Every detector gets `tests/fixtures/detect/<name>.yaml` with:

- **At least 40 positives** and **at least 40 negatives**.
- Hebrew context around the value, not bare strings. A detector that works on `123456782` and fails on `ת.ז. 123456782` is useless.
- Separator variants: hyphen, dot, space, none.
- Gershayim and geresh variants where relevant: both `"` and `״` (U+05F4), both `'` and `׳` (U+05F3).
- Near-miss negatives: values that look right and must be rejected. For a checksum detector, include values that fail only on the check digit.
- For Hebrew name detectors: proclitic forms (`ול`, `מה`, `כש`, `שה`), and names that are also ordinary Hebrew words (אור, שחר, רון, ברק, יונה, שרון, טל, גל, תום, שקד).

Record the provenance of anything not hand-authored in `tests/fixtures/MANIFEST.md`. Never use a real client document, in any form.

## 4. Checksum detectors

Where a checksum exists, the pattern is always: wide candidate regex, strip separators, then validate. Precision comes from the checksum, recall comes from the regex.

If recall comes in below the gate, **widen the regex. Never weaken the checksum.**

Validators already specified in `build-plan.md` Phase 1: Israeli ID (Luhn-style, nine digits), company and non-profit numbers (same check digit, prefix 5 and 58), IBAN (mod-97, `IL` plus 21 characters), credit card (Luhn).

## 5. Register and conform

Add the detector to the registry. Then run the T0 conformance suite, which checks the protocol contract against every registered detector, so a new one inherits the whole battery for free.

## 6. Measure and report

Run the detector's fixture test and paste the real output:

```
$ pytest tests/t1_unit/test_<name>.py -q
precision 0.994  recall 0.991  n_pos 42  n_neg 45
false negatives: [list them]
false positives: [list them]
```

Print the actual failing cases, not just the aggregate. The list of false negatives is where the next improvement comes from.

**Gate:** checksum-backed types at or above 0.98 recall and 0.98 precision. Pattern-only types report their numbers rather than being gated; `IL_PLATE` and `ADDRESS` are expected around 0.7 to 0.85 precision and that is recorded, not failed.

If a checksum-backed detector lands below 0.98 recall, follow the stop-and-report procedure: write a findings note, do not tune.

## 7. Commit

```
feat(detect): israeli ID checksum detector

precision 0.994, recall 0.991 on 42 positive and 45 negative fixtures.
False negatives: two cases with a newline inside the number.
```

The measurement goes in the commit body. Six months later that is how you know what changed.
