import math

import pytest

from usenet_no.replacement_chars.robustness import (
    PairSimilarity,
    correlate_with_similarity,
)

MEASURES = [
    "replacement char count",
    "body length",
    "damage density (chars per character)",
]


def make_row(count: int, length: int, score: float) -> PairSimilarity:
    return PairSimilarity(
        newsgroup="no.group",
        message_id_hash=f"hash-{count}-{length}",
        replacement_char_count=count,
        nb_body_length=length,
        matched_similarity=score,
        shuffled_similarity=0.2,
    )


def test_reports_all_three_measures():
    rows = [make_row(count, 100, 1.0 - count / 100) for count in range(1, 6)]

    assert list(correlate_with_similarity(rows)) == MEASURES


def test_a_measure_the_score_follows_exactly_correlates_perfectly():
    # At a fixed length, the score falls straight with the damage count
    rows = [make_row(count, 100, 1.0 - count / 100) for count in range(1, 6)]

    assert correlate_with_similarity(rows)["replacement char count"] == pytest.approx(
        -1.0
    )


def test_density_separates_from_count():
    # Every pair holds 10 replacement chars, so the count says nothing, but the
    # shorter the message the lower the score
    rows = [make_row(10, length, length / 1000) for length in (100, 200, 500, 1000)]

    correlations = correlate_with_similarity(rows)

    assert math.isnan(correlations["replacement char count"])
    assert correlations["damage density (chars per character)"] < 0


def test_a_measure_that_never_varies_correlates_with_nothing():
    rows = [make_row(3, 100, score) for score in (0.9, 0.95, 0.99)]

    assert math.isnan(correlate_with_similarity(rows)["replacement char count"])


def test_scores_that_never_vary_correlate_with_nothing():
    rows = [make_row(count, 100, 0.9) for count in (1, 2, 3)]

    assert math.isnan(correlate_with_similarity(rows)["body length"])


def test_a_single_pair_correlates_with_nothing():
    assert all(
        math.isnan(value)
        for value in correlate_with_similarity([make_row(3, 100, 0.9)]).values()
    )


def test_an_empty_body_leaves_the_density_undefined():
    rows = [make_row(count, 0, 1.0 - count / 100) for count in range(1, 6)]

    correlations = correlate_with_similarity(rows)

    assert math.isnan(correlations["damage density (chars per character)"])
    assert correlations["replacement char count"] == pytest.approx(-1.0)
