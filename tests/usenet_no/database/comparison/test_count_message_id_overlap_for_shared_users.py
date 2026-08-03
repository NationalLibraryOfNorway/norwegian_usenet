from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.comparison import (
    VennCounts,
    count_message_id_overlap_for_shared_users,
)

SPAN = ("1996-01-06", "1996-01-20")


def test_leaves_out_the_messages_of_a_user_only_one_archive_has(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.shared.senders.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.shared.senders.mbox", NB_ARCHIVE),
        ],
    )

    # Only k@example.no posted in both archives, so the messages of
    # o@example.no and n@example.no are dropped
    assert count_message_id_overlap_for_shared_users(connection) == VennCounts(
        nb_only=1, ia_only=1, both=1
    )


def test_messages_without_a_sender_are_left_out(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.shared.senders.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.id.without.sender.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.shared.senders.mbox", NB_ARCHIVE),
        ],
    )

    assert count_message_id_overlap_for_shared_users(connection) == VennCounts(
        nb_only=1, ia_only=1, both=1
    )


def test_no_shared_users_leaves_nothing_to_count(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.with.references.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.shared.senders.mbox", NB_ARCHIVE),
        ],
    )

    assert count_message_id_overlap_for_shared_users(connection) == VennCounts(
        nb_only=0, ia_only=0, both=0
    )


def test_date_filtering_decides_which_users_are_shared(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.shared.senders.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.shared.senders.mbox", NB_ARCHIVE),
        ],
    )

    # The IA messages carry no date, so the span drops every IA sender and
    # leaves no user the two archives have in common
    assert count_message_id_overlap_for_shared_users(
        connection, ia_date_span=SPAN
    ) == VennCounts(nb_only=0, ia_only=0, both=0)


def test_the_temporary_table_is_dropped_so_the_count_can_be_repeated(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.shared.senders.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.shared.senders.mbox", NB_ARCHIVE),
        ],
    )

    assert count_message_id_overlap_for_shared_users(
        connection
    ) == count_message_id_overlap_for_shared_users(connection)
