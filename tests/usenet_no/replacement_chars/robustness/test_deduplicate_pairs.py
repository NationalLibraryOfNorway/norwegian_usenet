from collections import Counter

from usenet_no.replacement_chars.robustness import deduplicate_pairs


def test_a_crossposted_message_is_kept_once(make_pair):
    crossposted = [
        make_pair(0, newsgroup="no.big", message_id_hash="crossposted"),
        make_pair(0, newsgroup="no.small", message_id_hash="crossposted"),
    ]

    assert len(deduplicate_pairs(crossposted)) == 1


def test_the_copy_from_the_smallest_newsgroup_is_the_one_kept(make_pair):
    pairs = [
        make_pair(index, newsgroup="no.big", message_id_hash=f"hash-{index}")
        for index in range(5)
    ] + [make_pair(0, newsgroup="no.small", message_id_hash="hash-0")]

    kept = {pair.message_id_hash: pair.newsgroup for pair in deduplicate_pairs(pairs)}

    assert kept["hash-0"] == "no.small"
    assert kept["hash-1"] == "no.big"


def test_newsgroup_size_counts_every_pair_not_just_the_kept_ones(make_pair):
    # no.medium holds three pairs, all of them crossposted to no.big, which
    # holds four. The count that decides is the one before deduplication, so
    # every crosspost goes to no.medium even though that leaves no.big with one
    pairs = [
        make_pair(index, newsgroup="no.big", message_id_hash=f"hash-{index}")
        for index in range(4)
    ] + [
        make_pair(index, newsgroup="no.medium", message_id_hash=f"hash-{index}")
        for index in range(3)
    ]

    per_newsgroup = Counter(pair.newsgroup for pair in deduplicate_pairs(pairs))

    assert per_newsgroup == {"no.medium": 3, "no.big": 1}


def test_equally_large_newsgroups_are_ordered_by_name(make_pair):
    crossposted = [
        make_pair(0, newsgroup="no.zulu", message_id_hash="crossposted"),
        make_pair(0, newsgroup="no.alpha", message_id_hash="crossposted"),
    ]

    (kept,) = deduplicate_pairs(crossposted)

    assert kept.newsgroup == "no.alpha"


def test_the_order_the_pairs_arrive_in_does_not_decide(make_pair):
    crossposted = [
        make_pair(0, newsgroup="no.zulu", message_id_hash="crossposted"),
        make_pair(0, newsgroup="no.alpha", message_id_hash="crossposted"),
    ]

    assert deduplicate_pairs(crossposted) == deduplicate_pairs(crossposted[::-1])


def test_pairs_with_distinct_ids_are_all_kept(pairs):
    assert deduplicate_pairs(pairs) == sorted(pairs, key=lambda pair: pair.newsgroup)


def test_result_is_sorted_by_newsgroup_and_message_id(make_pair):
    pairs = [
        make_pair(0, newsgroup="no.zulu", message_id_hash="hash-b"),
        make_pair(1, newsgroup="no.alpha", message_id_hash="hash-c"),
        make_pair(2, newsgroup="no.alpha", message_id_hash="hash-a"),
    ]

    assert [
        (pair.newsgroup, pair.message_id_hash) for pair in deduplicate_pairs(pairs)
    ] == [("no.alpha", "hash-a"), ("no.alpha", "hash-c"), ("no.zulu", "hash-b")]


def test_no_pairs_deduplicate_to_nothing():
    assert deduplicate_pairs([]) == []
