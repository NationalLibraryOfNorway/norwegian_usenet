"""Plot message counts per user, for full IA data and IA filtered to the NB date span.

A user is one email address, counted per archive, so no user is followed from one
archive to the other. Anything held up against NB is read off the date filtered
IA counts, since the full IA runs past the NB archive at both ends.
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from matplotlib.ticker import FuncFormatter

from usenet_no.plot_utils import format_count

# The two shares are two identities, so they are drawn in two colours of their
# own, and the text in the ink the other figures are lettered with. Nothing is
# lettered on top of a fill, where the ink would have to hold its own against
# the colour under it. The pair is muted as far as it can be: any softer and
# the blue reads as grey rather than as a colour.
TOP_COLOR = "#4a7fb5"
REST_COLOR = "#cb7c52"
TEXT_PRIMARY = "#0b0b0b"
SURFACE = "#ffffff"

# The two segments of the bar, and the two slices of the pie, are set apart by
# a gap of this many points in the colour of the surface behind them.
SEGMENT_GAP = 2


def space_thousands(value, _):
    return format_count(int(value))


space_fmt = FuncFormatter(space_thousands)


def load_user_counts(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df.sort_values("post_count", ascending=False)


def print_stats(df: pd.DataFrame, label: str) -> None:
    print(f"{label}")
    print(f"  Total unique users: {len(df):,}")
    print(f"  Total messages:     {df['post_count'].sum():,}")


def print_top_user_counts(df_ia: pd.DataFrame, df_nb: pd.DataFrame, n: int) -> None:
    print(f"\nTop {n} users — IA date-filtered")
    print(df_ia.head(n).reset_index().post_count.apply(space_fmt))
    print(f"Number of messages by top {n} users in Norwegian Web Archive data")
    print(df_nb.head(n).reset_index().post_count.apply(space_fmt))


def top_vs_rest_counts(df: pd.DataFrame, n: int) -> tuple[int, int]:
    """Messages written by the n users who wrote most, and by all the rest."""
    return df.head(n)["post_count"].sum(), df.iloc[n:]["post_count"].sum()


def legend_labels(df: pd.DataFrame, n: int) -> tuple[str, str]:
    """Name each of the two groups by whose messages it holds."""
    return (
        f"Messages by the top {n} users",
        f"Messages by the remaining {format_count(len(df) - n)} users",
    )


def share_label(count: int, total: int) -> str:
    """A group's messages, over what part of the archive they are."""
    return f"{format_count(count)}\n{count / total * 100:.1f} %"


def plot_top_vs_rest_bar(df: pd.DataFrame, n: int, title: str, out_path: Path) -> None:
    """Draw the two groups' messages as one horizontal bar split in two."""
    counts = top_vs_rest_counts(df, n)
    total = sum(counts)

    fig, ax = plt.subplots(figsize=(10, 2.4))
    left = 0
    for count, color, label in zip(
        counts, (TOP_COLOR, REST_COLOR), legend_labels(df, n)
    ):
        ax.barh(
            0,
            count,
            left=left,
            height=0.4,
            color=color,
            label=label,
            edgecolor=SURFACE,
            linewidth=SEGMENT_GAP,
        )
        ax.text(
            left + count / 2,
            -0.28,
            share_label(count, total),
            ha="center",
            multialignment="center",
            va="top",
            fontsize=11,
            color=TEXT_PRIMARY,
        )
        left += count

    ax.set_xlim(0, total)
    ax.set_ylim(-0.75, 0.55)
    ax.axis("off")
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 0.8),
        ncols=2,
        frameon=False,
        fontsize=11,
        labelcolor=TEXT_PRIMARY,
    )
    ax.set_title(title, color=TEXT_PRIMARY, pad=28)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=SURFACE)
    plt.close(fig)


def plot_top_vs_rest_pie(df: pd.DataFrame, n: int, title: str, out_path: Path) -> None:
    """Draw the two groups' messages as the two slices of a pie."""
    counts = top_vs_rest_counts(df, n)
    total = sum(counts)

    fig, ax = plt.subplots(figsize=(7, 5.5))
    wedges, _labels = ax.pie(
        counts,
        colors=(TOP_COLOR, REST_COLOR),
        # Clockwise from twelve o'clock, so the smaller share is read first.
        startangle=90,
        counterclock=False,
        labels=[share_label(count, total) for count in counts],
        labeldistance=1.08,
        wedgeprops={"edgecolor": SURFACE, "linewidth": SEGMENT_GAP},
        textprops={"color": TEXT_PRIMARY, "fontsize": 11, "multialignment": "center"},
    )
    ax.legend(
        wedges,
        legend_labels(df, n),
        loc="lower center",
        bbox_to_anchor=(0.5, -0.08),
        ncols=2,
        frameon=False,
        fontsize=11,
        labelcolor=TEXT_PRIMARY,
    )
    ax.set_title(title, color=TEXT_PRIMARY)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=SURFACE)
    plt.close(fig)


