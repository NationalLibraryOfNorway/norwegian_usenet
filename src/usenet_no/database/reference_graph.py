"""References between newsgroups as a directed weighted edge list, and their totals.

Every message carries a References header naming the messages it replies to.
When a message in one newsgroup references a message held by another newsgroup,
that is an edge from the first newsgroup to the second, and the edges
are weighted in one of two ways: by how many references run between the pair,
or by how many distinct messages in the target the source references.

A referenced id whose message is not in the read body of messages points to the
placeholder newsgroup `unknown`, and one whose message sits in several
newsgroups (crossposts are stored once per group's mbox) makes an edge to each
of them. References within a newsgroup are left out: the graph is about what
runs between newsgroups.

The archives hold the same message more than once, so sources are read as
distinct (message id, newsgroup, referenced ids) rows: a message held by both
archives counts once, and a message crossposted to two newsgroups is a source
in each.

The totals leave the newsgroup out altogether: a reference is a (referring
message, referenced id) pair, counted once however many newsgroups hold either
end of it, and split by where the referenced message is found.
"""

import logging
import sqlite3
from typing import NamedTuple

from usenet_no.database.core import MESSAGES_WITH_REFERENCES, date_span_clause
from usenet_no.database.overlap import ArchiveDatespan

logger = logging.getLogger(__name__)

UNKNOWN_NEWSGROUP = "unknown"

# Temporary tables holding one row per distinct reference and referenced id. The
# references run to tens of millions of rows, so they are built inside SQLite.
REFERENCE_PAIRS = "reference_pairs"
REFERENCE_TARGETS = "reference_targets"


class ReferenceEdge(NamedTuple):
    """One directed edge, under whichever weighting produced it.

    The field names are the edge list's CSV column names.
    """

    from_newsgroup: str
    to_newsgroup: str
    number_of_references: int


class ReferenceResolution(NamedTuple):
    """One archive's references, split by where the referenced message is found."""

    total: int
    resolved_in_archive: int
    resolved_in_other_archive: int
    unresolved: int


def _archive_scope(
    archive_datespans: list[ArchiveDatespan], table: str
) -> tuple[str, list[str]]:
    """The WHERE fragment restricting `table`'s messages to the archives and date spans."""
    conditions = []
    parameters: list[str] = []
    for archive, date_span in archive_datespans:
        clause, span_parameters = date_span_clause(date_span, column=f"{table}.date")
        conditions.append(f"({table}.archive = ?{clause})")
        parameters.extend((archive, *span_parameters))
    return f"({' OR '.join(conditions)})", parameters


def _count_edges(
    connection: sqlite3.Connection,
    archive_datespans: list[ArchiveDatespan],
    aggregate: str,
) -> list[ReferenceEdge]:
    """Aggregate the (source newsgroup, target newsgroup) pairs into edges.

    `resolved_references` is one row per distinct (message id, newsgroup,
    referenced id, target newsgroup); messages with no id fall back to their
    row id so they stay apart. The LEFT JOIN looks each referenced id up
    through the message id index and keeps the references that resolve
    nowhere, which COALESCE points at the unknown newsgroup. The join's scope
    condition sits in the ON clause: in a WHERE it would drop the unresolved
    rows, and both sides must read the same body of messages, so a reference
    to a message outside the scope is unknown, not resolved.

    `aggregate` is what an edge's weight counts, over the resolved rows of its
    (from, to) pair.
    """
    source_scope, source_parameters = _archive_scope(archive_datespans, "messages")
    target_scope, target_parameters = _archive_scope(archive_datespans, "targets")
    query = f"""
        WITH resolved_references AS (
            SELECT DISTINCT
                messages.message_id_hash AS source_message,
                messages.newsgroup AS from_newsgroup,
                message_references.referenced_id_hash AS referenced_id_hash,
                targets.newsgroup AS target_newsgroup
            FROM {MESSAGES_WITH_REFERENCES}
            LEFT JOIN messages AS targets
                ON targets.message_id_hash = message_references.referenced_id_hash
                AND {target_scope}
            WHERE {source_scope}
        )
        SELECT
            from_newsgroup,
            COALESCE(target_newsgroup, ?) AS to_newsgroup,
            {aggregate} AS number_of_references
        FROM resolved_references
        WHERE COALESCE(target_newsgroup, ?) != from_newsgroup
        GROUP BY from_newsgroup, to_newsgroup
        ORDER BY number_of_references DESC, from_newsgroup, to_newsgroup
    """
    parameters = [
        *target_parameters,
        *source_parameters,
        UNKNOWN_NEWSGROUP,
        UNKNOWN_NEWSGROUP,
    ]

    edges = [ReferenceEdge(*row) for row in connection.execute(query, parameters)]
    logger.info(
        "Counted %d directed edges between %d referring newsgroups",
        len(edges),
        len({edge.from_newsgroup for edge in edges}),
    )
    return edges


def count_references(
    connection: sqlite3.Connection, archive_datespans: list[ArchiveDatespan]
) -> list[ReferenceEdge]:
    """Weigh each edge by the number of references running along it.

    Every distinct (message, referenced id) pair adds one, so a message cited
    by five hundred messages pulls five hundred onto the edge. Sorted by
    descending weight, then by the pair of names.
    """
    return _count_edges(connection, archive_datespans, "COUNT(*)")


