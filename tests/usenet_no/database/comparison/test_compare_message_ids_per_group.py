from usenet_no.database.comparison import compare_message_ids_per_group
from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE

SPAN = ("1996-01-06", "1996-01-20")


def test_counts_an_id_both_archives_have_as_shared(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.id.overlap.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.id.overlap.mbox", NB_ARCHIVE),
        ],
    )

    assert compare_message_ids_per_group(connection) == [("no.id.overlap", 1, 1, 1)]


def test_a_newsgroup_only_one_archive_has_gets_a_zero_on_the_other_side(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database, [(mbox_data / "ia/no.id.overlap.mbox", IA_ARCHIVE)]
    )

    assert compare_message_ids_per_group(connection) == [("no.id.overlap", 2, 0, 0)]


def test_repeated_message_ids_are_counted_once(mbox_data, database, load_archives):
    connection = load_archives(
        database, [(mbox_data / "nb/no.repeated.message.mbox", NB_ARCHIVE)]
    )

    # Three messages, but <a@example.no> appears twice
    assert compare_message_ids_per_group(connection) == [
        ("no.repeated.message", 0, 2, 0)
    ]


def test_rows_are_sorted_by_newsgroup(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "nb/no.repeated.message.mbox", NB_ARCHIVE),
            (mbox_data / "nb/no.dated.ids.mbox", NB_ARCHIVE),
            (mbox_data / "nb/no.id.overlap.mbox", NB_ARCHIVE),
        ],
    )

    rows = compare_message_ids_per_group(connection)

    assert [newsgroup for newsgroup, *_ in rows] == [
        "no.dated.ids",
        "no.id.overlap",
        "no.repeated.message",
    ]


def test_date_filtering_restricts_ia_but_not_nb(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.dated.citations.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.dated.ids.mbox", NB_ARCHIVE),
        ],
    )

    rows = {
        newsgroup: counts
        for newsgroup, *counts in compare_message_ids_per_group(
            connection, ia_date_span=SPAN
        )
    }

    # Only the IA id inside the span is left, while NB keeps the one after it too
    assert rows["no.dated.citations"] == [1, 0, 0]
    assert rows["no.dated.ids"] == [0, 2, 0]
