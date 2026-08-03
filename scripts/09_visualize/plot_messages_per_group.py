"""Plot message counts per newsgroup, for full IA data and IA filtered to the NB date span."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from usenet_no.plot_utils import venn2_fmt


def load_group_counts(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[df.newsgroup != "Total"]
    df["newsgroup"] = df["newsgroup"].str.replace(".mbox", "", regex=False)
    return df.sort_values("message_count", ascending=False)


def print_group_stats(ia_dfs: list, df_nb: pd.DataFrame) -> None:
    for label, df_ia in ia_dfs:
        shared = set(df_ia["newsgroup"]) & set(df_nb["newsgroup"])
        print(
            f"{label} — groups: {len(df_ia)}, total messages: {df_ia['message_count'].sum():,}"
        )
        print(f"  Groups in both: {len(shared)}")
        print(f"  IA only:        {len(set(df_ia['newsgroup']) - shared)}")
        print(f"  NB only:       {len(set(df_nb['newsgroup']) - shared)}")
        print()
    print(
        f"NB — groups: {len(df_nb)}, total messages: {df_nb['message_count'].sum():,}"
    )


def plot_overlap_venn(
    ia_filtered: pd.DataFrame,
    ia_full: pd.DataFrame,
    df_nb: pd.DataFrame,
    out_path: Path,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    for ax, (label, df_ia) in zip(
        axes, [("1994-1997", ia_filtered), ("full period", ia_full)]
    ):
        venn2_fmt(
            [set(df_nb["newsgroup"]), set(df_ia["newsgroup"])],
            set_labels=("NB", "IA"),
            ax=ax,
            show_pct=False,
        )
        ax.set_title(f"Newsgroup overlap ({label})")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def print_top_groups(
    ia_dfs: list, df_nb: pd.DataFrame, sort_col: str, sort_label: str
) -> None:
    for label, df_ia in ia_dfs:
        merged = df_ia.merge(df_nb, on="newsgroup", suffixes=("_ia", "_nb"))
        merged["pct_ia"] = (
            merged["message_count_ia"] / df_ia["message_count"].sum() * 100
        )
        merged["pct_nb"] = (
            merged["message_count_nb"] / df_nb["message_count"].sum() * 100
        )
        result = (
            merged[["newsgroup", "pct_ia", "pct_nb"]]
            .sort_values(sort_col, ascending=False)
            .reset_index(drop=True)
        )
        result["pct_ia"] = result["pct_ia"].map("{:.2f}%".format)
        result["pct_nb"] = result["pct_nb"].map("{:.2f}%".format)
        print(f"\nTop 20 newsgroups by {sort_label} share — {label}")
        print(result.head(20).to_string())


def plot_top_vs_rest(df: pd.DataFrame, title: str, out_path: Path) -> None:
    top_20_sum = df.head(20)["message_count"].sum()
    rest_sum = df.iloc[20:]["message_count"].sum()
    rest_label = f"Rest ({len(df) - 20})"
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.bar(["Top 20", rest_label], [top_20_sum, rest_sum])
    for i, v in enumerate([top_20_sum, rest_sum]):
        ax.text(i, v, f"{v:,}".replace(",", " "), ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("Total Messages")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_distribution(df: pd.DataFrame, title: str, out_path: Path) -> None:
    bin_size = 5000
    max_count = int(np.ceil(df["message_count"].max() / bin_size) * bin_size)
    bins = np.arange(0, max_count + bin_size, bin_size)
    counts, bin_edges = np.histogram(df["message_count"], bins=bins)
    non_empty = np.where(counts > 0)[0]
    labels = [
        f"{int(bin_edges[i]):,}–{int(bin_edges[i + 1]):,}".replace(",", " ")
        for i in non_empty
    ]
    counts = counts[non_empty]
    gap_width = 0.9
    x_positions = [0.0]
    for i in range(1, len(non_empty)):
        step = 1.0
        if non_empty[i] - non_empty[i - 1] > 1:
            step += gap_width
        x_positions.append(x_positions[-1] + step)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(x_positions, counts, width=0.8)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    for x, c in zip(x_positions, counts):
        ax.text(x, c, str(c), ha="center", va="bottom", fontsize=8)
    ax.set_xlabel("Message Count Range")
    ax.set_ylabel("Number of Newsgroups")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot message counts per newsgroup for the IA and NB archives",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--ia-csv",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/messages_per_group_ia.csv"),
        help="CSV with IA message counts per newsgroup (default: %(default)s)",
    )
    parser.add_argument(
        "--ia-date-filtered-csv",
        type=Path,
        default=Path(
            "data/output/03_statistics_per_archive/messages_per_group_ia_date_filtered.csv"
        ),
        help="CSV with date filtered IA message counts per newsgroup (default: %(default)s)",
    )
    parser.add_argument(
        "--nb-csv",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/messages_per_group_nb.csv"),
        help="CSV with NB message counts per newsgroup (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/output/09_visualize/plot_messages_per_group"),
        help="Directory for output .png files (default: %(default)s)",
    )
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    ia_full = load_group_counts(args.ia_csv)
    ia_filtered = load_group_counts(args.ia_date_filtered_csv)
    df_nb = load_group_counts(args.nb_csv)
    ia_dfs = [("Full IA", ia_full), ("IA date-filtered", ia_filtered)]

    print_group_stats(ia_dfs, df_nb)
    plot_overlap_venn(
        ia_filtered, ia_full, df_nb, args.out_dir / "newsgroup_overlap_venn.png"
    )
    print_top_groups(ia_dfs, df_nb, "pct_ia", "IA")
    print_top_groups(ia_dfs, df_nb, "pct_nb", "NB")

    plot_top_vs_rest(
        ia_full,
        "Messages in Top 20 Groups vs Rest (IA full period)",
        args.out_dir / "top_20_groups_vs_rest_ia_full.png",
    )
    plot_top_vs_rest(
        ia_filtered,
        "Messages in Top 20 Groups vs Rest (IA 1994-1997)",
        args.out_dir / "top_20_groups_vs_rest_ia_date_filtered.png",
    )
    plot_top_vs_rest(
        df_nb,
        "Messages in Top 20 Groups vs Rest (NB)",
        args.out_dir / "top_20_groups_vs_rest_nb.png",
    )

    plot_distribution(
        ia_full,
        "Number of newsgroups by message count (full period) (intervals of 5,000)",
        args.out_dir / "newsgroups_by_message_count_ia_full.png",
    )
    plot_distribution(
        ia_filtered,
        "Number of newsgroups by message count (1994-1997) (intervals of 5,000)",
        args.out_dir / "newsgroups_by_message_count_ia_date_filtered.png",
    )
    plot_distribution(
        df_nb,
        "Number of newsgroups by message count (source: NB) (intervals of 5,000)",
        args.out_dir / "newsgroups_by_message_count_nb.png",
    )


if __name__ == "__main__":
    main()
