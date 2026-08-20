from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.comparison import VennCounts, count_message_id_overlap

SPAN = ("1996-01-06", "1996-01-20")


def test_counts_an_id_both_archives_have_as_shared(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.id.overlap.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.id.overlap.mbox", NB_ARCHIVE),
        ],
    )

    assert count_message_id_overlap(connection) == VennCounts(
        nb_only=1, ia_only=1, both=1
    )


def test_a_crossposted_id_counts_once(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.shared.group.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.ia.only.group.mbox", IA_ARCHIVE),
        ],
    )

    # Three distinct ids over four rows: <crossposted> is in both groups
    assert count_message_id_overlap(connection) == VennCounts(
        nb_only=0, ia_only=3, both=0
    )


def test_date_filtering_restricts_ia_but_not_nb(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.dated.citations.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.dated.ids.mbox", NB_ARCHIVE),
        ],
    )

    # IA keeps only <inside.span>, while NB keeps the id after the span too
    assert count_message_id_overlap(connection, ia_date_span=SPAN) == VennCounts(
        nb_only=2, ia_only=1, both=0
    )
