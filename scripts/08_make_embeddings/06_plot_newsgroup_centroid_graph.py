"""Draw the centroid similarity table as a graph of newsgroups joined by what they read like.

Reads the pair table written by 05_newsgroup_centroid_similarity.py and keeps
the pairs clearing the threshold as edges. Every newsgroup in the table is
drawn, so one with no edge left shows as a loose point rather than vanishing.

Where the newsgroups start out is decided by a Kamada-Kawai layout, which reads
each edge as a distance and looks for the arrangement whose drawn distances
come closest to those. The distance an edge asks for is 1 - cosine similarity,
so the more alike two newsgroups read the closer together they are drawn, and a
cluster in the picture is a set of newsgroups whose messages average out near
each other. The same distance is the length each edge pulls towards under the
physics the figure is drawn with.
"""

import argparse
import logging
from pathlib import Path

import networkx as nx
import pandas as pd
from pyvis.network import Network

from usenet_no.gephi import write_graph_gexf
from usenet_no.interactive_graph import (
    SURFACE,
    build_network,
    canvas_position,
    save_graph_png,
    spring_lengths,
    vertex_sizes,
    write_graph_html,
)
from usenet_no.newsgroup_graph import build_similarity_graph

logger = logging.getLogger(__name__)

NODE_COLOR = "#2a78d6"
EDGE_COLOR = "rgba(140, 139, 134, 0.6)"

HOW_TO_READ = (
    "Drag a vertex and the ones it is joined to follow, drag the background to"
    " pan, scroll to zoom, and hover over a vertex or an edge to read it."
)


def similarity_distance(similarity: float) -> float:
    """The distance an edge between centroids this alike wants to be drawn at."""
    return 1 - similarity


def layout_positions(graph: nx.Graph) -> dict[str, tuple[float, float]]:
    """Where the physics starts the joined newsgroups off from.

    Only the newsgroups that have an edge are laid out. A newsgroup too unlike
    the rest to be joined to anything has nothing to pull it into place, so it
    is left out of the physics and set out in a row under the graph instead.
    """
    # Sorted, because the layout starts the vertices off on a circle in the
    # order the graph holds them, and a subgraph hands them over in the order of
    # a set, which is a different order in every process.
    joined_nodes = sorted(node for node, degree in graph.degree() if degree > 0)
    joined = nx.Graph()
    joined.add_nodes_from(joined_nodes)
    joined.add_edges_from(graph.subgraph(joined_nodes).edges(data=True))

    distances = {
        edge: similarity_distance(joined.edges[edge]["cosine_similarity"])
        for edge in joined.edges
    }
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
    sizes = vertex_sizes(nx.get_node_attributes(graph, "messages"))
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
                f"{graph.nodes[node]['messages']:,} messages embedded\n"
                f"joined to {degree} newsgroup(s)"
            ),
            x=x,
            y=y,
            physics=joined,
            size=sizes[node],
            color={"background": NODE_COLOR, "border": SURFACE},
        )


def add_similarities(network: Network, graph: nx.Graph) -> None:
    lengths = spring_lengths(
        {
            edge: similarity_distance(graph.edges[edge]["cosine_similarity"])
            for edge in graph.edges
        }
    )
    for first, second, attributes in graph.edges(data=True):
        network.add_edge(
            first,
            second,
            title=(
                f"{first} — {second}\n"
                f"cosine similarity {attributes['cosine_similarity']:.4f}"
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
            f"The {loose} newsgroups joined to nothing at this threshold"
            " are set out in rows below the graph."
        )
    return notes


def plot_similarity_graph(
    graph: nx.Graph,
    title: str,
    subtitle: str,
    output_file: Path,
) -> None:
    positions = layout_positions(graph)
    network = build_network(directed=False)
    add_newsgroups(network, graph, positions)
    add_similarities(network, graph)

    # A vertex pulled out of the crowd to be read is left where it is put.
    write_graph_html(
        network,
        title,
        subtitle,
        [*graph_notes(graph), HOW_TO_READ],
        output_file,
        pin_on_drop=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Draw newsgroups joined by how alike their centroids are",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--similarity-file",
        type=Path,
        default=Path(
            "data/output/08_make_embeddings/newsgroup_centroid_similarity"
            "/codefuse-ai/F2LLM-v2-0.6B/centroid_similarity_nb.csv"
        ),
        help="Path to a centroid similarity CSV file",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.9,
        help="Join two newsgroups only if their centroids are at least this alike",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/output/08_make_embeddings/plot_newsgroup_centroid_graph"),
        help="Directory to write the HTML figure and the .gexf file to",
    )
    parser.add_argument(
        "--save-fig",
        action="store_true",
        help=(
            "If flagged, will also save the settled figure as a .png beside it,"
            " screenshot in a headless browser"
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite an existing figure instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    # The threshold is in the file name, so a run at one setting does not
    # overwrite the picture drawn at another.
    figure_file = args.output_directory / (
        f"{args.similarity_file.stem}_similarity{args.min_similarity:g}.html"
    )
    gephi_file = figure_file.with_suffix(".gexf")
    png_file = figure_file.with_suffix(".png")
    written = [figure_file, gephi_file] + ([png_file] if args.save_fig else [])
    if all(file.exists() for file in written) and not args.overwrite:
        logger.info(
            "Existing files found at %s; use --overwrite to regenerate",
            ", ".join(str(file) for file in written),
        )
        raise SystemExit(0)

    similarities = pd.read_csv(args.similarity_file)
    graph = build_similarity_graph(similarities, min_similarity=args.min_similarity)

    args.output_directory.mkdir(parents=True, exist_ok=True)
    plot_similarity_graph(
        graph,
        title="Newsgroups joined by how alike their messages read",
        subtitle=(
            f"{args.similarity_file.stem}, each edge joining centroids at least "
            f"{args.min_similarity:g} alike"
        ),
        output_file=figure_file,
    )
    write_graph_gexf(graph, gephi_file, weight_attribute="cosine_similarity")
    logger.info("See the graph in %s, and in Gephi from %s", figure_file, gephi_file)

    if args.save_fig:
        save_graph_png(figure_file, png_file)
        logger.info("Saved the settled figure to %s", png_file)
