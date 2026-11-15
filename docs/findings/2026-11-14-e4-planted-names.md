# Finding: E4 PERSON recall on planted names is 94.67 percent (1,084 of 1,145), inside the predicted 90 to 96; four Claude readers agree with the planted truth on 123 of 123 items; the readers' list of hints holds all 57 mentions the model missed, so a reader who has that list never has to find a missed name alone in this text

This note is not about a gate that failed. All three parts came out inside their predictions. It is written because the pre-registration says the result is reported in a findings note with `## Decision` left empty, and because E4 now stands where a person's check of E1 was meant to stand. Whether that is enough is Achia's decision.

## What was being measured

E1 measured 449 of 470 person mentions found on ten real judgments (`docs/findings/2026-11-13-e1-hebrew-recall.md`). Claude readers made that count and no person checked it. On 2026-11-14 Achia asked for something else in place of the check: "create a method to verify it and have a ground truth so i dont need to involve like that".

E4 is that method. A script writes 40 Hebrew documents from eight templates and puts every name in its place, so the right answer is known before the model runs. Nobody reads anything in order to count. Text and names are invented by Claude; no sentence is from a real document.

It measures three things. The third was added on 2026-11-14, after this note was first merged:

1. **The model.** `dicta-il/dictabert-joint` at E1's revision, with E1's input handling and E1's strict rule: a mention is found only if `PER` spans cover every character of the name.
2. **The readers.** Four of the 40 documents are counted by fresh Claude sessions in the way E1's documents were counted. A script then compares each reader's files with the planted names.
3. **The readers' list.** E1's readers and these readers were given a list of places that may hold a missed name. A script makes that list for all 40 documents and counts how many of the mentions the model missed are on it.

The rules are in `experiments/e4_planted_names/PREREGISTRATION.md`. It was committed before any template was written, and amended twice: after the review of the harness and before any run, and, for the third part, after the first two parts were reported and before the list of the other 36 documents was made.

## Prediction and threshold

As stated before the run. Achia set none; these are Claude's.

| What | Prediction | Threshold |
|---|---|---|
| Strict recall, pooled | 90 to 96 percent | below 80 percent |
| Against E1 (449/470 = 95.53 percent) | within 10 points | more than 10 points under E1 |
| `group`: a surname after `האחים` or `משפחת` | under 50 percent | none |
| `given_ordinary`: a given name alone that is an everyday word | 60 to 90 percent | none |
| `full`, `surname`, `title_surname`, `initial_surname`, `given_plain`, `prefix_on_name`, `prefix_on_title`, `alone` | 90 percent or more, each | none |
| Reader against gold, over four documents | 98 percent agreement or more | below 95 percent: the E1 note is amended to say its count is not supported |
| Third part: missed mentions that are on the readers' list | 90 percent or more. Not a blind prediction: Claude knew where the 57 misses were and expected 55 to 57 | below 80 percent: the E1 note is amended |

## Measured result

### Against the predictions

| What | Prediction | Measured | |
|---|---|---|---|
| Strict recall, pooled | 90 to 96 | 1084/1145 = 94.67% | inside |
| Against E1 | within 10 points | 0.86 points under | inside |
| `group` | under 50 | 22/55 = 40.00% | held |
| `given_ordinary` | 60 to 90 | 151/169 = 89.35% | held |
| `full` | 90 or more | 408/410 = 99.51% | held |
| `surname` | 90 or more | 119/120 = 99.17% | held |
| `title_surname` | 90 or more | 204/205 = 99.51% | held |
| `initial_surname` | 90 or more | 61/65 = 93.85% | held |
| `given_plain` | 90 or more | 95/96 = 98.96% | held |
| `prefix_on_name` | 90 or more | 62/64 = 96.88% | held |
| `prefix_on_title` | 90 or more | 95/95 = 100.00% | held |
| `alone` | 90 or more | 131/135 = 97.04% | held |
| Reader against gold | 98 or more | 123/123 = 100.00% | inside |
| Missed mentions on the readers' list | 90 or more | 57/57 = 100.00% | inside |

No threshold is crossed. Every prediction held.

### The run

Run once, on Achia's laptop, from `main` at `c05133a`, offline:

```
experiments/.venv/Scripts/python.exe -I experiments/e4_planted_names/run.py --model-dir models/dictabert-joint/7b1256fc0846e22d1af431eae299e2dcecee2778 --list-errors --worksheets-dir <private folder>
```

The output as printed. Its SHA-256 is `414cab2b144e0512d4320f4893da973937cf4c45d41a76f9a613fd553411e825`. Names are printed because every one of them is generated.

