"""Plot exact-body-match message overlap between IA and NB."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from usenet_no.plot_utils import venn2_fmt


def load_content(path: Path) -> pd.DataFrame:
    return pd.read_csv(path).sort_values("both", ascending=False)


def print_overlap_stats(dfs: list) -> None:
    for label, df in dfs:
        print(f"\n{label}")
        print(df.head(20).to_string())
    for label, df in dfs:
        print(f"{label}:")
        print(f"  IA only:  {df['ia_only'].sum():,}")
        print(f"  NB only: {df['nb_only'].sum():,}")
        print(f"  Both:     {df['both'].sum():,}")
        print()


def plot_overlap_venn(filtered: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    venn2_fmt(
        subsets=(
            filtered["nb_only"].sum(),
            filtered["ia_only"].sum(),
            filtered["both"].sum(),
        ),
        set_labels=("NB", "IA"),
        ax=ax,
        show_pct=True,
    )
    ax.set_title("Message overlap (1994-1997)")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot exact-body-match message overlap between IA and NB"
    )
    parser.add_argument(
        "--content-csv",
        type=Path,
        default=Path("data/output/04_compare_archives/ia_nb_content_comparison.csv"),
        help="CSV with content overlap per newsgroup (default: %(default)s)",
    )
    parser.add_argument(
        "--content-date-filtered-csv",
        type=Path,
        default=Path(
            "data/output/04_compare_archives/ia_nb_content_comparison_date_filtered.csv"
        ),
        help="CSV with date filtered content overlap per newsgroup (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/output/07_visualize/plot_ia_nb_content_comparison"),
        help="Directory for output files (default: %(default)s)",
    )
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    full = load_content(args.content_csv)
    filtered = load_content(args.content_date_filtered_csv)

    print_overlap_stats([("Full IA", full), ("IA date-filtered", filtered)])
    plot_overlap_venn(filtered, args.out_dir / "content_overlap_venn.png")


if __name__ == "__main__":
    main()
