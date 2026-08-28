import numpy as np
import pytest

from usenet_no.embed_messages import load_newsgroup_centroids


@pytest.fixture
def embeddings_dir(tmp_path):
    """Two newsgroups embedded from both archives, with an index file beside each."""
    directory = tmp_path / "embeddings"
    directory.mkdir()
    for source, offset in (("nb", 0.0), ("ia", 10.0)):
        for newsgroup, scale in (("no.bil", 1.0), ("no.musikk", 2.0)):
            embeddings = np.array([[0.0, 1.0], [2.0, 3.0]]) * scale + offset
            np.save(directory / f"{newsgroup}_{source}.npy", embeddings)
            np.save(directory / f"{newsgroup}_{source}_index.npy", np.array([0, 1]))
    return directory


@pytest.mark.parametrize(
    ("sources", "expected_stems"),
    [
        (("nb",), ["no.bil_nb", "no.musikk_nb"]),
        (("ia",), ["no.bil_ia", "no.musikk_ia"]),
        (
            ("nb", "ia"),
            ["no.bil_ia", "no.bil_nb", "no.musikk_ia", "no.musikk_nb"],
        ),
    ],
)
def test_reads_one_centroid_per_file_of_the_sources(
    embeddings_dir, sources, expected_stems
):
    centroids, stems, message_counts = load_newsgroup_centroids(embeddings_dir, sources)

    assert stems == expected_stems
    assert centroids.shape == (len(expected_stems), 2)
    assert message_counts == [2] * len(expected_stems)


def test_centroid_is_the_mean_of_the_message_embeddings(embeddings_dir):
    centroids, stems, _ = load_newsgroup_centroids(embeddings_dir, ("nb",))

    np.testing.assert_allclose(centroids[stems.index("no.bil_nb")], [1.0, 2.0])
    np.testing.assert_allclose(centroids[stems.index("no.musikk_nb")], [2.0, 4.0])
