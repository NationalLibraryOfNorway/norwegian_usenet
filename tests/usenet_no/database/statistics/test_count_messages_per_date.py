from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.statistics import count_messages_per_date


def test_counts_messages_per_date_with_undated_last(mbox_data, load_archives):
    mbox_file = mbox_data / "nb/no.mixed.dates.mbox"
    connection = load_archives([(mbox_file, NB_ARCHIVE)])

    counts = count_messages_per_date(connection, NB_ARCHIVE)

    # Sorted by date, with the undated group last so it lands at the CSV's end
    assert counts == [("1996-01-06", 1), ("1996-01-20", 1), (None, 1)]


def test_an_escaped_from_line_in_a_body_adds_no_undated_message(
    mbox_data, load_archives
):
    """no.from.line.in.body.mbox holds two dated messages, and a signature line
    starting with "From " that write_mbox escaped.
    """
    mbox_file = mbox_data / "ia/no.from.line.in.body.mbox"
    connection = load_archives([(mbox_file, IA_ARCHIVE)])

    counts = count_messages_per_date(connection, IA_ARCHIVE)

    assert counts == [("1996-01-06", 1), ("1996-01-20", 1)]
