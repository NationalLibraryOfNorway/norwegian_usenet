import numpy as np
import pytest

from usenet_no.replacement_chars.robustness import cosine_similarities


def test_identical_rows_score_one():
    embeddings = np.array([[1.0, 2.0, 3.0], [-1.0, 0.0, 4.0]])

    assert cosine_similarities(embeddings, embeddings) == pytest.approx([1.0, 1.0])


def test_similarity_ignores_length():
    left = np.array([[1.0, 0.0]])
    right = np.array([[7.0, 0.0]])

    assert cosine_similarities(left, right) == pytest.approx([1.0])


def test_orthogonal_and_opposite_rows():
    left = np.array([[1.0, 0.0], [1.0, 0.0]])
    right = np.array([[0.0, 1.0], [-1.0, 0.0]])

    assert cosine_similarities(left, right) == pytest.approx([0.0, -1.0])


def test_zero_vectors_are_undefined_rather_than_unrelated():
    left = np.array([[0.0, 0.0], [1.0, 0.0]])
    right = np.array([[1.0, 0.0], [1.0, 0.0]])

    similarities = cosine_similarities(left, right)

    assert np.isnan(similarities[0])
    assert similarities[1] == pytest.approx(1.0)


def test_mismatched_shapes_raise():
    with pytest.raises(ValueError, match="Embedding shapes differ"):
        cosine_similarities(np.zeros((2, 3)), np.zeros((3, 3)))
