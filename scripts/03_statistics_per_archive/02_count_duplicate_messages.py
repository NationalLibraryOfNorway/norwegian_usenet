"""Count true duplicate messages (same Message-ID and body) within each mbox file.

Reads the mbox files directly rather than the database: this is the check that
tells us what the database is allowed to drop, so it must not depend on it.

Writes one JSON object per duplicated Message-ID, sorted by
(source_archive, newsgroup, message_id) so the output is stable across runs.
"""

import argparse
import json
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tqdm import tqdm

from usenet_no.duplicates import find_true_duplicates_in_mbox_file

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Count true duplicate messages within each mbox file of both archives"
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/internet_archive/utf_8_data"),
        help="Directory containing Internet Archive (IA) .mbox files",
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/nb/utf_8_data"),
        help="Directory containing Nasjonalbiblioteket (NB) .mbox files",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("data/duplicate_messages_per_group.jsonl"),
        help="Path to JSONL output file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will overwrite an existing output file instead of skipping",
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        default=None,
        help="If passed, will only read the first N mbox files per archive",
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

    mbox_files_with_archive = [
        (mbox_file, archive)
        for directory, archive in [
            (args.ia_directory, "ia"),
            (args.nb_directory, "nb"),
        ]
        for mbox_file in sorted(directory.glob("*.mbox"))[: args.limit]
    ]

    with ProcessPoolExecutor() as executor:
        duplicates_per_file = list(
            tqdm(
                executor.map(
                    find_true_duplicates_in_mbox_file, mbox_files_with_archive
                ),
                total=len(mbox_files_with_archive),
                desc="Counting duplicate messages",
            )
        )

    # Sorted so that reruns produce identical output
    duplicates = sorted(
        (
            duplicate
            for file_duplicates in duplicates_per_file
            for duplicate in file_duplicates
        ),
        key=lambda duplicate: (
            duplicate.source_archive,
            duplicate.newsgroup,
            duplicate.message_id,
        ),
    )

    with args.output_file.open("w", encoding="utf-8") as file:
        for row in duplicates:
            file.write(
                json.dumps(
                    {
                        "source_archive": row.source_archive,
                        "newsgroup": row.newsgroup,
                        "message_id": row.message_id,
                        "count": row.count,
                    }
                )
                + "\n"
            )

    files_with_duplicates = sum(
        1 for file_duplicates in duplicates_per_file if file_duplicates
    )
    logger.info(
        "%d duplicated message ids in %d of %d mbox files (%d messages in total). Wrote %s",
        len(duplicates),
        files_with_duplicates,
        len(duplicates_per_file),
        sum(row.count for row in duplicates),
        args.output_file,
    )
