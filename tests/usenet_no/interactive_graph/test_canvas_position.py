from usenet_no.interactive_graph import VIEW_RADIUS, canvas_position


def test_the_middle_of_the_layout_is_the_middle_of_the_canvas():
    assert canvas_position((0.0, 0.0)) == (0.0, 0.0)


def test_the_corners_of_the_layout_are_a_view_radius_out():
    assert canvas_position((1.0, 0.0)) == (VIEW_RADIUS, 0.0)
    assert canvas_position((-1.0, 0.0)) == (-VIEW_RADIUS, 0.0)


def test_what_the_layout_puts_above_the_middle_is_drawn_above_it():
    _x, y = canvas_position((0.0, 0.5))
    assert y < 0
