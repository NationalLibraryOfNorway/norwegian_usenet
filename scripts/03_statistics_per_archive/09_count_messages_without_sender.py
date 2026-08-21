"""Count messages with no sender, per archive and newsgroup.
A message has no sender when no name or email could be read from its From
header.

Writes one JSON object per newsgroup that has at least one such message, sorted
by (archive, newsgroup) so the output is stable across runs.
"""

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from usenet_no.database import connect_archives
from usenet_no.database.statistics import count_messages_without_sender

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count messages with no From: header, per archive and newsgroup",
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
            "data/output/03_statistics_per_archive/messages_without_sender.jsonl"
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
    rows = count_messages_without_sender(connection)
    connection.close()

    with args.output_file.open("w", encoding="utf-8") as file:
        for archive, newsgroup, count in rows:
            file.write(
                json.dumps({"archive": archive, "newsgroup": newsgroup, "count": count})
                + "\n"
            )

    per_archive = Counter()
    for archive, _newsgroup, count in rows:
        per_archive[archive] += count

    for archive, count in sorted(per_archive.items()):
        logger.info("%s: %d messages with no sender", archive, count)
    logger.info("%d newsgroups affected. Wrote %s", len(rows), args.output_file)
