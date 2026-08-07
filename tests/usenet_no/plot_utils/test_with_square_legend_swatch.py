import numpy as np

from usenet_no.plot_utils import with_square_legend_swatch


def swatch():
    return with_square_legend_swatch(
        np.array([1.0, 2.0]),
        np.array([3.0, 4.0]),
        np.array(["circle", "triangle-up"]),
        np.array(["first message", "second message"]),
    )


def test_the_added_point_leads_with_a_square_and_no_coordinates():
    x, y, symbols, text = swatch()
    assert np.isnan(x[0]) and np.isnan(y[0])
    assert symbols[0] == "square"
    assert text[0] == ""


def test_the_points_that_are_drawn_keep_their_symbols_and_texts():
    x, y, symbols, text = swatch()
    assert x[1:].tolist() == [1.0, 2.0]
    assert y[1:].tolist() == [3.0, 4.0]
    assert symbols[1:].tolist() == ["circle", "triangle-up"]
    assert text[1:].tolist() == ["first message", "second message"]


def test_every_array_grows_by_the_one_point():
    assert all(len(array) == 3 for array in swatch())
