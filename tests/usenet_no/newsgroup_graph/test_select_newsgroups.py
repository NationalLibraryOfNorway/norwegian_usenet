import networkx as nx
import pytest

from usenet_no.newsgroup_graph import select_newsgroups


@pytest.fixture
def graph():
    """Three newsgroups, where the third is joined to the first one only."""
    graph = nx.Graph()
    graph.add_node("no.first", users=100)
    graph.add_node("no.second", users=80)
    graph.add_node("no.third", users=20)
    graph.add_edge("no.first", "no.second", jaccard=0.5, shared_users=40)
    graph.add_edge("no.first", "no.third", jaccard=0.1, shared_users=10)
    return graph


def test_newsgroups_outside_the_selection_are_dropped(graph):
    graph = select_newsgroups(graph, ["no.first", "no.third"])

    assert set(graph.nodes) == {"no.first", "no.third"}


def test_edges_to_dropped_newsgroups_go_with_them(graph):
    graph = select_newsgroups(graph, ["no.first", "no.third"])

    assert set(graph.edges) == {("no.first", "no.third")}


def test_a_selected_newsgroup_joined_to_none_of_the_others_is_kept(graph):
    """It is drawn as a loose point, rather than left out of the picture."""
    graph = select_newsgroups(graph, ["no.second", "no.third"])

    assert set(graph.nodes) == {"no.second", "no.third"}
    assert graph.number_of_edges() == 0


def test_the_selection_carries_what_the_drawing_needs(graph):
    graph = select_newsgroups(graph, ["no.first", "no.second"])

    assert graph.nodes["no.first"] == {"users": 100}
    assert graph.edges["no.first", "no.second"] == {
        "jaccard": 0.5,
        "shared_users": 40,
    }


def test_an_unknown_newsgroup_raises(graph):
    with pytest.raises(ValueError, match="no.fourth"):
        select_newsgroups(graph, ["no.first", "no.fourth"])
