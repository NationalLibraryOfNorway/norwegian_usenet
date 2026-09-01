import logging
import sqlite3
from dataclasses import dataclass

from usenet_no.database.core import (
    IA_ARCHIVE,
    MESSAGES_WITH_REFERENCES,
    MESSAGES_WITH_SENDER,
    NB_ARCHIVE,
    date_span_clause,
)

logger = logging.getLogger(__name__)

# Temporary tables holding one row per distinct hash. The id sets run to tens of
# millions of rows, so they are built inside SQLite rather than as Python sets.
IA_IDS = "ia_ids"
NB_IDS = "nb_ids"
IA_REFERENCES = "ia_references"
NB_REFERENCES = "nb_references"
SHARED_NEWSGROUPS = "shared_newsgroups"
SHARED_EMAILS = "shared_emails"


@dataclass(frozen=True)
class VennCounts:
    """The three regions of an NB/IA venn diagram, counted in distinct values."""

    nb_only: int
    ia_only: int
    both: int

    @property
    def total(self) -> int:
        return self.nb_only + self.ia_only + self.both


def _ia_only_span_clause(ia_date_span: tuple[str, str] | None) -> tuple[str, tuple]:
    """Build the WHERE fragment restricting IA to a date span, letting every NB row through."""
    if ia_date_span is None:
        return "", ()
    return (
        " AND (messages.archive = ? OR messages.date BETWEEN ? AND ?)",
        (NB_ARCHIVE, *ia_date_span),
    )


def _create_id_table(
    connection: sqlite3.Connection,
    table: str,
    archive: str,
    date_span: tuple[str, str] | None,
) -> None:
    """Collect the distinct hashed Message-IDs held by one archive."""
    clause, span_parameters = date_span_clause(date_span)
    connection.execute(f"DROP TABLE IF EXISTS temp.{table}")
    connection.execute(f"CREATE TEMP TABLE {table} (id_hash TEXT PRIMARY KEY)")
    connection.execute(
        f"INSERT INTO {table} SELECT DISTINCT message_id_hash FROM messages"
        f" WHERE archive = ?{clause}",
        (archive, *span_parameters),
    )


def _create_reference_table(
    connection: sqlite3.Connection,
    table: str,
    archive: str,
    date_span: tuple[str, str] | None,
) -> None:
    """Collect the distinct hashed ids cited in one archive's References headers."""
    clause, span_parameters = date_span_clause(date_span, column="messages.date")
    connection.execute(f"DROP TABLE IF EXISTS temp.{table}")
    connection.execute(f"CREATE TEMP TABLE {table} (id_hash TEXT PRIMARY KEY)")
    connection.execute(
        f"INSERT INTO {table}"
        " SELECT DISTINCT message_references.referenced_id_hash"
        f" FROM {MESSAGES_WITH_REFERENCES}"
        f" WHERE messages.archive = ?{clause}",
        (archive, *span_parameters),
    )


def _held_by(table: str) -> str:
    """A condition on `source.id_hash` being one of `table`'s hashes."""
    return f"EXISTS (SELECT 1 FROM {table} WHERE {table}.id_hash = source.id_hash)"


def _not_held_by(table: str) -> str:
    return f"NOT {_held_by(table)}"


def _count(connection: sqlite3.Connection, table: str, *conditions: str) -> int:
    """Count the rows of one hash table that satisfy every condition."""
    where = " AND ".join(conditions) if conditions else "1"
    (count,) = connection.execute(
        f"SELECT COUNT(*) FROM {table} AS source WHERE {where}"
    ).fetchone()
    return count


def compare_message_ids(
    connection: sqlite3.Connection, ia_date_span: tuple[str, str] | None = None
) -> dict[str, int]:
    """Compare message id overlap and reference resolution between IA and NB.

    Counts distinct hashed ids in three groups: the ids each archive holds, the
    references one archive cannot resolve on its own but the other can, and the
    "ghost" references that point at a posting neither archive kept, split by
    which archive cited them. When `ia_date_span` is given, only IA is
    restricted to it.
    """
    _create_id_table(connection, IA_IDS, IA_ARCHIVE, ia_date_span)
    _create_id_table(connection, NB_IDS, NB_ARCHIVE, None)
    _create_reference_table(connection, IA_REFERENCES, IA_ARCHIVE, ia_date_span)
    _create_reference_table(connection, NB_REFERENCES, NB_ARCHIVE, None)

    in_neither_archive = (_not_held_by(IA_IDS), _not_held_by(NB_IDS))

    results = {
        # Message ID overlap
        "ia_ids": _count(connection, IA_IDS),
        "nb_ids": _count(connection, NB_IDS),
        "ids_in_both": _count(connection, IA_IDS, _held_by(NB_IDS)),
        "ids_ia_only": _count(connection, IA_IDS, _not_held_by(NB_IDS)),
        "ids_nb_only": _count(connection, NB_IDS, _not_held_by(IA_IDS)),
        # Cross-archive reference resolution
        "ia_refs_resolved_by_nb": _count(
            connection, IA_REFERENCES, _not_held_by(IA_IDS), _held_by(NB_IDS)
        ),
        "nb_refs_resolved_by_ia": _count(
            connection, NB_REFERENCES, _not_held_by(NB_IDS), _held_by(IA_IDS)
        ),
        # Ghost references (cited but in neither archive)
        "ghost_cited_by_ia_only": _count(
            connection, IA_REFERENCES, _not_held_by(NB_REFERENCES), *in_neither_archive
        ),
        "ghost_cited_by_nb_only": _count(
            connection, NB_REFERENCES, _not_held_by(IA_REFERENCES), *in_neither_archive
        ),
        "ghost_cited_by_both": _count(
            connection, IA_REFERENCES, _held_by(NB_REFERENCES), *in_neither_archive
        ),
    }

    for table in (IA_IDS, NB_IDS, IA_REFERENCES, NB_REFERENCES):
        connection.execute(f"DROP TABLE temp.{table}")

    return results


