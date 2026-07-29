from usenet_no.replacement_chars.recovery import mask_norwegian_chars

REPLACEMENT_CHAR = "\N{REPLACEMENT CHARACTER}"


def test_masks_every_norwegian_char():
    assert mask_norwegian_chars("blåbærsyltetøy") == "bl" + REPLACEMENT_CHAR + "b" + (
        REPLACEMENT_CHAR + "rsyltet" + REPLACEMENT_CHAR + "y"
    )


def test_masks_upper_and_lower_case():
    assert mask_norwegian_chars("ÅGE") == REPLACEMENT_CHAR + "GE"
    assert mask_norwegian_chars("åge") == REPLACEMENT_CHAR + "ge"


def test_leaves_existing_replacement_char_in_place():
    assert mask_norwegian_chars("f" + REPLACEMENT_CHAR + "r") == (
        "f" + REPLACEMENT_CHAR + "r"
    )


def test_ascii_word_is_unchanged():
    assert mask_norwegian_chars("hello") == "hello"


def test_other_non_ascii_chars_are_not_masked():
    assert mask_norwegian_chars("café") == "café"
