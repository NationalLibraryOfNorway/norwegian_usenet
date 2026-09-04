"""Newsgroup graphs written as HTML the reader can drag the vertices around in.

The drawing is done by vis-network, whose assets pyvis brings along and which
are written into the figure itself, so the file can be read without a network.
The vertices are placed where the caller puts them, which is where the physics
the figure is drawn with starts from.
"""

from pathlib import Path

import pyvis
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright
from pyvis.network import Network

SURFACE = "#ffffff"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
BORDER = "#e2e1dc"
FONT_FAMILY = "Helvetica, Arial, sans-serif"

WIDTH = "1100px"
HEIGHT = "1000px"

# The box is taken in to what was drawn in it, keeping this many pixels of air
# above and below, since a graph fitted into the box keeping its proportions
# rarely fills it top to bottom.
BOX_PADDING = 20

# vis-network measures in pixels and counts y downwards, so a layout in the
# usual [-1, 1] square is stretched over this many pixels and turned over.
VIEW_RADIUS = 520

# Vertices are drawn between these two radii, and the count one stands for is
# put on a square root first, since the largest is some hundred times the
# smallest and would leave the rest as dots.
SMALLEST_VERTEX = 4
LARGEST_VERTEX = 22

# An edge is a spring pulling towards the distance it was laid out at. The
# average edge is scaled to this many pixels and the rest around it, so a
# figure settles at a readable size whatever scale its distances are on.
AVERAGE_SPRING = 150

# The physics runs this many rounds before the figure is shown, so it opens on
# a settled arrangement rather than on the vertices sorting themselves out.
STABILIZATION_ROUNDS = 400

# How far apart the vertices left out of the physics are set out under the
# graph. They are given more room across than down, since it is their names
# that crowd, and the rows are as wide as the graph settles, so the room across
# is what decides how many go in each of them. A graph that settles narrow
# would leave a long thin column of them, so the rows hold this many whatever
# the graph does.
LOOSE_COLUMN_SPACING = 130
LOOSE_ROW_SPACING = 60
LOOSE_LEAST_PER_ROW = 15

# A screenshot is taken in a window this wide, which holds the figure and the
# air around it, and at this many pixels to the pixel the page is drawn in.
SCREENSHOT_WIDTH = 1240
SCREENSHOT_SCALE = 4

# The page sets a flag when the physics has settled and the box is taken in,
# which the screenshot waits this many milliseconds for. The graph is still
# drifting a little then, so it is given another moment to come to rest.
SETTLE_TIMEOUT = 120_000
SETTLE_MILLISECONDS = 2_000

TEMPLATE_DIRECTORY = Path(__file__).parent / "templates"
TEMPLATE = "newsgroup_graph.html"
PYVIS_TEMPLATE_DIRECTORY = Path(pyvis.__file__).parent / "templates"


def canvas_position(position: tuple[float, float]) -> tuple[float, float]:
    """Turn a layout position into vis-network's pixel coordinates."""
    x, y = position
    return x * VIEW_RADIUS, -y * VIEW_RADIUS


def vertex_sizes[Vertex](counts: dict[Vertex, int]) -> dict[Vertex, float]:
    """Scale the count each vertex stands for into a radius in pixels."""
    largest = max(counts.values())
    return {
        vertex: SMALLEST_VERTEX
        + (LARGEST_VERTEX - SMALLEST_VERTEX) * (count / largest) ** 0.5
        for vertex, count in counts.items()
    }


def spring_lengths[Edge](
    distances: dict[Edge, float], average: float = AVERAGE_SPRING
) -> dict[Edge, float]:
    """Scale the distances the edges were laid out at into lengths in pixels.

    The average edge comes out `average` pixels long and the rest are scaled
    around it. A graph where nearly everything is joined to everything needs
    more room than that to be read. A threshold can leave a graph with no edges
    at all, which has no lengths to scale.
    """
    if not distances:
        return {}

    average_distance = sum(distances.values()) / len(distances)
    return {
        edge: average * distance / average_distance
        for edge, distance in distances.items()
    }


