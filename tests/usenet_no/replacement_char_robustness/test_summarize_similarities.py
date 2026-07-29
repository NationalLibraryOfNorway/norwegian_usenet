import numpy as np
import pytest

from usenet_no.replacement_char_robustness import PERCENTILES, summarize_similarities


def test_describes_the_distribution():
    statistics = summarize_similarities(np.array([0.0, 0.5, 1.0]))

    assert statistics.mean == pytest.approx(0.5)
    assert statistics.std == pytest.approx(np.std([0.0, 0.5, 1.0]))
    assert statistics.min == pytest.approx(0.0)
    assert statistics.max == pytest.approx(1.0)
    assert statistics.percentiles["p50"] == pytest.approx(0.5)


def test_reports_every_percentile():
    statistics = summarize_similarities(np.linspace(0.0, 1.0, 101))

    assert list(statistics.percentiles) == [
        f"p{percentile:02d}" for percentile in PERCENTILES
    ]


def test_undefined_similarities_are_left_out():
    statistics = summarize_similarities(np.array([0.2, np.nan, 0.4]))

    assert statistics.mean == pytest.approx(0.3)
    assert statistics.max == pytest.approx(0.4)
