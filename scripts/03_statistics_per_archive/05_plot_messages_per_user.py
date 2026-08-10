"""Plot message counts per user (anonymized with hashed identifiers), for full IA data and IA filtered to the NB date span."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from matplotlib.ticker import FuncFormatter


def space_thousands(value, _):
    return f"{int(value):,}".replace(",", " ")


space_fmt = FuncFormatter(space_thousands)


def load_user_counts(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df.sort_values("post_count", ascending=False)


def print_stats(df: pd.DataFrame, label: str) -> None:
    print(f"{label}")
    print(f"  Total unique users: {len(df):,}")
    print(f"  Total posts:        {df['post_count'].sum():,}")
    print(f"  Users with name:    {df['hashed_name'].notna().sum():,}")
    print(f"  Users with email:   {df['hashed_email'].notna().sum():,}")


def print_top_poster_counts(ia_dfs: list, df_nb: pd.DataFrame, n: int) -> None:
    for label, df_ia in ia_dfs:
        print(f"\nTop {n} posters — {label}")
        print(df_ia.head(n).reset_index().post_count.apply(space_fmt))
    print(f"Number of posts by top {n} posters in Norwegian Web Archive data")
    print(df_nb.head(n).reset_index().post_count.apply(space_fmt))


def plot_top_vs_rest(df: pd.DataFrame, n: int, title: str, out_path: Path) -> None:
    top_sum = df.head(n)["post_count"].sum()
    rest_sum = df.iloc[n:]["post_count"].sum()
    rest_label = f"Rest ({len(df) - n:,} users)".replace(",", " ")
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.bar([f"Top {n} users", rest_label], [top_sum, rest_sum])
    ax.yaxis.set_major_formatter(space_fmt)
    for i, v in enumerate([top_sum, rest_sum]):
        ax.text(i, v, f"{v:,}".replace(",", " "), ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("Total Posts")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path)
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
        title="Cumulative post distribution by user",
        xaxis_title="Number of top users",
        yaxis_title="Cumulative % of all posts",
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
            f"{label}: top {users_50:,} users ({users_50 / n * 100:.2f}%) account for 50% of posts"
        )
        print(
            f"{label}: top {users_80:,} users ({users_80 / n * 100:.2f}%) account for 80% of posts"
        )
        print()


def top_shared(
    shared: pd.DataFrame, total_ia: int, total_nb: int, n: int, sort_col: str
) -> pd.DataFrame:
    result = (
        shared.sort_values(sort_col, ascending=False)
        .head(n)
        .reset_index(drop=True)
        .copy()
    )
    result["pct_ia"] = (result["post_count_ia"] / total_ia * 100).map("{:.2f}%".format)
    result["pct_nb"] = (result["post_count_nb"] / total_nb * 100).map("{:.2f}%".format)
    return result[["hashed_email", "pct_ia", "pct_nb"]]


def print_shared_users(ia_dfs: list, df_nb: pd.DataFrame) -> None:
    nb_by_email = df_nb.groupby("hashed_email")["post_count"].sum().reset_index()
    total_nb = df_nb["post_count"].sum()
    n = 10

    for label, df_ia in ia_dfs:
        ia_by_email = df_ia.groupby("hashed_email")["post_count"].sum().reset_index()
        shared = ia_by_email.merge(
            nb_by_email, on="hashed_email", suffixes=("_ia", "_nb")
        )
        total_ia = df_ia["post_count"].sum()

        print(f"\n{label}")
        print(f"Users in both IA and NB (by email): {len(shared):,}")
        print(
            f"  IA-only users:  {len(ia_by_email[~ia_by_email['hashed_email'].isin(shared['hashed_email'])]):,}"
        )
        print(
            f"  NB-only users: {len(nb_by_email[~nb_by_email['hashed_email'].isin(shared['hashed_email'])]):,}"
        )
        for sort_col, sort_label in [("post_count_ia", "IA"), ("post_count_nb", "NB")]:
            print(f"Top {n} shared users by {sort_label} post count")
            print(top_shared(shared, total_ia, total_nb, n, sort_col).to_string())


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
    ia_dfs = [("Full IA", ia_full), ("IA date-filtered", ia_filtered)]

    for label, df_ia in ia_dfs:
        print_stats(df_ia, label)
        nb_pct = df_nb["post_count"].sum() / df_ia["post_count"].sum() * 100
        print(f"  NB is {nb_pct:.1f}% the size by post count")
        print()
    print_stats(df_nb, "NB")

    print_top_poster_counts(ia_dfs, df_nb, n=20)

    n = 100
    plot_top_vs_rest(
        df_nb,
        n,
        f"Posts by top {n} users vs rest (NB)",
        args.out_dir / "top_100_users_vs_rest_nb.png",
    )
    plot_top_vs_rest(
        ia_full,
        n,
        f"Posts by top {n} users vs rest (full period)",
        args.out_dir / "top_100_users_vs_rest_ia_full.png",
    )
    plot_top_vs_rest(
        ia_filtered,
        n,
        f"Posts by top {n} users vs rest (1994-1997)",
        args.out_dir / "top_100_users_vs_rest_ia_date_filtered.png",
    )

    cumulative_dfs = [
        (ia_full, "IA full period"),
        (ia_filtered, "IA 1994-1997"),
        (df_nb, "NB"),
    ]
    plot_cumulative_distribution(cumulative_dfs, args.out_dir / "users.png")
    print_cumulative_stats(
        [(ia_full, "Full IA"), (ia_filtered, "IA date-filtered"), (df_nb, "NB")]
    )

    print_shared_users(ia_dfs, df_nb)


if __name__ == "__main__":
    main()