```
E4 planted names, model revision 7b1256fc0846e22d1af431eae299e2dcecee2778
model.safetensors sha256 c59db02c002b69fd3c072c310e3ba578d036386477248d1c8576d896cc06aa1c
config.json sha256 507f247f97ccaed18308054d58b5f063dd2cc01e69204d13218703dc2512932c
tokenizer.json sha256 4e520fd9025a2fd5f2dce1d04df5922954c8ff050cc3e67d4bc54a7347eccb32
code c05133a3c5b112c827d3fca9d909bdaa8c34ce7b
torch 2.15.0+cpu, transformers 5.22.2, threads 4
corpus: 40 documents, 1035 paragraphs, 1145 counted mentions, 55 names that are not counted, seed e4-2026-11-14
windows 1035, cut paragraphs 0, hard cuts 0, unknown pieces 0, seconds 420.9
documents: 40
strict PERSON recall, pooled: 1084/1145 = 94.67%
verdict: inside_prediction (prediction 90 to 96 percent, threshold below 80 percent)
against E1 (449/470): within_10_points_of_e1
lenient recall (partial counted as found): 1088/1145 = 95.02%
any-label recall: 1096/1145 = 95.72%
errors: 61 (partial 4, missed 57, of them under another label 12)
by form:
  full  408/410 = 99.51%
  given  270/290 = 93.10%
  surname  119/120 = 99.17%
  title_surname  204/205 = 99.51%
  initial_surname  61/65 = 93.85%
  group  22/55 = 40.00%
by trait:
  given_ordinary  151/169 = 89.35%
  given_also_word  24/25 = 96.00%
  given_plain  95/96 = 98.96%
  prefixed  205/230 = 89.13%
  prefix_on_name  62/64 = 96.88%
  prefix_on_title  95/95 = 100.00%
  alone  131/135 = 97.04%
by name class:
  also_word  152/159 = 95.60%
  arabic  108/112 = 96.43%
  ordinary  384/411 = 93.43%
  prefix_initial  476/506 = 94.07%
  translit  150/157 = 95.54%
  no_class  195/204 = 95.59%
by kind of document:
  judgment  317/330 = 96.06%
  contract  266/285 = 93.33%
  letter  242/255 = 94.90%
  medical  259/275 = 94.18%
by template:
  contract_employment  140/145 = 96.55%
  contract_lease  126/140 = 90.00%
  judgment_accident  159/160 = 99.38%
  judgment_contract  158/170 = 92.94%
  letter_client  127/130 = 97.69%
  letter_demand  115/125 = 92.00%
  medical_discharge  135/145 = 93.10%
  medical_opinion  124/130 = 95.38%
mentions not found:
  doc01 contract_employment ¶26 partial initial_surname [ר' שפירא] :: אישור: אני מאשר כי ההסכם נחתם בפניי. ר' שפירא, עו"ד
  doc02 contract_employment ¶11 missed given [שיר] :: נה אישור בכתב של מר מקסים מילר או של מר ולדימיר מילר; הבטחה בעל פה של שיר אינה מחייבת את החברה.
  doc02 contract_employment ¶13 missed group_brothers [מילר] :: שיגיע לידיה על לקוחות החברה, ובכלל זה מידע על עסקיהם הפרטיים של האחים מילר.
  doc03 contract_employment ¶11 missed given [מעיין] :: ונה אישור בכתב של מר ולדימיר בלום או של מר ג'ון בלום; הבטחה בעל פה של מעיין אינה מחייבת את החברה.
  doc03 contract_employment ¶15 missed given [למעיין] :: ד רשאי לסיים את ההסכם בהודעה מוקדמת של שישים יום. הודעת העובדת תימסר למעיין בכתב; הודעת החברה תיחתם בידי ולדימיר בלום.
  doc06 contract_lease ¶17 missed group_family [בלום] :: 6. המשכיר מצהיר כי אין כל מניעה להשכיר את הדירה, וכי משפחת בלום מחזיקה בה כדין מאז שנת 2011.
  doc06 contract_lease ¶20 missed group_family [לבלום] :: ה כשהיא פנויה מכל אדם וחפץ. לא פינה לנדאו את הדירה במועד, ישלם למשפחת בלום פיצוי מוסכם של 500 ש"ח לכל יום איחור.
  doc07 contract_lease ¶17 missed group_family [עבאס] :: 6. המשכיר מצהיר כי אין כל מניעה להשכיר את הדירה, וכי משפחת עבאס מחזיקה בה כדין מאז שנת 2011.
  doc07 contract_lease ¶18 missed title_surname [קוזנצוב] :: חלוקת בעניין זה תובא להכרעת מהנדס מוסכם, ובהיעדר הסכמה ימנה אותו עו"ד קוזנצוב.
  doc07 contract_lease ¶20 missed group_family [לעבאס] :: ירה כשהיא פנויה מכל אדם וחפץ. לא פינה שמש את הדירה במועד, ישלם למשפחת עבאס פיצוי מוסכם של 500 ש"ח לכל יום איחור.
  doc08 contract_lease ¶15 missed given [לשיר] :: ת ההסכם, וכי היא ערבה לכל התחייבויות השוכר על פיו. המשכיר רשאי לפנות לשיר במישרין, בלי לפנות תחילה אל ברק.
  doc08 contract_lease ¶17 missed group_family [מולר] :: 6. המשכיר מצהיר כי אין כל מניעה להשכיר את הדירה, וכי משפחת מולר מחזיקה בה כדין מאז שנת 2011.
  doc08 contract_lease ¶20 missed other_label group_family [למולר] ::  כשהיא פנויה מכל אדם וחפץ. לא פינה בן דוד את הדירה במועד, ישלם למשפחת מולר פיצוי מוסכם של 500 ש"ח לכל יום איחור.
  doc09 contract_lease ¶17 missed other_label group_family [אלון] :: 6. המשכיר מצהיר כי אין כל מניעה להשכיר את הדירה, וכי משפחת אלון מחזיקה בה כדין מאז שנת 2011.
  doc09 contract_lease ¶20 missed other_label group_family [לאלון] :: ה כשהיא פנויה מכל אדם וחפץ. לא פינה אוחנה את הדירה במועד, ישלם למשפחת אלון פיצוי מוסכם של 500 ש"ח לכל יום איחור.
  doc10 contract_lease ¶4 missed full [ודינה שלום] :: ודינה שלום
  doc10 contract_lease ¶16 missed given [דינה] :: א יבצע שינויים בדירה בלא הסכמה מראש ובכתב. הסכמה שניתנה בעל פה על ידי דינה או על ידי בנימין, לא יהיה לה תוקף.
  doc10 contract_lease ¶17 missed group_family [שלום] :: 6. המשכיר מצהיר כי אין כל מניעה להשכיר את הדירה, וכי משפחת שלום מחזיקה בה כדין מאז שנת 2011.
  doc10 contract_lease ¶20 missed group_family [לשלום] :: כשהיא פנויה מכל אדם וחפץ. לא פינה גולדברג את הדירה במועד, ישלם למשפחת שלום פיצוי מוסכם של 500 ש"ח לכל יום איחור.
  doc12 judgment_accident ¶2 partial title_initial_surname [נ' גולדברג] :: לפני כבוד השופט נ' גולדברג
  doc16 judgment_contract ¶12 missed other_label group_brothers [סעדי] :: 1. לפניי תביעה כספית שהגישו האחים סעדי נגד גב' אוחנה, בגין הפרת הסכם לשיפוץ דירה ברחוב הגפן בחיפה.
  doc16 judgment_contract ¶16 missed given [וכששיר] :: מוחמד זועבי. לדברי זועבי, ביום 3.8.2021 מצא את הדירה ריקה מפועלים, וכששיר הגיעה למקום סירבה לשוחח עמו. בחקירתו הנגדית אישר מוחמד כי לא ראה את ה
  doc17 judgment_contract ¶12 missed other_label group_brothers [מלכה] :: 1. לפניי תביעה כספית שהגישו האחים מלכה נגד גב' סויסה, בגין הפרת הסכם לשיפוץ דירה ברחוב הגפן בחיפה.
  doc17 judgment_contract ¶16 missed given [וכשורד] ::  סאמי מנסור. לדברי מנסור, ביום 3.8.2021 מצא את הדירה ריקה מפועלים, וכשורד הגיעה למקום סירבה לשוחח עמו. בחקירתו הנגדית אישר סאמי כי לא ראה את הה
  doc18 judgment_contract ¶12 missed other_label group_brothers [גולדברג] :: 1. לפניי תביעה כספית שהגישו האחים גולדברג נגד גב' שוורץ, בגין הפרת הסכם לשיפוץ דירה ברחוב הגפן בחיפה.
  doc18 judgment_contract ¶16 missed given [וכשעדן] ::  סאמי ח'טיב. לדברי ח'טיב, ביום 3.8.2021 מצא את הדירה ריקה מפועלים, וכשעדן הגיעה למקום סירבה לשוחח עמו. בחקירתו הנגדית אישר סאמי כי לא ראה את הה
  doc19 judgment_contract ¶12 missed other_label group_brothers [אזולאי] :: 1. לפניי תביעה כספית שהגישו האחים אזולאי נגד גב' כרמי, בגין הפרת הסכם לשיפוץ דירה ברחוב הגפן בחיפה.
  doc19 judgment_contract ¶16 missed given [וכשעדן] :: י רוזנברג. לדברי רוזנברג, ביום 3.8.2021 מצא את הדירה ריקה מפועלים, וכשעדן הגיעה למקום סירבה לשוחח עמו. בחקירתו הנגדית אישר שי כי לא ראה את ההסכ
  doc19 judgment_contract ¶25 missed full [שיר שמש] :: שיר שמש
  doc20 judgment_contract ¶12 missed other_label group_brothers [הורוביץ] :: 1. לפניי תביעה כספית שהגישו האחים הורוביץ נגד גב' אלון, בגין הפרת הסכם לשיפוץ דירה ברחוב הגפן בחיפה.
  doc20 judgment_contract ¶16 missed given [וכששירה] :: ר דקל קליין. לדברי קליין, ביום 3.8.2021 מצא את הדירה ריקה מפועלים, וכששירה הגיעה למקום סירבה לשוחח עמו. בחקירתו הנגדית אישר דקל כי לא ראה את ההס
  doc20 judgment_contract ¶18 missed given [נתן] :: . עדותו של גל הייתה עקבית, ונתמכה במסרונים שהוחלפו בינו לבין אלון. גם נתן העיד באופן סדור, ולא נסתר בחקירתו.
  doc23 letter_client ¶7 missed given [שיר] :: שיר שלום רב,
  doc23 letter_client ¶14 missed other_label surname [מח'טיב] :: 6. לאחר הדיון קיבלתי מח'טיב הצעה לסיים את התיק בפשרה, שלפיה ישלם רון לוי סך של 220,000 ש"ח בארבעה
  doc24 letter_client ¶15 missed given [לילך] :: 7. אני ממליץ, לילך, שלא להשיב להצעה לפני שתתקבל חוות הדעת. ככל שהמומחית תאשר את חישובינו
  doc26 letter_demand ¶11 missed group_family [לגבאי] :: לעסק המשפחתי. ההלוואה ניתנה על יסוד היכרות ארוכת שנים בין וייס למשפחת גבאי.
  doc26 letter_demand ¶17 missed group_family [גבאי] :: וט נגדך ונגד ענת הליכים משפטיים, לרבות בקשה להטלת עיקול על נכסי משפחת גבאי.
  doc27 letter_demand ¶11 missed group_family [לשגיא] :: עסק המשפחתי. ההלוואה ניתנה על יסוד היכרות ארוכת שנים בין מנסור למשפחת שגיא.
  doc27 letter_demand ¶17 missed group_family [שגיא] :: וט נגדך ונגד רות הליכים משפטיים, לרבות בקשה להטלת עיקול על נכסי משפחת שגיא.
  doc28 letter_demand ¶11 missed group_family [לבן שושן] :: ק המשפחתי. ההלוואה ניתנה על יסוד היכרות ארוכת שנים בין רוזנברג למשפחת בן שושן.
  doc28 letter_demand ¶17 missed group_family [בן שושן] :: קוט נגדך ונגד חן הליכים משפטיים, לרבות בקשה להטלת עיקול על נכסי משפחת בן שושן.
  doc29 letter_demand ¶11 missed group_family [לביטון] :: ק המשפחתי. ההלוואה ניתנה על יסוד היכרות ארוכת שנים בין גולדברג למשפחת ביטון.
  doc29 letter_demand ¶17 missed group_family [ביטון] :: וט נגדך ונגד ורד הליכים משפטיים, לרבות בקשה להטלת עיקול על נכסי משפחת ביטון.
  doc30 letter_demand ¶11 missed group_family [לסגל] :: לעסק המשפחתי. ההלוואה ניתנה על יסוד היכרות ארוכת שנים בין קפלן למשפחת סגל.
  doc30 letter_demand ¶17 missed group_family [סגל] ::  נגדך ונגד אורית הליכים משפטיים, לרבות בקשה להטלת עיקול על נכסי משפחת סגל.
  doc31 medical_discharge ¶13 missed given [תום] :: ביום השני שלאחר הניתוח התלונן תום על כאב בכתף ימין. בן דוד בדקה אותו ושללה סיבוך; הכאב חלף לאחר טיפול ב
  doc31 medical_discharge ¶22 missed group_family [אלמוג] :: 5. ברקוביץ תיצור קשר עם משפחת אלמוג בתוך שבוע, לבירור הצורך בסיוע בבית.
  doc31 medical_discharge ¶24 missed given [לתום] ::  לבא כוחו, עו"ד צבי זהבי (משרד נחום ושות'), לצורך תביעת ביטוח. הובהר לתום כי הדבר טעון חתימה על טופס ויתור סודיות, והוא חתם עליו בנוכחות יונה.
  doc32 medical_discharge ¶22 missed group_family [קליין] :: 5. כהן תיצור קשר עם משפחת קליין בתוך שבוע, לבירור הצורך בסיוע בבית.
  doc33 medical_discharge ¶22 missed group_family [נוי] :: 5. הראל תיצור קשר עם משפחת נוי בתוך שבוע, לבירור הצורך בסיוע בבית.
  doc34 medical_discharge ¶11 missed given [באור] :: בקבלתו נבדק אור על ידי ד"ר גבאי. הטיפול האנטיביוטי באור החל עוד במיון. בבדיקת על-קול נמצאו אבנים בכיס המרה וסימני דלקת חריפה.
  doc34 medical_discharge ¶16 missed given [לאור] :: יתר לחץ דם מטופל תרופתית. לפי מכתב ההפניה של ד"ר אדלר, לאור אין רגישות ידועה לתרופות.
  doc34 medical_discharge ¶24 missed given [לאור] ::  עו"ד גדעון בן שושן (משרד רבינוביץ' ושות'), לצורך תביעת ביטוח. הובהר לאור כי הדבר טעון חתימה על טופס ויתור סודיות, והוא חתם עליו בנוכחות סמירה.
  doc35 medical_discharge ¶22 missed group_family [אזולאי] :: 5. פרידמן תיצור קשר עם משפחת אזולאי בתוך שבוע, לבירור הצורך בסיוע בבית.
  doc35 medical_discharge ¶26 partial title_initial_surname [ג' קוזנצוב] :: ד"ר ג' קוזנצוב
  doc36 medical_opinion ¶20 missed other_label group_brothers [אוחנה] :: 12. האחים אוחנה ביקשו לקבל העתק מחוות הדעת, והוא יימסר להם באמצעות בא כוחם.
  doc36 medical_opinion ¶22 partial title_initial_surname [ג' ביטון] :: ד"ר ג' ביטון
  doc38 medical_opinion ¶20 missed other_label group_brothers [אזולאי] :: 12. האחים אזולאי ביקשו לקבל העתק מחוות הדעת, והוא יימסר להם באמצעות בא כוחם.
  doc39 medical_opinion ¶11 missed given [לשיר] :: קת, מאז הנפילה היא סובלת מכאבי ראש יומיומיים ומסחרחורות. אריה מסר כי לשיר קשה להתרכז, וכי חדלה לנהוג.
  doc40 medical_opinion ¶11 missed given [לשיר] :: קת, מאז הנפילה היא סובלת מכאבי ראש יומיומיים ומסחרחורות. עמוס מסר כי לשיר קשה להתרכז, וכי חדלה לנהוג.
  doc40 medical_opinion ¶20 missed other_label group_brothers [אוחיון] :: 12. האחים אוחיון ביקשו לקבל העתק מחוות הדעת, והוא יימסר להם באמצעות בא כוחם.
worksheets written for doc01, doc11, doc21, doc31
```

