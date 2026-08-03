from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.comparison import VennCounts, count_newsgroup_overlap

SPAN = ("1996-01-06", "1996-01-20")


def test_counts_a_newsgroup_both_archives_have_as_shared(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.id.overlap.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.id.overlap.mbox", NB_ARCHIVE),
        ],
    )

    assert count_newsgroup_overlap(connection) == VennCounts(
        nb_only=0, ia_only=0, both=1
    )


def test_counts_a_newsgroup_one_archive_has_on_that_side_alone(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.id.overlap.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.ia.only.group.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.id.overlap.mbox", NB_ARCHIVE),
        ],
    )

    assert count_newsgroup_overlap(connection) == VennCounts(
        nb_only=0, ia_only=1, both=1
    )


def test_date_filtering_drops_a_group_whose_ia_messages_all_fall_outside_the_span(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.dates.around.span.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.one.dated.message.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.id.overlap.mbox", NB_ARCHIVE),
        ],
    )

    # no.one.dated.message is dated 1996-01-01, before the span starts
    assert count_newsgroup_overlap(connection, ia_date_span=SPAN) == VennCounts(
        nb_only=1, ia_only=1, both=0
    )


def test_date_filtering_leaves_nb_alone(mbox_data, database, load_archives):
    connection = load_archives(
        database, [(mbox_data / "nb/no.dated.ids.mbox", NB_ARCHIVE)]
    )

    # One NB message falls outside the span, but its group is still counted
    assert count_newsgroup_overlap(connection, ia_date_span=SPAN) == VennCounts(
        nb_only=1, ia_only=0, both=0
    )
