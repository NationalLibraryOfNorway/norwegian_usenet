from usenet_no.database import NB_ARCHIVE
from usenet_no.database.statistics import get_date_span


def test_date_span_ignores_unparseable_dates(mbox_data, database, load_archives):
    """The sample holds an undated message between 06 and 20 January."""
    mbox_file = mbox_data / "nb/no.mixed.dates.mbox"
    connection = load_archives(database, [(mbox_file, NB_ARCHIVE)])

    assert get_date_span(connection, NB_ARCHIVE) == ("1996-01-06", "1996-01-20")