### The 61 errors, by kind

Counted from the list above against the gold, by a throwaway script that is not in the repository. Anyone can count them again from the list.

| Kind | Errors | Of | Found |
|---|---|---|---|
| A surname after `משפחת`, no prefix letter on the word | 14 | 15 | 1/15 |
| A surname after `משפחת`, prefix letter on the word (`למשפחת`) | 10 | 10 | 0/10 |
| A surname after `האחים`, no prefix letter | 9 | 15 | 6/15 |
| A surname after `האחים`, prefix letter on the word | 0 | 15 | 15/15 |
| A given name alone, everyday word, with prefix letters | 13 | 46 | 33/46 = 71.74% |
| A given name alone, everyday word, no prefix | 5 | 123 | 118/123 = 95.93% |
| Everything else | 10 | 921 | 911/921 = 98.91% |
| All | 61 | 1,145 | 1084/1145 = 94.67% |

- **Group terms: 33 errors.** 11 of them carry another label, 22 carry none. `משפחת` and a surname is found once in 25 places.
- **A given name that is an everyday word: 18 errors.** 13 carry prefix letters: `ל` 7 times, `וכש` 5 times (all five places it stands), `ב` once. By name, missed of standing alone: `שיר` 6 of 19, `אור` 3 of 10, `מעיין` 2 of 2, `עדן` 2 of 12, `תום` 2 of 13, `ורד` 1 of 10, `שירה` 1 of 3, `לילך` 1 of 5.
- **The other 10.** Four partials, all an initial with a surname (`ר' שפירא`). Two full names alone on a line, both with an everyday word as surname (`שלום`, `שמש`). One surname with a prefix, under another label (`מח'טיב`). One surname after `עו"ד`. Two given names alone: `נתן`, `דינה`.
- 10 of the 40 documents have no error. The most in one document is 4.

