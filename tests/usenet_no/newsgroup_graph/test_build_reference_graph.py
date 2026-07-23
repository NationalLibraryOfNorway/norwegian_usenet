import pandas as pd
import pytest

from usenet_no.newsgroup_graph import build_reference_graph


@pytest.fixture
def edges():
    """Three newsgroups and the unknown placeholder, at falling weights."""
    return pd.DataFrame(
        [
            ("no.first", "no.second", 500),
            ("no.second", "no.first", 300),
            ("no.first", "unknown", 120),
            ("no.first", "no.third", 10),
        ],
        columns=["from_newsgroup", "to_newsgroup", "number_of_references"],
    )


@pytest.fixture
def message_counts():
    return {"no.first": 1000, "no.second": 400, "no.third": 50}


def test_every_newsgroup_becomes_a_vertex(edges, message_counts):
    """The threshold thins the edges, never the newsgroups."""
    graph = build_reference_graph(edges, message_counts, min_references=1000)

    assert set(graph.nodes) == {"no.first", "no.second", "no.third", "unknown"}
    assert graph.number_of_edges() == 0


def test_edges_below_the_minimum_are_dropped(edges, message_counts):
    graph = build_reference_graph(edges, message_counts, min_references=120)

    assert set(graph.edges) == {
        ("no.first", "no.second"),
        ("no.second", "no.first"),
        ("no.first", "unknown"),
    }


def test_an_edge_on_the_threshold_is_kept(edges, message_counts):
    graph = build_reference_graph(edges, message_counts, min_references=10)

    assert graph.number_of_edges() == 4


def test_the_two_directions_are_two_edges(edges, message_counts):
    graph = build_reference_graph(edges, message_counts, min_references=300)

    assert graph.edges["no.first", "no.second"] == {"references": 500}
    assert graph.edges["no.second", "no.first"] == {"references": 300}


def test_the_graph_carries_what_the_drawing_needs(edges, message_counts):
    graph = build_reference_graph(edges, message_counts, min_references=500)

    assert graph.nodes["no.first"] == {"messages": 1000}
    assert graph.edges["no.first", "no.second"] == {"references": 500}


def test_the_unknown_newsgroup_has_no_message_count(edges, message_counts):
    graph = build_reference_graph(edges, message_counts, min_references=500)

    assert graph.nodes["unknown"] == {"messages": None}


def test_a_newsgroup_without_a_message_count_raises(edges, message_counts):
    del message_counts["no.third"]

    with pytest.raises(ValueError, match="no.third"):
        build_reference_graph(edges, message_counts, min_references=500)