def _compare_hashes_per_group(
    connection: sqlite3.Connection,
    hash_column: str,
    ia_date_span: tuple[str, str] | None,
) -> list[tuple[str, int, int, int]]:
    """Count distinct hashes per newsgroup, as (newsgroup, ia_only, nb_only, both)."""
    clause, span_parameters = _ia_only_span_clause(ia_date_span)

    rows = connection.execute(
        "SELECT newsgroup,"
        "       SUM(in_ia AND NOT in_nb),"
        "       SUM(in_nb AND NOT in_ia),"
        "       SUM(in_ia AND in_nb)"
        " FROM ("
        "     SELECT newsgroup,"
        "            MAX(archive = ?) AS in_ia,"
        "            MAX(archive = ?) AS in_nb"
        "     FROM messages"
        f"     WHERE {hash_column} IS NOT NULL{clause}"
        f"     GROUP BY newsgroup, {hash_column}"
        " )"
        " GROUP BY newsgroup ORDER BY newsgroup",
        (IA_ARCHIVE, NB_ARCHIVE, *span_parameters),
    )
    return list(rows)


def compare_content_per_group(
    connection: sqlite3.Connection, ia_date_span: tuple[str, str] | None = None
) -> list[tuple[str, int, int, int]]:
    """Compare body overlap per newsgroup, as (newsgroup, ia_only, nb_only, both).

    A newsgroup is counted in distinct bodies, so a posting the archives hold
    several copies of counts once. Messages with an empty body carry no hash and
    are left out, and a newsgroup only one archive has gets a zero on the other
    side. When `ia_date_span` is given, only IA is restricted to it.
    """
    return _compare_hashes_per_group(connection, "body_hash", ia_date_span)


def compare_message_ids_per_group(
    connection: sqlite3.Connection, ia_date_span: tuple[str, str] | None = None
) -> list[tuple[str, int, int, int]]:
    """Compare id overlap per newsgroup, as (newsgroup, ia_only, nb_only, both).

    The per-newsgroup breakdown of `compare_message_ids`, counted in distinct
    hashed message ids, so a posting an archive kept several copies of counts
    once. Messages without an id are left out, and a newsgroup only one archive
    has gets a zero on the other side. When `ia_date_span` is given, only IA is
    restricted to it.
    """
    return _compare_hashes_per_group(connection, "message_id_hash", ia_date_span)


def _count_venn(
    connection: sqlite3.Connection,
    value: str,
    source: str = "messages",
    conditions: str = "",
    parameters: tuple = (),
) -> VennCounts:
    """Count the distinct values of `value` held by NB alone, IA alone and both."""
    ia_only, nb_only, both = connection.execute(
        "SELECT SUM(in_ia AND NOT in_nb),"
        "       SUM(in_nb AND NOT in_ia),"
        "       SUM(in_ia AND in_nb)"
        " FROM ("
        "     SELECT MAX(messages.archive = ?) AS in_ia,"
        "            MAX(messages.archive = ?) AS in_nb"
        f"     FROM {source}"
        f"     WHERE {value} IS NOT NULL{conditions}"
        f"     GROUP BY {value}"
        " )",
        (IA_ARCHIVE, NB_ARCHIVE, *parameters),
    ).fetchone()
    # SUM over no rows is NULL, which is what an empty archive pair gives
    return VennCounts(nb_only=nb_only or 0, ia_only=ia_only or 0, both=both or 0)


def count_newsgroup_overlap(
    connection: sqlite3.Connection, ia_date_span: tuple[str, str] | None = None
) -> VennCounts:
    """Count the newsgroups held by NB alone, IA alone and both.

    When `ia_date_span` is given, only IA is restricted to it, so a group whose
    IA messages all fall outside the span stops counting as one IA holds.
    """
    clause, parameters = _ia_only_span_clause(ia_date_span)
    return _count_venn(
        connection, "messages.newsgroup", conditions=clause, parameters=parameters
    )


def count_user_overlap(
    connection: sqlite3.Connection, ia_date_span: tuple[str, str] | None = None
) -> VennCounts:
    """Count the users held by NB alone, IA alone and both, identified by hashed email.

    Needs the user databases attached. Senders with no email are left out. When
    `ia_date_span` is given, only IA is restricted to it.
    """
    clause, parameters = _ia_only_span_clause(ia_date_span)
    return _count_venn(
        connection,
        "emails.email_hash",
        source=MESSAGES_WITH_SENDER,
        conditions=clause,
        parameters=parameters,
    )


