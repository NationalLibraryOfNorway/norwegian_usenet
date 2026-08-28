"""Newsgroup graphs written as .gexf files to be opened in Gephi.

The file holds the graph itself: the vertices and edges with the attributes
they were built from, and one edge attribute named as the weight Gephi ranks
and filters on. Nothing of how the figure beside it is drawn goes in, so Gephi
lays the graph out on its own.
"""

import logging
from pathlib import Path

import networkx as nx

logger = logging.getLogger(__name__)


def write_graph_gexf(
    graph: nx.Graph, output_file: Path, *, weight_attribute: str
) -> None:
    """Write the graph as a .gexf file.

    `weight_attribute` is the edge attribute Gephi is to read as the weight of
    an edge, and it stays on the edge as an attribute of its own. An attribute
    standing at None, which is what a newsgroup nobody holds the messages of
    carries, is left out of the file.
    """
    written = graph.copy()

    for _node, attributes in written.nodes(data=True):
        held = {name: value for name, value in attributes.items() if value is not None}
        attributes.clear()
        attributes.update(held)

    for edge, weight in nx.get_edge_attributes(written, weight_attribute).items():
        written.edges[edge]["weight"] = weight

    nx.write_gexf(written, output_file)
    logger.info(
        "Wrote %d vertices and %d edges to %s",
        written.number_of_nodes(),
        written.number_of_edges(),
        output_file,
    )
