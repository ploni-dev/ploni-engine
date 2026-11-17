"""Test matrix for layers: words, strip_prefix, name_words, propagate, after_triggers, from_list.

A span is (paragraph, start, end). `at` finds a word in a paragraph, so no test counts characters.

words
  EC1  plain words, punctuation between them          each word once, with its place
  EC2  a geresh or gershayim inside a word            ג'ון, עו"ד, ד"ר are one word each
  EC3  a geresh at the end                            גב' is one word
  B1   an empty paragraph, digits and Latin only      nothing
  A5   a maqaf or a hyphen inside a name             two words: the stated limit

strip_prefix
  EC4  the word itself is known                       itself
  EC5  one, two, three attached letters               the known remainder
  EC6  four attached letters                          None
  EC7  a letter that is no prefix letter in front     None
  B2   a remainder of one letter                      None
  A1   a name that begins with a prefix letter and is itself known (לביא)   itself, not ביא

name_words
  EC8  a span of two words                            both words, weak and strong
  EC9  one span of one word                           weak: the word; strong: nothing
  EC10 the same one word in two spans                 weak and strong
  EC11 a particle and an initial inside a span        left out
  B3   no spans                                       nothing
  EC25 one span per word, as whole words give them    two marked words side by side are a
                                                      name of two words: both are strong
  EC26 a title marked beside a name                   does not make the name strong

propagate
  EC12 a name found once stands again bare            the other place is marked
  EC13 ... behind attached letters                    marked with prefixes, not without
  EC14 ... in another paragraph                       marked
  EC15 the place already marked                       not returned again
  A2   an everyday word that is a name in this document (אור) is marked everywhere it stands
  A6   a name found only behind attached letters (לכהן) is not carried to its bare form:
       the stated limit

after_triggers
  EC16 משפחת X, האחים X                               X is marked
  EC17 the group word behind attached letters (למשפחת, והאחים)   X is marked
  EC18 משפחת בן דוד, משפחת אבו ראס                    both words are marked
  EC19 a title and a name, titles off                 nothing
  EC20 a title and a name, titles on                  the name
  EC21 a title, an initial and a surname              the initial and the surname
  EC22 the word already marked                        not returned again
  B4   a trigger as the last word of a paragraph      nothing, no error
  A3   a word that only looks like a trigger (שמר, מרב, רב, רשם, שופט, אחים; and behind ל, ב
       or כ: למנוחה, במנוחה, כשופט, לרב, לאחות, בשופט)   nothing
  A7   something between the trigger and the next word: a full stop, a bracket, a word
       in Latin letters   nothing; the same between an initial and the surname
  A4   a title inside a marked span                   not a name word, not carried

from_list
  EC23 a word on the list, bare and behind letters    marked; behind letters only with prefixes
  EC24 a word not on the list                         nothing
"""

import pytest

import layers


def at(paragraph: str, word: str, index: int = 0, nth: int = 0) -> tuple[int, int, int]:
    """Return the span of the nth place `word` stands in a paragraph."""
    start = -1
    for _ in range(nth + 1):
        start = paragraph.index(word, start + 1)
    return (index, start, start + len(word))


def test_ec1_plain_words() -> None:
    assert [text for _, _, text in layers.words("יעקב כהן, מנהל.")] == ["יעקב", "כהן", "מנהל"]
    assert layers.words("אב גד")[1] == (3, 5, "גד")


@pytest.mark.parametrize("word", ["ג'ון", 'עו"ד', 'ד"ר', "גב'", "צ׳רלי", "רו״ח"])
def test_ec2_ec3_marks_inside_and_at_the_end(word: str) -> None:
    assert [text for _, _, text in layers.words(f"פגש את {word} אתמול")] == ["פגש", "את", word, "אתמול"]


@pytest.mark.parametrize("paragraph", ["", "   ", "2025, 14:00", "John Smith"])
def test_b1_nothing_to_find(paragraph: str) -> None:
    assert layers.words(paragraph) == []


@pytest.mark.parametrize(
    ("word", "expected"),
    [("כהן", "כהן"), ("לכהן", "כהן"), ("ולכהן", "כהן"), ("וכשכהן", "כהן"), ("ולכשכהן", None), ("תכהן", None), ("וטכהן", None), ("וכטכהן", None),
     ("לוי", None), ("לביא", "לביא")],  # fmt: skip
)
def test_ec4_to_a1_strip_prefix(word: str, expected: str | None) -> None:
    assert layers.strip_prefix(word, {"כהן", "לביא", "י"}) == expected


def test_b2_a_remainder_of_one_letter() -> None:
    assert layers.strip_prefix("לי", {"י"}) is None


