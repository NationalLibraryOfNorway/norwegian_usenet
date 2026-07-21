"""Counting queries over the message database.

These replace repeated walks of the mbox directories: every count is a GROUP BY
over the table built in step 02. Restricting an archive to another archive's
date span is a WHERE clause here, rather than a filtered copy of the data.
"""

import logging
import sqlite3

from usenet_no.database import date_span_clause

logger = logging.getLogger(__name__)


def get_date_span(connection: sqlite3.Connection, archive: str) -> tuple[str, str]:
    """Return the first and last known date in an archive, as 'YYYY-MM-DD'.

    Messages with an unparseable date are stored as NULL and ignored here.
    """
    first_date, last_date = connection.execute(
        "SELECT MIN(date), MAX(date) FROM messages"
        " WHERE archive = ? AND date IS NOT NULL",
        (archive,),
    ).fetchone()
    return first_date, last_date


def count_messages_per_user(
    connection: sqlite3.Connection,
    archive: str,
    date_span: tuple[str, str] | None = None,
) -> list[tuple[str | None, str | None, int]]:
    """Count messages per user in one archive, as (name_hash, email_hash, count).

    Only hashes are returned, so the result can be published as it is. Messages
    with no sender have no user and are left out; they are counted separately by
    count_messages_without_sender.

    Returned sorted by (email_hash, name_hash) so reruns produce identical output.
    """
    clause, span_parameters = date_span_clause(date_span)
    return list(
        connection.execute(
            "SELECT users.name_hash, users.email_hash, COUNT(*)"
            " FROM messages JOIN users ON messages.user_id = users.id"
            f" WHERE messages.archive = ?{clause}"
            " GROUP BY messages.user_id"
            " ORDER BY users.email_hash, users.name_hash",
            (archive, *span_parameters),
        )
    )


def count_messages_per_date(
    connection: sqlite3.Connection, archive: str
) -> list[tuple[str | None, int]]:
    """Count messages per date in one archive.

    The date is None for messages whose Date header could not be parsed. Callers
    that write a report decide how to label those.

    Returned sorted by date, with the undated group last.
    """
    return list(
        connection.execute(
            "SELECT date, COUNT(*) FROM messages WHERE archive = ?"
            " GROUP BY date ORDER BY date IS NULL, date",
            (archive,),
        )
    )


def count_messages_without_sender(
    connection: sqlite3.Connection,
) -> list[tuple[str, str, int]]:
    """Count messages whose sender is unknown, per archive and newsgroup.

    A message has no user when it carried no From header at all. The mbox
    envelope is not used as a fallback, so nothing here is inferred from the
    storage format; see usenet_no.mbox_utils.get_from_field.

    Returns (archive, newsgroup, count) for newsgroups with at least one such
    message, sorted so reruns produce identical output.
    """
    return list(
        connection.execute(
            "SELECT archive, newsgroup, COUNT(*) FROM messages"
            " WHERE user_id IS NULL"
            " GROUP BY archive, newsgroup"
            " ORDER BY archive, newsgroup"
        )
    )


def count_messages_per_group(
    connection: sqlite3.Connection,
    archive: str,
    date_span: tuple[str, str] | None = None,
) -> dict[str, int]:
    """Count messages per newsgroup in one archive, newest ordering aside.

    When `date_span` is given, only messages inside it are counted, plus every
    message whose date could not be parsed. Keeping the unparseable ones matches
    how the date-filtered archive was built on disk: a message is only dropped
    when it is known to fall outside the span.

    Returned sorted by newsgroup so reruns produce identical output.
    """
    clause, span_parameters = date_span_clause(date_span)
    rows = connection.execute(
        f"SELECT newsgroup, COUNT(*) FROM messages WHERE archive = ?{clause}"
        " GROUP BY newsgroup",
        (archive, *span_parameters),
    )
    return dict(sorted(rows))
