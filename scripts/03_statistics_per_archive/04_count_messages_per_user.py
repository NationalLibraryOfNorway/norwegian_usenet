"""Count messages per user for IA, date-filtered IA and NB.

A user is one email address, named here by the `email_id` of the archive it was
read from, so the counts of two archives cannot be laid over each other:
user_overlap.py in step 05 is what compares the users of the two. The
date-filtered variant is a WHERE clause restricting IA to the NB date span, not a
separate copy of the archive.

Messages whose sender gave no address have no user and are not counted here; they
are reported separately, by the script counting messages without a sender.
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect_archives
from usenet_no.database.statistics import count_messages_per_user, get_date_span

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count messages per user",
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
        "--nb-output-file",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/messages_per_user_nb.csv"),
        help="Path to CSV output file for NB user counts",
    )
    parser.add_argument(
        "--ia-output-file",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/messages_per_user_ia.csv"),
        help="Path to CSV output file for IA user counts",
    )
    parser.add_argument(
        "--ia-date-filtered-output-file",
        type=Path,
        default=Path(
            "data/output/03_statistics_per_archive/messages_per_user_ia_date_filtered.csv"
        ),
        help="Path to CSV output file for IA counts restricted to the NB date span",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing files instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    connection = connect_archives(args.ia_database_file, args.nb_database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)

    for archive, date_span, output_file in [
        (NB_ARCHIVE, None, args.nb_output_file),
        (IA_ARCHIVE, None, args.ia_output_file),
        (IA_ARCHIVE, nb_date_span, args.ia_date_filtered_output_file),
    ]:
        if output_file.exists() and not args.overwrite:
            logger.info(
                "Existing file found at %s; use --overwrite to regenerate",
                output_file,
            )
            continue

        user_post_counts = count_messages_per_user(
            connection, archive=archive, date_span=date_span
        )

        pd.DataFrame(user_post_counts, columns=["email_id", "post_count"]).to_csv(
            output_file, index=False
        )

        logger.info(
            "Total unique users in %s%s: %d. See counts per user in %s",
            archive,
            " (date filtered)" if date_span else "",
            len(user_post_counts),
            output_file,
        )

    connection.close()
