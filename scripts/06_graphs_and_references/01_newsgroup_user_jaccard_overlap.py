"""Measure how much pairs of newsgroups share users.

Reads the NB database built in step 02 into a user x newsgroup matrix of
who posted where, then reduces it to the Jaccard overlap between the user sets
of every pair of newsgroups.

A user is one hashed email address, so a person who spelled their name two ways
counts once.
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from usenet_no.database import NB_ARCHIVE, connect_archive
from usenet_no.database.overlap import (
    NewsgroupOverlap,
    build_user_newsgroup_matrix,
    find_newsgroups_per_user,
    pairwise_jaccard,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute the user overlap between pairs of newsgroups",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--nb-database-file",
        type=Path,
        default=Path("data/output/02_build_database/nb.db"),
        help="Path to the SQLite database file of the NB archive",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(
            "data/output/06_graphs_and_references/newsgroup_user_jaccard_overlap_nb.csv"
        ),
        help="Path to the CSV output file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite an existing file instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    if args.output_file.exists() and not args.overwrite:
        logger.info(
            "Existing file found at %s; use --overwrite to regenerate",
            args.output_file,
        )
        raise SystemExit(0)

    connection = connect_archive(args.nb_database_file, NB_ARCHIVE)

    newsgroups_per_user = find_newsgroups_per_user(connection, [(NB_ARCHIVE, None)])
    matrix, users, newsgroups = build_user_newsgroup_matrix(newsgroups_per_user)
    overlaps = pairwise_jaccard(matrix, newsgroups)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(overlaps, columns=NewsgroupOverlap._fields).to_csv(
        args.output_file, index=False
    )

    logger.info(
        "%d users across %d newsgroups, %d pairs sharing at least one user."
        " See overlaps in %s",
        len(users),
        len(newsgroups),
        len(overlaps),
        args.output_file,
    )

    connection.close()
