"""Print the message one database row was built from, as its mbox file holds it.

A row's position in its newsgroup's mbox file is its id minus the lowest id of
that newsgroup, so a row id and its archive locate the message on their own.
"""

import argparse
import logging
import sqlite3
from pathlib import Path

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect_archives
from usenet_no.database.core import load_id_spans
from usenet_no.mbox_utils import get_message_body, open_mbox

logger = logging.getLogger(__name__)


def read_newsgroup(connection: sqlite3.Connection, archive: str, row_id: int) -> str:
    """The newsgroup of one row, which names the mbox file it was read from."""
    (newsgroup,) = connection.execute(
        "SELECT newsgroup FROM messages WHERE archive = ? AND id = ?",
        (archive, row_id),
    ).fetchone()
    return newsgroup


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Print the mbox file part one database row was built from",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "archive",
        choices=(IA_ARCHIVE, NB_ARCHIVE),
        help="Archive holding the row",
    )
    parser.add_argument(
        "row_id",
        type=int,
        help="messages.id of the row to print",
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

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    logger.info("Args: %s", args)

    connection = connect_archives(args.ia_database_file, args.nb_database_file)
    newsgroup = read_newsgroup(connection, args.archive, args.row_id)
    lowest_id, count = load_id_spans(connection)[(args.archive, newsgroup)]
    connection.close()

    directory = {IA_ARCHIVE: args.ia_directory, NB_ARCHIVE: args.nb_directory}[
        args.archive
    ]
    mbox_file = directory / f"{newsgroup}.mbox"
    position = args.row_id - lowest_id

    mbox = open_mbox(mbox_file)
    logger.info("%s, message %d of %d", mbox_file, position, count)
    logger.info("---file content---")
    print(mbox.get_bytes(position).decode("utf-8"))
    # What the analysis reads the message as: every run of whitespace collapsed
    logger.info("--- text from get_message_body---")
    print(get_message_body(mbox[position]))
