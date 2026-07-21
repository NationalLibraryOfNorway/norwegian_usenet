"""Load both archives' mbox files into the shared and private SQLite databases.

The shared database holds names, emails and message ids only as hashes; the
private database maps those hashes back to their plain text. Both are written
in one pass. Parsing happens in parallel, but SQLite takes one writer at a
time, so the extracted messages are inserted from the main process, one mbox
file at a time.
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
    create_private_schema,
    create_schema,
    extract_messages_from_mbox_file,
    insert_messages,
    load_user_ids,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build the shared and private SQLite databases from the mbox files of both archives"
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
        "--database-file",
        type=Path,
        default=Path("data/usenet.db"),
        help="Path to the shared (hashes only) SQLite database file",
    )
    parser.add_argument(
        "--private-database-file",
        type=Path,
        default=Path("data/usenet_private.db"),
        help="Path to the private hash-to-plaintext SQLite database file",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If flagged, will delete existing database files and rebuild them",
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

    # The two databases assign ids together, so they are only ever built as a
    # pair: if either file exists, both are rebuilt or the script stops.
    existing_files = [
        file
        for file in (args.database_file, args.private_database_file)
        if file.exists()
    ]
    if existing_files:
        if not args.overwrite:
            logger.info(
                "Database already exists: %s. Use --overwrite to rebuild.",
                ", ".join(str(file) for file in existing_files),
            )
            exit(0)
        for file in existing_files:
            file.unlink()

    args.database_file.parent.mkdir(exist_ok=True, parents=True)
    args.private_database_file.parent.mkdir(exist_ok=True, parents=True)

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
    private_connection = connect(args.private_database_file)
    create_private_schema(private_connection)
    user_ids = load_user_ids(private_connection)

    total_messages = 0
    with ProcessPoolExecutor() as executor:
        for messages in tqdm(
            executor.map(extract_messages_from_mbox_file, mbox_files_with_archive),
            total=len(mbox_files_with_archive),
            desc="Loading messages into database",
        ):
            insert_messages(connection, private_connection, messages, user_ids)
            total_messages += len(messages)

    connection.close()
    private_connection.close()
    logger.info(
        "Loaded %d messages from %d senders into %s (private mapping in %s)",
        total_messages,
        len(user_ids),
        args.database_file,
        args.private_database_file,
    )
