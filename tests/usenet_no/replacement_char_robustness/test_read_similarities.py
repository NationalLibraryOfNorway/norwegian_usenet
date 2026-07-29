import pytest

from usenet_no.replacement_char_robustness import read_similarities

CSV_TEXT = """\
newsgroup,message_id_hash,replacement_char_count,nb_body_length,matched_similarity,shuffled_similarity
no.alkohol,hash-a,12,1843,0.5473,0.2201
no.bil,hash-b,1,97,0.9912,0.3010
"""


@pytest.fixture
def similarities_file(tmp_path):
    path = tmp_path / "similarities.csv"
    path.write_text(CSV_TEXT, encoding="utf-8")
    return path


def test_reads_every_row(similarities_file):
    assert len(read_similarities(similarities_file)) == 2


def test_reads_the_fields_with_their_types(similarities_file):
    first, _ = read_similarities(similarities_file)

    assert first.newsgroup == "no.alkohol"
    assert first.message_id_hash == "hash-a"
    assert first.replacement_char_count == 12
    assert first.nb_body_length == 1843
    assert first.matched_similarity == pytest.approx(0.5473)
    assert first.shuffled_similarity == pytest.approx(0.2201)


def test_a_file_with_only_a_header_reads_as_nothing(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text(CSV_TEXT.splitlines()[0] + "\n", encoding="utf-8")

    assert read_similarities(path) == []
