from usenet_no.replacement_chars.recovery import build_norwegian_vocabulary_index

REPLACEMENT_CHAR = "\N{REPLACEMENT CHARACTER}"


def test_only_words_with_norwegian_chars_are_indexed():
    index = build_norwegian_vocabulary_index(["får og sau i fjæra"])
    assert set(index) == {"f" + REPLACEMENT_CHAR + "r", "fj" + REPLACEMENT_CHAR + "ra"}


def test_distinct_words_sharing_a_key_are_collected():
    index = build_norwegian_vocabulary_index(["får", "før", "far"])
    assert index["f" + REPLACEMENT_CHAR + "r"] == {"får", "før"}


def test_same_word_across_bodies_is_deduplicated():
    index = build_norwegian_vocabulary_index(["blå himmel", "blå sjø"])
    assert index["bl" + REPLACEMENT_CHAR] == {"blå"}


def test_ascii_only_corpus_yields_empty_index():
    assert build_norwegian_vocabulary_index(["hello there", "general kenobi"]) == {}
