from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.statistics import count_messages_per_email_hash
from usenet_no.hash import make_hash

SPAN = ("1996-01-06", "1996-01-20")


def test_collapses_the_names_one_email_posted_under(mbox_data, load_archives):
    connection = load_archives(
        [(mbox_data / "ia/no.same.email.two.names.mbox", IA_ARCHIVE)]
    )

    assert count_messages_per_email_hash(connection, IA_ARCHIVE) == [
        (make_hash("k@example.no"), 2)
    ]


def test_sorts_the_busiest_sender_first(mbox_data, load_archives):
    connection = load_archives([(mbox_data / "ia/no.two.senders.mbox", IA_ARCHIVE)])

    assert count_messages_per_email_hash(connection, IA_ARCHIVE) == [
        (make_hash("k@example.no"), 2),
        (make_hash("o@example.no"), 1),
    ]


def test_leaves_out_messages_without_a_sender(mbox_data, load_archives):
    connection = load_archives([(mbox_data / "ia/no.missing.sender.mbox", IA_ARCHIVE)])

    assert count_messages_per_email_hash(connection, IA_ARCHIVE) == []


def test_counts_only_the_named_archive(mbox_data, load_archives):
    connection = load_archives(
        [
            (mbox_data / "ia/no.two.senders.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.repeated.sender.mbox", NB_ARCHIVE),
        ],
    )

    assert count_messages_per_email_hash(connection, NB_ARCHIVE) == [
        (make_hash("k@example.no"), 1)
    ]


def test_date_span_drops_messages_outside_it(mbox_data, load_archives):
    connection = load_archives(
        [(mbox_data / "ia/no.senders.around.span.mbox", IA_ARCHIVE)]
    )

    assert count_messages_per_email_hash(connection, IA_ARCHIVE, date_span=SPAN) == [
        (make_hash("kari@example.no"), 1)
    ]
