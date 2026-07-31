"""Draw the newsgroup overlap table as a graph of newsgroups joined by users.

Reads the pair table written by 07_newsgroups_and_user_analysis and keeps the
pairs clearing both thresholds as edges. Every newsgroup in the table is drawn,
so a newsgroup with no edge left shows as a loose point rather than vanishing.
Pass --selection to draw only some of them.

Where the newsgroups land is decided by a Kamada-Kawai layout, which reads each
edge as a distance and looks for the arrangement whose drawn distances come
closest to those. The distance an edge asks for is 1 - jaccard, so the more two
newsgroups overlap the closer together they are drawn, and a cluster in the
picture is a set of newsgroups sharing users with each other.
"""

import argparse
import logging
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

from usenet_no.newsgroup_graph import build_overlap_graph, select_newsgroups

logger = logging.getLogger(__name__)

SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
NODE_COLOR = "#2a78d6"
EDGE_COLOR = "#8c8b86"

# Nodes are sized by how many users a newsgroup had, between these two, and the
# largest newsgroup is some hundred times the size of the smallest, so the count
# is put on a square root to keep the small ones visible.
SMALLEST_NODE = 6
LARGEST_NODE = 34

# Only the largest newsgroups are written on the picture itself; the rest are
# read by hovering, so the dense middle does not fill up with overlapping names.
# Size rather than edge count decides, because the most joined newsgroups sit on
# top of each other and their names would too.
DIRECTLY_LABELLED = 8

# A newsgroup sharing too few users to be joined to anything has nothing to pull
# it into place, so the unjoined ones are set out in rows below the graph rather
# than left to the layout, which rings them around it and squeezes the graph
# itself into the middle.
UNJOINED_PER_ROW = 26
UNJOINED_TOP = -1.25
UNJOINED_ROW_HEIGHT = 0.16


def layout_positions(graph: nx.Graph) -> dict[str, tuple[float, float]]:
    """Place the joined newsgroups by their overlap and the rest in rows below.

    Only the newsgroups that have an edge are laid out, so they get the whole
    picture to spread out in rather than being squeezed into the middle of the
    ones they are not joined to.
    """
    joined = graph.subgraph([node for node, degree in graph.degree() if degree > 0])
    unjoined = [node for node, degree in graph.degree() if degree == 0]

    # The layout reads the weight as the distance an edge would like to be
    # drawn at, which is the opposite of what jaccard says: the more two
    # newsgroups overlap, the nearer they belong.
    distances = {edge: 1 - graph.edges[edge]["jaccard"] for edge in joined.edges}
    joined = nx.Graph(joined)
    nx.set_edge_attributes(joined, distances, "distance")

    positions = {
        node: (float(x), float(y))
        for node, (x, y) in nx.kamada_kawai_layout(joined, weight="distance").items()
    }
    for index, node in enumerate(sorted(unjoined)):
        row, column = divmod(index, UNJOINED_PER_ROW)
        positions[node] = (
            -1 + 2 * column / max(UNJOINED_PER_ROW - 1, 1),
            UNJOINED_TOP - row * UNJOINED_ROW_HEIGHT,
        )
    return positions


def node_sizes(graph: nx.Graph) -> list[float]:
    """Scale each newsgroup's user count into a marker size."""
    users = [graph.nodes[node]["users"] for node in graph]
    largest = max(users)
    return [
        SMALLEST_NODE + (LARGEST_NODE - SMALLEST_NODE) * (count / largest) ** 0.5
        for count in users
    ]


def node_labels(graph: nx.Graph) -> list[str]:
    """Name the largest newsgroups on the picture, leaving the rest to hover."""
    joined = [node for node, degree in graph.degree() if degree > 0]
    by_users = sorted(joined, key=lambda node: -graph.nodes[node]["users"])
    labelled = set(by_users[:DIRECTLY_LABELLED])
    return [node if node in labelled else "" for node in graph]


