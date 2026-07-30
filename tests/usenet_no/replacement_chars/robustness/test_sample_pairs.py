from collections import Counter

import pytest

from usenet_no.replacement_chars.robustness import sample_pairs


@pytest.fixture
def uneven_pairs(make_pair):
    """Three newsgroups holding 10, 5 and 1 pairs."""
    sizes = {"no.large": 10, "no.medium": 5, "no.tiny": 1}
    return [
        make_pair(index, newsgroup=newsgroup, message_id_hash=f"{newsgroup}-{index}")
        for newsgroup, size in sizes.items()
        for index in range(size)
    ]


def test_samples_the_asked_for_number(pairs):
    assert len(sample_pairs(pairs, max_pairs=5, seed=42)) == 5


def test_sample_holds_no_pair_twice(uneven_pairs):
    sampled = sample_pairs(uneven_pairs, max_pairs=9, seed=42)

    assert len({pair.message_id_hash for pair in sampled}) == 9


def test_sample_keeps_the_input_order(pairs):
    sampled = sample_pairs(pairs, max_pairs=5, seed=42)

    assert sampled == sorted(sampled, key=pairs.index)


def test_newsgroups_contribute_as_evenly_as_they_can(uneven_pairs):
    # Nine pairs over newsgroups holding 10, 5 and 1: the small one gives what
    # it has and the rest is split evenly, rather than 9 coming from the largest
    sampled = sample_pairs(uneven_pairs, max_pairs=9, seed=42)

    assert Counter(pair.newsgroup for pair in sampled) == {
        "no.large": 4,
        "no.medium": 4,
        "no.tiny": 1,
    }


def test_every_newsgroup_is_represented(uneven_pairs):
    sampled = sample_pairs(uneven_pairs, max_pairs=3, seed=42)

    assert {pair.newsgroup for pair in sampled} == {
        "no.large",
        "no.medium",
        "no.tiny",
    }


def test_which_pairs_a_newsgroup_gives_is_not_its_first_ones(uneven_pairs):
    samples = {
        tuple(pair.message_id_hash for pair in sample_pairs(uneven_pairs, 6, seed))
        for seed in range(20)
    }

    assert len(samples) > 1


def test_same_seed_gives_the_same_sample(uneven_pairs):
    assert sample_pairs(uneven_pairs, max_pairs=6, seed=7) == sample_pairs(
        uneven_pairs, max_pairs=6, seed=7
    )


def test_fewer_pairs_than_asked_for_are_all_kept(pairs):
    assert sample_pairs(pairs, max_pairs=100, seed=42) == pairs


def test_zero_keeps_every_pair(pairs):
    assert sample_pairs(pairs, max_pairs=0, seed=42) == pairs


def test_no_pairs_at_all():
    assert sample_pairs([], max_pairs=5, seed=42) == []
