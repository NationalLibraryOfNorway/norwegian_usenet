"""Draw the newsgroup overlap table as a graph of newsgroups joined by users.

Reads the pair table written by 06_graphs_and_references and keeps the
pairs clearing both thresholds as edges. Every newsgroup in the table is drawn,
so a newsgroup with no edge left shows as a loose point rather than vanishing.

Where the newsgroups start out is decided by a Kamada-Kawai layout, which reads
each edge as a distance and looks for the arrangement whose drawn distances come
closest to those. The distance an edge asks for is 1 - jaccard, so the more two
newsgroups overlap the closer together they are drawn, and a cluster in the
picture is a set of newsgroups sharing users with each other. The same distance
is the length each edge pulls towards under the physics the figure is drawn
with, so a newsgroup dragged aside takes the ones it shares users with along
and the graph settles back at those distances when it is let go.
"""

import argparse
import logging
from pathlib import Path

import networkx as nx
import pandas as pd
from pyvis.network import Network

from usenet_no.interactive_graph import (
    SURFACE,
    build_network,
    canvas_position,
    spring_lengths,
    vertex_sizes,
    write_graph_html,
)
from usenet_no.newsgroup_graph import build_overlap_graph

logger = logging.getLogger(__name__)

NODE_COLOR = "#2a78d6"
EDGE_COLOR = "rgba(140, 139, 134, 0.6)"

HOW_TO_READ = (
    "Drag a vertex and the ones it is joined to follow, drag the background to"
    " pan, scroll to zoom, and hover over a vertex or an edge to read it."
)


def layout_positions(graph: nx.Graph) -> dict[str, tuple[float, float]]:
    """Where the physics starts the joined newsgroups off from.

    Only the newsgroups that have an edge are laid out. A newsgroup sharing too
    few users to be joined to anything has nothing to pull it into place, so it
    is left out of the physics and set out in a row under the graph instead.
    """
    # Sorted, because the layout starts the vertices off on a circle in the
    # order the graph holds them, and a subgraph hands them over in the order of
    # a set, which is a different order in every process.
    joined_nodes = sorted(node for node, degree in graph.degree() if degree > 0)
    joined = nx.Graph()
    joined.add_nodes_from(joined_nodes)
    joined.add_edges_from(graph.subgraph(joined_nodes).edges(data=True))

    # The layout reads the weight as the distance an edge would like to be
    # drawn at, which is the opposite of what jaccard says: the more two
    # newsgroups overlap, the nearer they belong.
    distances = {edge: 1 - joined.edges[edge]["jaccard"] for edge in joined.edges}
    nx.set_edge_attributes(joined, distances, "distance")

    return {
        node: (float(x), float(y))
        for node, (x, y) in nx.kamada_kawai_layout(joined, weight="distance").items()
    }


def add_newsgroups(
    network: Network,
    graph: nx.Graph,
    positions: dict[str, tuple[float, float]],
) -> None:
    sizes = vertex_sizes(nx.get_node_attributes(graph, "users"))
    for node, degree in graph.degree():
        # A newsgroup joined to nothing has no edge to hold it, so it is left
        # out of the physics and set out in a row under the graph by the page.
        joined = degree > 0
        x, y = canvas_position(positions[node]) if joined else (0.0, 0.0)
        network.add_node(
            node,
            label=node,
            title=(
                f"{node}\n"
                f"{graph.nodes[node]['users']:,} users\n"
                f"joined to {degree} newsgroup(s)"
            ),
            x=x,
            y=y,
            physics=joined,
            size=sizes[node],
            color={"background": NODE_COLOR, "border": SURFACE},
        )


def add_overlaps(network: Network, graph: nx.Graph) -> None:
    lengths = spring_lengths(
        {edge: 1 - graph.edges[edge]["jaccard"] for edge in graph.edges}
    )
    for first, second, attributes in graph.edges(data=True):
        network.add_edge(
            first,
            second,
            title=(
                f"{first} — {second}\n"
                f"jaccard {attributes['jaccard']:.3f}\n"
                f"{attributes['shared_users']:,} shared users"
            ),
            length=lengths[first, second],
            width=1,
            color=EDGE_COLOR,
        )


def graph_notes(graph: nx.Graph) -> list[str]:
    """What the graph holds: its connected sub-graphs and the loose newsgroups.

    The newsgroups joined to nothing are counted on their own rather than as a
    sub-graph each.
    """
    sub_graphs = sum(1 for part in nx.connected_components(graph) if len(part) > 1)
    loose = nx.number_of_isolates(graph)

    notes = [
        f"The newsgroups with edges fall into {sub_graphs} connected sub-graphs"
        " with no edge between them."
    ]
    if loose:
        notes.append(
            f"The {loose} newsgroups joined to nothing at these thresholds"
            " are set out in rows below the graph."
        )
    return notes


def plot_overlap_graph(
    graph: nx.Graph,
    title: str,
    subtitle: str,
    output_file: Path,
) -> None:
    positions = layout_positions(graph)
    network = build_network(directed=False)
    add_newsgroups(network, graph, positions)
    add_overlaps(network, graph)

    write_graph_html(
        network,
        title,
        subtitle,
        [*graph_notes(graph), HOW_TO_READ],
        output_file,
        pin_on_drop=False,
    )


def convert_and_validate_cli_arg_jaccard_threshold(value: str) -> float:
    threshold = float(value)
    if not 0 <= threshold <= 1:
        raise argparse.ArgumentTypeError(f"must be between 0 and 1, was {threshold}")
    return threshold


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Draw newsgroups joined by the users they share",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--overlap-file",
        type=Path,
        default=Path(
            "data/output/06_graphs_and_references/"
            "newsgroup_user_jaccard_overlap_nb_and_ia.csv"
        ),
        help="Path to a newsgroup overlap CSV file",
    )
    parser.add_argument(
        "--jaccard-threshold",
        type=convert_and_validate_cli_arg_jaccard_threshold,
        default=0.15,
        help="Join two newsgroups only if their jaccard overlap is at least this",
    )
    parser.add_argument(
        "--min-shared-users",
        type=int,
        default=5,
        help="Join two newsgroups only if they share at least this many users",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path(
            "data/output/06_graphs_and_references/plot_newsgroup_overlap_graph"
        ),
        help="Directory to write the HTML figure to",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite an existing figure instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    # The thresholds are in the file name, so a run at one setting does not
    # overwrite the picture drawn at another.
    output_file = args.output_directory / (
        f"{args.overlap_file.stem}"
        f"_jaccard{args.jaccard_threshold}"
        f"_shared{args.min_shared_users}.html"
    )
    if output_file.exists() and not args.overwrite:
        logger.info(
            "Existing file found at %s; use --overwrite to regenerate", output_file
        )
        raise SystemExit(0)

    overlaps = pd.read_csv(args.overlap_file)
    graph = build_overlap_graph(
        overlaps,
        jaccard_threshold=args.jaccard_threshold,
        min_shared_users=args.min_shared_users,
    )
    args.output_directory.mkdir(parents=True, exist_ok=True)
    plot_overlap_graph(
        graph,
        title="Newsgroups joined by the users they share",
        subtitle=(
            f"{args.overlap_file.stem}, "
            f"jaccard at least {args.jaccard_threshold}, "
            f"at least {args.min_shared_users} shared users"
        ),
        output_file=output_file,
    )
    logger.info("See the graph in %s", output_file)
