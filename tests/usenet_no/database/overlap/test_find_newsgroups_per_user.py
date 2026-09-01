from usenet_no.database import IA_ARCHIVE
from usenet_no.database.overlap import find_newsgroups_per_user


def test_a_user_posting_repeatedly_gives_one_pair(mbox_data, load_public_archives):
    """Kari posted twice in the group and Ola once."""
    mbox_file = mbox_data / "ia/no.two.senders.mbox"
    connection = load_public_archives([(mbox_file, IA_ARCHIVE)])

    posts = find_newsgroups_per_user(connection, IA_ARCHIVE)

    assert len(posts) == 2
    assert {group for _user, group in posts} == {"no.two.senders"}
    # A user is an email id here, so the archive's own file is all this reads
    assert all(isinstance(user, int) for user, _group in posts)


def test_messages_without_sender_are_left_out(mbox_data, load_public_archives):
    connection = load_public_archives(
        [
            (mbox_data / "ia/no.known.sender.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.missing.sender.mbox", IA_ARCHIVE),
        ],
    )

    posts = find_newsgroups_per_user(connection, IA_ARCHIVE)

    assert len(posts) == 1
    assert posts[0][1] == "no.known.sender"


def test_the_date_span_is_respected(mbox_data, load_public_archives):
    mbox_file = mbox_data / "ia/no.senders.around.span.mbox"
    connection = load_public_archives([(mbox_file, IA_ARCHIVE)])

    posts = find_newsgroups_per_user(
        connection, IA_ARCHIVE, date_span=("1996-01-06", "1996-01-20")
    )

    assert len(posts) == 1
