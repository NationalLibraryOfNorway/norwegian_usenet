"""Print how much the newsgroups overlap in users, and the pairs whose userbases overlap most."""

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def jaccard_of_every_pair(overlaps: pd.DataFrame, pairs: int) -> np.ndarray:
    """Take the overlap of every pair, the ones the table leaves out counted as 0."""
    return np.concatenate(
        [overlaps.jaccard.to_numpy(), np.zeros(pairs - len(overlaps))]
    )


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
    pairs = len(newsgroups) * (len(newsgroups) - 1) // 2
    jaccard = jaccard_of_every_pair(overlaps, pairs)

    print(args.overlap_file)
    print(f"{len(newsgroups):,} newsgroups, {pairs:,} pairs")
    print(f"{len(overlaps):,} pairs sharing at least one user")
    print(f"{pairs - len(overlaps):,} pairs sharing no user")
    print(
        f"Jaccard overlap over every pair: median {np.median(jaccard):.4f},"
        f" mean {jaccard.mean():.4f}, standard deviation {jaccard.std(ddof=1):.4f}"
    )

    print(f"\nThe {args.top_n} pairs with the most overlapping userbases")
    print(most_overlapping_pairs(overlaps, args.top_n).to_string(index=False))
