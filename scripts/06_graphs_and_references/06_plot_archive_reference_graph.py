"""Draw the archive reference edge list as a three vertex directed graph.

Reads the edge list written by 05_count_references_between_archives and draws
NB, IA and the placeholder for the references neither archive resolves, which
is drawn as `?`. Every edge carries its reference count beside it: the self
loops the references pointing at a message the archive holds itself, the two
arrows between NB and IA the ones only the other archive still holds, and the
arrows into `?` the ones that resolve nowhere.

The three vertices are placed by hand rather than laid out, with `?` over the
two archives, so the two self loops hang under them and the six edges keep
clear of each other.
"""

import argparse
import logging
import math
from pathlib import Path

import matplotlib.path as mpath
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Circle, FancyArrowPatch

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.reference_graph import UNKNOWN_NEWSGROUP
from usenet_no.plot_utils import format_count

logger = logging.getLogger(__name__)

NODE_LABELS = {NB_ARCHIVE: "NB", IA_ARCHIVE: "IA", UNKNOWN_NEWSGROUP: "?"}
NODE_POSITIONS = {
    NB_ARCHIVE: (-1.0, -0.35),
    IA_ARCHIVE: (1.0, -0.35),
    UNKNOWN_NEWSGROUP: (0.0, 1.15),
}
NODE_RADIUS = 0.34

NODE_COLOR = "#2a78d6"
UNKNOWN_COLOR = "#d97706"
EDGE_COLOR = "#52514e"
LABEL_COLOR = "#0b0b0b"
SURFACE = "#fcfcfb"

# An archive is drawn as a filled vertex. The placeholder is drawn as a dotted
# outline instead, standing as it does for messages neither archive holds.
ARCHIVE_VERTEX = {"facecolor": NODE_COLOR, "edgecolor": "none", "linewidth": 0}
PLACEHOLDER_VERTEX = {
    "facecolor": SURFACE,
    "edgecolor": UNKNOWN_COLOR,
    "linewidth": 2.0,
    # A dot and the gap after it, in points.
    "linestyle": (0, (1.5, 2.5)),
}

# How each edge is drawn: how much it bows, as the curvature matplotlib's arc3
# takes, and how far aside it is set from the line between its two vertices, to
# the right of the way it runs. The two arrows between the archives run
# straight, and are set aside so that they do not lie on top of each other; the
# two into `?` bow instead, the sign deciding which side they bow to. A self
# loop is no arc3 curve and is drawn as a circle of its own.
EDGE_SHAPES = {
    (NB_ARCHIVE, IA_ARCHIVE): (0.0, 0.09),
    (IA_ARCHIVE, NB_ARCHIVE): (0.0, 0.09),
    (NB_ARCHIVE, UNKNOWN_NEWSGROUP): (-0.16, 0.0),
    (IA_ARCHIVE, UNKNOWN_NEWSGROUP): (0.16, 0.0),
}

# Where a self loop leaves and re-enters its vertex, in degrees around it. The
# loops hang under the archives, the placeholder standing over them.
SELF_LOOP_ANGLES = (210, 330)

# The radius of the circle a self loop is drawn as, as a multiple of the vertex
# radius. It has to be more than half the distance between the loop's two ends,
# there being no circle through them below that.
SELF_LOOP_RADIUS = 1.05

# How many straight steps that circle is drawn in. Enough that the corners
# between them do not show at the size the figure is written at.
SELF_LOOP_STEPS = 72

# The arrow head stops this far outside the vertex it points at, and a count is
# written this far beyond the curve it belongs to.
ARROW_GAP = 0.05
LABEL_GAP = 0.2


def circle_point(
    centre: tuple[float, float], radius: float, direction: tuple[float, float]
) -> tuple[float, float]:
    """The point `radius` away from `centre` in the given direction."""
    x, y = centre
    dx, dy = direction
    length = (dx**2 + dy**2) ** 0.5
    return x + radius * dx / length, y + radius * dy / length


