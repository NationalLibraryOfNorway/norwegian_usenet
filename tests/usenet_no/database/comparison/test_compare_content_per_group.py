from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.comparison import compare_content_per_group

SPAN = ("1996-01-06", "1996-01-20")


def test_counts_a_body_both_archives_have_as_shared(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.shared.body.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.shared.body.mbox", NB_ARCHIVE),
        ],
    )

    assert compare_content_per_group(connection) == [("no.shared.body", 0, 0, 1)]


def test_counts_differing_bodies_on_each_side(mbox_data, database, load_archives):
    """The same posting, but the archives decoded it differently."""
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.across.archives.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.across.archives.mbox", NB_ARCHIVE),
        ],
    )

    assert compare_content_per_group(connection) == [("no.across.archives", 1, 1, 0)]


def test_a_newsgroup_only_one_archive_has_gets_a_zero_on_the_other_side(
    mbox_data, database, load_archives
):
    connection = load_archives(database, [(mbox_data / "ia/no.alpha.mbox", IA_ARCHIVE)])

    assert compare_content_per_group(connection) == [("no.alpha", 1, 0, 0)]


def test_repeated_bodies_are_counted_once(mbox_data, database, load_archives):
    connection = load_archives(
        database, [(mbox_data / "nb/no.repeated.message.mbox", NB_ARCHIVE)]
    )

    # Three messages, but two of them carry the same body
    assert compare_content_per_group(connection) == [("no.repeated.message", 0, 2, 0)]


def test_rows_are_sorted_by_newsgroup(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.zebra.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.alpha.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.middle.mbox", IA_ARCHIVE),
        ],
    )

    rows = compare_content_per_group(connection)

    assert [newsgroup for newsgroup, *_ in rows] == [
        "no.alpha",
        "no.middle",
        "no.zebra",
    ]


def test_date_filtering_restricts_ia_but_not_nb(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.dated.bodies.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.mixed.dates.mbox", NB_ARCHIVE),
        ],
    )

    rows = {
        newsgroup: counts
        for newsgroup, *counts in compare_content_per_group(
            connection, ia_date_span=SPAN
        )
    }

    # Only the IA message inside the span is left, while NB keeps all three
    assert rows["no.dated.bodies"] == [1, 0, 0]
    assert rows["no.mixed.dates"] == [0, 3, 0]
