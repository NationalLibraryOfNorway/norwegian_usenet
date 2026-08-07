"""Draw the reference edge lists as a directed graph of newsgroups.

Reads an edge list written by 09_graphs_and_references and keeps the
edges clearing the threshold, drawn as arrows from the referring newsgroup to
the referenced one, with the width following the weight. Every newsgroup in
the table is drawn, so one with no edge left shows as a loose point rather
than vanishing.

Vertices are sized by how many messages the newsgroup holds, read from the
per-group count tables written by 03_statistics_per_archive and summed over
the given files. The placeholder unknown newsgroup holds no messages and is
drawn as an orange diamond instead; pass --exclude-unknown to leave it and
its edges out.

Where the newsgroups land is decided by a Kamada-Kawai layout over the two
directions added together, which reads each pair's edge as a distance: the
more references run between two newsgroups the closer together they are
drawn, and a cluster in the picture is a set of newsgroups referencing each
other.
"""

import argparse
import logging
import math
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

from usenet_no.database.reference_graph import UNKNOWN_NEWSGROUP
from usenet_no.newsgroup_graph import build_reference_graph, load_message_counts

logger = logging.getLogger(__name__)

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
NODE_COLOR = "#2a78d6"
UNKNOWN_COLOR = "#d97706"
EDGE_COLOR = "rgba(140, 139, 134, 0.55)"

# Nodes are sized by how many messages a newsgroup holds, between these two,
# and the largest newsgroup is some hundred times the size of the smallest, so
# the count is put on a square root to keep the small ones visible.
SMALLEST_NODE = 6
LARGEST_NODE = 34
UNKNOWN_NODE = 18

# Edge widths follow the weight on a log scale, since the heaviest edge
# carries some hundred times the references of the lightest drawn one.
THINNEST_EDGE = 0.8
WIDEST_EDGE = 4.5

# The two directions between a pair are two arrows, and each is shifted a
# little to its own right so they lie side by side instead of on top of each
# other.
EDGE_OFFSET = 0.012

# Only the largest newsgroups are written on the picture itself; the rest are
# read by hovering, so the dense middle does not fill up with overlapping
# names.
DIRECTLY_LABELLED = 8

# A newsgroup with too few references to be joined to anything has nothing to
# pull it into place, so the unjoined ones are set out in rows below the graph
# rather than left to the layout.
UNJOINED_PER_ROW = 26
UNJOINED_TOP = -1.25
UNJOINED_ROW_HEIGHT = 0.16


def layout_positions(graph: nx.DiGraph) -> dict[str, tuple[float, float]]:
    """Place the joined newsgroups by their references and the rest in rows below.

    The layout reads an undirected collapse of the graph, with the two
    directions of a pair added together, and wants each edge drawn at a
    distance shrinking with that sum, so the pairs referencing each other the
    most sit closest.
    """
    joined = graph.subgraph([node for node, degree in graph.degree() if degree > 0])
    unjoined = [node for node, degree in graph.degree() if degree == 0]

    collapsed = nx.Graph()
    collapsed.add_nodes_from(joined.nodes)
    for source, target, attributes in joined.edges(data=True):
        already = collapsed.get_edge_data(source, target, {"references": 0})
        collapsed.add_edge(
            source,
            target,
            references=attributes["references"] + already["references"],
        )
    for edge in collapsed.edges:
        collapsed.edges[edge]["distance"] = 1 / (
            1 + math.log10(collapsed.edges[edge]["references"])
        )

    positions = {
        node: (float(x), float(y))
        for node, (x, y) in nx.kamada_kawai_layout(collapsed, weight="distance").items()
    }
    for index, node in enumerate(sorted(unjoined)):
        row, column = divmod(index, UNJOINED_PER_ROW)
        positions[node] = (
            -1 + 2 * column / max(UNJOINED_PER_ROW - 1, 1),
            UNJOINED_TOP - row * UNJOINED_ROW_HEIGHT,
        )
    return positions


def shifted_edge(
    positions: dict, source: str, target: str
) -> tuple[tuple[float, float], tuple[float, float]]:
    """The edge's endpoints, shifted a little to the right of its direction.

    The shift keeps the two directions between a pair from lying on top of
    each other, so both arrows can be seen and hovered.
    """
    (x0, y0), (x1, y1) = positions[source], positions[target]
    length = math.hypot(x1 - x0, y1 - y0) or 1
    right_x, right_y = (y1 - y0) / length, -(x1 - x0) / length
    offset_x, offset_y = right_x * EDGE_OFFSET, right_y * EDGE_OFFSET
    return (x0 + offset_x, y0 + offset_y), (x1 + offset_x, y1 + offset_y)


