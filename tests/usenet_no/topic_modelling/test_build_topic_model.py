import numpy as np
import pytest
from sklearn.manifold import TSNE
from turftopic import GMM, S3, ClusteringTopicModel, SensTopic, Topeax
from turftopic.encoders import ExternalEncoder

from usenet_no.topic_modelling import METHODS, REDUCING_METHODS, build_topic_model


class StubEncoder(ExternalEncoder):
    """Stands in for a named encoder, which turftopic would load on construction."""

    def encode(self, sentences):
        return np.zeros((len(list(sentences)), 8))


def build(method, nr_topics=None, **kwargs):
    return build_topic_model(method, nr_topics, encoder=StubEncoder(), **kwargs)


@pytest.mark.parametrize(
    "method,nr_topics,expected",
    [
        ("senstopic", None, SensTopic),
        ("s3", 10, S3),
        ("gmm", None, GMM),
        ("topeax", None, Topeax),
        ("clustering", None, ClusteringTopicModel),
    ],
)
def test_every_method_builds_its_own_turftopic_model(method, nr_topics, expected):
    assert isinstance(build(method, nr_topics), expected)


def test_an_unknown_method_is_rejected():
    with pytest.raises(ValueError, match="Unknown method"):
        build("bertopic")


def test_leaving_out_the_number_of_topics_lets_the_methods_that_can_pick_it_themselves():
    assert build("senstopic").n_components == "auto"
    assert build("gmm").n_components == "auto"


def test_the_methods_that_cannot_pick_the_number_of_topics_demand_one():
    with pytest.raises(ValueError, match="set --nr-topics"):
        build("s3")
    with pytest.raises(ValueError, match="set --nr-topics"):
        build("keynmf")


def test_topeax_always_picks_the_number_of_topics_so_passing_one_is_an_error():
    with pytest.raises(ValueError, match="drop --nr-topics"):
        build("topeax", 10)


def test_a_number_of_topics_reduces_the_clusters_of_a_clustering_run_after_fitting():
    assert build("clustering", 10).n_reduce_to == 10
    assert build("clustering").n_reduce_to is None


def test_terms_below_the_document_frequency_cutoff_are_left_out_of_the_descriptions():
    assert build("gmm", min_df=25).vectorizer.min_df == 25


@pytest.mark.parametrize("method", METHODS)
def test_the_reducing_methods_are_the_ones_that_come_with_a_t_sne(method):
    nr_topics = 10 if method in ("s3", "keynmf") else None
    reduction = getattr(build(method, nr_topics), "dimensionality_reduction", None)
    if method in REDUCING_METHODS:
        assert isinstance(reduction, TSNE)
        assert reduction.n_components == 2
    else:
        assert reduction is None
