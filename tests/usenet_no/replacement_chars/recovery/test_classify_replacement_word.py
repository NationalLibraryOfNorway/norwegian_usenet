from usenet_no.replacement_chars.recovery import (
    build_norwegian_vocabulary_index,
    classify_replacement_word,
)

REPLACEMENT_CHAR = "\N{REPLACEMENT CHARACTER}"


def test_classify_distinguishes_the_three_outcomes():
    # "får"/"før" share a key (ambiguous), "blå" is alone (unambiguous),
    # "xyz" has no Norwegian counterpart (unresolvable).
    index = build_norwegian_vocabulary_index(["får før blå"])
    candidate_counts = {key: len(words) for key, words in index.items()}

    assert classify_replacement_word(
        "f" + REPLACEMENT_CHAR + "r", candidate_counts
    ) == ("ambiguous")
    assert classify_replacement_word("bl" + REPLACEMENT_CHAR, candidate_counts) == (
        "unambiguous"
    )
    assert classify_replacement_word("xy" + REPLACEMENT_CHAR, candidate_counts) == (
        "unresolvable"
    )
