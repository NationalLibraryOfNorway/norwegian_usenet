from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.comparison import VennCounts, count_body_overlap

SPAN = ("1996-01-06", "1996-01-20")


def test_counts_a_body_both_archives_have_as_shared(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.identical.body.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.identical.body.mbox", NB_ARCHIVE),
        ],
    )

    assert count_body_overlap(connection) == VennCounts(nb_only=0, ia_only=0, both=1)


def test_a_crossposted_body_counts_once(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.shared.group.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.ia.only.group.mbox", IA_ARCHIVE),
        ],
    )

    # Three distinct bodies over four rows: the crossposted one is in both groups
    assert count_body_overlap(connection) == VennCounts(nb_only=0, ia_only=3, both=0)


def test_messages_with_an_empty_body_are_left_out(mbox_data, database, load_archives):
    connection = load_archives(
        database, [(mbox_data / "nb/no.count.third.mbox", NB_ARCHIVE)]
    )

    assert count_body_overlap(connection) == VennCounts(nb_only=1, ia_only=0, both=0)


def test_date_filtering_restricts_ia_but_not_nb(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.dated.bodies.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.mixed.dates.mbox", NB_ARCHIVE),
        ],
    )

    # IA loses the body dated after the span, while NB keeps its undated one
    assert count_body_overlap(connection, ia_date_span=SPAN) == VennCounts(
        nb_only=3, ia_only=1, both=0
    )
