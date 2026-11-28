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
and the account's (4 to 13 digits, with at most one separator but the plain space and the dot
between any two), in that order, and between each two either the words that name what follows (סניף before
the branch, after the bank's name in brackets when one stands there; חשבון, a possessive form of
it such as חשבונו, ח-ן or ח"ן before the account; with מס' or מספר, a proclitic, commas, colons
and brackets around them), or one separator, with a plain space on either side or none. On its
left no Latin letter, no digit, nor a digit and a separator; on its right no digit, nor a
separator but the plain space and a digit, nor a decimal part (a comma and one or two digits
that end there; a comma and another number is a list, and each account in it is found), nor a
currency (CURRENCY: ₪, ש"ח, ש.ח, NIS, שקל) after spaces: so an amount's decimal part or currency
refuses it. `is_bank_account` accepts it when a word stands
between two of its numbers, or, with none, when a bank label stands before it
(`bank_label_before`: חשבון, ח-ן, ח"ן, בנק or סניף, with no label of another number beside
it; or right after an accepted triple and LIST_GAP, a comma, a semicolon, ו-, וכן or a slash, as
in a list after one label), its bank has BANK_DIGITS digits and its branch BRANCH_DIGITS, and it is not written in a
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

A BANK_ACCOUNT is also a match of ALONE, an account written with no bank's number (issue #315;
Achia, 2026-11-27, "Yes, with the word (Recommended)": found when חשבון or ח-ן stands right
before it, with or without a branch, needs_review True): a word of ALONE_WORDS (חשבון, ח-ן, and
ח"ן read as its spelling; no possessive form, the review of #315 at d6bfbd6, finding 2), with
מס' or מספר, a proclitic, commas, colons and brackets around it as in TRIPLE, right before the
account's digits, as in TRIPLE with its right edge; and before that word, or not, סניף and the
branch's number (1 to 3 digits). `is_lone_account` accepts it with a branch; with none, when
the account word is a bank label and no other number's label stands beside it
(`bank_label_before` at the account's first digit), no other number follows it
(`israeli_id.NUMBER_AFTER`: separators, the plain space among them, and a digit), it is in at
most LONE_GROUPS groups of digits (three or more are a triple's shape, which TRIPLE judges),
it is not in a landline's shape (`israeli_id.is_other_shape`), and it is not another number
written so (`is_other_number`: a year, NNNN/YY, a range of years, a foreign currency after it,
"על חשבון" before it with no bank word near, a minus sign before it; the review's narrowings).
With a branch or none, it is refused where a detection of the phone detector starts at the
account (`Iban.alone` asks `phone.Phone().detect` once per projection): a phone after the
account word stays a phone, and no span is both.
Its span runs from the branch's first digit, or with no branch from the account's, to the
account's last; the words before them are read, never put in it. A match that shares a
character with an accepted triple or a match of BY_NAME is dropped: that one holds the account.
The same confidence, band and review flag.

`detect` returns the IBANs and the bank accounts in the order of the text.

Known limits: no check digit is applied to a triple: the banks' own check-digit rules are not
cited here, so none is invented (the brief of issue #34); a triple is found by its words and
labels only. The fewest digits of an account (ACCOUNT_SHORTEST, 4), the two digits of a bank and
the three of a branch with no word between, the three words of a bank's name and the run of
three separators in an IBAN are Claude's reading of how Israeli papers write them, with no
source; so is LONE_GROUPS. Not found: an account with no bank's number but with a word between
it and its account word (חשבון בנק, חשבון הבנק), or under no account word (סניף B A, a list's
second account after one word, "חשבון A, A2"), or under a possessive form with no bank's name
before (בחשבונו A, לחשבונה A, "סניף B חשבונו A": the review of #315 at d6bfbd6, finding 2,
"הכסף הופקד בחשבונו A" 1.000 before, 0.000 since; a triple and BY_NAME keep the possessive), or
with its word on the line before it or out of `israeli_id.window_before`, or with another number
after it by separators or a plain space ("חשבון A 3 עותקים"), or in three groups or more that
TRIPLE refuses, or written 0X-XXXXXXX, or of four digits from 1900 to 2099, or written NNNN/YY
(the review's script: a real account of four digits found 0.980; of five to nine, 1.000 after
every word and form it read); a
triple in another order (the account first); a triple grouped by
separators with no bank label before it, with a bank of one or three digits, or a branch of one
or two; a word between the numbers other than those listed (קוד בנק, a bar, the bank's name
between the branch and the account), or the words written with niqqud; a grouped triple in a
landline's shape (0X-XXX-XXXX) under a bank label, though a bank 04 or 09 is written so (a bank
01 to 09 with an account of four digits, grouped after חשבון, is found 0.442 of the time); an
account followed by an amount's decimal part or currency; an IBAN of another country (to be
found after this detector, by his answer of 2026-11-27 on issue #316, "Yes, all countries
(Recommended)"); an IBAN with
another number right after it by a separator but the plain space; an IBAN with a run of four
separators or marks or more inside it. A valid IBAN is found whatever stands around it; a run of
three numbers with סניף or חשבון between them is found as a triple whatever it is ("פרק 3 סניף 4
חשבון 2020" is one); so is any grouped triple's shape right after an accepted triple and
LIST_GAP, as numbers XX XXX XXXX after "<account>, ", " ו-", " וכן ", "; " or " / " (1.000 of
3,000 per gap; the other forms of the reviewer's pass3.py after each gap 0.000; pass 3 of the
review of #34, at a65350e). Measured on invented texts, 3,000 per form, by a scratch script that is not
in the repository (its table is in the text of this detector's PR, issue #34), at 4b2f0b4: IL
and 21 random digits give an IBAN 0.007 to 0.012 of the time in each of six written forms (the
check passes one in 97); and 0.000, IBAN and BANK_ACCOUNT alike, for each of: an ID after ת.ז.,
after חשבון (1.000 since issue #315, below), and written 3-3-3 after חשבון; a company number after ח.פ., and 2-6-1 after חשבון; a
card in fours after כרטיס and after חשבון; a landline 0X-XXX-XXXX with no label, after חשבון and
after "טלפון סניף הבנק", 0X XXX XXXX and 0X-XXXXXXX after חשבון; a mobile 05X-XXX-XXXX and
+972-5X-XXX-XXXX after חשבון; an amount XX XXX XXX, XX,XXX,XXX, XX.XXX.XXX, X XXX XXX XXX, XX XXX
XXX.XX and XX XXX XXXX ש"ח after בחשבון, and XX XXX XXX with no label; a case number
NNNNN-MM-YY, with and without חשבון before it, and NNNN/YY; a date DD.MM.YYYY and D/M/YY after
"חשבון מיום"; a bank by its name and a branch, then a balance after החשבון, or a date.
Since issue #315 a number of 4 to 13 digits, in one group or two, right after חשבון, ח-ן or
ח"ן, with no currency, decimal part or other number after it, and not one of `is_other_number`,
is found as an account whatever it is. Measured on invented texts, 3,000 per form after each of
חשבון, ח-ן, "חשבון מס'" and בחשבונו, by a scratch script that is not in the repository (its table
is in the text of this detector's PR, issue #315): found 1.000 after each but בחשבונו (0.000
there, a possessive form), an ID of nine digits; a company number of nine; an amount XXXXX with
no currency; a landline 0XXXXXXXX with no separator after חשבון and "חשבון מס'" (the phone
detector leaves nine digits under that label to the account), 0.000 after ח-ן (it takes them
there); and so the sentence "יתרה בחשבון XXXXX", a balance with no currency (and, by the
review's script, "יתרת החשבון N5" 1.000 and "לפי חשבון N4" 0.977). Found 0.000 after each: an
amount -XXXXX and XXXXX דולר, a case number NNNN/YY and a year (1.000 each before the review's
narrowings); an ID 3-3-3; a company number 2-6-1; a card in fours with spaces or hyphens, and of
sixteen digits; a landline 0X-XXXXXXX, 0X-XXX-XXXX and 0X XXX XXXX; a mobile 05X-XXX-XXXX,
05X-XXXXXXX, 05XXXXXXXX (since the phone detector is asked; 1.000 before) and +972-5X-XXX-XXXX; an amount
XX,XXX ש"ח, XX,XXX, X,XXX,XXX, XXXXX ש"ח, XXXXX ₪, XXXXX.XX, XXXXX,XX, XX XXX ש"ח, XX XXX XXX,
XX.XXX.XXX, X XXX XXX XXX, XX XXX XXX.XX and XX XXX XXXX ש"ח; a case number NNNNN-MM-YY; a date
DD.MM.YYYY, D.M.YYYY, DD/MM/YYYY and D/M/YY, and DD.MM.YYYY after מיום; an IBAN, paper and
electronic, as BANK_ACCOUNT; and the sentences "הופקדו לחשבון XX,XXX ש"ח", "יתרה בחשבון XX,XXX
ש"ח", "הופקדו לחשבון XXXXX ש"ח", "יתרה בחשבון XXXXX.XX ש"ח", "על חשבון XXXX ש"ח", "הופקדו
לחשבון XXXXX דולר", "יתרה בחשבון -XXXXX" and "על חשבון XXXX". No BANK_ACCOUNT shares a character
with a PHONE in any text of those forms and sentences (0 texts). An account alone of nine digits
right after ח-ן or ח"ן is also found by the Israeli ID or the company number detector when it
passes their check (the same script, 3,000 invented accounts per word: 0.107 after ח-ן, 0.099
after ח"ן, 0.102 after ח״ן; 0.000 after חשבון and "חשבון מס'"; accounts of 4 to 13 digits 0.006
to 0.013 after ח-ן and ח"ן, 0.001 after חשבון and "חשבון מס'", a few of them cards of thirteen
digits that the card detector finds; found 2,986 to 2,998 of 3,000 after each word but
בחשבונו, the four-digit years refused, and after "חשבון מס'" one number the phone detector
takes); so is a triple's account of nine digits after ח-ן or ח"ן, with words between (by the
reviewer's script of the review of #34 at 28b6032, 3,000 invented triples per form: 0.104 after
ח-ן, 0.088 after ח"ן, 0.104 after ח״ן; 0.000 after חשבון, and grouped after ח-ן): their labels
of other numbers do not hold ח-ן and ח"ן; treating them as another number's label there is a
follow-up named on issue #315. A long run of spaces or punctuation right after a digit is read
by TRIPLE in time that grows with the square of the run (its branch word, two runs of glue side
by side: 20,000 characters " ," after a digit, 17 s, on main as here): issue #321; ALONE starts
at its word and reads such a run in linear time (the review of #315, pass 2, finding 6). The
detection carries no id (detection_id is ""): ids are made just after detection, with
the matter's key, never inside a detector (Achia, 2026-11-26, issue #169, "Use the secret key
(Recommended)").
"""

from __future__ import annotations

import re
from typing import ClassVar

from ploni.detect.base import DetectContext
from ploni.detect.deterministic import israeli_id, phone
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
POSSESSIVE = r"חשבונ(?:ו|ה|ם|ן|י|נו|ך|כם)"
ACCOUNT_WORDS = (r"חשבון", POSSESSIVE, r"ח[-־–]ן", rf"ח{_GERSHAYIM}ן")
# The words before an account with no bank's number: Achia's "the word חשבון (or ח-ן)" (issue
# #315), ח"ן read as a spelling of ח-ן (Claude's reading); no possessive form (the review of #315
# at d6bfbd6, finding 2).
ALONE_WORDS = tuple(word for word in ACCOUNT_WORDS if word != POSSESSIVE)
# A word of a bank's name: Hebrew letters, with gershayim, geresh or a hyphen inside (בע"מ), and
# not סניף, with a proclitic or not. A name is one word to BANK_NAMES; Claude's reading, no source.
_NAME_WORD = r"(?![ובלהשמכ]{0,2}סניף)[א-ת][א-ת\"״'׳-]*"
BANK_NAMES = 3
_NAME = rf"{_NAME_WORD}(?:\s+{_NAME_WORD}){{0,{BANK_NAMES - 1}}}"
# The branch's word, after the bank's name in brackets when one stands there, "בנק 12 (לאומי) סניף".
_BRANCH_WORD = rf"{_GLUE}(?:\({_NAME}\))?{_GLUE}{_NO}{_BEFORE}(?:{'|'.join(BRANCH_WORDS)}){_AFTER}{_GLUE}{_NO}"
_ACCOUNT_WORD = rf"{_GLUE}{_NO}{_BEFORE}(?:{'|'.join(ACCOUNT_WORDS)}){_AFTER}{_GLUE}{_NO}"
_GAP = rf" ?{_SEP} ?"
# An account's digits, with a separator but the plain space and the dot between two of them: a dot
# and digits after them are an amount's decimal part (the review of #34 at 28b6032, finding 7).
_ACCOUNT_SEP = "[" + re.escape(SEPARATORS.replace(" ", "").replace(".", "")) + "]"
_ACCOUNT = rf"[0-9](?:{_ACCOUNT_SEP}?[0-9]){{{ACCOUNT_SHORTEST - 1},{ACCOUNT_LONGEST - 1}}}"
# The currency of an amount, after its number: the shekel's sign, ש"ח (any gershayim, or a dot),
# NIS, שקל (finding 7).
CURRENCY = (r"₪", rf"ש{_GERSHAYIM}ח", r"ש\.ח", r"NIS", r"שקל")
# What may not follow an account: a digit; a separator but the plain space and a digit; a decimal
# part, a comma and one or two digits with no digit, nor a separator and a digit, after them (a
# comma and another number is a list: pass 2 of the review of #34, at 0f6f0e7, item 8); spaces
# and a currency.
_DECIMAL = rf",[0-9]{{1,2}}(?![0-9]|{_SEP}[0-9])"
_ACCOUNT_END = rf"(?![0-9])(?!{_TIGHT}[0-9])(?!{_DECIMAL})(?!\s*(?:{'|'.join(CURRENCY)}))"
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
# An account with no bank's number, right after its word, and before the word, or not, סניף and
# the branch's number (issue #315). Its item runs from the branch's first digit, or the account's.
# A match starts at its word (or at סניף, or at מס' before the word), never in the glue before
# it: a start in the glue would be tried at every character of a run of spaces or punctuation,
# in time that grows with the square of the run (pass 2 of the review of #315 at adad401,
# finding 6: 20,000 characters " ," took 33 s). TRIPLE's word before a branch is issue #321.
_BRANCH = rf"{_BEFORE}(?:{'|'.join(BRANCH_WORDS)}){_AFTER}{_GLUE}{_NO}(?P<branch>[0-9]{{1,{BRANCH_LONGEST}}})"
_ALONE_WORD = rf"{_NO}{_BEFORE}(?:{'|'.join(ALONE_WORDS)}){_AFTER}{_GLUE}{_NO}"
ALONE = re.compile(rf"(?:{_BRANCH}{_GLUE})?{_ALONE_WORD}(?P<account>{_ACCOUNT}){_ACCOUNT_END}")
# An account alone is written in one group of digits, or two (a branch and an account together);
# in three or more it has a triple's shape, which TRIPLE judges. Claude's reading, no source.
LONE_GROUPS = 2
# What an account alone is not, though written right after its word: the review of #315 at
# d6bfbd6, finding 1, its narrowings N2, N3b, N4, N5, N6 and N9 (its measured costs are in the
# text of this detector's PR). A year: four digits from 1900 to 2099 (N2).
YEAR_DIGITS = 4
YEARS = range(1900, 2100)
# A case number written NNNN/YY exactly (N3b; build-plan.md Phase 1, "Court case numbers":
# "classic `<procedure> NNNN/NN`"), and a range of years, YYYY-YYYY or YYYY/YYYY (N9).
CASE_SHORT = re.compile(r"[0-9]{4}/[0-9]{2}")
YEAR_RANGE = re.compile(r"(?:19|20)[0-9]{2}[-/](?:19|20)[0-9]{2}")
# A foreign currency right after it, with spaces or none (N4): dollar, euro in two spellings, the
# dollar and euro signs, pound sterling (ליש"ט, any gershayim), pound.
FOREIGN_CURRENCY = re.compile(rf"\s*(?:דולר|אירו|יורו|\$|€|ליש{_GERSHAYIM}ט|פאונד)")
# "על חשבון", "on account of" a payment, right before it, with no bank or branch word in the
# BANK_NEAR characters before it (N5).
ON_ACCOUNT = re.compile(r"(?<![א-ת])על\s+חשבון\s*$")
BANK_NEAR_WORD = re.compile(r"בנק|סניף")
BANK_NEAR = 30
# A minus sign right before its digits, after a space or a colon: a balance below zero (N6).
MINUS = (" -", ":-")
# What stands between two accounts of a list after one label: a comma or a semicolon, a space,
# and the joining word ו ("and", with a hyphen or not) or וכן ("and also"), each optional; or a
# slash with a space on either side or none (item 8; pass 3 of the review of #34, at a65350e,
# finding 11: the account after ו-, וכן, ; or / was found 0.000). Claude's reading, no source.
LIST_GAP = re.compile(r"[,;]? ?(?:ו-?|וכן )?|\s?/\s?")
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


def is_lone_account(match: re.Match[str]) -> bool:
    """Say whether a match of ALONE, read in its own text, is a bank account.

    Why: the decision on an account written with no bank's number (issue #315), apart from the
    search, so each rule is tested by itself.

    Contract: `match`, a match of ALONE; its text is `match.string`. True when a branch stands
    before the account's word (its group branch matched); with none, when a bank label and no
    other number's stands before the account (`bank_label_before` at its first digit), no other
    number follows it (`israeli_id.NUMBER_AFTER` matches right after it), it is in at most
    LONE_GROUPS groups of digits, its shape is not a landline's (`israeli_id.is_other_shape`),
    and it is not another number written so (`is_other_number`).

    Known limits: those of the module.
    """
    if match["branch"] is not None:
        return True
    text, (start, end), raw = match.string, match.span("account"), match["account"]
    labelled = bank_label_before(text, start)
    beside = israeli_id.NUMBER_AFTER.match(text, end) is not None
    grouped = len(re.split(_SEP, raw)) <= LONE_GROUPS
    shaped = israeli_id.is_other_shape(raw) or is_other_number(text, start, end)
    return labelled and not beside and grouped and not shaped


def is_other_number(text: str, start: int, end: int) -> bool:
    """Say whether the digits right after an account word are another kind of number.

    Why: a year, a case number, an amount in a foreign currency, a payment "על חשבון" or a balance
    below zero is written right after חשבון too; the review of #315 at d6bfbd6 measured each found
    as an account 1.000 of the time and gave these narrowings, each for an account alone only.

    Contract: `text[start:end]`, the account's digits as written. True for four digits from 1900
    to 2099 (YEARS); NNNN/YY written exactly so (CASE_SHORT); a range of years (YEAR_RANGE); a
    foreign currency right after them (FOREIGN_CURRENCY); "על חשבון" right before them
    (ON_ACCOUNT, in `israeli_id.window_before`) with no בנק or סניף in the BANK_NEAR characters
    before them; a minus sign right before them after a space or a colon (MINUS). False
    otherwise.

    Known limits: a real account of four digits from 1900 to 2099, or written NNNN/YY, is not
    found alone; a balance with no currency after "יתרה בחשבון" or "יתרת החשבון" is still found,
    as is a number after "לפי חשבון" (the module's Known limits).
    """
    raw = text[start:end]
    digits = re.sub(r"[^0-9]", "", raw)
    year = len(digits) == YEAR_DIGITS and int(digits) in YEARS
    shaped = CASE_SHORT.fullmatch(raw) is not None or YEAR_RANGE.fullmatch(raw) is not None
    paid = ON_ACCOUNT.search(israeli_id.window_before(text, start)) is not None
    near_bank = BANK_NEAR_WORD.search(text, max(0, start - BANK_NEAR), start) is not None
    currency = FOREIGN_CURRENCY.match(text, end) is not None
    return year or shaped or currency or (paid and not near_bank) or text[start - 2 : start] in MINUS



class Iban:
    """The detector of IBANs and bank accounts, IBAN and BANK_ACCOUNT.

    Why: the fourth deterministic detector of Phase 1 (issue #34), registered in
    eval.detectors.DETECTORS after the credit card detector and before the phone detector, so
    the held-out batch scores it and the T0 suite checks it.

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
        `bank_label_before` (a match that follows an accepted one with only LIST_GAP between
        them counts as labelled: a list after one label), from its bank's first digit, one per
        match of BY_NAME, from its branch's first digit, and one per place of `alone` that shares
        no character with those, each to the account's last digit, sorted by where each starts;
        type BANK_ACCOUNT, CONFIDENCE_PATTERN, band "medium", needs_review True, review_reason
        REVIEW_REASON.

        Known limits: those of the module.
        """
        places: list[Span] = []
        for match in TRIPLE.finditer(proj.text):
            listed = bool(places) and LIST_GAP.fullmatch(proj.text, places[-1].end, match.start()) is not None
            if is_bank_account(match, listed or bank_label_before(proj.text, match.start())):
                places.append(Span(match.start(), match.end()))
        places += [Span(match.start("branch"), match.end("account")) for match in BY_NAME.finditer(proj.text)]
        places += [span for span in self.alone(proj) if not any(span.start < p.end and p.start < span.end for p in places)]
        return [
            Detection(
                "", proj.part, span, proj.text[span.start : span.end], BANK_ACCOUNT, CONFIDENCE_PATTERN, "medium",
                self.name, None, needs_review=True, review_reason=REVIEW_REASON,
            )  # fmt: skip
            for span in sorted(places, key=lambda span: span.start)
        ]

    def alone(self, proj: TextProjection) -> list[Span]:
        """Return the places of the accounts with no bank's number in one projection's text, in the order of the text.

        Why: the half of `accounts` that Achia's answer of 2026-11-27 on issue #315 adds, "Yes,
        with the word (Recommended)".

        Contract: one Span per match of ALONE in `proj.text` that `is_lone_account` accepts and
        where no detection of the phone detector starts at its account (`phone.Phone().detect`,
        called once on `proj` with an empty context: a phone after the account word stays a
        phone, and no span is both, #36); from the branch's first digit when its group branch
        matched, else from the account's, to the account's last digit.

        Known limits: those of the module, and of the phone detector: under חשבון it leaves a
        number of nine digits or fewer to the account, so a landline of nine digits right after
        חשבון is an account here.
        """
        phones = {found.span.start for found in phone.Phone().detect(proj, DetectContext())}
        places = []
        for match in ALONE.finditer(proj.text):
            start, end = match.span("account")
            if start not in phones and is_lone_account(match):
                places.append(Span(match.start("branch") if match["branch"] is not None else start, end))
        return places
