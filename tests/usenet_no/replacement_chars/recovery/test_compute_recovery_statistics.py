from collections import Counter

from usenet_no.replacement_chars.recovery import (
    build_norwegian_vocabulary_index,
    compute_recovery_statistics,
)

REPLACEMENT_CHAR = "\N{REPLACEMENT CHARACTER}"


def test_statistics_count_distinct_words_and_occurrences():
    index = build_norwegian_vocabulary_index(["får før blå himmel", "blå sjø"])
    ia_word_counts = Counter(
        {
            "bl" + REPLACEMENT_CHAR: 5,  # unambiguous -> "blå"
            "f" + REPLACEMENT_CHAR + "r": 3,  # ambiguous -> "får"/"før"
            "xy" + REPLACEMENT_CHAR: 2,  # unresolvable
        }
    )

    statistics = compute_recovery_statistics(index, ia_word_counts)

    assert statistics.ia_distinct_replacement_words == 3
    assert statistics.ia_total_replacement_word_occurrences == 10

    assert statistics.by_distinct_word.unambiguous == 1
    assert statistics.by_distinct_word.ambiguous == 1
    assert statistics.by_distinct_word.unresolvable == 1

    assert statistics.by_occurrence.unambiguous == 5
    assert statistics.by_occurrence.ambiguous == 3
    assert statistics.by_occurrence.unresolvable == 2


def test_statistics_report_vocabulary_size():
    index = build_norwegian_vocabulary_index(["får før blå", "blå"])
    statistics = compute_recovery_statistics(index, Counter())

    # Three distinct Norwegian words ("får", "før", "blå") under two keys
    # ("f_r" holds two, "bl_" holds one).
    assert statistics.nb_distinct_norwegian_words == 3
    assert statistics.nb_distinct_masked_keys == 2
