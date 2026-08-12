"""Load both archives' mbox files into the SQLite database.

Names, emails and message ids are stored only as hashes. Parsing happens in
parallel, but SQLite takes one writer at a time, so the extracted messages are
inserted from the main process, one mbox file at a time.
"""

import argparse
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tqdm import tqdm

from usenet_no.database import (
    IA_ARCHIVE,
    NB_ARCHIVE,
    connect,
    create_schema,
    extract_messages_from_mbox_file,
    insert_messages,
    load_user_ids,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build the SQLite database from the mbox files of both archives",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--ia-directory",
        type=Path,
        default=Path("data/input/internet_archive/utf_8_data"),
        help="Directory containing Internet Archive (IA) .mbox files",
    )
    parser.add_argument(
        "--nb-directory",
        type=Path,
        default=Path("data/input/nb/utf_8_data"),
        help="Directory containing Nasjonalbiblioteket (NB) .mbox files",
    )
    parser.add_argument(
        "--database-file",
        type=Path,
        default=Path("data/output/02_build_database/usenet.db"),
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will delete an existing database file and rebuild it",
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        default=None,
        help="If passed, will only load the first N mbox files per archive",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    if args.database_file.exists():
        if not args.overwrite:
            logger.info(
                "Database already exists: %s. Use --overwrite to rebuild.",
                args.database_file,
            )
            exit(0)
        args.database_file.unlink()

    args.database_file.parent.mkdir(exist_ok=True, parents=True)

    mbox_files_with_archive = [
        (mbox_file, archive)
        for directory, archive in [
            (args.ia_directory, IA_ARCHIVE),
            (args.nb_directory, NB_ARCHIVE),
        ]
        for mbox_file in sorted(directory.glob("*.mbox"))[: args.limit]
    ]
    logger.info("Loading %d mbox files", len(mbox_files_with_archive))

    connection = connect(args.database_file)
    create_schema(connection)
    user_ids = load_user_ids(connection)

    total_messages = 0
    with ProcessPoolExecutor() as executor:
        for messages in tqdm(
            executor.map(extract_messages_from_mbox_file, mbox_files_with_archive),
            total=len(mbox_files_with_archive),
            desc="Loading messages into database",
        ):
            insert_messages(connection, messages, user_ids)
            total_messages += len(messages)

    connection.close()
    logger.info(
        "Loaded %d messages from %d senders into %s",
        total_messages,
        len(user_ids),
        args.database_file,
    )
