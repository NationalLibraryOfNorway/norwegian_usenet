"""Query functions for duplicate message analysis."""

import sqlite3
from dataclasses import dataclass


@dataclass
class DuplicateSummary:
    total_messages: int
    unique_message_ids: int
    duplicate_message_ids: int


def summarize_nb_duplicates(connection: sqlite3.Connection) -> DuplicateSummary:
    """Count total messages, unique message-IDs, and duplicated message-IDs in NB."""
    total = connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    unique = connection.execute(
        "SELECT COUNT(*) FROM ("
        "  SELECT message_id_hash FROM messages GROUP BY message_id_hash HAVING COUNT(*) = 1"
        ")"
    ).fetchone()[0]
    duplicated = connection.execute(
        "SELECT COUNT(*) FROM ("
        "  SELECT message_id_hash FROM messages GROUP BY message_id_hash HAVING COUNT(*) > 1"
        ")"
    ).fetchone()[0]
    return DuplicateSummary(
        total_messages=total,
        unique_message_ids=unique,
        duplicate_message_ids=duplicated,
    )
