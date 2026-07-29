from usenet_no.replacement_chars.recovery import count_replacement_words

REPLACEMENT_CHAR = "\N{REPLACEMENT CHARACTER}"


def test_counts_only_words_containing_replacement_char():
    counts = count_replacement_words(["f" + REPLACEMENT_CHAR + "r og sau"])
    assert counts == {"f" + REPLACEMENT_CHAR + "r": 1}


def test_occurrences_accumulate_across_bodies():
    word = "sj" + REPLACEMENT_CHAR
    counts = count_replacement_words([f"{word} her", f"og {word} der", "ingen her"])
    assert counts[word] == 2


def test_ascii_only_corpus_yields_empty_counter():
    assert count_replacement_words(["hello there"]) == {}