def count_message_id_overlap(
    connection: sqlite3.Connection, ia_date_span: tuple[str, str] | None = None
) -> VennCounts:
    """Count the messages held by NB alone, IA alone and both, identified by hashed id.

    Counted over the whole archive rather than per newsgroup, so a crossposted
    message counts once. Messages without an id are left out. When
    `ia_date_span` is given, only IA is restricted to it.
    """
    clause, parameters = _ia_only_span_clause(ia_date_span)
    return _count_venn(
        connection,
        "messages.message_id_hash",
        conditions=clause,
        parameters=parameters,
    )


def count_body_overlap(
    connection: sqlite3.Connection, ia_date_span: tuple[str, str] | None = None
) -> VennCounts:
    """Count the message bodies held by NB alone, IA alone and both, by exact text match.

    Counted over the whole archive rather than per newsgroup, so a body posted
    to several groups counts once. Messages with an empty body carry no hash and
    are left out. When `ia_date_span` is given, only IA is restricted to it.
    """
    clause, parameters = _ia_only_span_clause(ia_date_span)
    return _count_venn(
        connection, "messages.body_hash", conditions=clause, parameters=parameters
    )


def _create_shared_newsgroup_table(
    connection: sqlite3.Connection, ia_date_span: tuple[str, str] | None
) -> None:
    """Collect the newsgroups both archives hold."""
    clause, parameters = _ia_only_span_clause(ia_date_span)
    connection.execute(f"DROP TABLE IF EXISTS temp.{SHARED_NEWSGROUPS}")
    connection.execute(
        f"CREATE TEMP TABLE {SHARED_NEWSGROUPS} (newsgroup TEXT PRIMARY KEY)"
    )
    connection.execute(
        f"INSERT INTO {SHARED_NEWSGROUPS}"
        " SELECT messages.newsgroup FROM messages"
        f" WHERE 1{clause}"
        " GROUP BY messages.newsgroup"
        " HAVING MAX(messages.archive = ?) AND MAX(messages.archive = ?)",
        (*parameters, IA_ARCHIVE, NB_ARCHIVE),
    )


def _create_shared_email_table(
    connection: sqlite3.Connection, ia_date_span: tuple[str, str] | None
) -> None:
    """Collect the hashed emails both archives hold."""
    clause, parameters = _ia_only_span_clause(ia_date_span)
    connection.execute(f"DROP TABLE IF EXISTS temp.{SHARED_EMAILS}")
    connection.execute(
        f"CREATE TEMP TABLE {SHARED_EMAILS} (email_hash TEXT PRIMARY KEY)"
    )
    connection.execute(
        f"INSERT INTO {SHARED_EMAILS}"
        f" SELECT emails.email_hash FROM {MESSAGES_WITH_SENDER}"
        f" WHERE emails.email_hash IS NOT NULL{clause}"
        " GROUP BY emails.email_hash"
        " HAVING MAX(messages.archive = ?) AND MAX(messages.archive = ?)",
        (*parameters, IA_ARCHIVE, NB_ARCHIVE),
    )


def count_message_id_overlap_in_shared_newsgroups(
    connection: sqlite3.Connection, ia_date_span: tuple[str, str] | None = None
) -> VennCounts:
    """Count message overlap over the newsgroups both archives hold.

    A message counts as soon as one of the groups carrying it is shared, and
    counts once however many groups that is. When `ia_date_span` is given, only
    IA is restricted to it, both when deciding which groups are shared and when
    counting messages.
    """
    _create_shared_newsgroup_table(connection, ia_date_span)
    clause, parameters = _ia_only_span_clause(ia_date_span)
    counts = _count_venn(
        connection,
        "messages.message_id_hash",
        conditions=clause
        + f" AND messages.newsgroup IN (SELECT newsgroup FROM {SHARED_NEWSGROUPS})",
        parameters=parameters,
    )
    connection.execute(f"DROP TABLE temp.{SHARED_NEWSGROUPS}")
    return counts


def count_message_id_overlap_for_shared_users(
    connection: sqlite3.Connection, ia_date_span: tuple[str, str] | None = None
) -> VennCounts:
    """Count message overlap over the users both archives hold, identified by hashed email.

    Needs the user databases attached. Messages whose sender has no email are
    left out, and a message counts once
    however many newsgroups carry it. When `ia_date_span` is given, only IA is
    restricted to it, both when deciding which users are shared and when
    counting messages.
    """
    _create_shared_email_table(connection, ia_date_span)
    clause, parameters = _ia_only_span_clause(ia_date_span)
    counts = _count_venn(
        connection,
        "messages.message_id_hash",
        source=MESSAGES_WITH_SENDER,
        conditions=clause
        + f" AND emails.email_hash IN (SELECT email_hash FROM {SHARED_EMAILS})",
        parameters=parameters,
    )
    connection.execute(f"DROP TABLE temp.{SHARED_EMAILS}")
    return counts
