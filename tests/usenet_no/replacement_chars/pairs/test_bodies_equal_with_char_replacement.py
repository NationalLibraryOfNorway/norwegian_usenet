from usenet_no.replacement_chars.pairs import bodies_equal_with_char_replacement


def test_norwegian_chars_against_replacement_chars_are_equal():
    assert bodies_equal_with_char_replacement(
        "Blåbærsyltetøy. ØL OG PØLSER, sa Åge.",
        "Bl�b�rsyltet�y. �L OG P�LSER, sa �ge.",
    )


def test_identical_ascii_bodies_are_equal():
    assert bodies_equal_with_char_replacement("hello", "hello")


def test_differing_text_is_not_equal():
    assert not bodies_equal_with_char_replacement("hello", "goodbye")


def test_replacement_char_where_nb_has_ascii_is_not_equal():
    assert not bodies_equal_with_char_replacement("hei", "h�i")


def test_other_non_ascii_chars_are_not_replaced():
    assert not bodies_equal_with_char_replacement("café", "caf�")
