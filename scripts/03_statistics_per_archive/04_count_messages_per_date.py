"""Count messages per date in each archive.

Counts come from the database built in step 02, where the Date header of every
message was already parsed and normalized. Messages whose date could not be
parsed are stored with no date, and are reported here in a row labelled
"unknown", as they were when the counts were read from the mbox files.
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect
from usenet_no.database.statistics import count_messages_per_date
from usenet_no.date_parsing import UNKNOWN_DATE

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count messages per date in both archives",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/output/02_build_database/usenet.db"),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--ia-output-file",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/date_count_ia.csv"),
        help="Path to CSV output file for IA date counts",
    )
    parser.add_argument(
        "--nb-output-file",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/date_count_nb.csv"),
        help="Path to CSV output file for NB date counts",
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

    for archive, output_file in [
        (IA_ARCHIVE, args.ia_output_file),
        (NB_ARCHIVE, args.nb_output_file),
    ]:
        if output_file.exists() and not args.overwrite:
            logger.info(
                "Existing file found at %s; use --overwrite to regenerate",
                output_file,
            )
            continue

        date_counts = count_messages_per_date(connection, archive=archive)

        pd.DataFrame(
            [(date or UNKNOWN_DATE, count) for date, count in date_counts],
            columns=["date", "count"],
        ).to_csv(output_file, index=False)

        logger.info(
            "Counted %d messages across %d dates in %s. Saved date counts to %s",
            sum(count for _date, count in date_counts),
            len(date_counts),
            archive,
            output_file,
        )

    connection.close()
