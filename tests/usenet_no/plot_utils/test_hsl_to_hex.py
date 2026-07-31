from usenet_no.plot_utils import hsl_to_hex


def test_the_primaries_are_the_corners_of_the_hue_circle():
    assert hsl_to_hex(0, 100, 50) == "#ff0000"
    assert hsl_to_hex(120, 100, 50) == "#00ff00"
    assert hsl_to_hex(240, 100, 50) == "#0000ff"


def test_lightness_runs_from_black_to_white():
    assert hsl_to_hex(0, 100, 0) == "#000000"
    assert hsl_to_hex(0, 100, 100) == "#ffffff"


def test_no_saturation_is_grey_whatever_the_hue():
    assert hsl_to_hex(0, 0, 50) == hsl_to_hex(200, 0, 50)
