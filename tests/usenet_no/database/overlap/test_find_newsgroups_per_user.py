from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.overlap import find_newsgroups_per_user


def test_a_user_posting_repeatedly_gives_one_pair(mbox_data, load_archives):
    """Kari posted twice in the group and Ola once."""
    mbox_file = mbox_data / "ia/no.two.senders.mbox"
    connection = load_archives([(mbox_file, IA_ARCHIVE)])

    posts = find_newsgroups_per_user(connection, [(IA_ARCHIVE, None)])

    assert len(posts) == 2
    assert {group for _user, group in posts} == {"no.two.senders"}
    # Only the hashed address is returned, never the address itself
    assert all("@" not in user for user, _group in posts)


def test_the_same_address_is_one_user_whatever_the_name(mbox_data, load_archives):
    """Both messages are from k@example.no, once as 'Kari Nordmann', once as 'kari'."""
    mbox_file = mbox_data / "ia/no.same.email.two.names.mbox"
    connection = load_archives([(mbox_file, IA_ARCHIVE)])

    posts = find_newsgroups_per_user(connection, [(IA_ARCHIVE, None)])

    assert posts == [(posts[0][0], "no.same.email.two.names")]


def test_messages_without_sender_are_left_out(mbox_data, load_archives):
    connection = load_archives(
        [
            (mbox_data / "ia/no.known.sender.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.missing.sender.mbox", IA_ARCHIVE),
        ],
    )

    posts = find_newsgroups_per_user(connection, [(IA_ARCHIVE, None)])

    assert len(posts) == 1
    assert posts[0][1] == "no.known.sender"


def test_the_date_span_is_respected(mbox_data, load_archives):
    mbox_file = mbox_data / "ia/no.senders.around.span.mbox"
    connection = load_archives([(mbox_file, IA_ARCHIVE)])

    posts = find_newsgroups_per_user(
        connection, [(IA_ARCHIVE, ("1996-01-06", "1996-01-20"))]
    )

    assert len(posts) == 1


def test_several_archives_are_read_as_one_body_of_messages(mbox_data, load_archives):
    """Kari posted in one group in IA and in another in NB."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.two.senders.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.repeated.sender.mbox", NB_ARCHIVE),
        ],
    )

    nb_only = find_newsgroups_per_user(connection, [(NB_ARCHIVE, None)])
    both = find_newsgroups_per_user(
        connection, [(NB_ARCHIVE, None), (IA_ARCHIVE, None)]
    )

    assert {group for _user, group in nb_only} == {"no.repeated.sender"}
    assert {group for _user, group in both} == {
        "no.repeated.sender",
        "no.two.senders",
    }


def test_the_same_newsgroup_in_both_archives_gives_one_pair(mbox_data, load_archives):
    """Kari posted in no.repeated.sender, and both archives hold that message."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.repeated.sender.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.repeated.sender.mbox", NB_ARCHIVE),
        ],
    )

    posts = find_newsgroups_per_user(
        connection, [(NB_ARCHIVE, None), (IA_ARCHIVE, None)]
    )

    assert len(posts) == 1
