import networkx as nx

from usenet_no.gephi import write_graph_gexf


def newsgroup_graph():
    graph = nx.Graph()
    graph.add_node("no.general", users=8)
    graph.add_node("no.test", users=3)
    graph.add_edge("no.general", "no.test", jaccard=0.25, shared_users=2)
    return graph


def written_graph(tmp_path, graph):
    output_file = tmp_path / "graph.gexf"
    write_graph_gexf(graph, output_file, weight_attribute="jaccard")
    return nx.read_gexf(output_file)


def test_the_edges_are_weighted_by_the_named_attribute(tmp_path):
    edge = written_graph(tmp_path, newsgroup_graph()).edges["no.general", "no.test"]
    assert edge["weight"] == 0.25
    assert edge["jaccard"] == 0.25


def test_an_attribute_no_newsgroup_holds_a_value_for_is_left_out(tmp_path):
    graph = newsgroup_graph()
    graph.add_node("unknown", users=None)

    written = written_graph(tmp_path, graph)
    assert "unknown" in written
    assert "users" not in written.nodes["unknown"]


def test_the_graph_handed_in_is_left_as_it_was(tmp_path):
    graph = newsgroup_graph()
    written_graph(tmp_path, graph)
    assert graph.nodes["no.general"] == {"users": 8}
    assert graph.edges["no.general", "no.test"] == {"jaccard": 0.25, "shared_users": 2}
