from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.comparison import (
    VennCounts,
    count_message_id_overlap_in_shared_newsgroups,
)

SPAN = ("1996-01-06", "1996-01-20")


def test_leaves_out_the_ids_of_a_newsgroup_only_one_archive_has(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.shared.group.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.ia.only.group.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.shared.group.mbox", NB_ARCHIVE),
        ],
    )

    # <only.in.ia.group> goes with its group, while <crossposted> stays through
    # no.shared.group and counts once despite being in the dropped group too
    assert count_message_id_overlap_in_shared_newsgroups(connection) == VennCounts(
        nb_only=1, ia_only=1, both=1
    )


def test_no_shared_newsgroups_leaves_nothing_to_count(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.ia.only.group.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.id.overlap.mbox", NB_ARCHIVE),
        ],
    )

    assert count_message_id_overlap_in_shared_newsgroups(connection) == VennCounts(
        nb_only=0, ia_only=0, both=0
    )


def test_date_filtering_restricts_ia_but_not_nb(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.dated.ids.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.dated.ids.mbox", NB_ARCHIVE),
        ],
    )

    assert count_message_id_overlap_in_shared_newsgroups(connection) == VennCounts(
        nb_only=2, ia_only=2, both=0
    )
    # IA keeps the id inside the span, so no.dated.ids is still shared
    assert count_message_id_overlap_in_shared_newsgroups(
        connection, ia_date_span=SPAN
    ) == VennCounts(nb_only=2, ia_only=1, both=0)


def test_the_temporary_table_is_dropped_so_the_count_can_be_repeated(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.shared.group.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.shared.group.mbox", NB_ARCHIVE),
        ],
    )

    assert count_message_id_overlap_in_shared_newsgroups(
        connection
    ) == count_message_id_overlap_in_shared_newsgroups(connection)
