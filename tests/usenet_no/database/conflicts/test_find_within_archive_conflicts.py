from usenet_no.database.conflicts import find_within_archive_conflicts
from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.hash import make_hash


def test_finds_conflict_within_one_archive_across_newsgroups(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.conflict.first.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.conflict.second.mbox", IA_ARCHIVE),
        ],
    )

    (conflict,) = find_within_archive_conflicts(connection)

    assert conflict.archive == IA_ARCHIVE
    assert conflict.message_id_hash == make_hash("<a@example.no>")
    assert conflict.num_distinct_bodies == 2
    assert conflict.newsgroups == ["no.conflict.first", "no.conflict.second"]


def test_disagreement_between_archives_is_not_a_within_archive_conflict(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.across.archives.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.across.archives.mbox", NB_ARCHIVE),
        ],
    )

    assert find_within_archive_conflicts(connection) == []


def test_conflict_order_is_stable_across_runs(mbox_data, database, load_archives):
    """Output ordering must not depend on dict or set iteration order."""
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.many.conflicts.a.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.many.conflicts.b.mbox", IA_ARCHIVE),
        ],
    )

    first_run = find_within_archive_conflicts(connection)
    second_run = find_within_archive_conflicts(connection)

    assert len(first_run) == 3
    assert first_run == second_run
    assert [conflict.message_id_hash for conflict in first_run] == sorted(
        conflict.message_id_hash for conflict in first_run
    )
