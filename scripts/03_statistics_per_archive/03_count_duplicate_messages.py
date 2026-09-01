import argparse
import dataclasses
import json
import logging
from pathlib import Path

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect_archives
from usenet_no.database.duplicates import summarize_duplicates
from usenet_no.database.statistics import get_date_span

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Summarize duplicate vs unique message-IDs in each archive",
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
        "--ia-date-filtered-output-file",
        type=Path,
        default=Path(
            "data/output/03_statistics_per_archive/ia_duplicate_summary_date_filtered.json"
        ),
        help="Path to JSON output file for the IA summary, restricted to the NB date span",
    )
    parser.add_argument(
        "--nb-output-file",
        type=Path,
        default=Path("data/output/03_statistics_per_archive/nb_duplicate_summary.json"),
        help="Path to JSON output file for the NB summary",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite existing output files instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    connection = connect_archives(args.ia_database_file, args.nb_database_file)
    nb_date_span = get_date_span(connection, NB_ARCHIVE)
    logger.info("NB date span: %s to %s", *nb_date_span)

    for archive, date_span, output_file in [
        (NB_ARCHIVE, None, args.nb_output_file),
        (IA_ARCHIVE, nb_date_span, args.ia_date_filtered_output_file),
    ]:
        if output_file.exists() and not args.overwrite:
            logger.info(
                "Existing file found at %s; use --overwrite to regenerate",
                output_file,
            )
            continue

        summary = summarize_duplicates(connection, archive, date_span)

        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open("w", encoding="utf-8") as file:
            json.dump(dataclasses.asdict(summary), file, indent=2)
            file.write("\n")

        logger.info(
            "%s%s: %s. Wrote %s",
            archive,
            " (date filtered)" if date_span else "",
            summary,
            output_file,
        )

    connection.close()
