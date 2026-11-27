"""The IBAN and bank account detector: Israeli IBANs by ISO 13616's mod-97 check, and bank, branch and account triples by their words and labels.

Why: a bank account names who holds the money and where; build-plan.md Phase 1, "IBAN": "`IL`
plus 2 check digits plus 19 characters, 23 total, mod-97. Plus domestic bank/branch/account
triples." Recall comes from the wide candidate, the IBAN's precision from its check, which is
never weakened (issue #34). The triples have no check digit here: they are found by their words
and labels only, and every one is flagged for review.

Contract: `Iban` is a Detector (`ploni/detect/base.py`) of the types IBAN and BANK_ACCOUNT, the
names of the held-out batch's span rules.

An IBAN is a match of IBAN_CANDIDATE: IL, in either case, then 21 ASCII digits, with a run of at
most IBAN_GAP_LONGEST separators (SEPARATORS of `israeli_id.py`) and marks of direction (LRM,
RLM) between any two characters but the two letters; no Latin letter or digit on its left, and
no digit, nor a separator but the plain space and a digit, on its right (a plain space and a
date after it end it). Its characters, the separators and marks taken out, pass `iban_ok`. Its span runs from I to the last digit,
the separators inside it included. The check is ISO 13616-1's: the IBAN's first four characters
moved to its end, each letter read as two digits (A = 10 to Z = 35), the number so made leaves 1
when divided by 97 (ISO 7064, MOD 97-10). Israel's IBAN is 23 characters: IL, two check digits,
a bank of three digits, a branch of three and an account of thirteen (ISO 13616's registry entry
for Israel, as the brief of issue #34 gives it; no copy of the standard is in the repository).
Confidence CONFIDENCE, band "high", needs_review False.

A BANK_ACCOUNT is a match of TRIPLE: the bank's number (1 to 3 digits), the branch's (1 to 3)
and the account's (4 to 13 digits, with at most one separator but the plain space between any
two), in that order, and between each two either the words that name what follows (סניף before
the branch, after the bank's name in brackets when one stands there; חשבון, a possessive form of
it such as חשבונו, ח-ן or ח"ן before the account; with מס' or מספר, a proclitic, commas, colons
and brackets around them), or one separator, with a plain space on either side or none. On its
left no Latin letter, no digit, nor a digit and a separator; on its right no digit, nor a
separator but the plain space and a digit. `is_bank_account` accepts it when a word stands
between two of its numbers, or, with none, when a bank label stands before it
(`bank_label_before`: חשבון, ח-ן, ח"ן, בנק or סניף, with no label of another number beside
it), its bank has BANK_DIGITS digits and its branch BRANCH_DIGITS, and it is not written in a
landline's shape (`israeli_id.is_other_shape`). Its span runs from the bank's first digit to the
account's last, the separators and the words between them included; a label before it is read,
never put in it. Confidence CONFIDENCE_PATTERN, band "medium", needs_review True with
REVIEW_REASON. The upper bounds of the three numbers (3, 3 and 13 digits) are those of Israel's
IBAN, which pads each to that length.

A BANK_ACCOUNT is also a match of BY_NAME: בנק (with a proclitic or not), the bank's name (one to
BANK_NAMES Hebrew words, none of them סניף), then the branch's number after its word and the
account's after its word, as in TRIPLE. Its span runs from the branch's first digit to the
account's last: the batch's rule starts at the bank's number, and with none, the first number is
the branch's (Claude's reading). The same confidence, band and review flag.

`detect` returns the IBANs and the triples in the order of the text.

Known limits: no check digit is applied to a triple: the banks' own check-digit rules are not
cited here, so none is invented (the brief of issue #34); a triple is found by its words and
labels only. The fewest digits of an account (ACCOUNT_SHORTEST, 4), the two digits of a bank and
the three of a branch with no word between are Claude's reading of how Israeli papers write them,
with no source. Not found: an account with no bank before it, by number or by name (a branch and an account,
or an account alone, under any label: an account alone is no triple, and the Israeli ID detector
drops nine digits under חשבון); a triple in another order (the account first); a triple grouped
by separators with no bank label before it, with a bank of one or three digits, or a branch of
one or two; a word between the numbers other than those listed (the bank's name between the
branch and the account), or written with niqqud; a grouped triple in a landline's shape
(0X-XXX-XXXX) under a bank label, though a bank 04 or 09 is written so; an IBAN of another
country (only Israel's is in the plan); an IBAN with another number right after it by a
separator but the plain space; an IBAN with a run of four separators or marks or more inside it. A valid IBAN is found
whatever stands around it; a run of three numbers with סניף or חשבון between them is found as a
triple whatever it is. Measured on invented texts, 3,000 per form, by a scratch script that is
not in the repository (its table is in the text of this detector's PR, issue #34): IL and 21
random digits give an IBAN 0.012 of the time (0.007 in the paper format; the check passes one
in 97); and 0.000, IBAN and BANK_ACCOUNT alike, for each of: an ID after ת.ז., after חשבון, and
written 3-3-3 after חשבון; a company number after ח.פ., and 2-6-1 after חשבון; a card in fours
after כרטיס and after חשבון; a landline 0X-XXX-XXXX with no label, after חשבון and after
"טלפון סניף הבנק", 0X XXX XXXX and 0X-XXXXXXX after חשבון; a mobile 05X-XXX-XXXX and
+972-5X-XXX-XXXX after חשבון; an amount XX XXX XXX, XX,XXX,XXX, XX.XXX.XXX and X XXX XXX XXX
after בחשבון, and XX XXX XXX with no label; a case number NNNNN-MM-YY, with and without חשבון
before it, and NNNN/YY; a date DD.MM.YYYY and D/M/YY after "חשבון מיום". A triple's account of
nine digits after ח-ן or ח"ן, with words between, is also found by the Israeli ID or the company
number detector when it passes their check (0.095 to 0.098 of 3,000 invented triples per word;
0.000 after חשבון, and grouped): their labels of other numbers do not hold ח-ן and ח"ן. The
detection carries no id (detection_id is ""): ids are made just after detection, with the
matter's key, never inside a detector (Achia, 2026-11-26, issue #169, "Use the secret key
(Recommended)").
"""

