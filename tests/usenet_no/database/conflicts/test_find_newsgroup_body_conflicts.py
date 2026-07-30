from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.conflicts import find_newsgroup_body_conflicts
from usenet_no.hash import make_hash


def test_finds_conflicts_with_row_ids_per_archive(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.replacement.chars.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.replacement.chars.mbox", NB_ARCHIVE),
        ],
    )

    conflicts = find_newsgroup_body_conflicts(connection)

    # The identical message and the ia-only padding message are not conflicts
    assert [conflict.message_id_hash for conflict in conflicts] == sorted(
        make_hash(message_id)
        for message_id in (
            "<damaged@example.no>",
            "<damaged-and-rewritten@example.no>",
            "<rewritten@example.no>",
        )
    )
    assert all(conflict.newsgroup == "no.replacement.chars" for conflict in conflicts)

    # The ia file loads first as rows 1-5, the nb file as rows 6-9
    conflict_by_id_hash = {conflict.message_id_hash: conflict for conflict in conflicts}
    damaged = conflict_by_id_hash[make_hash("<damaged@example.no>")]
    assert damaged.row_ids_per_archive == {IA_ARCHIVE: [2], NB_ARCHIVE: [6]}


def test_one_shared_body_is_not_a_newsgroup_conflict(
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

    assert find_newsgroup_body_conflicts(connection) == []


def test_conflicts_are_counted_per_newsgroup(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.across.archives.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.replacement.chars.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.across.archives.mbox", NB_ARCHIVE),
            (mbox_data / "nb/no.replacement.chars.mbox", NB_ARCHIVE),
        ],
    )

    conflicts = find_newsgroup_body_conflicts(connection)

    newsgroups = [conflict.newsgroup for conflict in conflicts]
    assert newsgroups == sorted(newsgroups)
    assert newsgroups.count("no.across.archives") == 1
    assert newsgroups.count("no.replacement.chars") == 3
