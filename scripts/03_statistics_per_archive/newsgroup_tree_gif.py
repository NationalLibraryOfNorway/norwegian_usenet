"""Generate scrolling .gif animations of the newsgroup hierarchy trees."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import animation

from usenet_no.newsgroup_tree import load_counts, tree_lines


def make_gif(
    label: str,
    lines: list[str],
    output_path: Path,
    viewport: int,
    step: int,
    fps: int,
    figsize: tuple[float, float],
    fontsize: int,
) -> None:
    n_scroll = max(1, (len(lines) - viewport + step - 1) // step)
    hold = fps  # 1 s hold at start and end
    total_frames = hold + n_scroll + hold

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    ax.axis("off")
    fig.suptitle(
        label,
        color="#58a6ff",
        fontsize=fontsize + 2,
        fontfamily="monospace",
        y=0.97,
    )

    txt = ax.text(
        0.02,
        0.94,
        "",
        transform=ax.transAxes,
        fontfamily="monospace",
        fontsize=fontsize,
        color="#3fb950",
        verticalalignment="top",
        linespacing=1.35,
    )

    def update(frame: int):
        if frame < hold:
            start = 0
        elif frame >= hold + n_scroll:
            start = (n_scroll - 1) * step
        else:
            start = (frame - hold) * step
        txt.set_text("\n".join(lines[start : start + viewport]))
        return (txt,)

    anim = animation.FuncAnimation(
        fig, update, frames=total_frames, interval=1000 / fps, blit=True
    )
    writer = animation.PillowWriter(fps=fps)
    anim.save(output_path, writer=writer)
    plt.close(fig)
    print(f"Saved {output_path}  ({total_frames} frames, {total_frames / fps:.1f}s)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate scrolling .gif of newsgroup hierarchy trees",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--ia-csv",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/messages_per_group_ia.csv"),
        help="CSV with IA message counts per newsgroup (default: %(default)s)",
    )
    parser.add_argument(
        "--nb-csv",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/messages_per_group_nb.csv"),
        help="CSV with NB message counts per newsgroup (default: %(default)s)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/newsgroup_tree"),
        help="Directory for output .gif files (default: %(default)s)",
    )
    parser.add_argument(
        "--viewport",
        type=int,
        default=30,
        help="Lines visible at once (default: %(default)s)",
    )
    parser.add_argument(
        "--step",
        type=int,
        default=1,
        help="Lines scrolled per frame (default: %(default)s)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=12,
        help="Frames per second (default: %(default)s)",
    )
    parser.add_argument(
        "--figsize",
        type=float,
        nargs=2,
        metavar=("W", "H"),
        default=[10.0, 6.0],
        help="Figure size in inches (default: %(default)s)",
    )
    parser.add_argument(
        "--fontsize",
        type=int,
        default=9,
        help="Font size in points (default: %(default)s)",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for archive_label, csv_path, gif_name in [
        ("IA", args.ia_csv, "newsgroup_tree_ia.gif"),
        ("NB", args.nb_csv, "newsgroup_tree_nb.gif"),
    ]:
        lines = tree_lines(archive_label, load_counts(csv_path))
        output_path = args.output_dir / gif_name
        print(f"Generating {output_path}  ({len(lines)} lines) ...")
        make_gif(
            archive_label,
            lines,
            output_path,
            viewport=args.viewport,
            step=args.step,
            fps=args.fps,
            figsize=tuple(args.figsize),
            fontsize=args.fontsize,
        )


if __name__ == "__main__":
    main()
