# Span rules of the held-out batch

Written by the batch's writer, by Achia's answer of 2026-11-26 on issue 283 ("Yes, the rules only (Recommended)": "The writer writes one rule per type ..., checked by the reviewer to quote nothing from the batch. I build the detectors to those rules."). These rules bind the detectors: a detection is scored against the stretch of text each rule names. They give no example and no value, on purpose.

## For every type

- A span is counted in code points of the document's text as given, start included, end excluded.
- A span never starts or ends with a space, and never takes in the punctuation around the item: a closing full stop, comma, colon, bracket or quotation mark stays out, except a mark that is part of the item itself (the dots of PLACEHOLDER initials, the brackets around a PHONE area code, below).
- A Hebrew proclitic letter glued to the front of an item (as ב, ל, כ, ו) is out of the span; the span starts at the letter after it.
- A label, a trigger word or a title before an item is out, and so is the proclitic glued to that label.
- Gershayim and geresh are written in the batch both as the ASCII marks and as the Hebrew signs. Where a rule takes them in, it takes in either form; the rule is the same.
- Separators between the digits of a number (hyphen, space, dot, slash) are in, wherever the rule says "the number".

## Per type

| Type | The span covers |
|---|---|
| IL_ID | The number only: its first digit to its last, separators between them included. Not the label. |
| COMPANY_NUMBER | The number only, as for IL_ID. Not the label, not the company's name. |
| NONPROFIT_NUMBER | The number only, as for IL_ID. Not the label, not the association's name. |
| IBAN | From the two country letters to the last character of the account, the spaces inside it included. Not a label. |
| BANK_ACCOUNT | From the first digit of the bank's number to the last digit of the account: the separators between the three numbers are in, and so are words that name the branch and the account when they stand between them. Not a label or a word before the first number. |
| CREDIT_CARD | The number only: first digit to last, separators between included. Not the label. |
| PHONE | The number from its first character to its last digit: a leading plus sign of an international prefix, a leading star, and brackets around the area code are in; separators are in. Not the label. |
| EMAIL | The whole address, from the first character of the part before the at sign to the last character of the domain. |
| URL | The whole address, from its first character (the scheme when there is one, else the host) to the last character of its path or query. |
| IP_ADDRESS | The dotted address, first digit to last. |
| IL_PLATE | The number only, separators between the digits included. Not a trigger word. |
| CASE_NUMBER | The procedure's abbreviation with its gershayim, the space after it, and the number, to its last digit. Not a word before it; a proclitic glued to the abbreviation is out. |
| GUSH_HELKA | From the word גוש to the last digit of the last number of the parcel (the helka, or the sub-parcel when one is given), all words, numbers and punctuation between them included. A proclitic glued to גוש is out. |
| DATE | The whole date, from its first character to its last: for a date in digits, first digit to last with the separators; for a date with a month name, in either calendar, from the day to the year, every word between included, with the gershayim and geresh of the day and the year. Not a word before it. |
| AMOUNT | The number, or the written-out number words, together with the currency sign or word, on whichever side the currency stands, with any space between them; thousands separators and decimals are in. Not a word before it. |
| ADDRESS | From the word for street or avenue, or its abbreviation with its geresh, when one stands there, else from the street's name, to the last letter of the city's name: the house number, and any comma between, are in. A proclitic glued to the first word is out. |
| PERSON | The name only, after its trigger: the given name, the family name, or both with the space between, as written, with any geresh or niqqud inside it. The trigger (a title or a role) is out. |
| PERSON_UNTITLED | A name that stands once in its document with no trigger or title before it: the given name and the family name with the space between, as written, with any geresh or niqqud inside it. |
| PLACEHOLDER | The placeholder whole: a placeholder word, or two such words that stand together, as one item; initials with every dot, the last one included; a run of underscores whole. A title before it is out. |
| HEALTH_FUND_ID | The number only. Not the label. |
| MILITARY_ID | The number only. Not the label. |
| PASSPORT_NUMBER | The number only, and letters that are part of it when it has them. Not the label. |

Every type's rule is given; none is "not given". How a detection is counted against these spans is the scorer's, and is written with it.
