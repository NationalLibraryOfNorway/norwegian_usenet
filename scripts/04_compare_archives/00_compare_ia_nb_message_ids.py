import argparse
import csv
import json
import logging
from pathlib import Path

from usenet_no.database.comparison import (
    compare_message_ids,
    compare_message_ids_per_group,
)
from usenet_no.database import NB_ARCHIVE, connect
from usenet_no.database.statistics import get_date_span

logger = logging.getLogger(__name__)


def export_id_comparison_to_csv(
    rows: list[tuple[str, int, int, int]], output_file: Path
) -> None:
    with output_file.open(mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["newsgroup", "ia_only", "nb_only", "both"])
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare message-id overlap between the IA and NB archives, and count references neither archive resolves"
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/output/02_build_database/usenet.db"),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--full-output-file",
        type=Path,
        default=Path("data/output/04_compare_archives/ia_nb_message_id_overlap.json"),
        help="Path to JSON output file for the full IA archive comparison",
    )
    parser.add_argument(
        "--date-filtered-output-file",
        type=Path,
        default=Path(
            "data/output/04_compare_archives/ia_nb_message_id_overlap_date_filtered.json"
        ),
        help="Path to JSON output file for the date-filtered IA archive comparison",
    )
    parser.add_argument(
        "--full-csv-output-file",
        type=Path,
        default=Path("data/output/04_compare_archives/ia_nb_message_id_comparison.csv"),
        help="Path to per-newsgroup CSV output file for the full IA archive comparison",
    )
    parser.add_argument(
        "--date-filtered-csv-output-file",
        type=Path,
        default=Path(
            "data/output/04_compare_archives/ia_nb_message_id_comparison_date_filtered.csv"
        ),
        help="Path to per-newsgroup CSV output file for the date-filtered IA archive comparison",
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

    for ia_date_span, output_file, csv_output_file in [
        (None, args.full_output_file, args.full_csv_output_file),
        (
            nb_date_span,
            args.date_filtered_output_file,
            args.date_filtered_csv_output_file,
        ),
    ]:
        if output_file.exists() and not args.overwrite:
            logger.info(
                "Existing file found at %s; use --overwrite to regenerate", output_file
            )
        else:
            results = compare_message_ids(connection, ia_date_span=ia_date_span)

            logger.info(
                "=== ia%s vs nb ===", " (date filtered)" if ia_date_span else ""
            )
            for key, value in results.items():
                logger.info("%-35s %d", key, value)

            output_file.write_text(json.dumps(results, indent=2))
            logger.info("Wrote results to %s", output_file)

        if csv_output_file.exists() and not args.overwrite:
            logger.info(
                "Existing file found at %s; use --overwrite to regenerate",
                csv_output_file,
            )
        else:
            rows = compare_message_ids_per_group(connection, ia_date_span=ia_date_span)
            export_id_comparison_to_csv(rows, csv_output_file)
            logger.info("Wrote %d rows to %s", len(rows), csv_output_file)

    connection.close()
