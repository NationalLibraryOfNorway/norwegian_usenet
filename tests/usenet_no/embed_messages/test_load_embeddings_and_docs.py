import numpy as np
import pytest

from usenet_no.embed_messages import load_embeddings_and_docs

MBOX = """\
From sender@example.com
Message-ID: <first@example.no>

first body

From sender@example.com
Message-ID: <second@example.no>

second body
"""

NEWSGROUPS = ("no.bil", "no.musikk")


@pytest.fixture
def dirs(tmp_path):
    """Two newsgroups embedded from both archives, two messages in each."""
    embeddings_dir = tmp_path / "embeddings"
    embeddings_dir.mkdir()
    directories = {"ia": tmp_path / "ia", "nb": tmp_path / "nb"}

    for source, directory in directories.items():
        directory.mkdir()
        for newsgroup in NEWSGROUPS:
            (directory / f"{newsgroup}.mbox").write_text(MBOX)
            np.save(embeddings_dir / f"{newsgroup}_{source}.npy", np.zeros((2, 3)))

    return embeddings_dir, directories["ia"], directories["nb"]


@pytest.mark.parametrize(
    ("sources", "expected_stems"),
    [
        (("nb",), ["no.bil_nb"]),
        (("ia",), ["no.bil_ia"]),
        (("nb", "ia"), ["no.bil_ia", "no.bil_nb"]),
    ],
)
def test_loads_the_requested_sources_only(dirs, sources, expected_stems):
    embeddings, stems, docs = load_embeddings_and_docs(
        *dirs, selection=["no.bil"], sources=sources
    )

    # Two messages per file, so every stem is loaded once per message.
    assert sorted(set(stems)) == sorted(expected_stems)
    assert len(embeddings) == len(docs) == 2 * len(expected_stems)


def test_a_newsgroup_outside_the_selection_is_left_out(dirs):
    _, stems, _ = load_embeddings_and_docs(
        *dirs, selection=["no.bil"], sources=("nb", "ia")
    )

    assert not any(stem.startswith("no.musikk") for stem in stems)
