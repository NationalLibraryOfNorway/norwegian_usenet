"""Connect to the archives' databases, and the row id and date span arithmetic their queries share."""

import sqlite3
from collections import defaultdict
from pathlib import Path

IA_ARCHIVE = "ia"
NB_ARCHIVE = "nb"

# Each archive has a database of its own, so `archive` is not a column there.
# Attaching both under their archive name and reading them through these views
# puts it back, as the value that says which file a row came from.
ARCHIVE_VIEWS = f"""
CREATE TEMP VIEW messages AS
    SELECT '{IA_ARCHIVE}' AS archive, id, newsgroup, message_id_hash, email_id, date, body_hash
    FROM {IA_ARCHIVE}.messages
    UNION ALL
    SELECT '{NB_ARCHIVE}', id, newsgroup, message_id_hash, email_id, date, body_hash
    FROM {NB_ARCHIVE}.messages;

CREATE TEMP VIEW message_references AS
    SELECT '{IA_ARCHIVE}' AS archive, message_row_id, referenced_id_hash
    FROM {IA_ARCHIVE}.message_references
    UNION ALL
    SELECT '{NB_ARCHIVE}', message_row_id, referenced_id_hash
    FROM {NB_ARCHIVE}.message_references;
"""

# The user databases, attached under the archive they belong to. A hashed
# address lives only there, so a comparison between the archives' users needs
# both files, while a count within one archive gets by on `messages.email_id`.
USER_VIEW = f"""
CREATE TEMP VIEW emails AS
    SELECT '{IA_ARCHIVE}' AS archive, id, email_hash FROM {IA_ARCHIVE}_users.emails
    UNION ALL
    SELECT '{NB_ARCHIVE}', id, email_hash FROM {NB_ARCHIVE}_users.emails;
"""

# Joining the sender in, for the comparisons that identify a user by email. Ids
# are handed out per archive, so an email id only means anything together with
# the archive it was read from.
MESSAGES_WITH_SENDER = (
    "messages JOIN emails"
    " ON messages.email_id = emails.id AND messages.archive = emails.archive"
)

# The same, for the references of a message: both tables are per archive.
MESSAGES_WITH_REFERENCES = (
    "messages JOIN message_references"
    " ON message_references.message_row_id = messages.id"
    " AND message_references.archive = messages.archive"
)


def connect(database_file: Path) -> sqlite3.Connection:
    """Open one archive's database."""
    connection = sqlite3.connect(database_file)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def connect_archive_and_users(
    database_file: Path, users_database_file: Path
) -> sqlite3.Connection:
    """Open one archive's database with its user database attached as `users`.

    What the build writes to: the archive's own tables in the main schema, and
    the hashed addresses they refer to by id in the attached one.
    """
    connection = connect(database_file)
    connection.execute("ATTACH DATABASE ? AS users", (str(users_database_file),))
    return connection


def connect_archives(
    ia_database_file: Path, nb_database_file: Path
) -> sqlite3.Connection:
    """Open both archives' databases as one connection, read through the archive views.

    The two files are attached under their archive names, and `messages` and
    `message_references` are views over both, each row carrying the `archive` it
    came from. A sender is `messages.email_id`, which means nothing outside the
    archive it was read from, so comparing the two archives' users is what
    `connect_archives_and_users` is for.
    """
    connection = sqlite3.connect(":memory:")
    connection.execute(f"ATTACH DATABASE ? AS {IA_ARCHIVE}", (str(ia_database_file),))
    connection.execute(f"ATTACH DATABASE ? AS {NB_ARCHIVE}", (str(nb_database_file),))
    connection.executescript(ARCHIVE_VIEWS)
    return connection


def connect_archives_and_users(
    ia_database_file: Path,
    nb_database_file: Path,
    ia_users_database_file: Path,
    nb_users_database_file: Path,
) -> sqlite3.Connection:
    """Open both archives and both user databases as one connection.

    As `connect_archives`, with `emails` a view over the two user databases, each
    row carrying the `archive` it came from. Joining it in is what lets a user be
    matched across the archives, on the hash rather than the id.
    """
    connection = connect_archives(ia_database_file, nb_database_file)
    connection.execute(
        f"ATTACH DATABASE ? AS {IA_ARCHIVE}_users", (str(ia_users_database_file),)
    )
    connection.execute(
        f"ATTACH DATABASE ? AS {NB_ARCHIVE}_users", (str(nb_users_database_file),)
    )
    connection.executescript(USER_VIEW)
    return connection


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
