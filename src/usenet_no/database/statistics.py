import logging
import sqlite3

from usenet_no.database.core import MESSAGES_WITH_SENDER, date_span_clause

logger = logging.getLogger(__name__)


def get_date_span(connection: sqlite3.Connection, archive: str) -> tuple[str, str]:
    """Return the first and last known date in an archive, as 'YYYY-MM-DD'.

    Messages with an unparseable date are stored as NULL and ignored.
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

    Messages with no sender are left out; count_messages_without_sender covers
    those. Sorted by (email_hash, name_hash).
    """
    clause, span_parameters = date_span_clause(date_span)
    return list(
        connection.execute(
            "SELECT users.name_hash, users.email_hash, COUNT(*)"
            f" FROM {MESSAGES_WITH_SENDER}"
            f" WHERE messages.archive = ?{clause}"
            " GROUP BY messages.user_id"
            " ORDER BY users.email_hash, users.name_hash",
            (archive, *span_parameters),
        )
    )


def count_messages_per_email(
    connection: sqlite3.Connection,
    archive: str,
    date_span: tuple[str, str] | None = None,
) -> list[tuple[str, int]]:
    """Count messages per hashed email in one archive, most posts first.

    The several (name, email) pairs an address was posted under collapse to one
    user. Senders with no email are left out.
    """
    clause, span_parameters = date_span_clause(date_span)
    return list(
        connection.execute(
            "SELECT users.email_hash, COUNT(*) AS post_count"
            f" FROM {MESSAGES_WITH_SENDER}"
            f" WHERE messages.archive = ? AND users.email_hash IS NOT NULL{clause}"
            " GROUP BY users.email_hash"
            " ORDER BY post_count DESC, users.email_hash",
            (archive, *span_parameters),
        )
    )


def count_messages_per_date(
    connection: sqlite3.Connection, archive: str
) -> list[tuple[str | None, int]]:
    """Count messages per date in one archive.

    The date is None for messages whose Date header could not be parsed. Sorted
    by date, with the undated group last.
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
    """Count messages with no sender, per archive and newsgroup.

    A message has no sender when no name or email could be read from its From
    header. Returns (archive, newsgroup, count) for newsgroups with at least
    one such message, sorted by (archive, newsgroup).
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
    """Count messages per newsgroup in one archive.

    When `date_span` is given, only messages inside it are counted; messages
    whose date can not be parsed are dropped. Sorted by newsgroup.
    """
    clause, span_parameters = date_span_clause(date_span)
    rows = connection.execute(
        f"SELECT newsgroup, COUNT(*) FROM messages WHERE archive = ?{clause}"
        " GROUP BY newsgroup",
        (archive, *span_parameters),
    )
    return dict(sorted(rows))