from __future__ import annotations

import re
from typing import ClassVar

from ploni.detect.base import DetectContext
from ploni.detect.deterministic import israeli_id
from ploni.detect.deterministic.israeli_id import _AFTER, _BEFORE, _GERSHAYIM, _SEP, _TIGHT, SEPARATORS
from ploni.types import Detection, Span, TextProjection

IBAN = "IBAN"
BANK_ACCOUNT = "BANK_ACCOUNT"
# ISO 13616, Israel: IL, two check digits, a bank of three digits, a branch of three and an
# account of thirteen (the module docstring).
IBAN_DIGITS = 21
BANK_LONGEST, BRANCH_LONGEST, ACCOUNT_LONGEST = 3, 3, 13
# ISO 7064, MOD 97-10: a valid IBAN leaves 1 when divided by 97.
MOD = 97
# With no word between the numbers: a bank of two digits and a branch of three; an account of
# four digits at least. Claude's reading, no source (Known limits).
BANK_DIGITS, BRANCH_DIGITS, ACCOUNT_SHORTEST = 2, 3, 4
# The marks of direction, LRM and RLM, that word processors put around Latin text in a Hebrew line.
DIRECTION_MARKS = "\u200e\u200f"
# Between two characters of an IBAN, a short run of separators and marks: two or three spaces, a
# space and a mark (the review of #34 at 28b6032, finding 5). Claude's reading, no source.
IBAN_GAP_LONGEST = 3
_IBAN_GAP_CHAR = "[" + re.escape(SEPARATORS + DIRECTION_MARKS) + "]"
# On its right no digit, nor a separator but the plain space and a digit: a plain space and a
# number after it end it.
IBAN_CANDIDATE = re.compile(
    rf"(?<![A-Za-z0-9])(?i:IL)(?:{_IBAN_GAP_CHAR}{{0,{IBAN_GAP_LONGEST}}}[0-9]){{{IBAN_DIGITS}}}(?![0-9])(?!{_TIGHT}[0-9])"
)
# Spaces and the punctuation that stands between a number and the word after it.
_GLUE = r"[\s,:;.()\-־–]*"
# מס' or מספר, "number", before or after a word, with either geresh or a dot.
_NO = rf"(?:מס(?:['׳.]|פר){_GLUE})?"
BRANCH_WORDS = (r"סניף",)
# חשבון, "account"; its forms with a possessive suffix, as חשבונו ("his account"), חשבונה, חשבונם,
# חשבוננו (the review of #34 at 28b6032, finding 3); its abbreviation ח-ן (a hyphen, a maqaf or
# an en dash) or ח"ן (any gershayim).
ACCOUNT_WORDS = (r"חשבון", r"חשבונ(?:ו|ה|ם|ן|י|נו|ך|כם)", r"ח[-־–]ן", rf"ח{_GERSHAYIM}ן")
# A word of a bank's name: Hebrew letters, with gershayim, geresh or a hyphen inside (בע"מ), and
# not סניף, with a proclitic or not. A name is one word to BANK_NAMES; Claude's reading, no source.
_NAME_WORD = r"(?![ובלהשמכ]{0,2}סניף)[א-ת][א-ת\"״'׳-]*"
BANK_NAMES = 3
_NAME = rf"{_NAME_WORD}(?:\s+{_NAME_WORD}){{0,{BANK_NAMES - 1}}}"
# The branch's word, after the bank's name in brackets when one stands there, "בנק 12 (לאומי) סניף".
_BRANCH_WORD = rf"{_GLUE}(?:\({_NAME}\))?{_GLUE}{_NO}{_BEFORE}(?:{'|'.join(BRANCH_WORDS)}){_AFTER}{_GLUE}{_NO}"
_ACCOUNT_WORD = rf"{_GLUE}{_NO}{_BEFORE}(?:{'|'.join(ACCOUNT_WORDS)}){_AFTER}{_GLUE}{_NO}"
_GAP = rf" ?{_SEP} ?"
# An account's digits, and what may not follow them.
_ACCOUNT = rf"[0-9](?:{_TIGHT}?[0-9]){{{ACCOUNT_SHORTEST - 1},{ACCOUNT_LONGEST - 1}}}"
_ACCOUNT_END = rf"(?![0-9])(?!{_TIGHT}[0-9])"
TRIPLE = re.compile(
    rf"(?<![0-9A-Za-z])(?<![0-9]{_SEP})(?P<bank>[0-9]{{1,{BANK_LONGEST}}})(?:(?P<branch_word>{_BRANCH_WORD})|{_GAP})"
    rf"(?P<branch>[0-9]{{1,{BRANCH_LONGEST}}})(?:(?P<account_word>{_ACCOUNT_WORD})|{_GAP})(?P<account>{_ACCOUNT}){_ACCOUNT_END}"
)
# A triple whose bank is named by its name, with no number: בנק, the name, then the branch and the
# account, each after its word (finding 3). Its item runs from the branch's first digit.
BY_NAME = re.compile(
    rf"(?<![א-ת])[ובלהשמכ]{{0,2}}בנק[\s,:]+{_NAME}{_BRANCH_WORD}(?P<branch>[0-9]{{1,{BRANCH_LONGEST}}})"
    rf"{_ACCOUNT_WORD}(?P<account>{_ACCOUNT}){_ACCOUNT_END}"
)
# The labels of a bank account in forms and court papers: the words of the account, בנק and סניף.
BANK_LABELS = (*ACCOUNT_WORDS, r"בנק", *BRANCH_WORDS)
# A bank label first, so that חשבון, בנק and סניף are read as one where the ID detector reads
# another number's.
LABEL = re.compile(rf"(?P<bank>{_BEFORE}(?:{'|'.join(BANK_LABELS)}){_AFTER})|{israeli_id.LABEL.pattern}")
# shortcut: fixed confidences until calibration (build-plan.md section 4.7, detect/calibration.py)
# gives measured ones; a run of 21 random digits after IL passes the check one time in 97, and
# a triple has no check at all.
CONFIDENCE = 0.99
CONFIDENCE_PATTERN = 0.85
REVIEW_REASON = "bank account found by its words or label only: no check digit"


