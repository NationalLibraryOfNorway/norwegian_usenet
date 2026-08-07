"""Write the top newsgroups by combined unique message count, as candidates for the embedding selection."""

import argparse
from pathlib import Path

import pandas as pd


def write_newsgroups_for_selection(filtered: pd.DataFrame, out_path: Path) -> None:
    sum_i = (filtered.nb_only + filtered.ia_only).sort_values(ascending=False).index
    sortby_sum = filtered.loc[sum_i]
    sortby_sum = sortby_sum[(sortby_sum.nb_only > 1) & (sortby_sum.ia_only > 1)]
    top_50_sum = sortby_sum.head(50)
    top_50_sum.to_json(out_path, index=False, lines=True, orient="records")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write the top newsgroups by combined unique message count",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--content-date-filtered-csv",
        type=Path,
        default=Path(
            "data/output/04_compare_message_bodies/ia_nb_content_comparison.csv"
        ),
        help="CSV with date filtered content overlap per newsgroup (default: %(default)s)",
    )
    parser.add_argument(
        "--out-file",
        type=Path,
        default=Path("data/output/07_make_embeddings/newsgroups_for_selection.jsonl"),
        help="Output .jsonl file (default: %(default)s)",
    )
    args = parser.parse_args()
    args.out_file.parent.mkdir(parents=True, exist_ok=True)

    filtered = pd.read_csv(args.content_date_filtered_csv)
    write_newsgroups_for_selection(filtered, args.out_file)


if __name__ == "__main__":
    main()
