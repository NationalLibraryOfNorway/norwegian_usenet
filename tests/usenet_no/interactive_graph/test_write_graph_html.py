from usenet_no.interactive_graph import build_network, write_graph_html


def written_page(tmp_path, pin_on_drop=False):
    network = build_network(directed=False)
    network.add_node("no.general", label="no.general", title="8 users", x=0, y=0)
    network.add_node("no.test", label="no.test", title="3 users", x=10, y=20)
    network.add_edge("no.general", "no.test", title="2 shared users")

    output_file = tmp_path / "graph.html"
    write_graph_html(
        network,
        title="Newsgroups",
        subtitle="a pair of them",
        notes=["it falls into one sub-graph", "nothing was left out"],
        pin_on_drop=pin_on_drop,
        output_file=output_file,
    )
    return output_file.read_text(encoding="utf-8")


def test_the_page_carries_the_newsgroups_and_what_joins_them(tmp_path):
    page = written_page(tmp_path)
    assert '"id": "no.general"' in page
    assert '"from": "no.general", "title": "2 shared users", "to": "no.test"' in page


def test_the_page_is_headed_by_the_title_the_subtitle_and_a_note_to_a_line(tmp_path):
    page = written_page(tmp_path)
    assert "<h1>Newsgroups</h1>" in page
    assert "a pair of them" in page
    assert "<p>it falls into one sub-graph</p>" in page
    assert "<p>nothing was left out</p>" in page


def test_a_page_that_pins_on_drop_listens_for_dropping_and_double_clicking(tmp_path):
    page = written_page(tmp_path, pin_on_drop=True)
    assert 'network.on("dragEnd"' in page
    assert 'network.on("doubleClick"' in page


def test_a_page_that_does_not_pin_listens_for_neither(tmp_path):
    page = written_page(tmp_path)
    assert "network.on(" not in page


def test_the_page_brings_its_drawing_library_along(tmp_path):
    page = written_page(tmp_path)
    assert "vis.Network" in page
    assert "<script src=" not in page
    assert "<link " not in page
