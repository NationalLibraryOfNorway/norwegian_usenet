"""load_message_positions is the date filter the archive used to keep on disk.

A position is the message's place in its newsgroup's mbox file, so the bodies
can be read out of the archive's own files instead of a filtered copy.
"""

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.core import load_message_positions

NB_SPAN = ("1996-01-01", "1996-12-31")


def test_positions_start_at_zero_in_each_newsgroup(mbox_data, load_archives):
    """Row ids run on across mbox files, positions restart at every file."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.dated.ids.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.replacement.chars.mbox", IA_ARCHIVE),
        ],
    )

    positions = load_message_positions(connection, IA_ARCHIVE)

    assert positions == {
        "no.dated.ids": [0, 1],
        "no.replacement.chars": [0, 1, 2, 3, 4],
    }


def test_keeps_only_the_messages_inside_the_span(mbox_data, load_archives):
    """no.dated.ids.mbox holds one message in 1996 and one in 2005."""
    connection = load_archives([(mbox_data / "ia/no.dated.ids.mbox", IA_ARCHIVE)])

    assert load_message_positions(connection, IA_ARCHIVE, NB_SPAN) == {
        "no.dated.ids": [0]
    }


def test_drops_messages_whose_date_did_not_parse(mbox_data, load_archives):
    """The undated message sits between the two dated ones, at position 1."""
    connection = load_archives([(mbox_data / "nb/no.mixed.dates.mbox", NB_ARCHIVE)])

    assert load_message_positions(connection, NB_ARCHIVE, NB_SPAN) == {
        "no.mixed.dates": [0, 2]
    }


def test_keeps_undated_messages_without_a_span(mbox_data, load_archives):
    connection = load_archives([(mbox_data / "nb/no.mixed.dates.mbox", NB_ARCHIVE)])

    assert load_message_positions(connection, NB_ARCHIVE) == {
        "no.mixed.dates": [0, 1, 2]
    }


def test_reads_one_archive_at_a_time(mbox_data, load_archives):
    """The same newsgroup name appears in both archives, with its own positions."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.replacement.chars.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.replacement.chars.mbox", NB_ARCHIVE),
        ],
    )

    assert load_message_positions(connection, NB_ARCHIVE) == {
        "no.replacement.chars": [0, 1, 2, 3]
    }


def test_a_newsgroup_with_no_message_in_the_span_is_left_out(mbox_data, load_archives):
    connection = load_archives([(mbox_data / "ia/no.dated.ids.mbox", IA_ARCHIVE)])

    assert (
        load_message_positions(connection, IA_ARCHIVE, ("2020-01-01", "2020-12-31"))
        == {}
    )
