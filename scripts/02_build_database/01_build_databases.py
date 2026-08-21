"""Load each archive's mbox files into a database of its own.

Names, emails and message ids are stored only as hashes. Parsing happens in
parallel, but SQLite takes one writer at a time, so the extracted messages are
inserted from the main process, one mbox file at a time. The two archives get
one database file each, built the same way and independently of one another.
"""

import argparse
import logging
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tqdm import tqdm

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect
from usenet_no.database.build import (
    create_schema,
    extract_messages_from_mbox_file,
    insert_messages,
    load_user_ids,
)

logger = logging.getLogger(__name__)


def build_database(
    mbox_files: list[Path], database_file: Path, executor: ProcessPoolExecutor
) -> None:
    """Read one archive's mbox files into a new database file."""
    database_file.parent.mkdir(exist_ok=True, parents=True)
    connection = connect(database_file)
    create_schema(connection)
    user_ids = load_user_ids(connection)

    total_messages = 0
    for messages in tqdm(
        executor.map(extract_messages_from_mbox_file, mbox_files),
        total=len(mbox_files),
        desc=f"Loading messages into {database_file.name}",
    ):
        insert_messages(connection, messages, user_ids)
        total_messages += len(messages)

    connection.close()
    logger.info(
        "Loaded %d messages from %d senders into %s",
        total_messages,
        len(user_ids),
        database_file,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build one SQLite database per archive from its mbox files",
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

    with ProcessPoolExecutor() as executor:
        for archive, directory, database_file in [
            (IA_ARCHIVE, args.ia_directory, args.ia_database_file),
            (NB_ARCHIVE, args.nb_directory, args.nb_database_file),
        ]:
            if database_file.exists():
                if not args.overwrite:
                    logger.info(
                        "Database already exists: %s. Use --overwrite to rebuild.",
                        database_file,
                    )
                    continue
                database_file.unlink()

            mbox_files = sorted(directory.glob("*.mbox"))[: args.limit]
            logger.info("Loading %d %s mbox files", len(mbox_files), archive)
            build_database(mbox_files, database_file, executor)
