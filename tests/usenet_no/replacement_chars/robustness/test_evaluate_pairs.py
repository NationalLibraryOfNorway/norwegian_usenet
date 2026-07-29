"""evaluate_pairs is tested against a stand-in model rather than a real one, so
the expected similarities can be worked out by hand.

`AngleEncoder` places pair `i` at angle 2*pi*i/20 on the unit circle and turns
the damaged copy a further 0.1 radians, so every matched pair scores cos(0.1)
and any two different pairs are at least 2*pi/20 radians apart.
"""

import numpy as np
import pytest

from usenet_no.replacement_chars.robustness import evaluate_pairs
from usenet_no.replacement_chars import REPLACEMENT_CHAR

DAMAGE_ANGLE = 0.1
NUM_ANGLES = 20


class AngleEncoder:
    """A stand-in model embedding a body by the pair index its text carries."""

    def __init__(self):
        self.encode_calls = []

    def encode(self, bodies, **kwargs):
        self.encode_calls.append(kwargs)
        return np.array([self._vector(body) for body in bodies])

    def _vector(self, body):
        index = int(body.rsplit(" ", maxsplit=1)[-1])
        angle = 2 * np.pi * index / NUM_ANGLES
        if REPLACEMENT_CHAR in body:
            angle += DAMAGE_ANGLE
        return np.array([np.cos(angle), np.sin(angle)])


def test_matched_similarities_are_one_per_pair(pairs):
    _, matched, _ = evaluate_pairs(pairs, AngleEncoder(), model_name="test-model")

    assert matched == pytest.approx(np.full(len(pairs), np.cos(DAMAGE_ANGLE)))


def test_shuffled_similarities_score_below_the_matched_ones(pairs):
    _, matched, shuffled = evaluate_pairs(
        pairs, AngleEncoder(), model_name="test-model"
    )

    assert len(shuffled) == len(pairs)
    assert np.all(shuffled < matched)


def test_summary_describes_both_sets(pairs):
    summary, matched, shuffled = evaluate_pairs(
        pairs, AngleEncoder(), model_name="test-model"
    )

    assert summary.model == "test-model"
    assert summary.num_pairs == len(pairs)
    assert summary.matched.mean == pytest.approx(np.mean(matched))
    assert summary.shuffled.mean == pytest.approx(np.mean(shuffled))


def test_same_seed_gives_the_same_baseline(pairs):
    _, _, first = evaluate_pairs(pairs, AngleEncoder(), model_name="m", seed=7)
    _, _, second = evaluate_pairs(pairs, AngleEncoder(), model_name="m", seed=7)

    assert first == pytest.approx(second)


def test_encode_kwargs_reach_the_model(pairs):
    model = AngleEncoder()

    evaluate_pairs(
        pairs,
        model,
        model_name="test-model",
        batch_size=8,
        encode_kwargs={"task": "clustering"},
    )

    # One call for the NB side, one for the IA side
    assert (
        model.encode_calls
        == [{"batch_size": 8, "show_progress_bar": True, "task": "clustering"}] * 2
    )
