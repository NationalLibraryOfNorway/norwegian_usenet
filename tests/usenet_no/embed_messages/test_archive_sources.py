import pytest

from usenet_no.embed_messages import ARCHIVE_CHOICES, archive_sources


@pytest.mark.parametrize("archive", ["nb", "ia"])
def test_one_archive_reads_its_own_source_only(archive):
    assert archive_sources(archive) == (archive,)


def test_both_reads_nb_before_ia():
    assert archive_sources("both") == ("nb", "ia")


@pytest.mark.parametrize("archive", ARCHIVE_CHOICES)
def test_every_choice_reads_at_least_one_source(archive):
    assert set(archive_sources(archive)) <= {"nb", "ia"}
    assert archive_sources(archive)
