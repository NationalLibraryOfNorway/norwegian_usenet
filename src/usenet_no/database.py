"""SQLite database holding the messages of both Usenet archives.

One row per message in `messages`, one row per (message, referenced id) pair in
`message_references`. The `archive` column distinguishes the two sources, so
analyses that used to run once per archive directory become a GROUP BY, and the
date-filtered IA subset becomes a WHERE clause instead of a copy on disk.

Message bodies are stored as hashes only: the content comparison needs exact
equality, not the text itself. Sender names and emails are stored both in plain
text and hashed, so that published statistics can report the hash while local
analysis can still use the address. The database itself is not shared.
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
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY,
    name       TEXT,
    email      TEXT,
    name_hash  TEXT,
    email_hash TEXT,
    UNIQUE(name, email)
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY,
    archive         TEXT NOT NULL,
    newsgroup       TEXT NOT NULL,
    message_id      TEXT,
    message_id_hash TEXT,
    user_id         INTEGER REFERENCES users(id),
    date            TEXT,
    body_hash       TEXT
);

-- Referenced ids are stored hashed only. A reference whose message is in the
-- archives resolves through messages.message_id_hash, and one whose message is
-- missing is only ever counted, so the plain text would add nothing but a
-- second copy of 27 million identifying strings.
CREATE TABLE IF NOT EXISTS message_references (
    message_row_id     INTEGER NOT NULL REFERENCES messages(id),
    referenced_id_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_messages_archive_newsgroup ON messages(archive, newsgroup);
CREATE INDEX IF NOT EXISTS idx_messages_archive_message_id ON messages(archive, message_id);
CREATE INDEX IF NOT EXISTS idx_messages_message_id_hash ON messages(message_id_hash);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date);
CREATE INDEX IF NOT EXISTS idx_messages_body_hash ON messages(body_hash);
CREATE INDEX IF NOT EXISTS idx_references_row_id ON message_references(message_row_id);
CREATE INDEX IF NOT EXISTS idx_references_hash ON message_references(referenced_id_hash);
"""


@dataclass
class ExtractedMessage:
    """The fields we keep from a single Usenet message."""

    archive: str
    newsgroup: str
    message_id: str | None
    message_id_hash: str | None
    from_name: str | None
    from_email: str | None
    from_name_hash: str | None
    from_email_hash: str | None
    date: str | None
    body_hash: str | None
    referenced_id_hashes: list[str]


def date_span_clause(
    date_span: tuple[str, str] | None, column: str = "date"
) -> tuple[str, tuple]:
    """Build the WHERE fragment restricting messages to a date span.

    Messages whose date could not be parsed are kept: a message is only dropped
    when it is known to fall outside the span. This matches how the
    date-filtered archive was built on disk.

    `column` names the date column, so the fragment can be used in a join where
    it has to be qualified.
    """
    if date_span is None:
        return "", ()
    return f" AND ({column} IS NULL OR {column} BETWEEN ? AND ?)", date_span


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

    Names and emails are stored both in plain text and hashed. The hashes are
    what published statistics report, so that no output file carries a real
    address; the plain text stays here because the database is local, and
    questions like which domains people posted from need the address itself.
    """
    try:
        from_field = get_from_field(message)
    except Exception as e:
        logger.debug("Could not read From field: %s %s", type(e), e)
        from_field = ""

    name, email = parseaddr(from_field or "")
    from_name = name or None
    from_email = email.lower() or None
    message_id = parse_message_id(message.get("Message-ID"))
    date = parse_and_normalize_date_field(message.get("Date", None))
    body = get_message_body(message=message)

    return ExtractedMessage(
        archive=archive,
        newsgroup=newsgroup,
        message_id=message_id,
        message_id_hash=make_hash(message_id) if message_id else None,
        from_name=from_name,
        from_email=from_email,
        from_name_hash=make_hash(from_name) if from_name else None,
        from_email_hash=make_hash(from_email) if from_email else None,
        date=None if date == UNKNOWN_DATE else date,
        body_hash=make_hash(body) if body else None,
        referenced_id_hashes=[
            make_hash(referenced_id)
            for referenced_id in parse_references(message.get("References"))
        ],
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


UserKey = tuple[str | None, str | None]


def load_user_ids(connection: sqlite3.Connection) -> dict[UserKey, int]:
    """Read the existing users into a lookup, so inserts can reuse their ids.

    Senders repeat across millions of messages, so the lookup is kept in memory
    for the whole load rather than queried per message.
    """
    return {
        (name, email): user_id
        for user_id, name, email in connection.execute(
            "SELECT id, name, email FROM users"
        )
    }


def insert_messages(
    connection: sqlite3.Connection,
    messages: list[ExtractedMessage],
    user_ids: dict[UserKey, int],
) -> None:
    """Insert messages, their senders and their references.

    Row ids are assigned in Python so that every table can be written with
    executemany. `user_ids` is read and extended in place: a sender seen in an
    earlier batch keeps the id it was given then.
    """
    if not messages:
        return

    cursor = connection.cursor()
    (max_message_id,) = cursor.execute(
        "SELECT COALESCE(MAX(id), 0) FROM messages"
    ).fetchone()
    next_user_id = max(user_ids.values(), default=0)

    user_rows = []
    message_rows = []
    reference_rows = []

    for offset, message in enumerate(messages, start=1):
        row_id = max_message_id + offset

        # Messages with no sender at all get no user, rather than a blank one
        if message.from_name is None and message.from_email is None:
            user_id = None
        else:
            user_key = (message.from_name, message.from_email)
            if user_key not in user_ids:
                next_user_id += 1
                user_ids[user_key] = next_user_id
                user_rows.append(
                    (
                        next_user_id,
                        message.from_name,
                        message.from_email,
                        message.from_name_hash,
                        message.from_email_hash,
                    )
                )
            user_id = user_ids[user_key]

        message_rows.append(
            (
                row_id,
                message.archive,
                message.newsgroup,
                message.message_id,
                message.message_id_hash,
                user_id,
                message.date,
                message.body_hash,
            )
        )
        reference_rows.extend(
            (row_id, referenced_id_hash)
            for referenced_id_hash in message.referenced_id_hashes
        )

    cursor.executemany(
        "INSERT INTO users (id, name, email, name_hash, email_hash)"
        " VALUES (?, ?, ?, ?, ?)",
        user_rows,
    )
    cursor.executemany(
        "INSERT INTO messages"
        " (id, archive, newsgroup, message_id, message_id_hash, user_id, date, body_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        message_rows,
    )
    cursor.executemany(
        "INSERT INTO message_references (message_row_id, referenced_id_hash)"
        " VALUES (?, ?)",
        reference_rows,
    )
    connection.commit()
