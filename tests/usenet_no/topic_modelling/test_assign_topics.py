import numpy as np

from usenet_no.topic_modelling import assign_topics


class ModelWithoutClasses:
    """A decomposition model, whose topic ids are the columns it scores."""


class ClusteringModel:
    """A clustering model, which numbers its topics and labels outliers -1."""

    def __init__(self, classes):
        self.classes_ = np.array(classes)


def test_a_document_gets_the_column_it_scores_highest_on():
    document_topic_matrix = np.array([[0.1, 0.9], [0.8, 0.2]])
    topics = assign_topics(ModelWithoutClasses(), document_topic_matrix)
    assert topics.tolist() == [1, 0]


def test_columns_are_read_through_the_classes_of_a_clustering_model():
    document_topic_matrix = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    topics = assign_topics(ClusteringModel([-1, 0, 1]), document_topic_matrix)
    assert topics.tolist() == [-1, 1]
