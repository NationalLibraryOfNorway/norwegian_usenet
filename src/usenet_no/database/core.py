"""Connect to the archives' databases, and the row id and date span arithmetic their queries share."""

import sqlite3
from collections import defaultdict
from pathlib import Path

IA_ARCHIVE = "ia"
NB_ARCHIVE = "nb"

# Each archive has a database of its own, so `archive` is not a column there.
# Attaching them under their archive name and reading them through a view per
# table puts it back, as the value that says which file a row came from.
ARCHIVE_TABLE_COLUMNS = {
    "messages": "id, newsgroup, message_id_hash, user_id, date, body_hash",
    "users": "id, name_hash, email_hash",
    "message_references": "message_row_id, referenced_id_hash",
}

# Joining the sender in, for the counts that identify a user by email. Row ids
# are handed out per archive, so a user id only means anything together with the
# archive it was read from.
MESSAGES_WITH_SENDER = (
    "messages JOIN users"
    " ON messages.user_id = users.id AND messages.archive = users.archive"
)

# The same, for the references of a message: both tables are per archive.
MESSAGES_WITH_REFERENCES = (
    "messages JOIN message_references"
    " ON message_references.message_row_id = messages.id"
    " AND message_references.archive = messages.archive"
)


def _archive_views(archives: list[str]) -> str:
    """The temp views reading the attached archives as one table apiece."""
    return "".join(
        f"CREATE TEMP VIEW {table} AS "
        + " UNION ALL ".join(
            f"SELECT '{archive}' AS archive, {columns} FROM {archive}.{table}"
            for archive in archives
        )
        + ";\n"
        for table, columns in ARCHIVE_TABLE_COLUMNS.items()
    )


def connect(database_file: Path) -> sqlite3.Connection:
    """Open one archive's database."""
    connection = sqlite3.connect(database_file)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def connect_archives(
    ia_database_file: Path, nb_database_file: Path
) -> sqlite3.Connection:
    """Open both archives' databases as one connection, read through the archive views.

    The two files are attached under their archive names, and `messages`,
    `users` and `message_references` are views over both, each row carrying the
    `archive` it came from.
    """
    connection = sqlite3.connect(":memory:")
    connection.execute(f"ATTACH DATABASE ? AS {IA_ARCHIVE}", (str(ia_database_file),))
    connection.execute(f"ATTACH DATABASE ? AS {NB_ARCHIVE}", (str(nb_database_file),))
    connection.executescript(_archive_views([IA_ARCHIVE, NB_ARCHIVE]))
    return connection


def connect_archive(database_file: Path, archive: str) -> sqlite3.Connection:
    """Open one archive's database on its own, read through the archive views.

    The file is attached under its archive name, and `messages`, `users` and
    `message_references` are views over it carrying `archive` as a column, so a
    query written for both archives reads this one the same way.
    """
    connection = sqlite3.connect(":memory:")
    connection.execute(f"ATTACH DATABASE ? AS {archive}", (str(database_file),))
    connection.executescript(_archive_views([archive]))
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