def test_ec8_a_span_of_two_words() -> None:
    paragraph = "יעקב כהן חתם"
    spans = [(0, 0, 8)]
    assert layers.name_words([paragraph], spans, strong=False) == {"יעקב", "כהן"}
    assert layers.name_words([paragraph], spans, strong=True) == {"יעקב", "כהן"}


def test_ec9_ec10_one_word_once_and_twice() -> None:
    paragraph = "כהן חתם ואז כהן הלך"
    once = [at(paragraph, "כהן")]
    twice = [*once, at(paragraph, "כהן", nth=1)]
    assert layers.name_words([paragraph], once, strong=False) == {"כהן"}
    assert layers.name_words([paragraph], once, strong=True) == set()
    assert layers.name_words([paragraph], twice, strong=True) == {"כהן"}


def test_ec11_particles_and_initials_are_left_out() -> None:
    paragraph = "דוד בן גוריון וגם י' כהן"
    spans = [(0, 0, paragraph.index(" וגם")), (0, paragraph.index("י'"), len(paragraph))]
    assert layers.name_words([paragraph], spans, strong=False) == {"דוד", "גוריון", "כהן"}


def test_b3_no_spans() -> None:
    assert layers.name_words(["יעקב כהן"], [], strong=False) == set()
    assert layers.propagate(["יעקב כהן"], []) == []


def test_ec12_ec15_a_name_found_once_is_marked_where_it_stands_again() -> None:
    paragraph = "יעקב כהן חתם. אחר כך כהן הלך."
    spans = [(0, 0, 8)]
    assert layers.propagate([paragraph], spans) == [at(paragraph, "כהן", nth=1)]


def test_ec13_behind_attached_letters() -> None:
    paragraph = "יעקב כהן חתם. נמסר לכהן וליעקב."
    spans = [(0, 0, 8)]
    assert layers.propagate([paragraph], spans) == [at(paragraph, "לכהן"), at(paragraph, "וליעקב")]
    assert layers.propagate([paragraph], spans, prefixes=False) == []


def test_ec14_in_another_paragraph() -> None:
    paragraphs = ["יעקב כהן חתם.", "כהן הלך."]
    assert layers.propagate(paragraphs, [(0, 0, 8)]) == [(1, 0, 3)]


def test_a2_an_everyday_word_that_is_a_name_here() -> None:
    paragraph = "אור לוי הגיעה. היה אור בחדר."
    assert layers.propagate([paragraph], [(0, 0, 7)]) == [at(paragraph, "אור", nth=1)]
    assert layers.propagate([paragraph], [at(paragraph, "אור")], strong=True) == []


@pytest.mark.parametrize("trigger", ["משפחת", "האחים", "האחיות", "למשפחת", "והאחים", "שמשפחת", "לאחים", "ולאחיות"])
def test_ec16_ec17_the_word_after_a_group_word(trigger: str) -> None:
    paragraph = f"הדירה של {trigger} מזרחי נמכרה"
    assert layers.after_triggers([paragraph], []) == [at(paragraph, "מזרחי")]


@pytest.mark.parametrize("name", ["בן דוד", "אבו ראס"])
def test_ec18_a_family_name_of_two_words(name: str) -> None:
    paragraph = f"משפחת {name} עברה"
    first, second = name.split()
    assert layers.after_triggers([paragraph], []) == [at(paragraph, first), at(paragraph, second)]


@pytest.mark.parametrize("title", ["מר", "למר", "גב'", "גב׳", 'ד"ר', "ד״ר", 'עו"ד', "השופטת", "לשופט", "ולשופטת", 'ולעו"ד', "שהרב"])
def test_ec19_ec20_the_word_after_a_title(title: str) -> None:
    paragraph = f"פנה אל {title} מזרחי בעניין"
    assert layers.after_triggers([paragraph], []) == []
    assert layers.after_triggers([paragraph], [], titles=True) == [at(paragraph, "מזרחי")]


@pytest.mark.parametrize(
    "word", ["שמר", "מרב", "רב", "ורב", "רשם", "שופט", "אחים", "חמר", "הר", "למנוחה", "במנוחה", "כשופט", "בשופט", "לרב", "לאחות", "למנוח"]
)
def test_a3_a_word_that_only_looks_like_a_title_or_a_group_word(word: str) -> None:
    paragraph = f"הוא {word} על הסדר"
    assert layers.after_triggers([paragraph], [], titles=True) == []


