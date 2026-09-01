"""User overlap between newsgroups, from the message databases built in step 02.

A user is one email address, which `messages.email_id` names.

Who posted where is collected as a one-hot user x newsgroup matrix, which the
Jaccard step reduces to one row per pair of newsgroups.
"""

import logging
import sqlite3
from typing import NamedTuple

import numpy as np
from scipy.sparse import coo_matrix, csr_matrix

from usenet_no.database.core import date_span_clause

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
    connection: sqlite3.Connection,
    archive: str,
    date_span: tuple[str, str] | None = None,
) -> list[tuple[int, str]]:
    """Find every newsgroup each user posted in, within one archive.

    Returns one (email_id, newsgroup) pair per newsgroup a user posted in, read
    from the archive's own file. Messages whose sender gave no address are left
    out. Sorted by (email_id, newsgroup).
    """
    clause, span_parameters = date_span_clause(date_span)
    return list(
        connection.execute(
            "SELECT DISTINCT email_id, newsgroup FROM messages"
            f" WHERE archive = ? AND email_id IS NOT NULL{clause}"
            " ORDER BY email_id, newsgroup",
            (archive, *span_parameters),
        )
    )


def build_user_newsgroup_matrix(
    newsgroups_per_user: list[tuple[int, str]],
) -> tuple[csr_matrix, list[int], list[str]]:
    """Lay (user, newsgroup) pairs out as a sparse users x newsgroups matrix.

    Cells are one where the user posted in the newsgroup. Returns the matrix
    with its row and column labels: users and newsgroup names, both sorted.
    """
    users = sorted({user for user, _group in newsgroups_per_user})
    newsgroups = sorted({group for _user, group in newsgroups_per_user})
    user_indices = {user: index for index, user in enumerate(users)}
    group_indices = {group: index for index, group in enumerate(newsgroups)}

    # coo_matrix adds up any values landing on the same cell, so a cell stays a
    # one only as long as the pairs are distinct, which the query above makes
    # them.
    matrix = coo_matrix(
        (
            np.ones(len(newsgroups_per_user), dtype=np.int64),
            (
                [user_indices[user] for user, _group in newsgroups_per_user],
                [group_indices[group] for _user, group in newsgroups_per_user],
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
