"""Print the newsgroup pairs sharing no users at all, and the pairs whose userbases overlap most."""

import argparse
import logging
from itertools import combinations
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def find_pairs_without_shared_users(overlaps: pd.DataFrame) -> list[tuple[str, str]]:
    """Take the newsgroup pairs missing from the overlap table, which are the pairs sharing no user."""
    newsgroups = sorted(set(overlaps.newsgroup_a) | set(overlaps.newsgroup_b))
    sharing = set(zip(overlaps.newsgroup_a, overlaps.newsgroup_b))
    return [pair for pair in combinations(newsgroups, 2) if pair not in sharing]


def most_overlapping_pairs(overlaps: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """Take the `top_n` pairs with the highest Jaccard overlap between their user sets."""
    top = overlaps.nlargest(top_n, "jaccard").copy()
    top["jaccard"] = top.jaccard.map("{:.3f}".format)
    return top[
        ["newsgroup_a", "newsgroup_b", "users_a", "users_b", "shared_users", "jaccard"]
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Print the newsgroup pairs sharing no users, and the pairs sharing most",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--overlap-file",
        type=Path,
        default=Path(
            "data/output/06_graphs_and_references/newsgroup_user_jaccard_overlap_nb.csv"
        ),
        help="Path to the user overlap CSV written by 01_newsgroup_user_jaccard_overlap.py",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="How many of the most overlapping pairs to print",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    overlaps = pd.read_csv(args.overlap_file)
    newsgroups = set(overlaps.newsgroup_a) | set(overlaps.newsgroup_b)
    pairs_without_shared_users = find_pairs_without_shared_users(overlaps)

    print(args.overlap_file)
    print(f"{len(newsgroups):,} newsgroups")
    print(f"{len(overlaps):,} pairs sharing at least one user")
    print(f"{len(pairs_without_shared_users):,} pairs sharing no user")

    print(f"\nThe {args.top_n} pairs with the most overlapping userbases")
    print(most_overlapping_pairs(overlaps, args.top_n).to_string(index=False))

    print(f"\nThe {len(pairs_without_shared_users):,} pairs sharing no user")
    for newsgroup_a, newsgroup_b in pairs_without_shared_users:
        print(f"{newsgroup_a} {newsgroup_b}")
