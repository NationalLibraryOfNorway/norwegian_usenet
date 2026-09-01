import argparse
import logging
from pathlib import Path
import usenet_no

import pandas as pd

logger = logging.getLogger(__name__)


def counts_df_to_top_n_with_shares(df: pd.DataFrame, n: int) -> pd.DataFrame:
    df = df[df.newsgroup != "Total"]
    total = df.message_count.sum()

    df = df.sort_values("message_count", ascending=False).head(n)
    df["share"] = df.message_count.apply(
        lambda count: f"{round(count / total * 100, 1)}%"
    )
    n_total = df.message_count.sum()
    n_share = f"{round(n_total / total * 100, 1)}%"
    n_total_row = pd.DataFrame(
        [
            {"newsgroup": f"Top {n}", "message_count": n_total, "share": n_share},
        ]
    )

    return pd.concat([df, n_total_row], ignore_index=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count messages per Usenet group",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--nb-counts-file",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/messages_per_group_nb.csv"),
        help="Path to CSV file with NB message counts",
    )
    parser.add_argument(
        "--ia-date-filtered-counts-file",
        type=Path,
        default=Path(
            "data/output/03_statistics_per_archive/messages_per_group_ia_date_filtered.csv"
        ),
        help="Path to CSV file with IA counts restricted to the NB date span",
    )
    parser.add_argument(
        "--nb-output-file",
        type=Path,
        default=Path(
            "data/output/03_statistics_per_archive/top_25_newsgroups_shares_nb.csv"
        ),
        help="Path to CSV output file with NB message counts and shares",
    )
    parser.add_argument(
        "--ia-output-file",
        type=Path,
        default=Path(
            "data/output/03_statistics_per_archive/top_25_newsgroups_shares_ia_date_filtered.csv"
        ),
        help="Path to CSV output file with IA message counts and shares",
    )
    args = parser.parse_args()

    for in_file, out_file in (
        (args.nb_counts_file, args.nb_output_file),
        (args.ia_date_filtered_counts_file, args.ia_output_file),
    ):
        df = pd.read_csv(in_file)
        top_25_with_shares = counts_df_to_top_n_with_shares(df, 25)
        top_25_with_shares.to_csv(out_file, index=False)
        logger.info("Wrote to %s", out_file)
