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
) -> list[tuple[int, int]]:
    """Count messages per user in one archive, as (email_id, count), most posts first.

    Reads the archive's own file alone: an email id is the sender, and the names
    it posted under are not part of the count. Messages whose sender gave no
    address are left out; count_messages_without_sender covers those.
    """
    clause, span_parameters = date_span_clause(date_span)
    return list(
        connection.execute(
            "SELECT email_id, COUNT(*) AS post_count FROM messages"
            f" WHERE archive = ? AND email_id IS NOT NULL{clause}"
            " GROUP BY email_id"
            " ORDER BY post_count DESC, email_id",
            (archive, *span_parameters),
        )
    )


def count_messages_per_email_hash(
    connection: sqlite3.Connection,
    archive: str,
    date_span: tuple[str, str] | None = None,
) -> list[tuple[str, int]]:
    """Count messages per hashed email in one archive, most posts first.

    Needs the archive's user database attached, and is only for comparing users
    across the archives; count_messages_per_user is the same count within one.
    Senders with no email are left out.
    """
    clause, span_parameters = date_span_clause(date_span)
    return list(
        connection.execute(
            "SELECT emails.email_hash, COUNT(*) AS post_count"
            f" FROM {MESSAGES_WITH_SENDER}"
            f" WHERE messages.archive = ?{clause}"
            " GROUP BY emails.email_hash"
            " ORDER BY post_count DESC, emails.email_hash",
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

    A message has no sender when no address could be read from its From header,
    which includes the headers giving a display name and nothing else. Returns
    (archive, newsgroup, count) for newsgroups with at least one such message,
    sorted by (archive, newsgroup).
    """
    return list(
        connection.execute(
            "SELECT archive, newsgroup, COUNT(*) FROM messages"
            " WHERE email_id IS NULL"
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