def edge_widths(graph: nx.DiGraph) -> dict[tuple[str, str], float]:
    """Scale each edge's reference count into a line width, on a log scale."""
    weights = {edge: graph.edges[edge]["references"] for edge in graph.edges}
    lightest = math.log10(min(weights.values()))
    heaviest = math.log10(max(weights.values()))
    span = (heaviest - lightest) or 1
    return {
        edge: THINNEST_EDGE
        + (WIDEST_EDGE - THINNEST_EDGE) * (math.log10(weight) - lightest) / span
        for edge, weight in weights.items()
    }


def edge_arrows(graph: nx.DiGraph, positions: dict) -> list[dict]:
    """One arrow per directed edge, drawn from the referring newsgroup."""
    widths = edge_widths(graph)
    arrows = []
    for source, target in graph.edges:
        (x0, y0), (x1, y1) = shifted_edge(positions, source, target)
        arrows.append(
            {
                "ax": x0,
                "ay": y0,
                "x": x1,
                "y": y1,
                "axref": "x",
                "ayref": "y",
                "xref": "x",
                "yref": "y",
                "showarrow": True,
                "arrowhead": 3,
                "arrowsize": 1.2,
                "arrowwidth": widths[source, target],
                "arrowcolor": EDGE_COLOR,
                "text": "",
            }
        )
    return arrows


def edge_hover_trace(graph: nx.DiGraph, positions: dict) -> go.Scatter:
    """An invisible marker on each arrow, nearer its head, so the edge can be read."""
    x, y, text = [], [], []
    for source, target, attributes in graph.edges(data=True):
        (x0, y0), (x1, y1) = shifted_edge(positions, source, target)
        x.append(x0 + (x1 - x0) * 0.6)
        y.append(y0 + (y1 - y0) * 0.6)
        text.append(f"{source} → {target}<br>{attributes['references']:,} references")
    return go.Scatter(
        x=x,
        y=y,
        mode="markers",
        marker={"size": 12, "color": EDGE_COLOR, "opacity": 0},
        hoverinfo="text",
        hovertext=text,
        showlegend=False,
    )


def newsgroup_nodes(graph: nx.DiGraph) -> list[str]:
    """The real newsgroups, leaving the unknown placeholder to its own trace."""
    return [node for node in graph if graph.nodes[node]["messages"] is not None]


def node_sizes(graph: nx.DiGraph) -> list[float]:
    """Scale each newsgroup's message count into a marker size."""
    messages = [graph.nodes[node]["messages"] for node in newsgroup_nodes(graph)]
    largest = max(messages)
    return [
        SMALLEST_NODE + (LARGEST_NODE - SMALLEST_NODE) * (count / largest) ** 0.5
        for count in messages
    ]


def node_labels(graph: nx.DiGraph) -> list[str]:
    """Name the largest newsgroups on the picture, leaving the rest to hover."""
    joined = [node for node in newsgroup_nodes(graph) if graph.degree(node) > 0]
    by_messages = sorted(joined, key=lambda node: -graph.nodes[node]["messages"])
    labelled = set(by_messages[:DIRECTLY_LABELLED])
    return [node if node in labelled else "" for node in newsgroup_nodes(graph)]


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
    return f"<b>{node}</b><br>{held}<br>{outgoing:,} references out, {incoming:,} in"


def node_trace(graph: nx.DiGraph, positions: dict) -> go.Scatter:
    nodes = newsgroup_nodes(graph)
    return go.Scatter(
        x=[positions[node][0] for node in nodes],
        y=[positions[node][1] for node in nodes],
        mode="markers+text",
        marker={
            "size": node_sizes(graph),
            "color": NODE_COLOR,
            "line": {"color": SURFACE, "width": 2},
        },
        text=node_labels(graph),
        textposition="top center",
        textfont={"size": 11, "color": TEXT_PRIMARY},
        hoverinfo="text",
        hovertext=[node_hover(graph, node) for node in nodes],
        showlegend=False,
    )


