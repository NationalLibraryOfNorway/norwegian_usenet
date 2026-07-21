from usenet_no.database import IA_ARCHIVE
from usenet_no.statistics import count_messages_without_sender


def test_counts_messages_with_no_from_header(mbox_data, database, load_archives):
    """A message with no From header has no user, and is counted here.

    no.missing.sender.mbox carries an empty envelope sender and no From header,
    which is how such messages appear in the archives.
    """
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.known.sender.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.missing.sender.mbox", IA_ARCHIVE),
        ],
    )

    assert count_messages_without_sender(connection) == [("ia", "no.missing.sender", 2)]


def test_no_rows_when_every_message_has_a_sender(mbox_data, database, load_archives):
    mbox_file = mbox_data / "ia/no.known.sender.mbox"
    connection = load_archives(database, [(mbox_file, IA_ARCHIVE)])

    assert count_messages_without_sender(connection) == []
