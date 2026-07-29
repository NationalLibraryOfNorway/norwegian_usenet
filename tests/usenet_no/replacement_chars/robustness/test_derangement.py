import numpy as np
import pytest

from usenet_no.replacement_chars.robustness import derangement

SIZES = [2, 3, 5, 50, 999]


@pytest.mark.parametrize("size", SIZES)
def test_is_a_permutation(size):
    assert sorted(derangement(size, seed=42)) == list(range(size))


@pytest.mark.parametrize("size", SIZES)
def test_leaves_no_index_in_place(size):
    permutation = derangement(size, seed=42)

    assert not np.any(permutation == np.arange(size))


def test_same_seed_gives_the_same_derangement():
    assert np.array_equal(derangement(20, seed=7), derangement(20, seed=7))


def test_different_seeds_give_different_derangements():
    assert not np.array_equal(derangement(20, seed=7), derangement(20, seed=8))


@pytest.mark.parametrize("size", [0, 1])
def test_too_few_elements_to_derange(size):
    with pytest.raises(ValueError, match="Cannot derange"):
        derangement(size, seed=42)
