from usenet_no.database import NB_ARCHIVE
from usenet_no.database.statistics import count_messages_per_date


def test_counts_messages_per_date_with_undated_last(mbox_data, database, load_archives):
    mbox_file = mbox_data / "nb/no.mixed.dates.mbox"
    connection = load_archives(database, [(mbox_file, NB_ARCHIVE)])

    counts = count_messages_per_date(connection, NB_ARCHIVE)

    # Sorted by date, with the undated group last so it lands at the CSV's end
    assert counts == [("1996-01-06", 1), ("1996-01-20", 1), (None, 1)]