def iban_ok(chars: str) -> bool:
    """Say whether an IBAN's characters pass ISO 13616's check, ISO 7064 MOD 97-10.

    Why: the check that gives the IBAN its precision (build-plan.md Phase 1: "mod-97"), never
    weakened.

    Contract: `chars`, the IBAN with its separators taken out. True when it is at least five
    ASCII letters and digits that, the first four moved to the end and each letter read as its
    two digits (A or a = 10, ..., Z or z = 35), make a number that leaves 1 when divided by 97.
    False otherwise, also for "".

    Known limits: it does not read the country or the length; IBAN_CANDIDATE does.
    """
    if len(chars) < 5 or not (chars.isascii() and chars.isalnum()):
        return False
    moved = chars[4:] + chars[:4]
    return int("".join(str(int(ch, 36)) for ch in moved)) % MOD == 1


def bank_label_before(text: str, start: int) -> bool:
    """Say whether a bank's label, and no other number's, stands before a number.

    Why: a triple grouped by separators alone is a bank account only when a form says so; a
    phone's or an ID's label beside it says it is that number.

    Contract: `start` is the number's first character in `text`. Reads the labels in
    `israeli_id.window_before` (the 20 characters before it, on its line, after the last digit).
    True when at least one is of BANK_LABELS, with a proclitic or not, and none is of the ID
    detector's other labels (an ID's, a phone's, a company's, a passport's, ...).

    Known limits: those of `israeli_id.label_before`; a bank label after the number, or on the
    line before it, is not seen.
    """
    kinds = {match.lastgroup for match in LABEL.finditer(israeli_id.window_before(text, start))}
    return kinds == {"bank"}


