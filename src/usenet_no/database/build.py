"""Read one archive's mbox files into its database and its user database."""

import logging
import mailbox
import sqlite3
from dataclasses import dataclass
from email.utils import parseaddr
from pathlib import Path

from usenet_no.date_parsing import UNKNOWN_DATE, parse_and_normalize_date_field
from usenet_no.hash import make_hash
from usenet_no.mbox_utils import (
    get_from_field,
    get_message_body,
    message_factory,
    parse_message_id,
    parse_references,
)

logger = logging.getLogger(__name__)

SCHEMA = """
-- `newsgroup` is the group whose mbox file held the message. The message's own
-- Newsgroups header is not stored, and neither is the subject; both are free
-- text that turned out to carry addresses and message ids in the clear.
--
-- `email_id` is a row of `emails` in the archive's user database. That file is
-- not published with this one, and SQLite declares no foreign key into it, so
-- the sender is an integer here and nothing else.
CREATE TABLE messages (
    id              INTEGER PRIMARY KEY,
    newsgroup       TEXT NOT NULL,
    message_id_hash TEXT NOT NULL,
    email_id        INTEGER,
    date            TEXT,
    body_hash       TEXT
);

-- Referenced ids are stored hashed only. A reference whose message is in the
-- archives resolves through messages.message_id_hash, and one whose message is
-- missing is only ever counted, so the plain text would add nothing but a
-- second copy of 27 million identifying strings.
CREATE TABLE message_references (
    message_row_id     INTEGER NOT NULL REFERENCES messages(id),
    referenced_id_hash TEXT NOT NULL
);

CREATE INDEX idx_messages_newsgroup ON messages(newsgroup);
CREATE INDEX idx_messages_message_id_hash ON messages(message_id_hash);
CREATE INDEX idx_messages_email_id ON messages(email_id);
CREATE INDEX idx_messages_date ON messages(date);
CREATE INDEX idx_messages_body_hash ON messages(body_hash);
CREATE INDEX idx_references_row_id ON message_references(message_row_id);
CREATE INDEX idx_references_hash ON message_references(referenced_id_hash);
"""

# Written into the user database, which is attached as `users`. It holds the
# hashed addresses the archive's database refers to by id alone. Ids are handed
# out per archive, so an address has an unrelated id in the other archive's user
# database, and the two are matched on the hash rather than the id.
USERS_SCHEMA = """
-- One user is one hashed address.
CREATE TABLE users.emails (
    id         INTEGER PRIMARY KEY,
    email_hash TEXT NOT NULL
);

-- The hashed display names an address posted under, one row each.
CREATE TABLE users.email_names (
    email_id  INTEGER NOT NULL REFERENCES emails(id),
    name_hash TEXT NOT NULL
);

CREATE INDEX users.idx_emails_email_hash ON emails(email_hash);
CREATE INDEX users.idx_email_names_email_id ON email_names(email_id);
"""


@dataclass
class ExtractedMessage:
    """The fields we keep from a single Usenet message."""

    newsgroup: str
    message_id_hash: str
    from_name_hash: str | None
    from_email_hash: str | None
    date: str | None
    body_hash: str | None
    referenced_id_hashes: list[str]


def create_schema(connection: sqlite3.Connection) -> None:
    """Create the archive's tables and indexes, and those of its user database."""
    connection.executescript(SCHEMA)
    connection.executescript(USERS_SCHEMA)
    connection.commit()


def extract_message(message: mailbox.mboxMessage, newsgroup: str) -> ExtractedMessage:
    """Pull the stored fields out of a single message.

    Emails are lowercased before hashing so that address variants collapse to
    one user; names keep their case.
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
        newsgroup=newsgroup,
        message_id_hash=make_hash(message_id),
        from_name_hash=make_hash(from_name) if from_name else None,
        from_email_hash=make_hash(from_email) if from_email else None,
        date=None if date == UNKNOWN_DATE else date,
        body_hash=make_hash(body) if body else None,
        referenced_id_hashes=[
            make_hash(referenced_id)
            for referenced_id in parse_references(message.get("References"))
        ],
    )


def extract_messages_from_mbox_file(mbox_file: Path) -> list[ExtractedMessage]:
    """Extract every message in one mbox file."""
    newsgroup = mbox_file.stem
    mbox = mailbox.mbox(str(mbox_file), factory=message_factory)
    return [extract_message(message=message, newsgroup=newsgroup) for message in mbox]


def load_email_ids(connection: sqlite3.Connection) -> dict[str, int]:
    """Read the stored addresses into a lookup, so inserts can reuse their ids.

    Kept in memory for the whole load rather than queried per message, as
    senders repeat across millions of messages.
    """
    return {
        email_hash: email_id
        for email_id, email_hash in connection.execute(
            "SELECT id, email_hash FROM users.emails"
        )
    }


def load_email_names(connection: sqlite3.Connection) -> set[tuple[int, str]]:
    """The (email id, name hash) pairs already stored, so inserts do not repeat them."""
    return set(connection.execute("SELECT email_id, name_hash FROM users.email_names"))


def insert_messages(
    connection: sqlite3.Connection,
    messages: list[ExtractedMessage],
    email_ids: dict[str, int],
    email_names: set[tuple[int, str]],
) -> None:
    """Insert messages, their senders and their references into the database.

    Row ids are assigned in Python so that every table can be written with
    executemany. `email_ids` and `email_names` are read and extended in place: an
    address seen in an earlier batch keeps the id it was given then. A sender who
    gave a name but no address gets no id, and their name is not stored.
    """
    if not messages:
        return

    cursor = connection.cursor()
    (max_message_id,) = cursor.execute(
        "SELECT COALESCE(MAX(id), 0) FROM messages"
    ).fetchone()
    next_email_id = max(email_ids.values(), default=0)

    email_rows = []
    name_rows = []
    message_rows = []
    reference_rows = []

    for offset, message in enumerate(messages, start=1):
        row_id = max_message_id + offset

        if message.from_email_hash is None:
            email_id = None
        else:
            if message.from_email_hash not in email_ids:
                next_email_id += 1
                email_ids[message.from_email_hash] = next_email_id
                email_rows.append((next_email_id, message.from_email_hash))
            email_id = email_ids[message.from_email_hash]

            name = (email_id, message.from_name_hash)
            if message.from_name_hash is not None and name not in email_names:
                email_names.add(name)
                name_rows.append(name)

        message_rows.append(
            (
                row_id,
                message.newsgroup,
                message.message_id_hash,
                email_id,
                message.date,
                message.body_hash,
            )
        )
        reference_rows.extend(
            (row_id, referenced_id_hash)
            for referenced_id_hash in message.referenced_id_hashes
        )

    cursor.executemany(
        "INSERT INTO users.emails (id, email_hash) VALUES (?, ?)",
        email_rows,
    )
    cursor.executemany(
        "INSERT INTO users.email_names (email_id, name_hash) VALUES (?, ?)",
        name_rows,
    )
    cursor.executemany(
        "INSERT INTO messages"
        " (id, newsgroup, message_id_hash, email_id, date, body_hash)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        message_rows,
    )
    cursor.executemany(
        "INSERT INTO message_references (message_row_id, referenced_id_hash)"
        " VALUES (?, ?)",
        reference_rows,
    )
    connection.commit()
