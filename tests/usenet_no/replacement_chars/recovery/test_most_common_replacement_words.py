from collections import Counter

from usenet_no.replacement_chars.recovery import (
    build_norwegian_vocabulary_index,
    most_common_replacement_words,
)

REPLACEMENT_CHAR = "\N{REPLACEMENT CHARACTER}"


def test_words_are_ranked_by_occurrence_and_limited_to_n():
    index = build_norwegian_vocabulary_index(["blå får før"])
    ia_word_counts = Counter(
        {
            "bl" + REPLACEMENT_CHAR: 1,
            "f" + REPLACEMENT_CHAR + "r": 9,
            "xy" + REPLACEMENT_CHAR: 5,
        }
    )

    ranked = most_common_replacement_words(ia_word_counts, index, n=2)

    assert [word.word for word in ranked] == [
        "f" + REPLACEMENT_CHAR + "r",
        "xy" + REPLACEMENT_CHAR,
    ]


def test_ranked_word_carries_category_and_sorted_candidates():
    index = build_norwegian_vocabulary_index(["får før blå"])
    ia_word_counts = Counter(
        {
            "f" + REPLACEMENT_CHAR + "r": 3,
            "bl" + REPLACEMENT_CHAR: 2,
            "xy" + REPLACEMENT_CHAR: 1,
        }
    )

    ambiguous, unambiguous, unresolvable = most_common_replacement_words(
        ia_word_counts, index, n=3
    )

    assert ambiguous.category == "ambiguous"
    assert ambiguous.candidates == ["får", "før"]
    assert unambiguous.category == "unambiguous"
    assert unambiguous.candidates == ["blå"]
    assert unresolvable.category == "unresolvable"
    assert unresolvable.candidates == []
