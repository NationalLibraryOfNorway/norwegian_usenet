from usenet_no.interactive_graph import AVERAGE_SPRING, spring_lengths


def test_the_average_edge_is_drawn_at_the_average_length():
    lengths = spring_lengths({"a": 0.5, "b": 1.5})
    assert sum(lengths.values()) / len(lengths) == AVERAGE_SPRING


def test_the_edges_keep_their_distances_relative_to_each_other():
    lengths = spring_lengths({"near": 0.2, "far": 0.6})
    assert lengths["far"] == 3 * lengths["near"]


def test_distances_on_another_scale_come_out_the_same_length():
    assert spring_lengths({"a": 1, "b": 3}) == spring_lengths({"a": 100, "b": 300})


def test_a_graph_with_no_edges_has_no_lengths():
    assert spring_lengths({}) == {}
