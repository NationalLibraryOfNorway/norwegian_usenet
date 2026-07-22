"""Finding message ids whose copies disagree about the message body.

Two questions, kept apart because they mean different things:

- A *within-archive conflict* is one Message-ID carrying different bodies inside
  a single archive. That archive holds two versions of the same posting, so
  collapsing them on Message-ID would lose one.
- An *across-archive conflict* is one Message-ID whose copies in the two
  archives never agree on a body, most often because the archives decoded the
  same characters differently.

Both read the database built in step 02. Redundant copies that agree on the
body are not conflicts at all; those are counted in `usenet_no.database.duplicates`.
"""

import logging
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class WithinArchiveConflict:
    """One Message-ID carrying several bodies inside a single archive."""

    archive: str
    message_id_hash: str
    num_distinct_bodies: int
    newsgroups: list[str] = field(default_factory=list)


@dataclass
class AcrossArchiveConflict:
    """One Message-ID whose copies in the two archives never agree on a body."""

    message_id_hash: str
    num_distinct_bodies: int
    newsgroups_per_archive: dict[str, list[str]] = field(default_factory=dict)


def _fetch_rows_by_message_id_hash(
    connection: sqlite3.Connection,
) -> dict[str, list[tuple[str, str, str | None]]]:
    """Map each hashed message id to its (archive, newsgroup, body_hash) rows.

    Rows come back ordered so that the grouping below is reproducible.
    """
    rows_by_message_id_hash: dict[str, list[tuple[str, str, str | None]]] = defaultdict(
        list
    )
    for message_id_hash, archive, newsgroup, body_hash in connection.execute(
        "SELECT message_id_hash, archive, newsgroup, body_hash FROM messages"
        " WHERE message_id_hash IS NOT NULL"
        " ORDER BY message_id_hash, archive, newsgroup, body_hash"
    ):
        rows_by_message_id_hash[message_id_hash].append((archive, newsgroup, body_hash))
    return rows_by_message_id_hash


def _group_by_archive(
    rows: list[tuple[str, str, str | None]],
) -> tuple[dict[str, set[str | None]], dict[str, list[str]]]:
    """Split one message id's rows into body hashes and newsgroups per archive."""
    hashes_by_archive: dict[str, set[str | None]] = defaultdict(set)
    newsgroups_by_archive: dict[str, set[str]] = defaultdict(set)
    for archive, newsgroup, body_hash in rows:
        hashes_by_archive[archive].add(body_hash)
        newsgroups_by_archive[archive].add(newsgroup)
    return hashes_by_archive, {
        archive: sorted(newsgroups)
        for archive, newsgroups in newsgroups_by_archive.items()
    }


def find_within_archive_conflicts(
    connection: sqlite3.Connection,
) -> list[WithinArchiveConflict]:
    """Find message ids that carry more than one body inside a single archive.

    Returned sorted by (archive, message_id_hash) so reruns produce identical output.
    """
    conflicts: list[WithinArchiveConflict] = []

    for message_id_hash, rows in _fetch_rows_by_message_id_hash(connection).items():
        hashes_by_archive, newsgroups_by_archive = _group_by_archive(rows)
        for archive, body_hashes in hashes_by_archive.items():
            if len(body_hashes) > 1:
                conflicts.append(
                    WithinArchiveConflict(
                        archive=archive,
                        message_id_hash=message_id_hash,
                        num_distinct_bodies=len(body_hashes),
                        newsgroups=newsgroups_by_archive[archive],
                    )
                )

    return sorted(
        conflicts, key=lambda conflict: (conflict.archive, conflict.message_id_hash)
    )


def find_across_archive_conflicts(
    connection: sqlite3.Connection,
) -> list[AcrossArchiveConflict]:
    """Find message ids held by both archives whose copies never share a body.

    A message id counts as conflicting only when the archives have no body in
    common: if one version matches, the message did survive intact in both, even
    where one archive also holds an extra variant.

    Returned sorted by message_id_hash so reruns produce identical output.
    """
    conflicts: list[AcrossArchiveConflict] = []

    for message_id_hash, rows in _fetch_rows_by_message_id_hash(connection).items():
        hashes_by_archive, newsgroups_by_archive = _group_by_archive(rows)
        if len(hashes_by_archive) < 2:
            continue

        if not set.intersection(*hashes_by_archive.values()):
            conflicts.append(
                AcrossArchiveConflict(
                    message_id_hash=message_id_hash,
                    num_distinct_bodies=len(set().union(*hashes_by_archive.values())),
                    newsgroups_per_archive=dict(sorted(newsgroups_by_archive.items())),
                )
            )

    return sorted(conflicts, key=lambda conflict: conflict.message_id_hash)
