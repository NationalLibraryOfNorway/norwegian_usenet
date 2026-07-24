from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.statistics import count_messages_per_group

SPAN = ("1996-01-06", "1996-01-20")


def test_counts_messages_per_newsgroup_of_one_archive(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.count.first.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.count.second.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.count.third.mbox", NB_ARCHIVE),
        ],
    )

    # The NB newsgroup is excluded, since only one archive is asked for
    assert count_messages_per_group(connection, IA_ARCHIVE) == {
        "no.count.first": 2,
        "no.count.second": 1,
    }


def test_date_filtering_excludes_messages_outside_the_span(
    mbox_data, database, load_archives
):
    mbox_file = mbox_data / "ia/no.dates.around.span.mbox"
    connection = load_archives(database, [(mbox_file, IA_ARCHIVE)])

    counts = count_messages_per_group(connection, IA_ARCHIVE, date_span=SPAN)

    assert counts == {"no.dates.around.span": 1}


def test_date_filtering_excludes_messages_with_unparseable_dates(
    mbox_data, database, load_archives
):
    """Matches how the date-filtered archive was built: unknown dates are dropped."""
    mbox_file = mbox_data / "ia/no.unparseable.and.late.mbox"
    connection = load_archives(database, [(mbox_file, IA_ARCHIVE)])

    counts = count_messages_per_group(connection, IA_ARCHIVE, date_span=SPAN)

    assert counts == {"no.unparseable.and.late": 1}


def test_counts_are_sorted_by_newsgroup(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.zebra.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.alpha.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.middle.mbox", IA_ARCHIVE),
        ],
    )

    counts = count_messages_per_group(connection, IA_ARCHIVE)

    assert list(counts) == ["no.alpha", "no.middle", "no.zebra"]
