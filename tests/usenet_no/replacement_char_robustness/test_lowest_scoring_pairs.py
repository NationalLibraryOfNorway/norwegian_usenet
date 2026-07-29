import pytest

from usenet_no.replacement_char_robustness import lowest_scoring_pairs

SCORES = [0.95, 0.42, 0.68, 0.55, 0.99]


@pytest.fixture
def similarities(make_similarity):
    return [make_similarity(index, score) for index, score in enumerate(SCORES)]


def test_worst_scoring_pair_comes_first(similarities, pairs):
    examples = lowest_scoring_pairs(similarities, pairs, num_examples=3, max_score=0.7)

    assert [similarity.matched_similarity for similarity, _ in examples] == [
        0.42,
        0.55,
        0.68,
    ]


def test_pairs_scoring_at_or_above_max_score_are_left_out(similarities, pairs):
    examples = lowest_scoring_pairs(
        similarities, pairs, num_examples=10, max_score=0.68
    )

    assert [similarity.matched_similarity for similarity, _ in examples] == [0.42, 0.55]


def test_no_more_than_num_examples_come_back(similarities, pairs):
    examples = lowest_scoring_pairs(similarities, pairs, num_examples=2, max_score=1.0)

    assert len(examples) == 2


def test_fewer_than_num_examples_when_few_score_that_low(similarities, pairs):
    examples = lowest_scoring_pairs(similarities, pairs, num_examples=20, max_score=0.5)

    assert len(examples) == 1


def test_each_row_is_paired_with_its_own_bodies(similarities, pairs):
    examples = lowest_scoring_pairs(similarities, pairs, num_examples=3, max_score=0.7)

    assert all(
        similarity.message_id_hash == pair.message_id_hash
        for similarity, pair in examples
    )


def test_rows_whose_pair_is_missing_are_skipped(similarities, pairs, caplog):
    # The pair that scored worst is not in the pairs file
    without_the_worst = [pair for pair in pairs if pair.message_id_hash != "hash-1"]

    examples = lowest_scoring_pairs(
        similarities, without_the_worst, num_examples=3, max_score=0.7
    )

    assert [similarity.matched_similarity for similarity, _ in examples] == [0.55, 0.68]
    assert "hash-1" in caplog.text


def test_nothing_scores_low_enough(similarities, pairs):
    assert (
        lowest_scoring_pairs(similarities, pairs, num_examples=3, max_score=0.1) == []
    )