def edge_ends(
    source: tuple[float, float], target: tuple[float, float]
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Where an edge between two vertices starts and where its arrow head lands."""
    towards = (target[0] - source[0], target[1] - source[1])
    away = (-towards[0], -towards[1])
    return (
        circle_point(source, NODE_RADIUS, towards),
        circle_point(target, NODE_RADIUS + ARROW_GAP, away),
    )


def offset_ends(
    start: tuple[float, float], end: tuple[float, float], offset: float
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Both ends of an edge, set `offset` aside to the right of the way it runs."""
    (x1, y1), (x2, y2) = start, end
    dx, dy = x2 - x1, y2 - y1
    length = (dx**2 + dy**2) ** 0.5
    across_x, across_y = offset * dy / length, -offset * dx / length
    return (x1 + across_x, y1 + across_y), (x2 + across_x, y2 + across_y)


def self_loop_ends(
    centre: tuple[float, float],
) -> tuple[tuple[float, float], tuple[float, float]]:
    """The two points on its vertex that a self loop leaves from and comes back to."""
    left, right = (
        (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
        for angle in SELF_LOOP_ANGLES
    )
    return (
        circle_point(centre, NODE_RADIUS, left),
        circle_point(centre, NODE_RADIUS, right),
    )


def self_loop_circle(
    centre: tuple[float, float],
) -> tuple[tuple[float, float], float]:
    """The centre and radius of the circle a self loop is drawn as.

    The circle runs through both ends of the loop, and of the two circles of
    that radius that do, this is the one whose centre lies away from the
    vertex, so that the loop stands outside it rather than across it.
    """
    (x1, y1), (x2, y2) = self_loop_ends(centre)
    middle = ((x1 + x2) / 2, (y1 + y2) / 2)
    half_chord = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 / 2
    radius = SELF_LOOP_RADIUS * NODE_RADIUS
    outwards = (middle[0] - centre[0], middle[1] - centre[1])
    return (
        circle_point(middle, (radius**2 - half_chord**2) ** 0.5, outwards),
        radius,
    )


def self_loop_path(centre: tuple[float, float]) -> mpath.Path:
    """The circular arc a self loop is drawn along, from one of its ends round to the other.

    The arc taken is the longer of the two between the loop's ends, the vertex
    lying on the near side of the line between them, and it stops short of the
    end it comes back to, leaving the arrow head the same gap as the other
    edges keep. A negative sweep runs the arc anticlockwise.
    """
    (loop_x, loop_y), radius = self_loop_circle(centre)
    (x1, y1), (x2, y2) = self_loop_ends(centre)
    start = math.atan2(y1 - loop_y, x1 - loop_x)
    end = math.atan2(y2 - loop_y, x2 - loop_x)
    clockwise = (start - end) % (2 * math.pi)
    sweep = clockwise if clockwise >= math.pi else clockwise - 2 * math.pi
    sweep -= math.copysign(ARROW_GAP / radius, sweep)
    return mpath.Path(
        [
            (
                loop_x + radius * math.cos(start - sweep * step / SELF_LOOP_STEPS),
                loop_y + radius * math.sin(start - sweep * step / SELF_LOOP_STEPS),
            )
            for step in range(SELF_LOOP_STEPS + 1)
        ]
    )


def label_position(
    start: tuple[float, float], end: tuple[float, float], curvature: float
) -> tuple[float, float]:
    """Where to write an edge's count: past the middle of the curve it bows into.

    An arc3 curve reaches half its curvature out from the middle of the
    straight line, along the perpendicular the sign of the curvature picks, and
    the count is set a little further out again so it clears the line.
    """
    (x1, y1), (x2, y2) = start, end
    dx, dy = x2 - x1, y2 - y1
    length = (dx**2 + dy**2) ** 0.5
    outwards = 1 if curvature >= 0 else -1
    return (
        (x1 + x2) / 2 + curvature * dy / 2 + outwards * LABEL_GAP * dy / length,
        (y1 + y2) / 2 - curvature * dx / 2 - outwards * LABEL_GAP * dx / length,
    )


def write_count(ax, position: tuple[float, float], references: int) -> None:
    """Write one edge's reference count at a point, on a patch of the background."""
    ax.text(
        *position,
        format_count(references),
        ha="center",
        va="center",
        fontsize=11,
        color=LABEL_COLOR,
        bbox={"facecolor": SURFACE, "edgecolor": "none", "pad": 2},
    )


def draw_edge(ax, start, end, curvature: float, references: int) -> None:
    """Draw one arrow between two points, with its reference count beside it."""
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops={
            "arrowstyle": "-|>",
            "color": EDGE_COLOR,
            "linewidth": 1.6,
            "shrinkA": 0,
            "shrinkB": 0,
            "connectionstyle": f"arc3,rad={curvature}",
            "mutation_scale": 18,
        },
    )
    write_count(ax, label_position(start, end, curvature), references)


def draw_self_loop(ax, centre: tuple[float, float], references: int) -> None:
    """Draw one vertex's self loop as a circle standing on it, with its count above."""
    ax.add_patch(
        FancyArrowPatch(
            path=self_loop_path(centre),
            arrowstyle="-|>",
            color=EDGE_COLOR,
            linewidth=1.6,
            shrinkA=0,
            shrinkB=0,
            mutation_scale=18,
        )
    )
    loop_centre, radius = self_loop_circle(centre)
    outwards = (loop_centre[0] - centre[0], loop_centre[1] - centre[1])
    write_count(ax, circle_point(loop_centre, radius + LABEL_GAP, outwards), references)


def draw_vertices(ax) -> None:
    """Draw the two archives and the placeholder for what neither of them holds."""
    for node, position in NODE_POSITIONS.items():
        placeholder = node == UNKNOWN_NEWSGROUP
        ax.add_patch(
            Circle(
                position,
                NODE_RADIUS,
                zorder=3,
                **(PLACEHOLDER_VERTEX if placeholder else ARCHIVE_VERTEX),
            )
        )
        ax.text(
            *position,
            NODE_LABELS[node],
            ha="center",
            va="center",
            fontsize=18,
            color=UNKNOWN_COLOR if placeholder else SURFACE,
            zorder=4,
        )


def plot_archive_reference_graph(edges: pd.DataFrame, title: str, output_file: Path):
    """Draw the edge list as a graph over NB, IA and the unknown placeholder."""
    fig, ax = plt.subplots(figsize=(7, 6.5))

    draw_vertices(ax)
    for row in edges.itertuples():
        references = int(row.number_of_references)
        if row.from_archive == row.to_archive:
            draw_self_loop(ax, NODE_POSITIONS[row.from_archive], references)
        else:
            curvature, offset = EDGE_SHAPES[(row.from_archive, row.to_archive)]
            start, end = offset_ends(
                *edge_ends(
                    NODE_POSITIONS[row.from_archive], NODE_POSITIONS[row.to_archive]
                ),
                offset,
            )
            draw_edge(ax, start, end, curvature, references)

    ax.set_xlim(-1.85, 1.85)
    ax.set_ylim(-1.42, 1.68)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title)

    fig.tight_layout()
    fig.savefig(output_file, dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Draw NB, IA and the unresolved placeholder as a reference graph",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--edges-file",
        type=Path,
        default=Path(
            "data/output/06_graphs_and_references/archive_reference_counts.csv"
        ),
        help="Path to the archive reference edge list CSV file",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(
            "data/output/06_graphs_and_references/archive_reference_graph.png"
        ),
        help="The .png file to write the figure to",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite an existing figure instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    if args.output_file.exists() and not args.overwrite:
        logger.info(
            "Existing file found at %s; use --overwrite to regenerate", args.output_file
        )
        raise SystemExit(0)

    edges = pd.read_csv(args.edges_file)
    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    plot_archive_reference_graph(
        edges,
        title="Where the references of each archive resolve",
        output_file=args.output_file,
    )
    logger.info("Wrote figure to %s", args.output_file)
