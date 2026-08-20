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
from itertools import groupby
from operator import itemgetter

from usenet_no.database.core import load_id_spans

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


@dataclass
class NewsgroupBodyConflict:
    """One Message-ID whose copies in one newsgroup never agree on a body across archives."""

    newsgroup: str
    message_id_hash: str
    # One message row id per distinct body per archive, so the bodies of a
    # conflict can be looked up without touching redundant identical copies.
    row_ids_per_archive: dict[str, list[int]] = field(default_factory=dict)


def _fetch_rows_by_message_id_hash(
    connection: sqlite3.Connection,
) -> dict[str, list[tuple[str, str, str | None]]]:
    """Map each hashed message id to its (archive, newsgroup, body_hash) rows."""
    rows_by_message_id_hash: dict[str, list[tuple[str, str, str | None]]] = defaultdict(
        list
    )
    for message_id_hash, archive, newsgroup, body_hash in connection.execute(
        "SELECT message_id_hash, archive, newsgroup, body_hash FROM messages"
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

    Sorted by (archive, message_id_hash).
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
    common, so an id whose copies match on one version is not a conflict even
    where one archive also holds an extra variant. Sorted by message_id_hash.
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


def find_newsgroup_body_conflicts(
    connection: sqlite3.Connection,
) -> list[NewsgroupBodyConflict]:
    """Find, per newsgroup, message ids whose copies in the two archives never share a body.

    The per-newsgroup counterpart of `find_across_archive_conflicts`, with the
    same definition of a conflict. Each conflict carries one message row id per
    distinct body per archive. Sorted by (newsgroup, message_id_hash).
    """
    rows = connection.execute(
        "SELECT newsgroup, message_id_hash, archive, body_hash, MIN(id)"
        " FROM messages"
        " GROUP BY newsgroup, message_id_hash, archive, body_hash"
        " ORDER BY newsgroup, message_id_hash, archive, body_hash"
    )

    conflicts = []
    for (newsgroup, message_id_hash), id_rows in groupby(rows, key=itemgetter(0, 1)):
        hashes_by_archive: dict[str, set[str | None]] = defaultdict(set)
        row_ids_by_archive: dict[str, list[int]] = defaultdict(list)
        for _, _, archive, body_hash, row_id in id_rows:
            hashes_by_archive[archive].add(body_hash)
            row_ids_by_archive[archive].append(row_id)

        if len(hashes_by_archive) < 2:
            continue
        if set.intersection(*hashes_by_archive.values()):
            continue

        conflicts.append(
            NewsgroupBodyConflict(
                newsgroup=newsgroup,
                message_id_hash=message_id_hash,
                row_ids_per_archive=dict(sorted(row_ids_by_archive.items())),
            )
        )

    return conflicts


def load_conflicts_and_id_spans(
    connection: sqlite3.Connection,
) -> tuple[list[NewsgroupBodyConflict], dict[tuple[str, str], tuple[int, int]]]:
    """Read the body conflicts together with the id spans that place their row ids.

    Bundled so the mbox-reading side (`usenet_no.replacement_chars.pairs`) needs
    no connection of its own.
    """
    conflicts = find_newsgroup_body_conflicts(connection)
    id_spans = load_id_spans(connection)
    logger.info("Found %d body conflicts", len(conflicts))
    return conflicts, id_spans
