import pandas as pd

from usenet_no.topic_modelling import make_topic_words


def make_topic_info(rows):
    return pd.DataFrame(rows, columns=["Topic ID", "Highest Ranking"])


def test_the_ranking_is_split_into_words_without_their_spacing():
    words = make_topic_words(make_topic_info([(0, "bil, motor, hjul")]))
    assert words == {0: ["bil", "motor", "hjul"]}


def test_only_the_first_n_words_of_the_ranking_are_kept():
    words = make_topic_words(
        make_topic_info([(0, "bil, motor, hjul, ratt")]), n_words=2
    )
    assert words == {0: ["bil", "motor"]}


def test_the_outlier_topic_is_described_like_any_other():
    words = make_topic_words(make_topic_info([(-1, "og, i"), (0, "bil, motor")]))
    assert words == {-1: ["og", "i"], 0: ["bil", "motor"]}