def test_a4_a_title_inside_a_marked_span_is_not_carried_as_a_name() -> None:
    paragraph = "מר כהן חתם. מר לוי ראה את כהן."
    whole = (0, 0, 6)
    assert layers.name_words([paragraph], [whole], strong=False) == {"כהן"}
    assert layers.propagate([paragraph], [whole]) == [at(paragraph, "כהן", nth=1)]


def test_ec21_a_title_an_initial_and_a_surname() -> None:
    paragraph = "לפני כב' השופט י' עמית נדון"
    found = layers.after_triggers([paragraph], [], titles=True)
    assert at(paragraph, "י'") in found
    assert at(paragraph, "עמית") in found


def test_ec22_a_word_already_marked_is_not_returned_again() -> None:
    paragraph = "משפחת מזרחי עברה"
    assert layers.after_triggers([paragraph], [at(paragraph, "מזרחי")]) == []


def test_b4_a_trigger_as_the_last_word() -> None:
    assert layers.after_triggers(["כך אמרה משפחת"], [], titles=True) == []
    assert layers.after_triggers(["מר"], [], titles=True) == []


def test_ec23_ec24_from_a_list() -> None:
    paragraph = "נועה פגשה את לנועה ואת רותם"
    names = frozenset({"נועה"})
    assert layers.from_list([paragraph], [], names) == [at(paragraph, "נועה"), at(paragraph, "לנועה")]
    assert layers.from_list([paragraph], [], names, prefixes=False) == [at(paragraph, "נועה")]
    assert layers.from_list([paragraph], [at(paragraph, "נועה")], names, prefixes=False) == []


@pytest.mark.parametrize("name", ["בן־גוריון", "בן-גוריון"])
def test_a5_a_maqaf_or_a_hyphen_ends_a_word(name: str) -> None:
    assert [text for _, _, text in layers.words(f"דוד {name} אמר")] == ["דוד", "בן", "גוריון", "אמר"]


def test_ec25_two_marked_words_side_by_side_are_a_name_of_two_words() -> None:
    # As `evaluate.whole_words` gives them: one span per word, never one span over the name.
    paragraph = "יעקב כהן חתם. אחר כך כהן הלך, ויעקב נשאר."
    per_word = [at(paragraph, "יעקב"), at(paragraph, "כהן")]
    assert layers.name_words([paragraph], per_word, strong=True) == {"יעקב", "כהן"}
    assert layers.propagate([paragraph], per_word, strong=True) == [at(paragraph, "כהן", nth=1), at(paragraph, "ויעקב")]
    apart = "יעקב חתם, וגם כהן. אחר כך כהן הלך."
    assert layers.name_words([apart], [at(apart, "יעקב"), at(apart, "כהן")], strong=True) == set()


def test_ec26_a_title_beside_a_name_does_not_make_it_strong() -> None:
    paragraph = "מר כהן חתם. אחר כך כהן הלך."
    per_word = [at(paragraph, "מר"), at(paragraph, "כהן")]
    assert layers.name_words([paragraph], per_word, strong=True) == set()
    assert layers.name_words([paragraph], per_word, strong=False) == {"כהן"}
    group = "משפחת לוי באה. אחר כך לוי הלך."
    assert layers.name_words([group], [at(group, "משפחת"), at(group, "לוי")], strong=True) == set()
    listed = "כהן, לוי חתמו. אחר כך כהן הלך ולוי נשאר."
    assert layers.name_words([listed], [at(listed, "כהן"), at(listed, "לוי")], strong=True) == set()
    with_initial = "י' כהן חתם."
    assert layers.name_words([with_initial], [at(with_initial, "י'"), at(with_initial, "כהן")], strong=True) == {"כהן"}


def test_a6_a_name_found_only_behind_attached_letters_is_not_carried_to_its_bare_form() -> None:
    # A stated limit of `name_words`, pinned: cutting letters off without knowing the name would make `רק` of `ברק`.
    paragraph = "נמסר לכהן אתמול. כהן לא ענה, וגם לכהן השני לא."
    found = layers.propagate([paragraph], [at(paragraph, "לכהן")])
    assert found == [at(paragraph, "לכהן", nth=1)]


@pytest.mark.parametrize(
    "paragraph",
    ["פנה אל האחות. היא לא ענתה", "מר (להלן: המוכר) חתם", "גב' Cohen ואחר כך הלכה", "משפחת, כך נאמר, עברה", "עו\"ד: כהן"],
)
def test_a7_something_between_the_trigger_and_the_next_word(paragraph: str) -> None:
    assert layers.after_triggers([paragraph], [], titles=True) == []


def test_a7_something_between_an_initial_and_the_surname() -> None:
    paragraph = "השופט י'. כהן חתם"
    assert layers.after_triggers([paragraph], [], titles=True) == [at(paragraph, "י'")]
