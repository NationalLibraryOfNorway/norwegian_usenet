import numpy as np

from usenet_no.topic_modelling import count_documents_per_source


def test_each_source_is_counted_on_its_own_and_summed():
    topics = np.array([0, 0, 0, 1])
    sources = ["nb", "ia", "ia", "nb"]
    assert count_documents_per_source(topics, sources) == [
        {
            "topic_id": 0,
            "nb_message_count": 1,
            "ia_message_count": 2,
            "total_message_count": 3,
        },
        {
            "topic_id": 1,
            "nb_message_count": 1,
            "ia_message_count": 0,
            "total_message_count": 1,
        },
    ]


def test_topics_come_out_sorted_by_id_with_the_outliers_first():
    topics = np.array([2, -1, 0])
    sources = ["nb", "nb", "ia"]
    rows = count_documents_per_source(topics, sources)
    assert [row["topic_id"] for row in rows] == [-1, 0, 2]


def test_a_topic_no_document_was_assigned_to_gets_no_row():
    rows = count_documents_per_source(np.array([0, 0]), ["nb", "ia"])
    assert [row["topic_id"] for row in rows] == [0]