def build_network(directed: bool) -> Network:
    """An empty network drawn in the colours of the figures around it.

    A directed network draws its edges as arrows and curves them, so the two
    directions between a pair lie side by side rather than on top of each other.

    The physics is on, so a dragged newsgroup pulls the ones it is joined to
    after it and the graph settles again when it is let go. The vertices are
    still put where the caller puts them, which is where the physics starts
    from, and a vertex added with `physics=False` stays there.
    """
    network = Network(height=HEIGHT, width=WIDTH, directed=directed, bgcolor=SURFACE)
    network.options = {
        "nodes": {
            "borderWidth": 2,
            "borderWidthSelected": 2,
            "font": {
                "size": 16,
                "face": FONT_FAMILY,
                "color": TEXT_PRIMARY,
                "strokeWidth": 4,
                "strokeColor": SURFACE,
            },
        },
        "edges": {
            "arrows": {"to": {"enabled": directed, "scaleFactor": 0.55}},
            "smooth": (
                {"enabled": True, "type": "curvedCW", "roundness": 0.1}
                if directed
                else False
            ),
            "selectionWidth": 2,
        },
        "physics": {
            "enabled": True,
            "solver": "barnesHut",
            "barnesHut": {
                "gravitationalConstant": -2500,
                # The pull towards the middle is the only force on a part of
                # the graph joined to nothing else, so it is kept weak: enough
                # to hold such a part in view, little enough that one dragged
                # aside stays roughly where it is put.
                "centralGravity": 0.2,
                "springConstant": 0.05,
                "damping": 0.5,
                "avoidOverlap": 0.2,
            },
            "stabilization": {
                "enabled": True,
                "iterations": STABILIZATION_ROUNDS,
                "fit": True,
            },
        },
        "interaction": {"hover": True, "tooltipDelay": 80, "keyboard": False},
    }
    return network


def _template_environment() -> Environment:
    """Jinja reading both our page template and the vis-network assets."""
    return Environment(
        loader=FileSystemLoader([TEMPLATE_DIRECTORY, PYVIS_TEMPLATE_DIRECTORY]),
        autoescape=select_autoescape(enabled_extensions=("html",)),
    )


def write_graph_html(
    network: Network,
    title: str,
    subtitle: str,
    notes: list[str],
    output_file: Path,
    *,
    pin_on_drop: bool,
) -> None:
    """Write the network as a page of its own, under the title and the notes.

    The notes are written one to a line, above the graph along with the title
    and subtitle. Under `pin_on_drop` a vertex is left where the reader drops
    it instead of being pulled back by the physics, until they double-click it.
    """
    nodes, edges, _heading, height, width, options = network.get_network_data()
    page = _template_environment().get_template(TEMPLATE)
    output_file.write_text(
        page.render(
            title=title,
            subtitle=subtitle,
            notes=notes,
            pin_on_drop=pin_on_drop,
            nodes=nodes,
            edges=edges,
            options=options,
            width=width,
            height=height,
            box_padding=BOX_PADDING,
            loose_column_spacing=LOOSE_COLUMN_SPACING,
            loose_row_spacing=LOOSE_ROW_SPACING,
            loose_least_per_row=LOOSE_LEAST_PER_ROW,
            surface=SURFACE,
            border=BORDER,
            text_primary=TEXT_PRIMARY,
            text_secondary=TEXT_SECONDARY,
            font_family=FONT_FAMILY,
        ),
        encoding="utf-8",
    )


def save_graph_png(html_file: Path, output_file: Path) -> None:
    """Screenshot a written figure with a headless browser, once it has settled."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(
            viewport={"width": SCREENSHOT_WIDTH, "height": 1000},
            device_scale_factor=SCREENSHOT_SCALE,
        )
        page.goto(html_file.resolve().as_uri())
        page.wait_for_function("window.graphSettled === true", timeout=SETTLE_TIMEOUT)
        page.wait_for_timeout(SETTLE_MILLISECONDS)
        page.screenshot(path=output_file, full_page=True)
        browser.close()
