import pandas as pd
import pytest

from usenet_no.newsgroup_graph import build_overlap_graph


@pytest.fixture
def overlaps():
    """Three newsgroups, pairwise, at falling overlaps."""
    return pd.DataFrame(
        [
            ("no.first", "no.second", 100, 80, 40, 0.5),
            ("no.first", "no.third", 100, 20, 10, 0.1),
            ("no.second", "no.third", 80, 20, 4, 0.04),
        ],
        columns=[
            "newsgroup_a",
            "newsgroup_b",
            "users_a",
            "users_b",
            "shared_users",
            "jaccard",
        ],
    )


def test_every_newsgroup_becomes_a_vertex(overlaps):
    """Thresholds thin the edges, never the newsgroups."""
    graph = build_overlap_graph(overlaps, jaccard_threshold=1.0, min_shared_users=1)

    assert set(graph.nodes) == {"no.first", "no.second", "no.third"}
    assert graph.number_of_edges() == 0


def test_pairs_below_the_jaccard_threshold_are_not_joined(overlaps):
    graph = build_overlap_graph(overlaps, jaccard_threshold=0.1, min_shared_users=0)

    assert set(graph.edges) == {
        ("no.first", "no.second"),
        ("no.first", "no.third"),
    }


def test_pairs_below_the_shared_user_minimum_are_not_joined(overlaps):
    graph = build_overlap_graph(overlaps, jaccard_threshold=0.0, min_shared_users=40)

    assert set(graph.edges) == {("no.first", "no.second")}


def test_both_thresholds_have_to_be_cleared(overlaps):
    """no.first-no.third clears the jaccard one alone, and is left unjoined."""
    graph = build_overlap_graph(overlaps, jaccard_threshold=0.1, min_shared_users=40)

    assert set(graph.edges) == {("no.first", "no.second")}


def test_a_pair_on_the_threshold_is_joined(overlaps):
    """Both thresholds are inclusive, so the weakest pair survives its own values."""
    graph = build_overlap_graph(overlaps, jaccard_threshold=0.04, min_shared_users=4)

    assert graph.number_of_edges() == 3


def test_the_graph_carries_what_the_drawing_needs(overlaps):
    graph = build_overlap_graph(overlaps, jaccard_threshold=0.5, min_shared_users=1)

    assert graph.nodes["no.first"] == {"users": 100}
    assert graph.edges["no.first", "no.second"] == {
        "jaccard": 0.5,
        "shared_users": 40,
    }