def plot_cumulative_distribution(dfs: list, out_path: Path) -> None:
    fig = go.Figure()
    for df, label in dfs:
        df_sorted = df.sort_values("post_count", ascending=False).reset_index(drop=True)
        df_sorted["cumulative_pct"] = (
            df_sorted["post_count"].cumsum() / df_sorted["post_count"].sum() * 100
        )
        fig.add_trace(
            go.Scatter(
                x=df_sorted.index + 1,
                y=df_sorted["cumulative_pct"],
                mode="lines",
                name=label,
            )
        )
    fig.add_hline(y=50, line_dash="dash", line_color="purple", annotation_text="50%")
    fig.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="80%")
    fig.update_layout(
        title="Cumulative message distribution by user",
        xaxis_title="Number of top users",
        yaxis_title="Cumulative % of all messages",
    )
    fig.write_image(out_path)


def print_cumulative_stats(dfs: list) -> None:
    for df, label in dfs:
        df_sorted = df.sort_values("post_count", ascending=False).reset_index(drop=True)
        df_sorted["cumulative_pct"] = (
            df_sorted["post_count"].cumsum() / df_sorted["post_count"].sum() * 100
        )
        n = len(df_sorted)
        users_50 = (df_sorted["cumulative_pct"] >= 50).idxmax() + 1
        users_80 = (df_sorted["cumulative_pct"] >= 80).idxmax() + 1
        print(
            f"{label}: top {users_50:,} users ({users_50 / n * 100:.2f}%) account for 50% of messages"
        )
        print(
            f"{label}: top {users_80:,} users ({users_80 / n * 100:.2f}%) account for 80% of messages"
        )
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot message counts per user for the IA and NB archives",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--ia-csv",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/messages_per_user_ia.csv"),
        help="CSV with IA message counts per user (default: %(default)s)",
    )
    parser.add_argument(
        "--ia-date-filtered-csv",
        type=Path,
        default=Path(
            "data/output/03_statistics_per_archive/messages_per_user_ia_date_filtered.csv"
        ),
        help="CSV with date filtered IA message counts per user (default: %(default)s)",
    )
    parser.add_argument(
        "--nb-csv",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/messages_per_user_nb.csv"),
        help="CSV with NB message counts per user (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/plot_messages_per_user"),
        help="Directory for output image files (default: %(default)s)",
    )
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    ia_full = load_user_counts(args.ia_csv)
    ia_filtered = load_user_counts(args.ia_date_filtered_csv)
    df_nb = load_user_counts(args.nb_csv)

    for label, df in [
        ("Full IA", ia_full),
        ("IA date-filtered", ia_filtered),
        ("NB", df_nb),
    ]:
        print_stats(df, label)
        print()

    nb_pct = df_nb["post_count"].sum() / ia_filtered["post_count"].sum() * 100
    print(f"NB is {nb_pct:.1f}% the size of the date-filtered IA by message count")

    print_top_user_counts(ia_filtered, df_nb, n=20)

    n = 100
    for df, title, suffix in [
        (df_nb, "NB", "nb"),
        (ia_full, "full period", "ia_full"),
        (ia_filtered, "1994-1997", "ia_date_filtered"),
    ]:
        for plot, shape in [
            (plot_top_vs_rest_bar, "bar"),
            (plot_top_vs_rest_pie, "pie"),
        ]:
            plot(
                df,
                n,
                f"Number of messages posted by the top {n} users ({title})",
                args.out_dir / f"top_{n}_users_vs_rest_{shape}_{suffix}.png",
            )

    cumulative_dfs = [
        (ia_filtered, "IA 1994-1997"),
        (df_nb, "NB"),
    ]
    plot_cumulative_distribution(cumulative_dfs, args.out_dir / "users.png")
    print_cumulative_stats(
        [(ia_full, "Full IA"), (ia_filtered, "IA date-filtered"), (df_nb, "NB")]
    )


if __name__ == "__main__":
    main()
