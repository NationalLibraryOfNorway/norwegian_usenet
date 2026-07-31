import argparse
import json
import logging
from pathlib import Path

from usenet_no.database import connect
from usenet_no.database.conflicts import find_across_archive_conflicts

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Find message ids whose copies in the two archives never share a body",
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
            "data/output/04_compare_archives/conflicting_message_ids_across_archives.jsonl"
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
        exit(0)

    connection = connect(args.database_file)
    conflicts = find_across_archive_conflicts(connection)
    connection.close()

    with args.output_file.open("w", encoding="utf-8") as file:
        for conflict in conflicts:
            file.write(
                json.dumps(
                    {
                        "hashed_message_id": conflict.message_id_hash,
                        "num_distinct_bodies": conflict.num_distinct_bodies,
                        "newsgroups_per_archive": conflict.newsgroups_per_archive,
                    }
                )
                + "\n"
            )

    logger.info(
        "%d message ids are held by both archives without a body in common. Wrote %s",
        len(conflicts),
        args.output_file,
    )
