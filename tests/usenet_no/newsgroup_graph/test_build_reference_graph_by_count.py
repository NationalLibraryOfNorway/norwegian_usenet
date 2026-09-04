import pandas as pd
import pytest

from usenet_no.newsgroup_graph import build_reference_graph_by_count


@pytest.fixture
def edges():
    """Three newsgroups and the unknown placeholder, at falling counts.

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
    graph = build_reference_graph_by_count(edges, message_counts, min_references=1000)

    assert set(graph.nodes) == {"no.first", "no.second", "no.third", "unknown"}
    assert graph.number_of_edges() == 0


def test_edges_below_the_minimum_count_are_dropped(edges, message_counts):
    graph = build_reference_graph_by_count(edges, message_counts, min_references=300)

    assert set(graph.edges) == {
        ("no.first", "no.second"),
        ("no.second", "no.first"),
    }


def test_the_count_is_read_whatever_the_referring_newsgroup_sends(
    edges, message_counts
):
    """120 of no.first's references clear a threshold that 100 of no.second's does not."""
    graph = build_reference_graph_by_count(edges, message_counts, min_references=120)

    assert ("no.first", "unknown") in graph.edges
    assert ("no.second", "unknown") not in graph.edges


def test_an_edge_on_the_threshold_is_kept(edges, message_counts):
    graph = build_reference_graph_by_count(edges, message_counts, min_references=100)

    assert ("no.second", "unknown") in graph.edges


def test_the_graph_carries_what_the_drawing_needs(edges, message_counts):
    graph = build_reference_graph_by_count(edges, message_counts, min_references=300)

    assert graph.nodes["no.first"] == {"messages": 1000}
    assert graph.edges["no.first", "no.second"] == pytest.approx(
        {"references": 500, "share": 500 / 630}
    )
