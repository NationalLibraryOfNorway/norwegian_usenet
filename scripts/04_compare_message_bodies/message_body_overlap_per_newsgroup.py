import argparse
import csv
import logging
from pathlib import Path

from usenet_no.database import NB_ARCHIVE, connect
from usenet_no.database.comparison import compare_content_per_group
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
        description="Compare message bodies per newsgroup, between NB and the IA "
        "archive restricted to the NB date span",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/output/02_build_database/usenet.db"),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path(
            "data/output/04_compare_message_bodies/ia_nb_content_comparison_date_filtered.csv"
        ),
        help="Path to CSV output file",
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

    if args.output_file.exists() and not args.overwrite:
        logger.info(
            "Output file already exists: %s. Use --overwrite to regenerate.",
            args.output_file,
        )
    else:
        rows = compare_content_per_group(connection, ia_date_span=nb_date_span)
        export_content_comparison_to_csv(rows, args.output_file)
        logger.info("Wrote %d rows to %s", len(rows), args.output_file)

    connection.close()
