import pandas as pd
import pytest

from usenet_no.newsgroup_graph import build_similarity_graph


@pytest.fixture
def similarities():
    """Three newsgroups, pairwise, at falling similarities."""
    return pd.DataFrame(
        [
            ("no.first", "no.second", 100, 80, 0.95),
            ("no.first", "no.third", 100, 20, 0.8),
            ("no.second", "no.third", 80, 20, 0.4),
        ],
        columns=[
            "newsgroup_a",
            "newsgroup_b",
            "messages_a",
            "messages_b",
            "cosine_similarity",
        ],
    )


def test_every_newsgroup_becomes_a_vertex(similarities):
    """The threshold thins the edges, never the newsgroups."""
    graph = build_similarity_graph(similarities, min_similarity=1.0)

    assert set(graph.nodes) == {"no.first", "no.second", "no.third"}
    assert graph.number_of_edges() == 0


def test_pairs_below_the_threshold_are_not_joined(similarities):
    graph = build_similarity_graph(similarities, min_similarity=0.9)

    assert set(graph.edges) == {("no.first", "no.second")}


def test_a_pair_on_the_threshold_is_joined(similarities):
    graph = build_similarity_graph(similarities, min_similarity=0.4)

    assert graph.number_of_edges() == 3


def test_the_graph_carries_what_the_drawing_needs(similarities):
    graph = build_similarity_graph(similarities, min_similarity=0.9)

    assert graph.nodes["no.first"] == {"messages": 100}
    assert graph.edges["no.first", "no.second"] == {"cosine_similarity": 0.95}
