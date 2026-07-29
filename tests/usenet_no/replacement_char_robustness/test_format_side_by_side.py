from usenet_no.replacement_char_robustness import format_side_by_side

LEFT = "Blåbærsyltetøy på loffen, og øl og pølser til alle som vil ha."
RIGHT = LEFT.translate(
    str.maketrans({char: "\N{REPLACEMENT CHARACTER}" for char in "æøåÆØÅ"})
)


def test_no_line_is_wider_than_the_asked_for_width():
    lines = format_side_by_side("NB", LEFT, "IA", RIGHT, width=60).splitlines()

    assert max(len(line) for line in lines) <= 60


def test_both_headings_are_on_the_first_line():
    first_line, *_ = format_side_by_side("NB", LEFT, "IA", RIGHT, width=60).splitlines()

    assert "NB" in first_line
    assert "IA" in first_line


def test_both_texts_are_shown():
    formatted = format_side_by_side("NB", LEFT, "IA", RIGHT, width=60)

    assert "Blåbærsyltetøy" in formatted
    assert "Bl\N{REPLACEMENT CHARACTER}b\N{REPLACEMENT CHARACTER}rsyltet" in formatted


def test_the_two_columns_wrap_the_same_way():
    """The bodies hold the same characters, so the same words line up."""
    lines = format_side_by_side("NB", LEFT, "IA", RIGHT, width=60).splitlines()

    # Past the heading and its rule, the two columns hold the same word count
    for line in lines[2:]:
        left, right = line.split("|")
        assert len(left.split()) == len(right.split())


def test_a_column_that_runs_out_of_text_is_left_blank():
    formatted = format_side_by_side("NB", LEFT, "IA", "short", width=60)

    assert formatted.splitlines()[-1].strip() != ""


def test_texts_too_narrow_to_wrap_still_produce_columns():
    lines = format_side_by_side("NB", LEFT, "IA", RIGHT, width=4).splitlines()

    assert all("|" in line for line in lines)


def test_empty_texts():
    formatted = format_side_by_side("NB", "", "IA", "", width=60)

    assert formatted.splitlines()[0].startswith("NB")
