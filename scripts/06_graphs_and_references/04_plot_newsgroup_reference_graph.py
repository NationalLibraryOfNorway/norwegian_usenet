"""Draw the reference edge lists as a directed graph of newsgroups.

Reads an edge list written by 06_graphs_and_references and keeps the edges
carrying at least a given share of the references leaving the referring
newsgroup, so that the considerable size differences between the newsgroups do
not decide which edges are drawn. They are drawn as arrows from the referring
newsgroup to the referenced one, with the width following the number of
references. The two directions between a pair are drawn as two curves, so both
can be seen and hovered. Every newsgroup in the table is drawn, so one with no
edge left shows as a loose point rather than vanishing.

Vertices are sized by how many messages the newsgroup holds, read from the
per-group count tables written by 03_statistics_per_archive and summed over
the given files. The placeholder unknown newsgroup holds no messages and is
drawn as an orange diamond instead; pass --exclude-unknown to leave it and
its edges out.

Where the newsgroups start out is decided by a Kamada-Kawai layout over the two
directions added together, which reads each pair's edge as a distance: the
more references run between two newsgroups the closer together they are
drawn, and a cluster in the picture is a set of newsgroups referencing each
other. The same distance is the length each edge pulls towards under the
physics the figure is drawn with, so a newsgroup dragged aside takes the ones
referencing it along and the graph settles back at those distances when it is
let go.
"""

import argparse
import logging
import math
from pathlib import Path

import networkx as nx
import pandas as pd
from pyvis.network import Network

from usenet_no.database.reference_graph import UNKNOWN_NEWSGROUP
from usenet_no.gephi import write_graph_gexf
from usenet_no.interactive_graph import (
    SURFACE,
    build_network,
    canvas_position,
    spring_lengths,
    vertex_sizes,
    write_graph_html,
)
from usenet_no.newsgroup_graph import build_reference_graph, load_message_counts

logger = logging.getLogger(__name__)

NODE_COLOR = "#2a78d6"
UNKNOWN_COLOR = "#d97706"
EDGE_COLOR = "rgba(140, 139, 134, 0.55)"

# The unknown placeholder holds no messages to be sized by, so its diamond is
# drawn at this radius.
UNKNOWN_NODE = 12

# Nearly every newsgroup references the busiest few, so the springs are given
# more room than the usual, or the arrows crowd into one grey ball.
AVERAGE_SPRING = 460

# Edge widths follow the weight on a log scale, since the heaviest edge
# carries some hundred times the references of the lightest drawn one.
THINNEST_EDGE = 0.8
WIDEST_EDGE = 4.5


def reference_distance(references: int) -> float:
    """The distance an edge carrying this many references wants to be drawn at."""
    return 1 / (1 + math.log10(references))


