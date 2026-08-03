from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.comparison import VennCounts, count_user_overlap

SPAN = ("1996-01-06", "1996-01-20")


def test_counts_an_email_both_archives_have_as_shared(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.two.senders.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.repeated.sender.mbox", NB_ARCHIVE),
        ],
    )

    # k@example.no posted in both archives, o@example.no only in IA
    assert count_user_overlap(connection) == VennCounts(nb_only=0, ia_only=1, both=1)


def test_one_email_posted_under_several_names_counts_once(
    mbox_data, database, load_archives
):
    connection = load_archives(
        database, [(mbox_data / "ia/no.same.email.two.names.mbox", IA_ARCHIVE)]
    )

    assert count_user_overlap(connection) == VennCounts(nb_only=0, ia_only=1, both=0)


def test_messages_without_a_sender_are_left_out(mbox_data, database, load_archives):
    connection = load_archives(
        database, [(mbox_data / "ia/no.missing.sender.mbox", IA_ARCHIVE)]
    )

    assert count_user_overlap(connection) == VennCounts(nb_only=0, ia_only=0, both=0)


def test_date_filtering_restricts_ia_but_not_nb(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.senders.around.span.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.repeated.sender.mbox", NB_ARCHIVE),
        ],
    )

    # Only kari@example.no is inside the span, and NB's k@example.no is unrelated
    assert count_user_overlap(connection, ia_date_span=SPAN) == VennCounts(
        nb_only=1, ia_only=1, both=0
    )
