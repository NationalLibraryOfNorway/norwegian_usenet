"""The pair table, over (user, newsgroup) pairs written out by hand.

Every case goes through build_user_newsgroup_matrix, since the labels it returns
are what pairwise_jaccard reports the pairs by.
"""

from usenet_no.database.overlap import build_user_newsgroup_matrix, pairwise_jaccard


def jaccard_for(newsgroups_per_user, **kwargs):
    matrix, _users, newsgroups = build_user_newsgroup_matrix(newsgroups_per_user)
    return pairwise_jaccard(matrix, newsgroups, **kwargs)


def test_groups_with_the_same_users_overlap_completely():
    pairs = jaccard_for(
        [
            ("kari", "no.first"),
            ("kari", "no.second"),
            ("ola", "no.first"),
            ("ola", "no.second"),
        ]
    )

    assert pairs == [("no.first", "no.second", 2, 2, 2, 1.0)]


def test_groups_sharing_no_users_are_left_out():
    pairs = jaccard_for([("kari", "no.first"), ("ola", "no.second")])

    assert pairs == []


def test_partial_overlap_is_the_shared_users_over_the_union():
    pairs = jaccard_for(
        [
            ("kari", "no.first"),
            ("ola", "no.first"),
            ("ola", "no.second"),
            ("per", "no.second"),
        ]
    )

    assert pairs == [("no.first", "no.second", 2, 2, 1, 1 / 3)]


def test_pairs_come_back_sorted_by_descending_overlap():
    pairs = jaccard_for(
        [
            ("kari", "no.first"),
            ("kari", "no.second"),
            ("kari", "no.third"),
            ("ola", "no.first"),
            ("ola", "no.second"),
        ]
    )

    assert [pair.jaccard for pair in pairs] == sorted(
        (pair.jaccard for pair in pairs), reverse=True
    )
    assert pairs[0][:2] == ("no.first", "no.second")
