"""Plot message counts over time for the IA and NB archives."""

import argparse
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter


def space_thousands(value, _):
    return f"{value:,.0f}".replace(",", " ")


def load_date_counts(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    num_unknown = df[df.date == "unknown"]["count"].item()
    print(f"Number of messages with unknown date in {path}: {num_unknown}")
    df = df[df["date"] != "unknown"]
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")


def plot_per_day(df_ia: pd.DataFrame, df_nb: pd.DataFrame, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(df_ia["date"], df_ia["count"], label="Internet Archive", color="steelblue")
    ax.plot(df_nb["date"], df_nb["count"], label="NB", color="darkorange")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlabel("Date")
    ax.set_ylabel("Message Count")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_per_month(df: pd.DataFrame, name: str, out_path: Path) -> None:
    df["month"] = df["date"].dt.to_period("M")
    monthly = df.groupby("month")["count"].sum().reset_index()
    monthly["month"] = monthly["month"].dt.to_timestamp()

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(monthly["month"], monthly["count"], width=20)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.yaxis.set_major_formatter(FuncFormatter(space_thousands))
    ax.set_xlabel("Year")
    ax.set_ylabel("Message Count")
    ax.set_title(f"Messages per Month ({name})")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_per_year(df: pd.DataFrame, name: str, out_path: Path) -> None:
    df["year"] = df["date"].dt.year
    yearly = df.groupby("year")["count"].sum().reset_index()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(yearly["year"], yearly["count"])
    ax.set_xticks(yearly["year"])
    ax.set_xticklabels(yearly["year"], rotation=45)
    ax.yaxis.set_major_formatter(FuncFormatter(space_thousands))
    ax.set_xlabel("Year")
    ax.set_ylabel("Message Count")
    ax.set_title(f"Messages per Year ({name})")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plot message counts over time for the IA and NB archives"
    )
    parser.add_argument(
        "--ia-csv",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/date_count_ia.csv"),
        help="CSV with IA message counts per date (default: %(default)s)",
    )
    parser.add_argument(
        "--nb-csv",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/date_count_nb.csv"),
        help="CSV with NB message counts per date (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("data/output/07_visualize/plot_date_counts"),
        help="Directory for output .png files (default: %(default)s)",
    )
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    df_ia = load_date_counts(args.ia_csv)
    df_nb = load_date_counts(args.nb_csv)

    plot_per_day(df_ia, df_nb, args.out_dir / "date_count_daily.png")
    plot_per_month(
        df_ia, "Internet Archive data", args.out_dir / "messages_per_month_ia.png"
    )
    plot_per_month(
        df_nb, "Norwegian Web Archive data", args.out_dir / "messages_per_month_nb.png"
    )
    plot_per_year(
        df_ia, "Internet Archive data", args.out_dir / "messages_per_year_ia.png"
    )
    plot_per_year(
        df_nb, "Norwegian Web Archive data", args.out_dir / "messages_per_year_nb.png"
    )


if __name__ == "__main__":
    main()