Five fillings of a template share every sentence, so these rows are not independent draws. `וכש` stands in one sentence, filled five times. `משפחת` stands in five sentences.

### Against E1

| | E1, ten real judgments | E4, 40 generated documents |
|---|---|---|
| Strict recall | 449/470 = 95.53% | 1084/1145 = 94.67% |
| `האחים` and a surname | 1/14 | 21/30 |
| A family surname for a group | 6/6 | 1/25 |
| Both kinds of group term | 7/20 | 22/55 |
| Without the group terms | 442/450 = 98.22% | 1062/1090 = 97.43% |
| How the count was made | Claude readers, not checked | a script, from planted positions |

The E1 column is from the E1 note, table of doubtful cases: "14 places, 1 found", "highlights 29 to 34, all found", "Both: 442 of 450". The rows below the first are arithmetic on measured counts.

Pooled, group terms are weak in both. By wording the two disagree, both ways: `האחים` and a surname is almost never found in E1 and mostly found here; a family surname is always found in E1 and almost never here. The E1 places are other sentences, in one document each. This note does not explain the difference. What both show is that a surname after a group word cannot be relied on.

The pre-registered test against E1 was "within 10 points", and it held. That the two numbers are 0.86 points apart says less than it seems. The pooled number here is a mean of two groups: the two weak kinds, 173/224 = 77.23 percent, and the rest, 911/921 = 98.91 percent. Claude chose how much of each the templates hold.

