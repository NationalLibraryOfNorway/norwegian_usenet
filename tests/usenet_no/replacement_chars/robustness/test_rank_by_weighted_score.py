import pytest

from usenet_no.replacement_chars.robustness import (
    ModelRun,
    RobustnessSummary,
    SimilarityStatistics,
    rank_by_weighted_score,
    weighted_score,
)


def make_statistics(mean: float) -> SimilarityStatistics:
    return SimilarityStatistics(
        mean=mean, std=0.01, min=mean - 0.1, max=mean + 0.01, percentiles={}
    )


def make_run(model: str, matched_mean: float, shuffled_mean: float) -> ModelRun:
    return ModelRun(
        summary=RobustnessSummary(
            model=model,
            num_pairs=10,
            matched=make_statistics(matched_mean),
            shuffled=make_statistics(shuffled_mean),
        ),
        similarities=[],
    )


def test_the_score_is_the_matched_mean_less_the_shuffled_one():
    summary = make_run("model", 0.99, 0.55).summary

    assert weighted_score(summary) == pytest.approx(0.44)


def test_the_weights_scale_each_mean():
    summary = make_run("model", 0.9, 0.5).summary

    assert weighted_score(summary, 2.0, 0.5) == pytest.approx(2 * 0.9 - 0.5 * 0.5)


def test_a_shuffled_weight_of_zero_scores_the_matched_mean_alone():
    summary = make_run("model", 0.9, 0.5).summary

    assert weighted_score(summary, shuffled_weight=0.0) == pytest.approx(0.9)


def test_the_best_score_comes_first():
    runs = [
        make_run("close", 0.99, 0.90),
        make_run("separated", 0.95, 0.30),
        make_run("middling", 0.97, 0.60),
    ]

    ranking = rank_by_weighted_score(runs)

    assert [run.summary.model for run, _ in ranking] == [
        "separated",
        "middling",
        "close",
    ]


def test_each_run_comes_back_with_its_score():
    ranking = rank_by_weighted_score([make_run("model", 0.99, 0.55)])

    [(run, score)] = ranking
    assert run.summary.model == "model"
    assert score == pytest.approx(0.44)


def test_the_weights_decide_the_order():
    runs = [make_run("high-matched", 0.99, 0.90), make_run("low-shuffled", 0.95, 0.30)]

    # Ignoring the shuffled baseline ranks the higher matched mean first
    ranking = rank_by_weighted_score(runs, shuffled_weight=0.0)

    assert [run.summary.model for run, _ in ranking] == ["high-matched", "low-shuffled"]


def test_equal_scores_are_ordered_by_model_name():
    runs = [make_run("zeta", 0.9, 0.5), make_run("alpha", 0.9, 0.5)]

    ranking = rank_by_weighted_score(runs)

    assert [run.summary.model for run, _ in ranking] == ["alpha", "zeta"]


def test_nothing_to_rank_ranks_as_nothing():
    assert rank_by_weighted_score([]) == []
