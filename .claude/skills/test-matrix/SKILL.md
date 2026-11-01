---
name: test-matrix
description: Build the equivalence-class and edge-case test battery for a function or module before implementing it, with Hebrew-specific and document-structure axes and a minimum sample size. Use when writing tests for any new function, module or feature branch.
---

# Building the test matrix

"Tested" in this project does not mean a happy path and one error. It means a sample that represents the input space, enumerated before the implementation exists.

Do this **before** writing any implementation. The matrix is what the tests are written from, and writing it first is what stops the tests from merely describing whatever the code happened to do.

## 1. Write the matrix into the test file as a comment block first

At the top of the test file, enumerate the classes. This is the artifact a reviewer reads to decide whether the sample is honest.

```python
"""Test matrix for split_proclitic.

Equivalence classes:
  EC1  no prefix                      יעקב
  EC2  single-letter prefix           ליעקב, ביעקב, מיעקב
  EC3  multi-letter prefix            וליעקב, כשיעקב, לכשיעקב
  EC4  name that begins with a prefix letter and has none
                                      ברק, משה, שרה, לביא
  EC5  name that is an ordinary word  אור, שחר, טל, יונה

Boundaries:
  B1  empty token
  B2  single character
  B3  prefix only, no base
  B4  longest legal prefix chain

Error paths:
  E1  segmentation does not reassemble into token -> SegmentationMismatch

Adversarial:
  A1  בברק  (prefix letter twice, where one is part of the name)
  A2  והוא  (all letters are prefix letters)
"""
```

One test case per line of the matrix, named after it: `test_ec3_multiletter_prefix`.

## 2. The standard axes

**Equivalence classes.** Partition valid input by behavior, one case per class. If two inputs take the same path through the function, they are one class and one test.

**Boundaries of every class.** Zero, one, maximum, maximum plus one, empty, single element, duplicate elements, all-identical, all-distinct.

**Every documented error path.** One case per `Raises:` entry in the docstring, asserting the specific exception type, not just that something was raised.

**Adversarial cases.** The input designed to break this specific function, labelled as such. If you cannot think of one, you do not understand the function well enough yet.

## 3. The Hebrew axes, which is where this product actually breaks

Apply every axis that could touch the code under test. Skipping an applicable one is a review finding.

- Proclitics and their combinations: ו, ה, ב, ל, מ, כ, ש, and ול, וב, ומ, וה, כש, לכש, מה, שה, וכש
- Names that begin with a prefix letter but carry no prefix: ברק, משה, הדר, לביא, שרה, כנרת
- Names that are ordinary Hebrew words: אור, שחר, רון, יונה, שרון, עדן, טל, גל, שקד, ים, תום, עומר, חן, שירה
- Ktiv male and ktiv haser: יוסף / יסף, דוד / דויד
- Final letter forms: ך ם ן ף ץ, including a name that gains a suffix and changes form
- Niqqud present and absent
- Gershayim as both `"` (U+0022) and `״` (U+05F4); geresh as both `'` (U+0027) and `׳` (U+05F3)
- Hebrew abbreviations: עו"ד, ד"ר, רו"ח, ת"א, בג"ץ, כב' השופט
- Geresh inside transliterated names: ג'ון, צ'רלי, ז'אק, ג'ורג'
- Mixed Hebrew and Latin inside one span
- RTL and LTR runs adjacent
- Separator variants on identifiers: hyphen, dot, space, none

## 4. The document-structure axes, for anything touching documents

- Text split across runs, including a name split mid-word
- Span at a block break
- Span at a model window edge
- Text in a header, a footer, a footnote, an endnote, a comment
- Text inside a tracked insertion and inside a tracked deletion
- Text in a table cell, and in a text box
- Text in document metadata
- Text in a hyperlink target
- A document with zero matches
- A document with the same entity in six surface forms

## 5. Minimum sample sizes

Enforced at review. Record the actual number in the PR body.

| Kind of code | Minimum |
|---|---|
| Detector | 40 positive, 40 negative, with the Hebrew and separator axes present |
| Pure function with a stated invariant | 500 generated cases, 5,000 at phase close |
| Document adapter | the full 15-file fixture corpus |
| Module suite | every public function exercised, plus the module's own failure modes |
| Full pipeline | the 200-document eval corpus |

## 6. Use property tests to get a large sample honestly

Hand-written examples cover what you thought of. Generated cases cover what you did not. For anything with a statable invariant, write it as a `hypothesis` property with a custom strategy rather than adding more examples by hand.

The project-wide invariants are listed in `build-plan.md` section 7 under T2. If the function you are writing participates in one of them, add it to that property rather than writing a new one.

When a property test finds a failing case, **add that case as a named regression example in T1** as well as fixing the code. The generated case will not be regenerated reliably; the example will.

## 7. Where each test goes

- `tests/t0_contract/` interfaces, adapter and detector conformance, layering
- `tests/t1_unit/` the matrix above, one file per module under test
- `tests/t2_property/` invariants over generated input
- `tests/t3_golden/` frozen verified output
- `tests/t4_integration/` the module suite over its public surface
- `tests/t5_system/` full user journeys
- `tests/t6_metrics/` metric gates
- `tests/t7_perf/` performance budget
- `tests/t8_privacy/` network, logs, temp files, scrub, co-location

## 8. The module suite is not the sum of the unit tests

Every module also gets `tests/t4_integration/test_<module>.py` that exercises its **public surface end to end**, not function by function. It answers a different question: do these functions compose correctly, and does the module behave as one thing. Include the module's own failure modes, the ones that only appear when its parts interact.

## 9. Coverage

A diagnostic, never a target. The review questions are "is every documented error path tested" and "is every applicable axis present", not "what is the percentage". A module at 100 percent coverage with no boundary cases is untested in the way that matters.