### The second part

In the order it happened:

1. The run above wrote worksheets and span lists for `doc01`, `doc11`, `doc21` and `doc31` into a folder outside the repository. E1's throwaway script, which is not in the repository, then made what E1's readers also had: a plain-text worksheet, and a **cross-check list** of places that may hold a missed name. It holds two kinds of place, as in E1 (E1 note, "The cross-check"): a word that the model highlighted as a person somewhere in the document, where it stands without a highlight; and a word after a title that has no highlight. No file in the folder holds a gold position.
2. Four fresh Claude sessions, one per document, counted them with E1's guide. Each was told the folder and told not to open `experiments/e4_planted_names/`. The brief also said: "every natural person named in it is a counted mention; a name in the title of a cited decision, a name inside the name of a firm, and a placeholder are not." The guide holds these rules among others. They are also the three kinds of name the generator plants as not counted, and the session that wrote the brief knew that.
3. Each reader's final answer came back to the writing session with its counts (for `doc31`: three missed, in paragraphs 13, 22 and 24). That was before the comparison script was written, and the writing session knows the gold. What protects the result is that the rule of the comparison was fixed in the pre-registration before the run (`c05133a`), and that file is unchanged since.
4. The comparison script `reader_check.py` was written with tests, reviewed in three passes by a session that was told not to open the readers' folder, and merged (PR #56, `4c0a281`). Until then neither the writing session nor the reviewer opened a reader's file.
5. The script was run once, from `main` at `4c0a281`:

```
experiments/.venv/Scripts/python.exe -I experiments/e4_planted_names/reader_check.py --folder <private folder>
```

The output as printed. Its SHA-256 is `399498e92c56609c066eabbefda9cca011d20483831c17f9f14f048113f91fed`.

```
doc01: gold items 30, agreeing 30, reader-only 0, agreement 30/30 = 100.00%
doc11: gold items 35, agreeing 35, reader-only 0, agreement 35/35 = 100.00%
doc21: gold items 28, agreeing 28, reader-only 0, agreement 28/28 = 100.00%
doc31: gold items 30, agreeing 30, reader-only 0, agreement 30/30 = 100.00%
reader against gold, pooled: 123/123 = 100.00%
verdict: inside_prediction (prediction 98 percent or more, threshold below 95 percent)
disagreements:
  none
```

What the four documents held, counted after the comparison by a throwaway script:

| | doc01 | doc11 | doc21 | doc31 | All |
|---|---|---|---|---|---|
| Template | contract_employment | judgment_accident | letter_client | medical_discharge | |
| Paragraphs | 27 | 27 | 22 | 27 | 103 |
| Characters | 1,742 | 1,902 | 1,570 | 1,560 | 6,774 |
| Counted mentions | 29 | 32 | 26 | 29 | 116 |
| of them the model found | 28 | 32 | 26 | 26 | 112 |
| of them partial | 1 | 0 | 0 | 0 | 1 |
| of them missed, no highlight | 0 | 0 | 0 | 3 | 3 |
| of those, on the cross-check list | | | | 3 | 3 |
| Rows of the cross-check list | 0 | 0 | 0 | 4 | 4 |
| Names that are not counted | 1 | 3 | 2 | 1 | 7 |
| of them under a highlight | 1 | 2 | 2 | 1 | 6 |
| Highlights | 30 | 33 | 28 | 27 | 118 |
| Reader: found | 28 | 32 | 26 | 26 | 112 |
| Reader: partial | 1 | 0 | 0 | 0 | 1 |
| Reader: not a person | 1 | 1 | 2 | 1 | 5 |
| Reader: lines for missed mentions | 0 | 0 | 0 | 3 | 3 |

