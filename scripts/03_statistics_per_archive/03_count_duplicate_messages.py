import argparse
import dataclasses
import json
import logging
import sqlite3
import sys
from pathlib import Path

from usenet_no.database.duplicates import summarize_nb_duplicates

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Summarize duplicate vs unique message-IDs in the NB archive",
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
        default=Path("data/output/03_statistics_per_archive/nb_duplicate_summary.json"),
        help="Path to JSON output file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite an existing output file instead of skipping",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    if args.output_file.exists() and not args.overwrite:
        logger.info(
            "Output file already exists: %s. Use --overwrite to regenerate.",
            args.output_file,
        )
        sys.exit(0)

    connection = sqlite3.connect(args.nb_database_file)
    summary = summarize_nb_duplicates(connection)
    connection.close()

    args.output_file.parent.mkdir(parents=True, exist_ok=True)
    with args.output_file.open("w", encoding="utf-8") as f:
        json.dump(dataclasses.asdict(summary), f, indent=2)
        f.write("\n")

    logger.info("Result: %s. Wrote %s", summary, args.output_file)
