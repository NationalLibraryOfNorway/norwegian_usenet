import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from usenet_no.database import connect_archives
from usenet_no.database.conflicts import find_within_archive_conflicts

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find message ids carrying several distinct message bodies within one archive",
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
        "--output-file",
        type=Path,
        default=Path(
            "data/output/03_statistics_per_archive/conflicting_message_ids_within_archive.jsonl"
        ),
        help="Path to JSONL output file",
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

    connection = connect_archives(args.ia_database_file, args.nb_database_file)
    conflicts = find_within_archive_conflicts(connection)
    connection.close()

    with args.output_file.open("w", encoding="utf-8") as file:
        for conflict in conflicts:
            file.write(
                json.dumps(
                    {
                        "archive": conflict.archive,
                        "hashed_message_id": conflict.message_id_hash,
                        "num_distinct_bodies": conflict.num_distinct_bodies,
                        "newsgroups": conflict.newsgroups,
                    }
                )
                + "\n"
            )

    conflicts_per_archive = Counter(conflict.archive for conflict in conflicts)
    for archive, count in sorted(conflicts_per_archive.items()):
        logger.info("%s: %d conflicting message ids", archive, count)
    logger.info("Wrote %d conflicts to %s", len(conflicts), args.output_file)