The readers listed the three mentions that had no highlight, marked the one partial as partial, and counted none of the six highlighted names that E1's rules leave out. No reader used `surplus` or `extra`, and no highlight fell on plain text.

**The three missed mentions were all on the cross-check list.** The list for `doc31` has four rows: the three missed names and the word `בן`. The reader of `doc31` wrote in its final answer that it found no miss beyond those rows. So what was tested is that a reader takes a miss from the list and leaves a false row out. A name with no highlight that is not on the list was tested on no case. For E1 the same figure is 17 of 18 misses on the list (E1 note, "The cross-check").

**The readers' doubts.** Three readers wrote doubts; the reader of `doc11` had none. In five places a reader wrote that another reading was possible. Each time the reader chose what the gold says.

| Where | The doubt | Decided |
|---|---|---|
| `doc01` highlight 30 | `ר'` before a surname: an initial, or the title `רב` | an initial, so partial |
| `doc01` highlights 15 and 25 | a surname after `האחים` stands for two brothers: `extra` 1 or 0 | 0 |
| `doc21` highlight 1 | a full name alone on a letterhead: a person, or a firm | a person |
| `doc31` highlight 8 | `בתום`: the given name with a prefix, or the word "at the end of" | the name |
| `doc31` paragraph 22 | a surname after `משפחת`: a counted mention or not | counted, missed |

By the count of the reviewer of this note, who ran the comparison on copies of the files with the other reading: any one of them alone gives 122/123 = 99.19 percent (the brothers one, 123/125 = 98.40 percent), and all five together 119/125 = 95.20 percent, which is outside the prediction and does not cross the threshold. E1's guide does not settle the last row; the reader reasoned it out.

**Did a reader look at the answer?** Nothing prevents it; the pre-registration says so. The session logs of the four readers, which are on Achia's laptop and not in the repository, were searched after the comparison. Each session read and wrote files in the worksheet folder. Every read, search and write in them is inside the worksheet folder. The only call that reads, searches or runs anything and names the repository is one command per reader: it runs the repository's Python on the reader's own check script, which is in the worksheet folder. The reviewer of this note read the four logs separately and found the same.

### The third part: the readers' list against the gold

Added on 2026-11-14, after this note was first merged. The rule, the prediction and the threshold are in the pre-registration, "the third part". The prediction was not blind, and the pre-registration says so: from part one Claude knew where the 57 missed mentions were, and expected 55 to 57 of them on the list.

1. The model was run again, from `main` at `83f875d`, with `--all-documents`, into a new folder outside the repository. Its output equals the first run's in every line but three: the commit, the seconds (421.1) and the last line. It gives 1084/1145 and the same 61 errors. SHA-256 `2ff4231498c7d750aaa33e1f53282f90642d3d4579dedfacfd004fe4c2123da4`. The span lists of the four documents of the second part are the same files, byte for byte.
2. `list_check.py` was run once, from `main` at `83f875d`:

```
experiments/.venv/Scripts/python.exe -I experiments/e4_planted_names/list_check.py --folder <private folder>
```

The output as printed. Its SHA-256 is `a3779fe0471a66ccb07a9bb30de52c55d5e78c70aef8e7feb812aff44e821032`.

```
doc01: list rows 0, on a missed mention 0; missed mentions 0, on the list 0
doc02: list rows 2, on a missed mention 2; missed mentions 2, on the list 2
doc03: list rows 2, on a missed mention 2; missed mentions 2, on the list 2
doc04: list rows 0, on a missed mention 0; missed mentions 0, on the list 0
doc05: list rows 0, on a missed mention 0; missed mentions 0, on the list 0
doc06: list rows 4, on a missed mention 2; missed mentions 2, on the list 2
doc07: list rows 4, on a missed mention 4; missed mentions 3, on the list 3
doc08: list rows 3, on a missed mention 3; missed mentions 3, on the list 3
doc09: list rows 2, on a missed mention 2; missed mentions 2, on the list 2
doc10: list rows 5, on a missed mention 5; missed mentions 4, on the list 4
doc11: list rows 0, on a missed mention 0; missed mentions 0, on the list 0
doc12: list rows 1, on a missed mention 0; missed mentions 0, on the list 0
doc13: list rows 0, on a missed mention 0; missed mentions 0, on the list 0
doc14: list rows 0, on a missed mention 0; missed mentions 0, on the list 0
doc15: list rows 0, on a missed mention 0; missed mentions 0, on the list 0
doc16: list rows 2, on a missed mention 2; missed mentions 2, on the list 2
doc17: list rows 2, on a missed mention 2; missed mentions 2, on the list 2
doc18: list rows 3, on a missed mention 2; missed mentions 2, on the list 2
doc19: list rows 4, on a missed mention 4; missed mentions 3, on the list 3
doc20: list rows 3, on a missed mention 3; missed mentions 3, on the list 3
doc21: list rows 0, on a missed mention 0; missed mentions 0, on the list 0
doc22: list rows 0, on a missed mention 0; missed mentions 0, on the list 0
doc23: list rows 3, on a missed mention 2; missed mentions 2, on the list 2
doc24: list rows 1, on a missed mention 1; missed mentions 1, on the list 1
doc25: list rows 0, on a missed mention 0; missed mentions 0, on the list 0
doc26: list rows 7, on a missed mention 2; missed mentions 2, on the list 2
doc27: list rows 9, on a missed mention 2; missed mentions 2, on the list 2
doc28: list rows 9, on a missed mention 4; missed mentions 2, on the list 2
doc29: list rows 7, on a missed mention 2; missed mentions 2, on the list 2
doc30: list rows 9, on a missed mention 2; missed mentions 2, on the list 2
doc31: list rows 4, on a missed mention 3; missed mentions 3, on the list 3
doc32: list rows 1, on a missed mention 1; missed mentions 1, on the list 1
doc33: list rows 2, on a missed mention 1; missed mentions 1, on the list 1
doc34: list rows 4, on a missed mention 3; missed mentions 3, on the list 3
doc35: list rows 2, on a missed mention 1; missed mentions 1, on the list 1
doc36: list rows 2, on a missed mention 1; missed mentions 1, on the list 1
doc37: list rows 0, on a missed mention 0; missed mentions 0, on the list 0
doc38: list rows 1, on a missed mention 1; missed mentions 1, on the list 1
doc39: list rows 1, on a missed mention 1; missed mentions 1, on the list 1
doc40: list rows 3, on a missed mention 2; missed mentions 2, on the list 2
strict PERSON recall from the span lists: 1084/1145 = 94.67%
cross-check lists: 102 rows (name_word 95, after_title 7) in 29 of 40 documents; 62 of them on a missed mention
missed mentions on the list, pooled: 57/57 = 100.00%
verdict: inside_prediction (prediction 90 percent or more, threshold below 80 percent)
by kind:
  family  24/24 = 100.00%
  brothers  9/9 = 100.00%
  given_ordinary  18/18 = 100.00%
  rest  6/6 = 100.00%
missed mentions off the list:
  none
```

