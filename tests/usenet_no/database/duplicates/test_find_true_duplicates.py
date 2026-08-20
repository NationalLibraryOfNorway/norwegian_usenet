from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.duplicates import find_true_duplicates
from usenet_no.hash import make_hash


def test_counts_every_copy_of_a_repeated_message(mbox_data, database, load_archives):
    connection = load_archives(
        database, [(mbox_data / "nb/no.repeated.message.mbox", NB_ARCHIVE)]
    )

    (duplicate,) = find_true_duplicates(connection)

    # Both copies are counted, not just the redundant one
    assert duplicate.count == 2
    assert duplicate.message_id_hash == make_hash("<a@example.no>")
    assert duplicate.archive == NB_ARCHIVE
    assert duplicate.newsgroup == "no.repeated.message"


def test_same_id_different_body_is_not_a_true_duplicate(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database, [(mbox_data / "nb/no.same.id.different.body.mbox", NB_ARCHIVE)]
    )

    assert find_true_duplicates(connection) == []


def test_reports_one_row_per_duplicated_message_id(mbox_data, database, load_archives):
    connection = load_archives(
        database, [(mbox_data / "ia/no.many.duplicates.mbox", IA_ARCHIVE)]
    )

    duplicates = find_true_duplicates(connection)

    # Sorted by hashed message id, and the unique message is absent
    assert [(d.message_id_hash, d.count) for d in duplicates] == sorted(
        [(make_hash("<a@example.no>"), 2), (make_hash("<b@example.no>"), 3)]
    )


def test_identical_copies_in_different_archives_are_not_duplicates(
    mbox_data, database, load_archives
):
    """Both archives hold the same message (same id, same body); a true
    duplicate is a repeat within one mbox file, not across archives."""
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.identical.across.archives.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.identical.across.archives.mbox", NB_ARCHIVE),
        ],
    )

    assert find_true_duplicates(connection) == []
