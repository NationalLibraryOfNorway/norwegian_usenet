import pandas as pd

from usenet_no.topic_modelling import make_topic_labels


def make_topic_info(rows):
    return pd.DataFrame(rows, columns=["Topic ID", "Highest Ranking"])


def test_a_label_holds_the_topic_id_and_its_top_terms():
    labels = make_topic_labels(make_topic_info([(0, "bil, motor, hjul")]))
    assert labels == {0: "Topic 0: bil, motor, hjul"}


def test_only_the_first_n_words_of_the_ranking_are_kept():
    labels = make_topic_labels(
        make_topic_info([(0, "bil, motor, hjul, ratt, bensin")]), n_words=2
    )
    assert labels == {0: "Topic 0: bil, motor"}


def test_the_outlier_topic_of_a_clustering_run_is_named_rather_than_described():
    labels = make_topic_labels(make_topic_info([(-1, "og, i, det"), (0, "bil, motor")]))
    assert labels[-1] == "outliers (-1)"
    assert labels[0] == "Topic 0: bil, motor"
