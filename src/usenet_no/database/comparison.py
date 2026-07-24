import logging
import sqlite3

from usenet_no.database.core import IA_ARCHIVE, NB_ARCHIVE, date_span_clause

logger = logging.getLogger(__name__)

# Temporary tables holding one row per distinct hash. The id sets run to tens of
# millions of rows, so they are built inside SQLite rather than as Python sets.
IA_IDS = "ia_ids"
NB_IDS = "nb_ids"
IA_REFERENCES = "ia_references"
NB_REFERENCES = "nb_references"


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
        f" WHERE archive = ? AND message_id_hash IS NOT NULL{clause}",
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
        " FROM message_references"
        " JOIN messages ON message_references.message_row_id = messages.id"
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
    which archive cited them.

    When `ia_date_span` is given, only IA is restricted to it; see the module
    docstring.
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
    # NB rows pass the span unconditionally, so that only IA is restricted
    if ia_date_span is None:
        clause, span_parameters = "", ()
    else:
        clause = " AND (archive = ? OR date BETWEEN ? AND ?)"
        span_parameters = (NB_ARCHIVE, *ia_date_span)

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
    are left out. A newsgroup only one archive has simply gets a zero on the
    other side.

    When `ia_date_span` is given, only IA is restricted to it; see the module
    docstring.
    """
    return _compare_hashes_per_group(connection, "body_hash", ia_date_span)


def compare_message_ids_per_group(
    connection: sqlite3.Connection, ia_date_span: tuple[str, str] | None = None
) -> list[tuple[str, int, int, int]]:
    """Compare id overlap per newsgroup, as (newsgroup, ia_only, nb_only, both).

    The per-newsgroup breakdown of `compare_message_ids`, counted in distinct
    hashed message ids, so a posting an archive kept several copies of counts
    once. Messages without an id are left out, and a newsgroup only one archive
    has simply gets a zero on the other side.

    When `ia_date_span` is given, only IA is restricted to it; see the module
    docstring.
    """
    return _compare_hashes_per_group(connection, "message_id_hash", ia_date_span)
