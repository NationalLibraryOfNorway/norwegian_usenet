"""Compare message content per newsgroup between the IA and NB archives.

Counts come from the database built in step 02, comparing bodies through the
hashes it stores. The date-filtered variant restricts IA to the NB date span
with a WHERE clause, instead of a separate copy of the archive on disk.
"""

import argparse
import csv
import logging
from pathlib import Path

from usenet_no.database.comparison import compare_content_per_group
from usenet_no.database import NB_ARCHIVE, connect
from usenet_no.database.statistics import get_date_span

logger = logging.getLogger(__name__)


def export_content_comparison_to_csv(
    rows: list[tuple[str, int, int, int]], output_file: Path
) -> None:
    with output_file.open(mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["newsgroup", "ia_only", "nb_only", "both"])
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare message content between the IA and NB archives"
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/usenet.db"),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--full-output-file",
        type=Path,
        default=Path("data/ia_nb_content_comparison.csv"),
        help="Path to CSV output file for the full IA archive comparison",
    )
    parser.add_argument(
        "--date-filtered-output-file",
        type=Path,
        default=Path("data/ia_nb_content_comparison_date_filtered.csv"),
        help="Path to CSV output file for the date-filtered IA archive comparison",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing output files instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    connection = connect(args.database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)

    for ia_date_span, output_file in [
        (None, args.full_output_file),
        (nb_date_span, args.date_filtered_output_file),
    ]:
        if output_file.exists() and not args.overwrite:
            logger.info(
                "Output file already exists: %s. Use --overwrite to regenerate.",
                output_file,
            )
            continue

        rows = compare_content_per_group(connection, ia_date_span=ia_date_span)
        export_content_comparison_to_csv(rows, output_file)
        logger.info("Wrote %d rows to %s", len(rows), output_file)

    connection.close()
