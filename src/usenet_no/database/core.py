"""Connect to the database, and the row id and date span arithmetic its queries share."""

import sqlite3
from collections import defaultdict
from pathlib import Path

IA_ARCHIVE = "ia"
NB_ARCHIVE = "nb"


def connect(database_file: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_file)
    connection.execute("PRAGMA foreign_keys = ON")
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
