from usenet_no.database import IA_ARCHIVE
from usenet_no.database.statistics import count_messages_per_user


def test_counts_messages_per_user_by_hash(mbox_data, load_archives):
    """Two of the three messages come from the same address, spelled differently."""
    mbox_file = mbox_data / "ia/no.two.senders.mbox"
    connection = load_archives([(mbox_file, IA_ARCHIVE)])

    counts = count_messages_per_user(connection, IA_ARCHIVE)

    assert sorted(count for _n, _e, count in counts) == [1, 2]
    # Only hashes are returned, never the address itself
    assert all("@" not in (email or "") for _n, email, _c in counts)


def test_per_user_counts_exclude_messages_without_sender(mbox_data, load_archives):
    connection = load_archives(
        [
            (mbox_data / "ia/no.known.sender.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.missing.sender.mbox", IA_ARCHIVE),
        ],
    )

    counts = count_messages_per_user(connection, IA_ARCHIVE)

    assert len(counts) == 1


def test_per_user_counts_respect_the_date_span(mbox_data, load_archives):
    mbox_file = mbox_data / "ia/no.senders.around.span.mbox"
    connection = load_archives([(mbox_file, IA_ARCHIVE)])

    counts = count_messages_per_user(
        connection, IA_ARCHIVE, date_span=("1996-01-06", "1996-01-20")
    )

    assert len(counts) == 1