def unknown_trace(graph: nx.DiGraph, positions: dict) -> go.Scatter | None:
    """The placeholder for references to messages nobody kept, as an orange diamond."""
    unknown = [node for node in graph if graph.nodes[node]["messages"] is None]
    if not unknown:
        return None
    return go.Scatter(
        x=[positions[node][0] for node in unknown],
        y=[positions[node][1] for node in unknown],
        mode="markers+text",
        marker={
            "size": UNKNOWN_NODE,
            "color": UNKNOWN_COLOR,
            "symbol": "diamond",
            "line": {"color": SURFACE, "width": 2},
        },
        text=unknown,
        textposition="top center",
        textfont={"size": 11, "color": TEXT_PRIMARY},
        hoverinfo="text",
        hovertext=[node_hover(graph, node) for node in unknown],
        showlegend=False,
    )


def plot_reference_graph(
    graph: nx.DiGraph, title: str, subtitle: str, output_file: Path
) -> None:
    positions = layout_positions(graph)
    traces = [edge_hover_trace(graph, positions), node_trace(graph, positions)]
    unknown = unknown_trace(graph, positions)
    if unknown is not None:
        traces.append(unknown)

    figure = go.Figure(data=traces)
    for arrow in edge_arrows(graph, positions):
        figure.add_annotation(**arrow)

    hidden_axis = {
        "showgrid": False,
        "zeroline": False,
        "showticklabels": False,
        "visible": False,
    }
    unjoined = [node for node, degree in graph.degree() if degree == 0]
    if unjoined:
        figure.add_annotation(
            x=-1,
            y=UNJOINED_TOP + UNJOINED_ROW_HEIGHT * 0.75,
            text=f"{len(unjoined)} newsgroups joined to nothing at this threshold",
            showarrow=False,
            xanchor="left",
            font={"size": 12, "color": TEXT_SECONDARY},
        )
    figure.update_layout(
        title={
            "text": f"{title}<br><sup>{subtitle}</sup>",
            "font": {"size": 18, "color": TEXT_PRIMARY},
        },
        xaxis=hidden_axis,
        yaxis=hidden_axis,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"color": TEXT_SECONDARY},
        hoverlabel={"bgcolor": SURFACE, "font": {"color": TEXT_PRIMARY}},
        width=1100,
        height=850,
        margin={"l": 20, "r": 20, "t": 80, "b": 20},
    )
    figure.write_html(output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Draw newsgroups joined by the references between them",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--edges-file",
        type=Path,
        default=Path(
            "data/output/09_graphs_and_references/"
            "newsgroup_reference_counts_nb_and_ia.csv"
        ),
        help="Path to a reference edge list CSV file",
    )
    parser.add_argument(
        "--message-counts-files",
        type=Path,
        nargs="+",
        default=[
            Path("data/output/03_statistics_per_archive/messages_per_group_nb.csv"),
            Path(
                "data/output/03_statistics_per_archive/"
                "messages_per_group_ia_date_filtered.csv"
            ),
        ],
        help="Per-group message count CSV files, summed to size the vertices",
    )
    parser.add_argument(
        "--min-references",
        type=int,
        default=500,
        help="Draw an edge only if at least this many references run along it",
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
            "data/output/09_graphs_and_references/plot_newsgroup_reference_graph"
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

    # The threshold and the unknown flag are in the file name, so a run at one
    # setting does not overwrite the picture drawn at another.
    unknown_tag = "_no_unknown" if args.exclude_unknown else ""
    output_file = args.output_directory / (
        f"{args.edges_file.stem}{unknown_tag}_min{args.min_references}.html"
    )
    if output_file.exists() and not args.overwrite:
        logger.info(
            "Existing file found at %s; use --overwrite to regenerate", output_file
        )
        raise SystemExit(0)

    edges = pd.read_csv(args.edges_file)
    message_counts = load_message_counts(args.message_counts_files)
    graph = build_reference_graph(
        edges, message_counts, min_references=args.min_references
    )
    if args.exclude_unknown and UNKNOWN_NEWSGROUP in graph:
        graph.remove_node(UNKNOWN_NEWSGROUP)

    args.output_directory.mkdir(parents=True, exist_ok=True)
    plot_reference_graph(
        graph,
        title="Newsgroups joined by the references between them",
        subtitle=(
            f"{args.edges_file.stem}, "
            f"at least {args.min_references} references per drawn edge"
        ),
        output_file=output_file,
    )
    logger.info("See the graph in %s", output_file)
