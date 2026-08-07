import numpy as np

from usenet_no.topic_modelling import count_documents_per_source

WORDS = {0: ["bok", "leser"], 1: ["bil", "motor"], 2: ["hund"], -1: ["og", "det"]}


def test_each_source_is_counted_on_its_own_and_summed():
    topics = np.array([0, 0, 0, 1])
    sources = ["nb", "ia", "ia", "nb"]
    assert count_documents_per_source(topics, sources, WORDS) == [
        {
            "topic_id": 0,
            "words": ["bok", "leser"],
            "nb_message_count": 1,
            "ia_message_count": 2,
            "total_message_count": 3,
        },
        {
            "topic_id": 1,
            "words": ["bil", "motor"],
            "nb_message_count": 1,
            "ia_message_count": 0,
            "total_message_count": 1,
        },
    ]


def test_topics_come_out_sorted_by_id_with_the_outliers_first():
    topics = np.array([2, -1, 0])
    sources = ["nb", "nb", "ia"]
    rows = count_documents_per_source(topics, sources, WORDS)
    assert [row["topic_id"] for row in rows] == [-1, 0, 2]


def test_a_topic_no_document_was_assigned_to_gets_no_row():
    rows = count_documents_per_source(np.array([0, 0]), ["nb", "ia"], WORDS)
    assert [row["topic_id"] for row in rows] == [0]


def test_a_topic_the_table_has_no_words_for_still_gets_its_counts():
    rows = count_documents_per_source(np.array([7]), ["nb"], WORDS)
    assert rows == [
        {
            "topic_id": 7,
            "words": [],
            "nb_message_count": 1,
            "ia_message_count": 0,
            "total_message_count": 1,
        }
    ]
