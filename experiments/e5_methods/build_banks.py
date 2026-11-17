"""Write the two name banks of E5 from the lists below.

Why: the corpora for choosing and for judging must not share a name with each other or
with E4's bank, or a method that learned a name on one would be judged on it on the other.
The banks are in the repository; this script is kept so that they can be made again and
so that the claim can be checked.

Contract: `python build_banks.py <e4 names.tsv> <out dir>`. Writes `names_select.tsv` and
`names_heldout.tsv` into the folder and prints how many names each holds. A name that
E4's bank holds, or that both lists hold, is left out, so the three banks share no name.
The class `prefix_initial` is worked out from the first letter.

Known limits: the names are common Israeli given names and surnames, written by Claude.
No name of a real person is meant.
"""

import sys
from pathlib import Path

PREFIX_LETTERS = "והבלמכש"

# (kind, gender, class other than prefix_initial, names). Gender "-" for surnames.
SELECT = [
    ("given", "m", "", "נדב איתמר אסף אוהד עידו אלעד יהונתן אביתר אריאל ליאור בועז מרדכי שלמה הלל"),
    ("given", "m", "ordinary", "נועם עמית תומר דור שי גיא ניר זיו כפיר לביא"),
    ("given", "m", "also_word", "אשר דן גד עזרא"),
    ("given", "m", "arabic", "אחמד יוסוף ח'אלד סמיר מחמוד באסל"),
    ("given", "m", "translit", "אלכסנדר איגור דמיטרי פיליפ בוריס מקסים"),
    ("given", "f", "", "רחל תמר נעמי רבקה אסתר יעל עדי אביגיל מיכל לאה בתיה"),
    ("given", "f", "ordinary", "אורית נוגה רותם מעיין הדס לילך כנרת ורד הילה"),
    ("given", "f", "also_word", "דבורה צביה אילה נחמה"),
    ("given", "f", "arabic", "פאטמה אמל רים סוהא לילא היבא"),
    ("given", "f", "translit", "נטשה אולגה סבטלנה קטרין ז'קלין ויקטוריה"),
    ("surname", "-", "", "אברהמי יוספי גבריאלי אשכנזי דיין גרינברג זילברמן טננבאום קורן רביבו אדרי עטיה סבג זכאי טייב הלוי הכהן ברגר בוזגלו מלול לנקרי וולך כץ שמעוני מרקוביץ לוינסון הרשקוביץ ויצמן כהנא"),
    ("surname", "-", "also_word", "גולן יעקבי אפרתי גבע נגר חייט"),
    ("surname", "-", "ordinary", "אבן גפן תמיר שדה הדר ברק"),
    ("surname", "-", "arabic", "חורי נאסר עיסא סלאמה דיאב כנאענה מחאמיד שחאדה"),
    ("surname", "-", "translit", "קוזנצוב סמירנוב פופוב וולקוב מורוזוב לבדב רבינוביץ גורביץ"),
]

HELDOUT = [
    ("given", "m", "", "אהוד עוזיאל ירון אלחנן יאיר נחום עמיחי אבישי יחזקאל צדוק שמואל מתן ברוך כלב"),
    ("given", "m", "ordinary", "עוז אייל ארז אלון סהר רז גל בר הוד שלו"),
    ("given", "m", "also_word", "ישי אמיר נסים ששון"),
    ("given", "m", "arabic", "עלי חסן נביל ראמי כרים וליד"),
    ("given", "m", "translit", "אנדריי פבל ניקולאי רומן ליאוניד מיכאיל"),
    ("given", "f", "", "גליה אפרת זהבה ציפורה עינת טליה אילנה דליה ענת ליאת מירב שולמית בלה הודיה"),
    ("given", "f", "ordinary", "שני מור אגם זוהר ענבל סיון פז לבנה שושנה ברכה"),
    ("given", "f", "also_word", "עדנה פנינה אורה טובה שמחה"),
    ("given", "f", "arabic", "עביר סמאח נסרין ח'דיג'ה מנאל הנאא"),
    ("given", "f", "translit", "אירינה טטיאנה ילנה מרינה לריסה ג'ולי"),
    ("surname", "-", "", "אדלשטיין גוטמן דוידוב זוסמן יחזקאלי נגבי סעדה עמרני פולק קדוש רחמים תורג'מן אלבז גרשון דנינו חיון הרוש בניטה ברנשטיין לוינגר מנדלסון מימון שמואלי שרעבי ויסמן וולפסון כחלון כספי הורן לנדסמן מושקוביץ"),
    ("surname", "-", "also_word", "רביב גורן דגן בוקר מלמד שוחט"),
    ("surname", "-", "ordinary", "אביב זמיר יער נהר ענבר שביט להב ברוש"),
    ("surname", "-", "arabic", "ג'בארין טאהא עזאם קאסם מרעי בדראן שלבי"),
    ("surname", "-", "translit", "סוקולוב נוביקוב פדורוב קרסנוב מדבדב בלוב וסילייב לויטין"),
]


def rows(lists: list[tuple[str, str, str, str]], taken: set[str]) -> list[str]:
    """Return the rows of one bank, without the names that an earlier bank holds.

    Why: see the module: no name in two banks.

    Contract: one row per name, `kind, gender, name, classes`, tab-separated. A name in
    `taken` is left out; every name kept is added to `taken`, so that the next bank
    leaves it out too.
    """
    out = []
    for kind, gender, name_class, names in lists:
        for name in names.split():
            if name in taken:
                continue
            taken.add(name)
            classes = [name_class] if name_class else []
            if name[0] in PREFIX_LETTERS:
                classes.append("prefix_initial")
            out.append("\t".join([kind, gender, name, ",".join(sorted(classes))]))
    return out


def main() -> None:
    """Write the two banks.

    Why and contract: see the module docstring. E4's bank is read first, so that no name of
    it is used again.
    """
    e4 = Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()[1:]
    taken = {line.split("\t")[2] for line in e4 if line.strip()}
    out = Path(sys.argv[2])
    for name, lists in (("names_select.tsv", SELECT), ("names_heldout.tsv", HELDOUT)):
        body = rows(lists, taken)
        (out / name).write_text("kind\tgender\tname\tclasses\n" + "\n".join(body) + "\n", encoding="utf-8")
        print(name, len(body))


if __name__ == "__main__":
    main()