def count_referenced_messages(
    connection: sqlite3.Connection, archive_datespans: list[ArchiveDatespan]
) -> list[ReferenceEdge]:
    """Weigh each edge by how many distinct messages it reaches.

    Every referenced id adds one however many messages cite it, so a message
    cited by five hundred messages pulls one onto the edge. Unresolved ids are
    distinct ids too: two references to the same lost message weigh one. Sorted
    by descending weight, then by the pair of names.
    """
    return _count_edges(
        connection,
        archive_datespans,
        "COUNT(DISTINCT referenced_id_hash)",
    )


def _create_reference_pair_table(
    connection: sqlite3.Connection, archive_datespan: ArchiveDatespan
) -> None:
    """Collect one archive's distinct (referring message, referenced id) pairs.

    A message held by several newsgroups, or by both archives, is one referring
    message, so its references count once.
    """
    scope, parameters = _archive_scope([archive_datespan], "messages")
    connection.execute(f"DROP TABLE IF EXISTS temp.{REFERENCE_PAIRS}")
    connection.execute(
        f"CREATE TEMP TABLE {REFERENCE_PAIRS} ("
        "    from_id TEXT NOT NULL,"
        "    to_id TEXT NOT NULL,"
        "    PRIMARY KEY (from_id, to_id)"
        ") WITHOUT ROWID"
    )
    connection.execute(
        f"INSERT INTO {REFERENCE_PAIRS}"
        " SELECT DISTINCT"
        "     messages.message_id_hash,"
        "     message_references.referenced_id_hash"
        f" FROM {MESSAGES_WITH_REFERENCES}"
        f" WHERE {scope}",
        parameters,
    )


def _create_reference_target_table(
    connection: sqlite3.Connection,
    archive_datespan: ArchiveDatespan,
    other_archive_datespan: ArchiveDatespan,
) -> None:
    """Look each referenced id up in both archives, one row per distinct id."""
    archive_scope, archive_parameters = _archive_scope([archive_datespan], "held")
    other_scope, other_parameters = _archive_scope(
        [other_archive_datespan], "other_held"
    )
    connection.execute(f"DROP TABLE IF EXISTS temp.{REFERENCE_TARGETS}")
    connection.execute(
        f"CREATE TEMP TABLE {REFERENCE_TARGETS} ("
        "    to_id TEXT PRIMARY KEY,"
        "    in_archive INTEGER NOT NULL,"
        "    in_other_archive INTEGER NOT NULL"
        ") WITHOUT ROWID"
    )
    connection.execute(
        f"INSERT INTO {REFERENCE_TARGETS}"
        " SELECT"
        "     targets.to_id,"
        "     EXISTS (SELECT 1 FROM messages AS held"
        "             WHERE held.message_id_hash = targets.to_id"
        f"             AND {archive_scope}),"
        "     EXISTS (SELECT 1 FROM messages AS other_held"
        "             WHERE other_held.message_id_hash = targets.to_id"
        f"             AND {other_scope})"
        f" FROM (SELECT DISTINCT to_id FROM {REFERENCE_PAIRS}) AS targets",
        (*archive_parameters, *other_parameters),
    )


def count_reference_resolution(
    connection: sqlite3.Connection,
    archive_datespan: ArchiveDatespan,
    other_archive_datespan: ArchiveDatespan,
) -> ReferenceResolution:
    """Count one archive's references, split by where the referenced message is found.

    A reference is a distinct (referring message, referenced id) pair, so the
    same reply stored twice counts once and a message referencing five hundred
    others counts five hundred. Each pair falls in exactly one of three groups:
    the referenced message
    is in the archive itself, it is missing from the archive but the other
    archive holds it, or neither holds it.
    """
    _create_reference_pair_table(connection, archive_datespan)
    _create_reference_target_table(connection, archive_datespan, other_archive_datespan)
    total, resolved, resolved_by_other, unresolved = connection.execute(
        "SELECT"
        "     COUNT(*),"
        "     SUM(in_archive),"
        "     SUM(NOT in_archive AND in_other_archive),"
        "     SUM(NOT in_archive AND NOT in_other_archive)"
        f" FROM {REFERENCE_PAIRS}"
        f" JOIN {REFERENCE_TARGETS} USING (to_id)"
    ).fetchone()

    for table in (REFERENCE_PAIRS, REFERENCE_TARGETS):
        connection.execute(f"DROP TABLE temp.{table}")

    # SUM over no rows is NULL, which is what an archive with no references gives
    resolution = ReferenceResolution(
        total=total,
        resolved_in_archive=resolved or 0,
        resolved_in_other_archive=resolved_by_other or 0,
        unresolved=unresolved or 0,
    )
    logger.info(
        "Counted %d references in %s: %d resolved, %d resolved by %s, %d unresolved",
        resolution.total,
        archive_datespan[0],
        resolution.resolved_in_archive,
        resolution.resolved_in_other_archive,
        other_archive_datespan[0],
        resolution.unresolved,
    )
    return resolution
