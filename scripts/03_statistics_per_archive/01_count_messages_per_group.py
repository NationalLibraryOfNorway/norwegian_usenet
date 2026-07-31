"""Count messages per newsgroup for IA, date-filtered IA and NB.

Counts come from the database built in step 02, so all three outputs are
produced from one pass over one dataset. The date-filtered variant is a WHERE
clause restricting IA to the NB date span, not a separate copy of the archive.
"""

import argparse
import csv
import logging
from pathlib import Path

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect
from usenet_no.database.statistics import count_messages_per_group, get_date_span

logger = logging.getLogger(__name__)


def export_newsgroup_message_counts_to_csv(
    newsgroup_message_counts: dict[str, int], output_file: Path
):
    """Write counts per newsgroup, with a total row at the end.

    Newsgroups are named by their mbox filename, as they were when the counts
    were read from the archive directories.
    """
    total_messages = sum(newsgroup_message_counts.values())
    with output_file.open(mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["newsgroup", "message_count"])

        for newsgroup, count in newsgroup_message_counts.items():
            writer.writerow([f"{newsgroup}.mbox", count])

        writer.writerow(["Total", total_messages])
    logger.info("Exported results to %s", output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count messages per Usenet group",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        default=Path("data/output/03_statistics_per_archive/messages_per_group_nb.csv"),
        help="Path to CSV output file for NB message counts",
    )
    parser.add_argument(
        "--ia-output-file",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/messages_per_group_ia.csv"),
        help="Path to CSV output file for IA message counts",
    )
    parser.add_argument(
        "--ia-date-filtered-output-file",
        type=Path,
        default=Path(
            "data/output/03_statistics_per_archive/messages_per_group_ia_date_filtered.csv"
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

    connection = connect(args.database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)

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

        newsgroup_message_counts = count_messages_per_group(
            connection, archive=archive, date_span=date_span
        )
        logger.info(
            "%s%s: %d messages across %d newsgroups",
            archive,
            " (date filtered)" if date_span else "",
            sum(newsgroup_message_counts.values()),
            len(newsgroup_message_counts),
        )
        export_newsgroup_message_counts_to_csv(newsgroup_message_counts, output_file)

    connection.close()
