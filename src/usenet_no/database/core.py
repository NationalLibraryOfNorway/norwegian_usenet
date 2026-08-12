"""The SQLite database holding the messages of both Usenet archives.

It holds one row per message in `messages`, one row per (message, referenced id)
pair in `message_references` and one row per sender in `users`. Names, emails,
message ids and bodies appear only as hashes, so the file can be shared. No free
text is stored at all: subjects and the Newsgroups header carried plain text
addresses and message ids of their own (cancel messages name their target id in
the subject, mis-addressed posts put an address in the Newsgroups list), which
would have handed back the plain text the hashing is there to withhold.

Message bodies are not stored either: the content comparison needs exact
equality, not the text itself, so the database holds a hash and the full text
lives only in the mbox files. A row's message is found in them by position:
`id` minus the lowest id of its (archive, newsgroup), as `load_id_spans`
describes, which is also how a hash is traced back to its plain text.

The `archive` column distinguishes the two sources, so analyses that used to
run once per archive directory become a GROUP BY, and the date-filtered IA
subset becomes a WHERE clause instead of a copy on disk.
"""

import logging
import mailbox
import sqlite3
from collections import defaultdict
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

IA_ARCHIVE = "ia"
NB_ARCHIVE = "nb"

SCHEMA = """
-- Two senders are the same user exactly when they share the (name, email) pair
-- the hashes were made from.
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY,
    name_hash  TEXT,
    email_hash TEXT
);

-- `newsgroup` is the group whose mbox file held the message. The message's own
-- Newsgroups header is not stored, and neither is the subject; both are free
-- text that turned out to carry addresses and message ids in the clear.
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY,
    archive         TEXT NOT NULL,
    newsgroup       TEXT NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_users_email_hash ON users(email_hash);
CREATE INDEX IF NOT EXISTS idx_messages_archive_newsgroup ON messages(archive, newsgroup);
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
    message_id_hash: str | None
    from_name_hash: str | None
    from_email_hash: str | None
    date: str | None
    body_hash: str | None
    referenced_id_hashes: list[str]


def date_span_clause(
    date_span: tuple[str, str] | None, column: str = "date"
) -> tuple[str, tuple]:
    """Build the WHERE fragment restricting messages to a date span.

    Messages whose date could not be parsed (stored as NULL) are dropped, which
    matches how the date-filtered archive was built on disk. `column` names the
    date column, for use in a join where it has to be qualified.
    """
    if date_span is None:
        return "", ()
    return f" AND {column} BETWEEN ? AND ?", date_span


def load_id_spans(
    connection: sqlite3.Connection,
) -> dict[tuple[str, str], tuple[int, int]]:
    """Map each (archive, newsgroup) to its (lowest row id, message count).

    The build inserts one mbox file at a time with contiguous row ids in file
    order, so within one (archive, newsgroup) a message's position in its mbox
    file is `id - lowest row id`. Raises when a span is not contiguous, since a
    positional lookup depends on row ids following file order without gaps.
    """
    spans = {}
    for archive, newsgroup, min_id, max_id, count in connection.execute(
        "SELECT archive, newsgroup, MIN(id), MAX(id), COUNT(*)"
        " FROM messages GROUP BY archive, newsgroup"
    ):
        if max_id - min_id + 1 != count:
            raise ValueError(
                f"Row ids of ({archive}, {newsgroup}) are not contiguous:"
                f" {count} rows span ids {min_id}..{max_id}"
            )
        spans[(archive, newsgroup)] = (min_id, count)
    return spans


def load_message_positions(
    connection: sqlite3.Connection,
    archive: str,
    date_span: tuple[str, str] | None = None,
) -> dict[str, list[int]]:
    """Map each newsgroup to the mbox file positions of its messages in the span.

    A position is `id - lowest row id` for the (archive, newsgroup), as
    `load_id_spans` describes, so the bodies can be read straight out of the
    archive's own mbox files without filtering them onto disk first.
    """
    clause, span_parameters = date_span_clause(date_span)
    spans = load_id_spans(connection)
    positions: dict[str, list[int]] = defaultdict(list)
    for newsgroup, row_id in connection.execute(
        f"SELECT newsgroup, id FROM messages WHERE archive = ?{clause} ORDER BY id",
        (archive, *span_parameters),
    ):
        min_id, _count = spans[(archive, newsgroup)]
        positions[newsgroup].append(row_id - min_id)
    return dict(positions)


def connect(database_file: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_file)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    """Create the database's tables and indexes."""
    connection.executescript(SCHEMA)
    connection.commit()


def extract_message(
    message: mailbox.mboxMessage, archive: str, newsgroup: str
) -> ExtractedMessage:
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
        archive=archive,
        newsgroup=newsgroup,
        message_id_hash=make_hash(message_id) if message_id else None,
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

    Kept in memory for the whole load rather than queried per message, as
    senders repeat across millions of messages.
    """
    return {
        (name_hash, email_hash): user_id
        for user_id, name_hash, email_hash in connection.execute(
            "SELECT id, name_hash, email_hash FROM users"
        )
    }


def insert_messages(
    connection: sqlite3.Connection,
    messages: list[ExtractedMessage],
    user_ids: dict[UserKey, int],
) -> None:
    """Insert messages, their senders and their references into the database.

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
        if message.from_name_hash is None and message.from_email_hash is None:
            user_id = None
        else:
            user_key = (message.from_name_hash, message.from_email_hash)
            if user_key not in user_ids:
                next_user_id += 1
                user_ids[user_key] = next_user_id
                user_rows.append(
                    (next_user_id, message.from_name_hash, message.from_email_hash)
                )
            user_id = user_ids[user_key]

        message_rows.append(
            (
                row_id,
                message.archive,
                message.newsgroup,
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
        "INSERT INTO users (id, name_hash, email_hash) VALUES (?, ?, ?)",
        user_rows,
    )
    cursor.executemany(
        "INSERT INTO messages"
        " (id, archive, newsgroup, message_id_hash, user_id, date, body_hash)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        message_rows,
    )
    cursor.executemany(
        "INSERT INTO message_references (message_row_id, referenced_id_hash)"
        " VALUES (?, ?)",
        reference_rows,
    )
    connection.commit()
