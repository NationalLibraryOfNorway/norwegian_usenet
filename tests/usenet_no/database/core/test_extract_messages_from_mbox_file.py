from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, extract_messages_from_mbox_file
from usenet_no.hash import make_hash


def test_extracts_message_fields(mbox_data):
    mbox_file = mbox_data / "ia/no.full.message.mbox"

    (message,) = extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE))

    assert message.archive == IA_ARCHIVE
    assert message.newsgroup == "no.full.message"
    assert message.message_id == "<abc@example.no>"
    assert message.message_id_hash == make_hash("<abc@example.no>")
    assert message.from_name == "Kari Nordmann"
    assert message.date == "1996-01-01"
    assert message.body_hash is not None


def test_lowercases_email_but_keeps_name_case(mbox_data):
    """The sample holds `Kari Nordmann <Kari@Example.NO>`."""
    mbox_file = mbox_data / "ia/no.full.message.mbox"

    (message,) = extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE))

    assert message.from_email == "kari@example.no"
    assert message.from_name == "Kari Nordmann"


def test_hashes_the_stored_name_and_email(mbox_data):
    """The hash must match the value actually stored, i.e. the lowercased email."""
    mbox_file = mbox_data / "ia/no.full.message.mbox"

    (message,) = extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE))

    assert message.from_email_hash == make_hash(message.from_email)
    assert message.from_name_hash == make_hash(message.from_name)
    # Address variants must hash alike, since they are one user
    assert message.from_email_hash == make_hash("kari@example.no")


def test_missing_sender_hashes_to_null(mbox_data):
    mbox_file = mbox_data / "ia/no.sender.without.name.mbox"

    (message,) = extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE))

    assert message.from_name is None
    assert message.from_name_hash is None
    assert message.from_email_hash is not None


def test_unparseable_date_is_stored_as_null(mbox_data):
    mbox_file = mbox_data / "ia/no.unparseable.date.mbox"

    (message,) = extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE))

    assert message.date is None


def test_identical_bodies_hash_equal_across_archives(mbox_data):
    (ia_message,) = extract_messages_from_mbox_file(
        (mbox_data / "ia/no.identical.body.mbox", IA_ARCHIVE)
    )
    (nb_message,) = extract_messages_from_mbox_file(
        (mbox_data / "nb/no.identical.body.mbox", NB_ARCHIVE)
    )

    # Different senders, same body text
    assert ia_message.body_hash == nb_message.body_hash