- **All 57 missed mentions are on the list.** That is inside the prediction and at the top of what Claude expected.
- The split the pre-registration asks for, from the error list of the same run: 12 of the 57 lie under a highlight of another label, which the worksheet shows in grey; 45 have no highlight of any label. All 45 are on the list. No mention is left that a reader would have to find alone.
- The lists have 102 rows, in 29 of the 40 documents. Counted by a throwaway script: 62 rows lie on a missed mention (5 mentions have two rows), 3 on the part of a partial mention that the highlight left out, and 37 on plain text. 32 of the 37 are words the model highlighted as a person somewhere else: `מרשי` 20 times, `למרות` and `ולמרות` 4, `בן` 3, `תום` and `בתום` 3, `שלום` and `השלום` 2. The other 5 are `על` after `שומר`, which the rule reads as two prefix letters and the title `מר`.
- So a reader of these 40 documents is pointed to 102 places and to every miss. In E1 it was 281 places and 17 of 18 misses.
- The check of the port: the rows the script makes for the four documents of the second part equal the files the readers had (0, 0, 0 and 4 rows). The reviewer of the script compared it with the throwaway on 4,800 made-up cases and found no difference (PR #59).

What follows from it:

- The second part's three of three was not an accident of four documents. No document of the 40 holds a miss that is off the list. With the list in hand, as E1's readers worked, a reader's unaided search cannot be tested on this corpus.
- Without the list it can. 45 missed mentions have no highlight of any label, in 25 documents, and the worksheets of all 40 documents now exist. A reader given a worksheet and no list would have to find those 45 by reading.
- The reason for the 57 of 57 is in how the corpus is built, and the pre-registration names it. 240 of the 250 people are named more than once, so a missed name has a highlighted twin in the same document. The other 10 are named once, after a title, which is the list's second kind of place; the model found all 10. A name that stands once in a real document with no title before it, and is missed, is on no list. E1 had one such miss in 18, the caption line of `doc06`, and the reader found it. By the count of the reviewer of this note, who took the highlight off one found mention at a time and made the list again, 1,083 of the 1,084 found mentions would be on the list if missed.
- The estimate the pre-registration names, as arithmetic: with a share of 57/57 on the list, E1's 17 misses from the list stand for 17. No correction follows. It rests on the assumption that the share carries over from this text to a judgment, and the point above is a reason to think the real share is lower.
- One more piece of arithmetic, on E1's own numbers: its recall is 449 of 470. A name the readers overlooked adds one to the 470. E1 would be under 80 percent only at 449 of 562 or worse, which is 92 or more overlooked names in ten judgments, beside the 18 misses the readers did report.

## What this rules in and what it rules out

**Rules in**

- On generated legal, contract, letter and medical text, the model finds 94.67 percent of person mentions by the strict rule. That is inside what was predicted, far above the line of 80, and the count needs no reader.
- The errors are concentrated. 51 of the 61 are in two kinds of mention: a surname after a group word (33), and a given name alone that is an everyday word (18, of them 13 with prefix letters). Everything else is found 98.91 percent of the time.
- Document kind does not move the number much: 93.33 to 96.06 percent over the four kinds.
- Readers who follow E1's guide, with the model's highlights and the cross-check list before them, gave the same answer as the planted truth on all 123 items of four documents.
- On this text the cross-check list points to every mention the model missed: 57 of 57. This is a count by script. No reader was tested on 54 of the 57.

**Does not rule in**

- **Real documents.** The text is written by a language model, and the names come from a bank of 166. A client's document has stranger sentences and names no bank holds. E1 is still the only measurement on real text, and its corpus is ten Supreme Court judgments.
- **The readers' main risk is tested on no case.** The risk in E1 is a name that the model did not highlight and the reader also passed over. In these four documents the model left three mentions without a highlight, and all three were on the list handed to the reader. A missed name that the list does not hold, which the reader must find by reading, did not occur. The third part shows that it occurs in none of the 40 documents, for a reader who has the list: almost every person is named several times, and the few named once follow a title.
- **Whether a reader takes every miss from the list.** The readers saw four rows of one list: three misses and one false row. The other 98 rows, 36 of them on plain text, no reader has seen. The pre-registration names this limit. The four documents are also short and clean: about 1,700 characters each, against judgments of 8 to 20 pages in E1.
- **The 57 are not independent.** Five fillings of a template share every sentence. By the count of the reviewer of this note the 57 come from 25 places in the templates, 6 of them missed in all five fillings.
- **Not a random sample of sentences.** Eight templates, five fillings each. A sentence the model cannot read is missed five times.
- **How often these forms occur.** A given name alone is a quarter of the mentions here. A formal document uses it far less. So the pooled number depends on a mix that Claude chose.
- **The 123 of 123 rests on five judgement calls** that went the gold's way (the table of doubts above).
- **No person checked anything.** What replaces the person is that the script wrote the answer down before the model ran.

## Options, with the cost of each

1. **Take E4 as the check that stands in for the person's check of E1, and go on to the decision the E1 note asks for.** Cost: nothing more is built. What stays open is whether a reader finds a missed name that the cross-check list does not hold. E4 has no case of it in any document, and E1 has one (the caption line of `doc06`).
2. **Measure the cross-check list against the gold, with no reader.** Done on 2026-11-14: the third part above. 57 of 57.
3. **Test a reader's own search.** As first written this was "have readers count the documents that hold a miss off the list". There is no such document. Two forms are left:
   - *Readers with no list, on this corpus.* The 25 documents that hold the 45 misses with no highlight of any label, one reader each, with the worksheet and without the list. Cost: 25 reader sessions, a line in the pre-registration, and the comparison script opened to those documents. No new text and no model run. Its limit: it tests reading with no list, which is harder than what E1's readers did, and the text is still short and generated.
   - *A new corpus* in which some names stand once with no title before them, so that a miss of them is on no list even for a reader who has it. Cost: new templates, a pre-registration, a model run, the list check, and a reader session for each document with such a miss.
4. **Ask for a person's check after all**, of E1 or of E4. Cost: Achia's reading time, which Achia chose not to spend on 2026-11-14.

Apart from these: the two weak kinds of mention are worth carrying into the plan as named test cases, whatever is decided. The E1 note already proposes this for a shared surname in a group term (Phase 6). For names that are everyday words, the plan's main defence is a title before the name (`build-plan.md:575`). The 18 missed here stand alone, with no title, so that defence does not reach them.

## Recommendation

Option 1. As first written this said "and option 2 beside it"; option 2 is now done.

- The first part needs no reader at all. On four kinds of text the model is far above the line of 80, and 51 of its 61 errors are of two known kinds. That is what the plan asked E1 to show on real documents (`build-plan.md:1031`); here it is shown on generated text, and it does not rest on anyone's count.
- The second and third parts together show this much about the readers: where a highlight pointed, they were right on 118 highlights; where the list pointed, on the four rows they saw; and on this text the list points to every miss. Whether they find a miss that nothing points to is not shown. E1's count of real documents therefore stands as before: a reader's count, not checked.
- Not option 3 now, in either form. The first costs 25 reader sessions and the second a new experiment. What either would protect is E1's verdict against the line of 80, and by the arithmetic above that verdict would change only if the readers had overlooked 92 names or more. A name that stands once with no title is better made a hard case of the Phase 5 corpus, where it tests the product and not a reader (`build-plan.md:685` lists the hard cases; this one would be added).
- The plan measures recall again later: on the 10 real documents at the gate of Phase 3 (`build-plan.md:645`), on a larger generated corpus in Phase 5 (`build-plan.md:683`), with hard cases, among them names that are everyday words and two people sharing a surname (`:685`), and on client documents only at the pilot firm (`build-plan.md:687`).

## Scope requested

None. This is not a waiver request.

## Decision

Achia, 2026-11-15, in the Claude Code session. Claude asked, word for word:

> One decision of yours stands between us and Phase 0: **is the model good enough at finding names to start building?**
>
> - **E1, real court judgments:** 449 of 470 names found (95.5%). I counted these, and no person checked the count.
> - **E4, generated text where a script knows every name:** 1,084 of 1,145 found (94.7%), as predicted.
> - **The bar in the plan:** below 80% means rethink the architecture. Both results are well above it.
> - **Known weak spots:** a surname after a group word such as `משפחת`, and a first name alone that is also an everyday word. Both would become named test cases.
>
> I recommend yes. If you say yes, I write your decision into the two findings notes as a PR for you to approve, and then start Phase 0 with the merge gate.
>
> **Start Phase 0: yes or no?**

Achia answered:

> Yes

What follows from it, as Claude reads it:

1. Option 1, and this point is Claude's reading more than the others. The question did not put it in words: it gave E4's number beside E1's and said that no person checked E1's count. Claude reads the yes as option 1: E4 is taken as the check that stands in for a person's check of E1, and Phase 0 starts (`docs/findings/2026-11-13-e1-hebrew-recall.md`, Decision). Claude put this reading to Achia in chat the same day, in the message that announced the PR adding this section, and marked it there as Claude's reading. Achia did not answer it in words: his reply told Claude to stop asking him about each merge and to merge what passes the gating. So it stands as Claude's reading and not as Achia's words, and he can change it. What E4 does not show stays as written above: whether a reader finds a missed name that nothing points to.
2. The two weak kinds of mention become named test cases: a surname after a group word such as `משפחת` or `האחים`, and a given name alone that is an everyday word. Where each test sits in the plan is a PR to `build-plan.md`, which Achia approves. That PR is not written yet, and nothing in Phase 0 waits on it.
3. Not decided here: option 3, a test of a reader's own search, and the proposal in its place, that a name standing once with no title becomes a hard case of the Phase 5 corpus. The question named neither. Neither is done now, and nothing before Phase 5 waits on them.
4. Not option 4 now: Phase 0 does not wait for a person's check of E1 or of E4. The question did not ask for one. Achia chose on 2026-11-14 not to spend that reading time (option 4, above).
