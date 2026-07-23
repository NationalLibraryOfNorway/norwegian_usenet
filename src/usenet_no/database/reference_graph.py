"""References between newsgroups, read as a directed weighted edge list.

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
in each. The few messages with no message id at all cannot be deduplicated
that way and count once per stored row instead.
"""

import logging
import sqlite3
from typing import NamedTuple

from usenet_no.database.core import date_span_clause
from usenet_no.database.overlap import ArchiveDatespan

logger = logging.getLogger(__name__)

UNKNOWN_NEWSGROUP = "unknown"


class ReferenceEdge(NamedTuple):
    """One directed edge, under whichever weighting produced it.

    The field names are what the edge list is written out under, so a reader of
    the CSV sees the same names as a reader of this module.
    """

    from_newsgroup: str
    to_newsgroup: str
    number_of_references: int


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
                COALESCE(messages.message_id_hash, 'row:' || messages.id)
                    AS source_message,
                messages.newsgroup AS from_newsgroup,
                message_references.referenced_id_hash AS referenced_id_hash,
                targets.newsgroup AS target_newsgroup
            FROM messages
            JOIN message_references
                ON message_references.message_row_id = messages.id
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
    by five hundred messages pulls five hundred onto the edge.

    Returned sorted by descending weight and then by the pair of names, so
    reruns produce identical output.
    """
    return _count_edges(connection, archive_datespans, "COUNT(*)")


def count_referenced_messages(
    connection: sqlite3.Connection, archive_datespans: list[ArchiveDatespan]
) -> list[ReferenceEdge]:
    """Weigh each edge by how many distinct messages it reaches.

    Every referenced id adds one however many messages cite it, so a message
    cited by five hundred messages pulls one onto the edge. Unresolved ids are
    distinct ids too: two references to the same lost message weigh one.

    Returned sorted by descending weight and then by the pair of names, so
    reruns produce identical output.
    """
    return _count_edges(
        connection,
        archive_datespans,
        "COUNT(DISTINCT referenced_id_hash)",
    )
