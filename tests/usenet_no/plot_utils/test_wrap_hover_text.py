from usenet_no.plot_utils import wrap_hover_text


def test_a_line_that_fits_is_left_alone():
    assert wrap_hover_text("kort linje", width=70) == "kort linje"


def test_a_line_longer_than_the_width_is_broken_between_words():
    assert wrap_hover_text("en to tre fire fem", width=10) == "en to tre<br>fire fem"


def test_the_lines_of_the_text_are_kept_apart():
    assert wrap_hover_text("første\n\nandre", width=70) == "første<br><br>andre"


def test_a_word_wider_than_the_width_is_broken_rather_than_left_hanging():
    assert wrap_hover_text("aaaaaaaa", width=3) == "aaa<br>aaa<br>aa"


def test_every_line_stays_within_the_width():
    text = "Dette er en ganske lang setning som må brytes\nog her kommer en til"
    assert all(
        len(line) <= 20 for line in wrap_hover_text(text, width=20).split("<br>")
    )