def edge_trace(graph: nx.Graph, positions: dict) -> go.Scatter:
    """One line per edge, drawn as a single trace broken by None between them."""
    x, y = [], []
    for first, second in graph.edges():
        x.extend([positions[first][0], positions[second][0], None])
        y.extend([positions[first][1], positions[second][1], None])
    return go.Scatter(
        x=x,
        y=y,
        mode="lines",
        line={"color": EDGE_COLOR, "width": 1},
        opacity=0.6,
        hoverinfo="skip",
        showlegend=False,
    )


def edge_hover_trace(graph: nx.Graph, positions: dict) -> go.Scatter:
    """An invisible marker at each edge's midpoint, so the edge can be read."""
    x, y, text = [], [], []
    for first, second, attributes in graph.edges(data=True):
        x.append((positions[first][0] + positions[second][0]) / 2)
        y.append((positions[first][1] + positions[second][1]) / 2)
        text.append(
            f"{first} — {second}<br>"
            f"jaccard {attributes['jaccard']:.3f}<br>"
            f"{attributes['shared_users']:,} shared users"
        )
    return go.Scatter(
        x=x,
        y=y,
        mode="markers",
        marker={"size": 12, "color": EDGE_COLOR, "opacity": 0},
        hoverinfo="text",
        hovertext=text,
        showlegend=False,
    )


def node_trace(graph: nx.Graph, positions: dict) -> go.Scatter:
    hover = [
        f"<b>{node}</b><br>"
        f"{graph.nodes[node]['users']:,} users<br>"
        f"joined to {degree} newsgroup(s)"
        for node, degree in graph.degree()
    ]
    return go.Scatter(
        x=[positions[node][0] for node in graph],
        y=[positions[node][1] for node in graph],
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
        hovertext=hover,
        showlegend=False,
    )


def plot_overlap_graph(
    graph: nx.Graph, title: str, subtitle: str, output_file: Path
) -> None:
    positions = layout_positions(graph)
    figure = go.Figure(
        data=[
            edge_trace(graph, positions),
            edge_hover_trace(graph, positions),
            node_trace(graph, positions),
        ]
    )
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
            text=f"{len(unjoined)} newsgroups joined to nothing at these thresholds",
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


def convert_and_validate_cli_arg_jaccard_threshold(value: str) -> float:
    threshold = float(value)
    if not 0 <= threshold <= 1:
        raise argparse.ArgumentTypeError(f"must be between 0 and 1, was {threshold}")
    return threshold


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Draw newsgroups joined by the users they share"
    )
    parser.add_argument(
        "--overlap-file",
        type=Path,
        default=Path(
            "data/output/07_newsgroups_and_user_analysis/"
            "newsgroup_user_jaccard_overlap_nb_and_ia_date_filtered.csv"
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
        default=25,
        help="Join two newsgroups only if they share at least this many users",
    )
    parser.add_argument(
        "--selection",
        nargs="+",
        metavar="NEWSGROUP",
        default=None,
        help="Newsgroup names to draw (default: every newsgroup in the overlap file)",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("data/output/08_visualize/plot_newsgroup_overlap_graph"),
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

    # The thresholds and the selection are in the file name, so a run at one
    # setting does not overwrite the picture drawn at another.
    selection_tag = f"_{'_'.join(sorted(args.selection))}" if args.selection else ""
    output_file = args.output_directory / (
        f"{args.overlap_file.stem}"
        f"{selection_tag}"
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
    if args.selection:
        # Selecting after the graph is built, so that the thresholds are read
        # against the whole table and a selected newsgroup keeps its user count
        # even when none of the others share enough users with it.
        graph = select_newsgroups(graph, args.selection)

    args.output_directory.mkdir(parents=True, exist_ok=True)
    plot_overlap_graph(
        graph,
        title="Newsgroups joined by the users they share",
        subtitle=(
            f"{args.overlap_file.stem}, "
            f"jaccard at least {args.jaccard_threshold}, "
            f"at least {args.min_shared_users} shared users"
            + (f", {len(args.selection)} selected newsgroups" if args.selection else "")
        ),
        output_file=output_file,
    )
    logger.info("See the graph in %s", output_file)
