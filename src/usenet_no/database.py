"""SQLite database holding the messages of both Usenet archives.

One row per message in `messages`, one row per (message, referenced id) pair in
`message_references`. The `archive` column distinguishes the two sources, so
analyses that used to run once per archive directory become a GROUP BY, and the
date-filtered IA subset becomes a WHERE clause instead of a copy on disk.

Message bodies are stored as hashes only: the content comparison needs exact
equality, not the text itself.
"""

import logging
import mailbox
import sqlite3
from dataclasses import dataclass
from email.utils import parseaddr
from pathlib import Path

from usenet_no.date_parsing import parse_and_normalize_date_field
from usenet_no.hash import make_hash
from usenet_no.mbox_utils import (
    get_from_field,
    get_message_body,
    message_factory,
    parse_message_id,
    parse_references,
)

logger = logging.getLogger(__name__)

IA_ARCHIVE = "ia"
NB_ARCHIVE = "nb"

# parse_and_normalize_date_field returns this string for unparseable dates,
# which we store as NULL instead.
UNKNOWN_DATE = "unknown"

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY,
    archive    TEXT NOT NULL,
    newsgroup  TEXT NOT NULL,
    message_id TEXT,
    from_name  TEXT,
    from_email TEXT,
    date       TEXT,
    body_hash  TEXT
);

CREATE TABLE IF NOT EXISTS message_references (
    message_row_id INTEGER NOT NULL REFERENCES messages(id),
    referenced_id  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_archive_newsgroup ON messages(archive, newsgroup);
CREATE INDEX IF NOT EXISTS idx_messages_archive_message_id ON messages(archive, message_id);
CREATE INDEX IF NOT EXISTS idx_messages_from_email ON messages(from_email);
CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date);
CREATE INDEX IF NOT EXISTS idx_messages_body_hash ON messages(body_hash);
CREATE INDEX IF NOT EXISTS idx_references_row_id ON message_references(message_row_id);
CREATE INDEX IF NOT EXISTS idx_references_referenced_id ON message_references(referenced_id);
"""


@dataclass
class ExtractedMessage:
    """The fields we keep from a single Usenet message."""

    archive: str
    newsgroup: str
    message_id: str | None
    from_name: str | None
    from_email: str | None
    date: str | None
    body_hash: str | None
    references: list[str]


def connect(database_file: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_file)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.commit()


def extract_message(
    message: mailbox.mboxMessage, archive: str, newsgroup: str
) -> ExtractedMessage:
    """Pull the stored fields out of a single message.

    Emails are lowercased so that address variants collapse to one user; names
    keep their case, where it is meaningful.
    """
    try:
        from_field = get_from_field(message)
    except Exception as e:
        logger.debug("Could not read From field: %s %s", type(e), e)
        from_field = ""

    name, email = parseaddr(from_field or "")
    date = parse_and_normalize_date_field(message.get("Date", None))
    body = get_message_body(message=message)

    return ExtractedMessage(
        archive=archive,
        newsgroup=newsgroup,
        message_id=parse_message_id(message.get("Message-ID")),
        from_name=name or None,
        from_email=email.lower() or None,
        date=None if date == UNKNOWN_DATE else date,
        body_hash=make_hash(body) if body else None,
        references=parse_references(message.get("References")),
    )


def extract_messages_from_mbox_file(
    mbox_file_and_archive: tuple[Path, str],
) -> list[ExtractedMessage]:
    """Extract every message in one mbox file. Takes a tuple so it can be mapped over a process pool."""
    mbox_file, archive = mbox_file_and_archive
    newsgroup = mbox_file.stem
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    return [
        extract_message(message=message, archive=archive, newsgroup=newsgroup)
        for message in mbox
    ]


def insert_messages(
    connection: sqlite3.Connection, messages: list[ExtractedMessage]
) -> None:
    """Insert messages and their references, assigning row ids in Python so both
    tables can be written with executemany."""
    if not messages:
        return

    cursor = connection.cursor()
    (max_id,) = cursor.execute("SELECT COALESCE(MAX(id), 0) FROM messages").fetchone()

    message_rows = []
    reference_rows = []
    for offset, message in enumerate(messages, start=1):
        row_id = max_id + offset
        message_rows.append(
            (
                row_id,
                message.archive,
                message.newsgroup,
                message.message_id,
                message.from_name,
                message.from_email,
                message.date,
                message.body_hash,
            )
        )
        reference_rows.extend(
            (row_id, referenced_id) for referenced_id in message.references
        )

    cursor.executemany(
        "INSERT INTO messages (id, archive, newsgroup, message_id, from_name, from_email, date, body_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        message_rows,
    )
    cursor.executemany(
        "INSERT INTO message_references (message_row_id, referenced_id) VALUES (?, ?)",
        reference_rows,
    )
    connection.commit()
