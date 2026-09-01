from usenet_no.database import IA_ARCHIVE
from usenet_no.database.statistics import count_messages_per_user


def test_counts_messages_per_user(mbox_data, load_public_archives):
    """Two of the three messages come from the same address, spelled differently,
    and are one user because a user is an address."""
    mbox_file = mbox_data / "ia/no.two.senders.mbox"
    connection = load_public_archives([(mbox_file, IA_ARCHIVE)])

    counts = count_messages_per_user(connection, IA_ARCHIVE)

    assert [count for _user, count in counts] == [2, 1]
    # A user is an email id here, so the archive's own file is all this reads
    assert all(isinstance(user, int) for user, _count in counts)


def test_per_user_counts_exclude_messages_without_sender(
    mbox_data, load_public_archives
):
    connection = load_public_archives(
        [
            (mbox_data / "ia/no.known.sender.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.missing.sender.mbox", IA_ARCHIVE),
        ],
    )

    counts = count_messages_per_user(connection, IA_ARCHIVE)

    assert len(counts) == 1


def test_per_user_counts_respect_the_date_span(mbox_data, load_public_archives):
    mbox_file = mbox_data / "ia/no.senders.around.span.mbox"
    connection = load_public_archives([(mbox_file, IA_ARCHIVE)])

    counts = count_messages_per_user(
        connection, IA_ARCHIVE, date_span=("1996-01-06", "1996-01-20")
    )

    assert len(counts) == 1
