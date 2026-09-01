"""Query functions for duplicate message analysis."""

import sqlite3
from dataclasses import dataclass

from usenet_no.database.core import date_span_clause


@dataclass
class DuplicateSummary:
    total_messages: int
    unique_message_ids: int
    duplicate_messages: int
    message_IDs_that_appear_more_than_once: int


def summarize_duplicates(
    connection: sqlite3.Connection,
    archive: str,
    date_span: tuple[str, str] | None = None,
) -> DuplicateSummary:
    """Count messages, unique and duplicated message-IDs, and messages holding a duplicated id, in one archive."""
    clause, span_parameters = date_span_clause(date_span)
    parameters = (archive, *span_parameters)
    total = connection.execute(
        f"SELECT COUNT(*) FROM messages WHERE archive = ?{clause}", parameters
    ).fetchone()[0]
    unique = connection.execute(
        "SELECT COUNT(*) FROM ("
        f"  SELECT message_id_hash FROM messages WHERE archive = ?{clause}"
        "  GROUP BY message_id_hash HAVING COUNT(*) = 1"
        ")",
        parameters,
    ).fetchone()[0]
    duplicated = connection.execute(
        "SELECT COUNT(*) FROM ("
        f"  SELECT message_id_hash FROM messages WHERE archive = ?{clause}"
        "  GROUP BY message_id_hash HAVING COUNT(*) > 1"
        ")",
        parameters,
    ).fetchone()[0]
    return DuplicateSummary(
        total_messages=total,
        unique_message_ids=unique,
        duplicate_messages=total - unique,
        message_IDs_that_appear_more_than_once=duplicated,
    )
