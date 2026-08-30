import pandas as pd
import pytest

from usenet_no.newsgroup_graph import build_reference_graph


@pytest.fixture
def edges():
    """Three newsgroups and the unknown placeholder, at falling shares.

    no.first sends 630 references out of itself and no.second 400, so the same
    count is a different share of what leaves each of them.
    """
    return pd.DataFrame(
        [
            ("no.first", "no.second", 500, 1200, 630),
            ("no.second", "no.first", 300, 500, 400),
            ("no.first", "unknown", 120, 1200, 630),
            ("no.second", "unknown", 100, 500, 400),
            ("no.first", "no.third", 10, 1200, 630),
        ],
        columns=[
            "from_newsgroup",
            "to_newsgroup",
            "number_of_references",
            "references_from_newsgroup",
            "references_out_of_newsgroup",
        ],
    )


@pytest.fixture
def message_counts():
    return {"no.first": 1000, "no.second": 400, "no.third": 50}


def test_every_newsgroup_becomes_a_vertex(edges, message_counts):
    """The threshold thins the edges, never the newsgroups."""
    graph = build_reference_graph(edges, message_counts, min_reference_share=0.9)

    assert set(graph.nodes) == {"no.first", "no.second", "no.third", "unknown"}
    assert graph.number_of_edges() == 0


def test_edges_below_the_minimum_share_are_dropped(edges, message_counts):
    graph = build_reference_graph(edges, message_counts, min_reference_share=0.5)

    assert set(graph.edges) == {
        ("no.first", "no.second"),
        ("no.second", "no.first"),
    }


def test_the_share_is_read_against_the_referring_newsgroup(edges, message_counts):
    """100 of no.second's references clear a threshold that 120 of no.first's does not."""
    graph = build_reference_graph(edges, message_counts, min_reference_share=0.25)

    assert ("no.second", "unknown") in graph.edges
    assert ("no.first", "unknown") not in graph.edges


def test_an_edge_on_the_threshold_is_kept(edges, message_counts):
    graph = build_reference_graph(edges, message_counts, min_reference_share=100 / 400)

    assert ("no.second", "unknown") in graph.edges


def test_the_two_directions_are_two_edges(edges, message_counts):
    graph = build_reference_graph(edges, message_counts, min_reference_share=0.5)

    assert graph.edges["no.first", "no.second"] == pytest.approx(
        {"references": 500, "share": 500 / 630}
    )
    assert graph.edges["no.second", "no.first"] == pytest.approx(
        {"references": 300, "share": 300 / 400}
    )


def test_the_graph_carries_what_the_drawing_needs(edges, message_counts):
    graph = build_reference_graph(edges, message_counts, min_reference_share=0.5)

    assert graph.nodes["no.first"] == {"messages": 1000}
    assert graph.edges["no.first", "no.second"]["references"] == 500


def test_the_unknown_newsgroup_has_no_message_count(edges, message_counts):
    graph = build_reference_graph(edges, message_counts, min_reference_share=0.5)

    assert graph.nodes["unknown"] == {"messages": None}


def test_a_newsgroup_without_a_message_count_raises(edges, message_counts):
    del message_counts["no.third"]

    with pytest.raises(ValueError, match="no.third"):
        build_reference_graph(edges, message_counts, min_reference_share=0.5)
