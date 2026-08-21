"""User overlap between newsgroups, from the message databases built in step 02.

A user is one `users.email_hash`. The `users` table holds one row per (name,
email) pair, so a person who spelled their name two ways has several ids there,
and a person who posted in both archives has one in each database; grouping on
the hashed email instead keeps them a single user. The plain address is never
read, so everything here can be published as it is.

Who posted where is collected as a one-hot user x newsgroup matrix, which the
Jaccard step reduces to one row per pair of newsgroups.
"""

import logging
import sqlite3
from typing import NamedTuple

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

from usenet_no.database.core import MESSAGES_WITH_SENDER, date_span_clause

logger = logging.getLogger(__name__)

# One (archive, date span) pair to read messages from; the span is None for the
# whole archive. A list of these is what lets an archive and another archive's
# date-restricted slice be read as one body of messages.
ArchiveDatespan = tuple[str, tuple[str, str] | None]


class NewsgroupOverlap(NamedTuple):
    """One pair of newsgroups and how many users they have in common.

    The field names are the pair table's CSV column names.
    """

    newsgroup_a: str
    newsgroup_b: str
    users_a: int
    users_b: int
    shared_users: int
    jaccard: float


def find_newsgroups_per_user(
    connection: sqlite3.Connection, archive_datespans: list[ArchiveDatespan]
) -> list[tuple[str, str]]:
    """Find every newsgroup each user posted in, over one or more archives.

    Returns one (email_hash, newsgroup) pair per newsgroup a user posted in.
    Senders with no email_hash (no sender at all, or a From header carrying no
    address) are left out. A newsgroup of the same name in two archives is one
    newsgroup here. Sorted by (email_hash, newsgroup).
    """
    conditions = []
    parameters: list[str] = []
    for archive, date_span in archive_datespans:
        clause, span_parameters = date_span_clause(date_span, column="messages.date")
        conditions.append(f"(messages.archive = ?{clause})")
        parameters.extend((archive, *span_parameters))

    return list(
        connection.execute(
            "SELECT DISTINCT users.email_hash, messages.newsgroup"
            f" FROM {MESSAGES_WITH_SENDER}"
            f" WHERE ({' OR '.join(conditions)}) AND users.email_hash IS NOT NULL"
            " ORDER BY users.email_hash, messages.newsgroup",
            parameters,
        )
    )


def build_user_newsgroup_matrix(
    newsgroups_per_user: list[tuple[str, str]],
) -> tuple[csr_matrix, list[str], list[str]]:
    """Lay (user, newsgroup) pairs out as a sparse users x newsgroups matrix.

    Cells are one where the user posted in the newsgroup. Returns the matrix
    with its row and column labels: hashed emails and newsgroup names, both
    sorted.
    """
    users = sorted({email_hash for email_hash, _group in newsgroups_per_user})
    newsgroups = sorted({group for _email_hash, group in newsgroups_per_user})
    user_indices = {email_hash: index for index, email_hash in enumerate(users)}
    group_indices = {group: index for index, group in enumerate(newsgroups)}

    # coo_matrix adds up any values landing on the same cell, so a cell stays a
    # one only as long as the pairs are distinct, which the query above makes
    # them.
    matrix = coo_matrix(
        (
            np.ones(len(newsgroups_per_user), dtype=np.int64),
            (
                [
                    user_indices[email_hash]
                    for email_hash, _group in newsgroups_per_user
                ],
                [group_indices[group] for _email_hash, group in newsgroups_per_user],
            ),
        ),
        shape=(len(users), len(newsgroups)),
        dtype=np.int64,
    ).tocsr()

    logger.info(
        "Built a %d user x %d newsgroup matrix from %d (user, newsgroup) pairs",
        len(users),
        len(newsgroups),
        len(newsgroups_per_user),
    )
    return matrix, users, newsgroups


def pairwise_jaccard(
    matrix: csr_matrix, newsgroups: list[str]
) -> list[NewsgroupOverlap]:
    """Jaccard overlap between the user sets of every pair of newsgroups.

    Takes the matrix and labels from build_user_newsgroup_matrix: the score is
    |A and B| / |A or B| over the two newsgroups' sets of users. One
    NewsgroupOverlap per pair, sorted by descending overlap, then by name.
    """
    # Every intersection at once. matrix.T is newsgroups x users, so the product is
    # newsgroups x newsgroups, and each cell (i, j) is the number of users
    # that posted in both newsgroup i and newsgroup j.
    intersections = np.asarray((matrix.T @ matrix).todense())

    # The diagonal: how many users posted in both newsgroup i and newsgroup i,
    # which is just how many users posted in the newsgroup on index i.
    user_count_per_newsgroup = intersections.diagonal()

    overlap_info = []
    for index_a in range(len(newsgroups)):
        # Each pair is visited once, in the upper triangle: the matrix is
        # symmetric, and a newsgroup's overlap with itself is not a pair.
        for index_b in range(index_a + 1, len(newsgroups)):
            shared_users = int(intersections[index_a, index_b])
            if shared_users < 1:  # jaccard overlap is 0 if no shared users
                continue
            users_a = int(user_count_per_newsgroup[index_a])
            users_b = int(user_count_per_newsgroup[index_b])

            # |A or B|: the two sets added up, less the users counted twice.
            union = users_a + users_b - shared_users
            overlap_info.append(
                NewsgroupOverlap(
                    newsgroup_a=newsgroups[index_a],
                    newsgroup_b=newsgroups[index_b],
                    users_a=users_a,
                    users_b=users_b,
                    shared_users=shared_users,
                    jaccard=shared_users / union,
                )
            )

    overlap_info.sort(
        key=lambda pair: (-pair.jaccard, pair.newsgroup_a, pair.newsgroup_b)
    )
    return overlap_info
