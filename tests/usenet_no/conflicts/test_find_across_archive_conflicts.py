from usenet_no.conflicts import (
    find_across_archive_conflicts,
    find_within_archive_conflicts,
)
from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.hash import make_hash


def test_finds_conflict_across_archives(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.across.archives.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.across.archives.mbox", NB_ARCHIVE),
        ],
    )

    (conflict,) = find_across_archive_conflicts(connection)

    assert conflict.message_id_hash == make_hash("<a@example.no>")
    assert conflict.num_distinct_bodies == 2
    assert conflict.newsgroups_per_archive == {
        "ia": ["no.across.archives"],
        "nb": ["no.across.archives"],
    }


def test_identical_message_in_both_archives_is_not_a_conflict(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.identical.across.archives.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.identical.across.archives.mbox", NB_ARCHIVE),
        ],
    )

    assert find_across_archive_conflicts(connection) == []


def test_one_shared_body_means_archives_do_not_conflict(
    mbox_data, database, load_archives
):
    """IA holds an extra variant, but both archives still share a version."""
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.shared.body.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.shared.body.variant.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.shared.body.mbox", NB_ARCHIVE),
        ],
    )

    # IA disagrees with itself, but the archives share a body
    assert len(find_within_archive_conflicts(connection)) == 1
    assert find_across_archive_conflicts(connection) == []
