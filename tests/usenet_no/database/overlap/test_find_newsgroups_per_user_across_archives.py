from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.overlap import find_newsgroups_per_user_across_archives


def test_several_archives_are_read_as_one_body_of_messages(mbox_data, load_archives):
    """Kari posted in one group in IA and in another in NB."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.two.senders.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.repeated.sender.mbox", NB_ARCHIVE),
        ],
    )

    nb_only = find_newsgroups_per_user_across_archives(connection, [(NB_ARCHIVE, None)])
    both = find_newsgroups_per_user_across_archives(
        connection, [(NB_ARCHIVE, None), (IA_ARCHIVE, None)]
    )

    assert {group for _user, group in nb_only} == {"no.repeated.sender"}
    assert {group for _user, group in both} == {
        "no.repeated.sender",
        "no.two.senders",
    }
    # Kari is one user across the two archives, so Kari and Ola are the two here
    assert len({user for user, _group in both}) == 2


def test_the_same_newsgroup_in_both_archives_gives_one_pair(mbox_data, load_archives):
    """Kari posted in no.repeated.sender, and both archives hold that message.
    The email ids are handed out per archive, so this pair collapses to one only
    because the two are matched on the hashed address."""
    connection = load_archives(
        [
            (mbox_data / "ia/no.repeated.sender.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.repeated.sender.mbox", NB_ARCHIVE),
        ],
    )

    posts = find_newsgroups_per_user_across_archives(
        connection, [(NB_ARCHIVE, None), (IA_ARCHIVE, None)]
    )

    assert len(posts) == 1
