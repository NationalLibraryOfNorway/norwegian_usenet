"""Shared plotting utilities."""

from __future__ import annotations

import colorsys
import textwrap

import matplotlib.axes
import numpy as np
from matplotlib_venn import venn2 as _venn2


def format_count(count: int) -> str:
    """Format a count with a narrow no-break space between thousands."""
    return f"{count:,}".replace(",", " ")


def hsl_to_hex(hue: float, saturation: float, lightness: float) -> str:
    """Convert an HSL colour to a hex string.

    Hue is in degrees, saturation and lightness in percent.
    """
    r, g, b = colorsys.hls_to_rgb(hue / 360, lightness / 100, saturation / 100)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def with_square_legend_swatch(
    x: np.ndarray, y: np.ndarray, symbols: np.ndarray, text: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Prepend a point that is not drawn, to make the legend swatch a square.

    Plotly reads the swatch off the first point of a trace, which in a trace of
    mixed marker symbols would name one of them over the others.
    """
    return (
        np.concatenate([[np.nan], x]),
        np.concatenate([[np.nan], y]),
        np.concatenate([["square"], symbols]),
        np.concatenate([[""], text]),
    )


def wrap_hover_text(text: str, width: int = 70) -> str:
    """Break a text into `<br>`-separated lines of at most `width` characters."""
    lines = []
    for line in text.splitlines():
        lines.extend(textwrap.wrap(line, width) or [""])
    return "<br>".join(lines)


def venn2_fmt(
    subsets,
    set_labels: tuple[str, str] = ("A", "B"),
    ax: matplotlib.axes.Axes | None = None,
    show_pct: bool = False,
):
    """Drop-in replacement for venn2 with formatted labels.

    Numbers are space-separated (10 000 instead of 10,000).
    Zero regions are hidden. Optionally a percentage-of-total line is shown
    below each count.

    Parameters
    ----------
    subsets:
        Either a tuple of three ints ``(Ab, aB, AB)`` or a list of two sets.
    set_labels:
        Labels for the two circles.
    ax:
        Axes to draw on.
    show_pct:
        If True, append a ``n.n%`` line below each region count.
    """
    if len(subsets) == 2:
        set_a, set_b = set(subsets[0]), set(subsets[1])
        sizes = (len(set_a - set_b), len(set_b - set_a), len(set_a & set_b))
    else:
        sizes = tuple(int(x) for x in subsets)

    v = _venn2(subsets=sizes, set_labels=set_labels, ax=ax)

    total = sum(sizes)
    for region_id, size in zip(("10", "01", "11"), sizes):
        lbl = v.get_label_by_id(region_id)
        if lbl is None:
            continue
        if size == 0:
            lbl.set_text("")
            continue
        text = format_count(size)
        if show_pct and total > 0:
            text += f"\n{size / total * 100:.1f}%"
        lbl.set_text(text)

    return v