def layout_positions(graph: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Where the physics starts the joined newsgroups off from.

    The layout reads an undirected collapse of the graph, with the two
    directions of a pair added together, and wants each edge drawn at a
    distance shrinking with that sum, so the pairs referencing each other the
    most sit closest. Only the newsgroups that have an edge are laid out; a
    newsgroup with too few references to be joined to anything has nothing to
    pull it into place, so it is left out of the physics and set out in a row
    under the graph instead.
    """
    # Sorted, because the layout starts the vertices off on a circle in the
    # order the graph holds them, and a subgraph hands them over in the order of
    # a set, which is a different order in every process.
    joined_nodes = sorted(node for node, degree in graph.degree() if degree > 0)
    joined = graph.subgraph(joined_nodes)

    collapsed = nx.Graph()
    collapsed.add_nodes_from(joined_nodes)
    for source, target, attributes in joined.edges(data=True):
        already = collapsed.get_edge_data(source, target, {"references": 0})
        collapsed.add_edge(
            source,
            target,
            references=attributes["references"] + already["references"],
        )
    for edge in collapsed.edges:
        collapsed.edges[edge]["distance"] = reference_distance(
            collapsed.edges[edge]["references"]
        )

    return {
        node: (float(x), float(y))
        for node, (x, y) in nx.kamada_kawai_layout(collapsed, weight="distance").items()
    }


def edge_widths(graph: nx.DiGraph) -> dict[tuple[str, str], float]:
    """Scale each edge's reference count into a line width, on a log scale.

    A threshold can leave a graph with no edges at all, which has no widths.
    """
    weights = {edge: graph.edges[edge]["references"] for edge in graph.edges}
    if not weights:
        return {}

    lightest = math.log10(min(weights.values()))
    heaviest = math.log10(max(weights.values()))
    span = (heaviest - lightest) or 1
    return {
        edge: THINNEST_EDGE
        + (WIDEST_EDGE - THINNEST_EDGE) * (math.log10(weight) - lightest) / span
        for edge, weight in weights.items()
    }


def node_hover(graph: nx.DiGraph, node: str) -> str:
    outgoing = sum(
        attributes["references"]
        for _s, _t, attributes in graph.out_edges(node, data=True)
    )
    incoming = sum(
        attributes["references"]
        for _s, _t, attributes in graph.in_edges(node, data=True)
    )
    messages = graph.nodes[node]["messages"]
    held = f"{messages:,} messages" if messages is not None else "messages nobody kept"
    return f"{node}\n{held}\n{outgoing:,} references out, {incoming:,} in"


def add_newsgroups(
    network: Network,
    graph: nx.DiGraph,
    positions: dict[str, tuple[float, float]],
) -> None:
    """Add a vertex per newsgroup, the unknown placeholder as an orange diamond."""
    messages = nx.get_node_attributes(graph, "messages")
    sizes = vertex_sizes(
        {node: held for node, held in messages.items() if held is not None}
    )
    for node in graph:
        # A newsgroup joined to nothing has no edge to hold it, so it is left
        # out of the physics and set out in a row under the graph by the page.
        joined = graph.degree(node) > 0
        x, y = canvas_position(positions[node]) if joined else (0.0, 0.0)
        unknown = messages[node] is None
        network.add_node(
            node,
            label=node,
            title=node_hover(graph, node),
            x=x,
            y=y,
            physics=joined,
            shape="diamond" if unknown else "dot",
            size=UNKNOWN_NODE if unknown else sizes[node],
            color={
                "background": UNKNOWN_COLOR if unknown else NODE_COLOR,
                "border": SURFACE,
            },
        )


def add_references(network: Network, graph: nx.DiGraph) -> None:
    widths = edge_widths(graph)
    lengths = spring_lengths(
        {
            edge: reference_distance(graph.edges[edge]["references"])
            for edge in graph.edges
        },
        average=AVERAGE_SPRING,
    )
    for source, target, attributes in graph.edges(data=True):
        network.add_edge(
            source,
            target,
            title=(
                f"{source} → {target}\n{attributes['references']:,} references,"
                f" {attributes['share']:.1%} of the references leaving {source}"
            ),
            length=lengths[source, target],
            width=widths[source, target],
            color=EDGE_COLOR,
        )


def graph_notes(graph: nx.DiGraph) -> list[str]:
    """What the graph holds: its connected sub-graphs and the loose newsgroups.

    A sub-graph is read without the direction of its references, so two
    newsgroups referencing each other one way round belong to the same one, and
    the newsgroups joined to nothing are counted on their own rather than as a
    sub-graph each.
    """
    sub_graphs = sum(
        1 for part in nx.weakly_connected_components(graph) if len(part) > 1
    )
    loose = nx.number_of_isolates(graph)

    notes = [
        f"The newsgroups with edges fall into {sub_graphs} connected sub-graphs"
        " with no reference between them."
    ]
    if loose:
        notes.append(
            f"The {loose} newsgroups joined to nothing at this threshold"
            " are set out in rows below the graph."
        )
    return notes


def plot_reference_graph(
    graph: nx.DiGraph,
    title: str,
    subtitle: str,
    output_file: Path,
) -> None:
    positions = layout_positions(graph)
    network = build_network(directed=True)
    add_newsgroups(network, graph, positions)
    add_references(network, graph)

    # A vertex pulled out of the crowd to be read is left where it is put.
    write_graph_html(
        network, title, subtitle, graph_notes(graph), output_file, pin_on_drop=True
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Draw newsgroups joined by the references between them",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--edges-file",
        type=Path,
        default=Path(
            "data/output/06_graphs_and_references/newsgroup_reference_counts_nb.csv"
        ),
        help="Path to a reference edge list CSV file",
    )
    parser.add_argument(
        "--message-counts-files",
        type=Path,
        nargs="+",
        default=[
            Path("data/output/03_statistics_per_archive/messages_per_group_nb.csv"),
        ],
        help="Per-group message count CSV files, summed to size the vertices",
    )
    parser.add_argument(
        "--min-reference-share",
        type=float,
        default=0.2,
        help=(
            "Draw an edge only if it carries at least this share of the"
            " references leaving the referring newsgroup"
        ),
    )
    parser.add_argument(
        "--exclude-unknown",
        action="store_true",
        help=(
            "If flagged, leave out the unknown placeholder for references"
            " to messages nobody kept, and every edge reaching it"
        ),
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path(
            "data/output/06_graphs_and_references/plot_newsgroup_reference_graph"
        ),
        help="Directory to write the HTML figure and the .gexf file to",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite an existing figure instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    # The threshold and the flag are in the file name, so a run at one setting
    # does not overwrite the picture drawn at another.
    unknown_tag = "_no_unknown" if args.exclude_unknown else ""
    figure_file = args.output_directory / (
        f"{args.edges_file.stem}{unknown_tag}_share{args.min_reference_share:g}.html"
    )
    gephi_file = figure_file.with_suffix(".gexf")
    if figure_file.exists() and gephi_file.exists() and not args.overwrite:
        logger.info(
            "Existing files found at %s and %s; use --overwrite to regenerate",
            figure_file,
            gephi_file,
        )
        raise SystemExit(0)

    edges = pd.read_csv(args.edges_file)
    message_counts = load_message_counts(args.message_counts_files)
    graph = build_reference_graph(
        edges, message_counts, min_reference_share=args.min_reference_share
    )
    if args.exclude_unknown and UNKNOWN_NEWSGROUP in graph:
        graph.remove_node(UNKNOWN_NEWSGROUP)

    args.output_directory.mkdir(parents=True, exist_ok=True)
    plot_reference_graph(
        graph,
        title="Newsgroups joined by the references between them",
        subtitle=(
            f"{args.edges_file.stem}, each drawn edge carrying at least "
            f"{args.min_reference_share:.1%} of the references leaving its newsgroup"
        ),
        output_file=figure_file,
    )
    write_graph_gexf(graph, gephi_file, weight_attribute="references")
    logger.info("See the graph in %s, and in Gephi from %s", figure_file, gephi_file)
