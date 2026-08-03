import json
import logging
from dataclasses import asdict
from pathlib import Path

import matplotlib.pyplot as plt

from usenet_no.database.comparison import VennCounts
from usenet_no.plot_utils import format_count, venn2_fmt

logger = logging.getLogger(__name__)

SET_LABELS = ("NB", "IA")


def write_counts(counts: VennCounts, out_path: Path) -> None:
    """Write the three regions of a venn diagram as JSON."""
    out_path.write_text(json.dumps(asdict(counts) | {"total": counts.total}, indent=2))
    logger.info("Wrote counts to %s", out_path)


def write_venn(
    counts: VennCounts,
    title: str,
    out_path: Path,
    set_labels: tuple[str, str] = SET_LABELS,
    show_total: bool = False,
) -> None:
    """Draw one NB/IA venn diagram as a .png, optionally with the total under the title."""
    fig, ax = plt.subplots(figsize=(6, 5))
    venn2_fmt(
        subsets=(counts.nb_only, counts.ia_only, counts.both),
        set_labels=set_labels,
        ax=ax,
        show_pct=True,
    )
    ax.set_title(title, pad=24 if show_total else None)
    if show_total:
        ax.text(
            0.5,
            1.02,
            f"Total: {format_count(counts.total)}",
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            fontsize=10,
        )
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    logger.info("Wrote figure to %s", out_path)


def write_venn_and_counts(
    counts: VennCounts, title: str, out_dir: Path, name: str
) -> None:
    """Write `name`.json with the counts and `name`.png with the venn diagram."""
    out_dir.mkdir(parents=True, exist_ok=True)
    write_counts(counts, out_dir / f"{name}.json")
    write_venn(counts, title, out_dir / f"{name}.png")
