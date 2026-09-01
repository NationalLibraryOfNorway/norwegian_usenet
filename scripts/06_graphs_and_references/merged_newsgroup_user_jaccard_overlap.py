"""Measure how much pairs of newsgroups share users, over both archives at once.

As 01_newsgroup_user_jaccard_overlap.py, but reading NB and the date filtered IA
as one body of messages, so that a newsgroup pair is weighed by everyone who
posted in it whichever archive kept the message.

Needs both user databases: the email ids of the two archives are unrelated, so
the hashed address is the only thing that says a user of one is a user of the
other. Nothing read from them is written out; the output holds newsgroup names
and counts.
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect_archives_and_users
from usenet_no.database.overlap import (
    ArchiveDatespan,
    NewsgroupOverlap,
    build_user_newsgroup_matrix,
    find_newsgroups_per_user_across_archives,
    pairwise_jaccard,
)
from usenet_no.database.statistics import get_date_span

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compute the user overlap between pairs of newsgroups over both archives",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--ia-database-file",
        type=Path,
        default=Path("data/output/02_build_database/ia.db"),
        help="Path to the SQLite database file of the IA archive",
    )
    parser.add_argument(
        "--nb-database-file",
        type=Path,
        default=Path("data/output/02_build_database/nb.db"),
        help="Path to the SQLite database file of the NB archive",
    )
    parser.add_argument(
        "--ia-users-database-file",
        type=Path,
        default=Path("data/output/02_build_database/ia_users.db"),
        help="Path to the SQLite user database of the IA archive",
    )
    parser.add_argument(
        "--nb-users-database-file",
        type=Path,
        default=Path("data/output/02_build_database/nb_users.db"),
        help="Path to the SQLite user database of the NB archive",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(
            "data/output/06_graphs_and_references/"
            "newsgroup_user_jaccard_overlap_nb_and_ia.csv"
        ),
        help="Path to CSV output file for NB and the date-filtered IA together",
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
            "Existing file found at %s; use --overwrite to regenerate", args.output_file
        )
        raise SystemExit

    connection = connect_archives_and_users(
        args.ia_database_file,
        args.nb_database_file,
        args.ia_users_database_file,
        args.nb_users_database_file,
    )
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)

    nb: ArchiveDatespan = (NB_ARCHIVE, None)
    ia_date_filtered: ArchiveDatespan = (IA_ARCHIVE, nb_date_span)

    newsgroups_per_user = find_newsgroups_per_user_across_archives(
        connection, [nb, ia_date_filtered]
    )
    matrix, users, newsgroups = build_user_newsgroup_matrix(newsgroups_per_user)
    overlaps = pairwise_jaccard(matrix, newsgroups)

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(overlaps, columns=NewsgroupOverlap._fields).to_csv(
        args.output_file, index=False
    )

    logger.info(
        "nb and ia (date filtered): %d users across %d newsgroups,"
        " %d pairs sharing at least one user. See overlaps in %s",
        len(users),
        len(newsgroups),
        len(overlaps),
        args.output_file,
    )

    connection.close()
