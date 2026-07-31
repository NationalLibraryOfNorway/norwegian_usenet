"""Plot the U+FFFD share of IA/NB body conflicts as bars."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

CONFLICTS_COLUMN = "message_body_conflict"
IA_CONTAINS_COLUMN = "ia_contains_�"
EQUAL_COLUMN = "messages_equal_with_char_replacement"

# One blue per nesting level, light to dark, with counts labeled on every level
LEVEL_COLORS = ("#c6dbef", "#6baed6", "#2171b5")
INK = "#333333"


def format_count(count: int) -> str:
    return f"{count:,}".replace(",", " ")  # narrow no-break space


def print_conflict_stats(conflicts: int, ia_contains: int, equal: int) -> None:
    print(f"Message body conflicts:        {conflicts:,}")
    print(
        f"IA body contains �:            {ia_contains:,}"
        f" ({ia_contains / conflicts:.1%})"
    )
    print(f"Equal with char replacement:   {equal:,} ({equal / conflicts:.1%})")


def plot_conflict_bars(
    conflicts: int, ia_contains: int, equal: int, out_path: Path
) -> None:
    """Draw the three counts as bars scaled to their share of all conflicts."""
    fig, ax = plt.subplots(figsize=(7, 5))

    counts = (conflicts, ia_contains, equal)
    shares = [count / conflicts for count in counts]
    labels = [
        "message body\nconflicts",
        "IA body\ncontains �",
        "equal with char\nreplacement",
    ]
    bars = ax.bar(labels, [share * 100 for share in shares], color=LEVEL_COLORS)
    ax.bar_label(
        bars,
        labels=[
            f"{format_count(count)}\n({share:.1%})"
            for count, share in zip(counts, shares)
        ],
        padding=4,
        color=INK,
    )

    ax.set_ylim(0, 112)
    ax.set_yticks(range(0, 101, 20))
    ax.set_ylabel("% of conflicts")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title("IA/NB body conflicts and the � replacement character")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot the U+FFFD share of IA/NB body conflicts as bars",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--conflicts-csv",
        type=Path,
        default=Path(
            "data/output/04_compare_archives/replacement_char_body_conflicts.csv"
        ),
        help="CSV with replacement char conflict counts per newsgroup (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/output/08_visualize/plot_replacement_char_body_conflicts"),
        help="Directory for output files (default: %(default)s)",
    )
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.conflicts_csv)
    conflicts = int(df[CONFLICTS_COLUMN].sum())
    ia_contains = int(df[IA_CONTAINS_COLUMN].sum())
    equal = int(df[EQUAL_COLUMN].sum())

    print_conflict_stats(conflicts, ia_contains, equal)
    out_path = args.out_dir / "replacement_char_body_conflicts_bars.png"
    plot_conflict_bars(conflicts, ia_contains, equal, out_path)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
