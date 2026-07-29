"""Measure how much pairs of newsgroups share users.

Reads the database built in step 02 into a user x newsgroup matrix of
who posted where, then reduces it to the Jaccard overlap between the user sets
of every pair of newsgroups.

A user is one hashed email address, so a person who spelled their name two ways
counts once.

Three bodies of messages are covered: NB, IA restricted to the NB date span, and
the two together.
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect
from usenet_no.database.overlap import (
    ArchiveDatespan,
    NewsgroupOverlap,
    build_user_newsgroup_matrix,
    find_newsgroups_per_user,
    pairwise_jaccard,
)
from usenet_no.database.statistics import get_date_span

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute the user overlap between pairs of newsgroups"
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/output/02_build_database/usenet.db"),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--nb-output-file",
        type=Path,
        default=Path(
            "data/output/06_newsgroups_and_user_analysis/"
            "newsgroup_user_jaccard_overlap_nb.csv"
        ),
        help="Path to CSV output file for the NB archive",
    )
    parser.add_argument(
        "--ia-date-filtered-output-file",
        type=Path,
        default=Path(
            "data/output/06_newsgroups_and_user_analysis/"
            "newsgroup_user_jaccard_overlap_ia_date_filtered.csv"
        ),
        help="Path to CSV output file for IA restricted to the NB date span",
    )
    parser.add_argument(
        "--merged-output-file",
        type=Path,
        default=Path(
            "data/output/06_newsgroups_and_user_analysis/"
            "newsgroup_user_jaccard_overlap_nb_and_ia_date_filtered.csv"
        ),
        help="Path to CSV output file for NB and the date-filtered IA together",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing files instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    connection = connect(args.database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)

    nb: ArchiveDatespan = (NB_ARCHIVE, None)
    ia_date_filtered: ArchiveDatespan = (IA_ARCHIVE, nb_date_span)

    for name, archive_datespans, output_file in [
        ("nb", [nb], args.nb_output_file),
        (
            "ia (date filtered)",
            [ia_date_filtered],
            args.ia_date_filtered_output_file,
        ),
        (
            "nb and ia (date filtered)",
            [nb, ia_date_filtered],
            args.merged_output_file,
        ),
    ]:
        if output_file.exists() and not args.overwrite:
            logger.info(
                "Existing file found at %s; use --overwrite to regenerate",
                output_file,
            )
            continue

        newsgroups_per_user = find_newsgroups_per_user(connection, archive_datespans)
        matrix, users, newsgroups = build_user_newsgroup_matrix(newsgroups_per_user)
        overlaps = pairwise_jaccard(matrix, newsgroups)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(overlaps, columns=NewsgroupOverlap._fields).to_csv(
            output_file, index=False
        )

        logger.info(
            "%s: %d users across %d newsgroups, %d pairs sharing at least one user."
            " See overlaps in %s",
            name,
            len(users),
            len(newsgroups),
            len(overlaps),
            output_file,
        )

    connection.close()