def is_bank_account(match: re.Match[str], labelled: bool) -> bool:
    """Say whether a match of TRIPLE, under its label, is a bank account.

    Why: the decision of the detector on a triple, apart from the search, so each rule is tested
    by itself.

    Contract: `match`, a match of TRIPLE; `labelled`, what `bank_label_before` gives for it.
    True when a word stands between two of its numbers (its group branch_word or account_word
    matched); with none, when it is labelled, its bank has BANK_DIGITS digits, its branch
    BRANCH_DIGITS, and its shape is not a landline's (`israeli_id.is_other_shape`).

    Known limits: those of the module.
    """
    if match["branch_word"] is not None or match["account_word"] is not None:
        return True
    shaped = len(match["bank"]) == BANK_DIGITS and len(match["branch"]) == BRANCH_DIGITS
    return labelled and shaped and not israeli_id.is_other_shape(match.group())


class Iban:
    """The detector of IBANs and bank accounts, IBAN and BANK_ACCOUNT.

    Why: the fourth deterministic detector of Phase 1 (issue #34), registered in
    eval.detectors.DETECTORS last, after the credit card detector, so the held-out batch scores
    it and the T0 suite checks it.

    Contract: a Detector; `detect` returns the IBANs and the bank accounts, as the module
    docstring says.

    Known limits: those of the module.
    """

    name: ClassVar[str] = "iban"
    produces: ClassVar[frozenset[str]] = frozenset({IBAN, BANK_ACCOUNT})
    requires_morph: ClassVar[bool] = False

    def detect(self, proj: TextProjection, ctx: DetectContext) -> list[Detection]:
        """Find the IBANs and the bank accounts in the text of one projection.

        Why: the one call fusion makes of this detector.

        Contract: returns a Detection per IBAN and per triple, sorted by where each starts, with
        the part of `proj`, its surface the text of its span, no base span and detection_id ""
        (the module docstring gives each type's confidence, band and review flag). Raises
        nothing.

        Known limits: those of the module.
        """
        return sorted(self.ibans(proj) + self.accounts(proj), key=lambda found: found.span.start)

    def ibans(self, proj: TextProjection) -> list[Detection]:
        """Return the IBANs of one projection's text, in the order of the text.

        Why: the checksum-backed half of `detect`.

        Contract: one Detection per match of IBAN_CANDIDATE whose characters, the separators
        and the marks of direction taken out, pass `iban_ok`; type IBAN, CONFIDENCE, band "high".

        Known limits: those of the module.
        """
        return [
            Detection("", proj.part, Span(match.start(), match.end()), match.group(), IBAN, CONFIDENCE, "high", self.name, None)
            for match in IBAN_CANDIDATE.finditer(proj.text)
            if iban_ok(re.sub(_IBAN_GAP_CHAR, "", match.group()))
        ]

    def accounts(self, proj: TextProjection) -> list[Detection]:
        """Return the bank account triples of one projection's text, in the order of the text.

        Why: the pattern-only half of `detect`, flagged for review.

        Contract: one Detection per match of TRIPLE that `is_bank_account` accepts under
        `bank_label_before`, from its bank's first digit, and one per match of BY_NAME, from its
        branch's first digit, each to the account's last digit, sorted by where each starts; type
        BANK_ACCOUNT, CONFIDENCE_PATTERN, band "medium", needs_review True, review_reason
        REVIEW_REASON.

        Known limits: those of the module.
        """
        places = [
            Span(match.start(), match.end())
            for match in TRIPLE.finditer(proj.text)
            if is_bank_account(match, bank_label_before(proj.text, match.start()))
        ] + [Span(match.start("branch"), match.end("account")) for match in BY_NAME.finditer(proj.text)]
        return [
            Detection(
                "", proj.part, span, proj.text[span.start : span.end], BANK_ACCOUNT, CONFIDENCE_PATTERN, "medium",
                self.name, None, needs_review=True, review_reason=REVIEW_REASON,
            )  # fmt: skip
            for span in sorted(places, key=lambda span: span.start)
        ]
