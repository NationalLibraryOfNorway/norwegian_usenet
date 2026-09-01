"""Count true duplicate messages (same Message-ID and body) within each mbox file.

Reads the databases built in step 02: every copy of a message is stored as its
own row there, so the duplicates are rows sharing (archive, newsgroup,
message_id_hash, body_hash).

Writes one JSON object per duplicated Message-ID, sorted by
(archive, newsgroup, hashed_message_id) so the output is stable across runs.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from usenet_no.database import connect_archives
from usenet_no.database.duplicates import find_true_duplicates

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count true duplicate messages within each mbox file of both archives",
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
            "data/output/03_statistics_per_archive/duplicate_messages_per_group.jsonl"
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
    duplicates = find_true_duplicates(connection)
    connection.close()

    with args.output_file.open("w", encoding="utf-8") as file:
        for row in duplicates:
            file.write(
                json.dumps(
                    {
                        "archive": row.archive,
                        "newsgroup": row.newsgroup,
                        "hashed_message_id": row.message_id_hash,
                        "count": row.count,
                    }
                )
                + "\n"
            )

    newsgroups_with_duplicates = len(
        {(row.archive, row.newsgroup) for row in duplicates}
    )
    logger.info(
        "%d duplicated message ids in %d newsgroups (%d messages in total). Wrote %s",
        len(duplicates),
        newsgroups_with_duplicates,
        sum(row.count for row in duplicates),
        args.output_file,
    )
