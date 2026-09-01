from usenet_no.database.build import extract_messages_from_mbox_file
from usenet_no.hash import make_hash


def test_extracts_message_fields(mbox_data):
    mbox_file = mbox_data / "ia/no.full.message.mbox"

    (message,) = extract_messages_from_mbox_file(mbox_file)

    assert message.newsgroup == "no.full.message"
    assert message.message_id_hash == make_hash("<abc@example.no>")
    assert message.from_name_hash == make_hash("Kari Nordmann")
    assert message.date == "1996-01-01"
    assert message.body_hash is not None


def test_lowercases_email_but_keeps_name_case(mbox_data):
    """The sample holds `Kari Nordmann <Kari@Example.NO>`, and address variants
    must hash alike, since they are one user."""
    mbox_file = mbox_data / "ia/no.full.message.mbox"

    (message,) = extract_messages_from_mbox_file(mbox_file)

    assert message.from_email_hash == make_hash("kari@example.no")
    assert message.from_name_hash == make_hash("Kari Nordmann")


def test_missing_name_hashes_to_null(mbox_data):
    mbox_file = mbox_data / "ia/no.sender.without.name.mbox"

    (message,) = extract_messages_from_mbox_file(mbox_file)

    assert message.from_name_hash is None
    assert message.from_email_hash is not None


def test_name_without_an_address_hashes_the_name_only(mbox_data):
    """The sample holds `From: HOLDEJ <>`, empty angle brackets after a display
    name, which is the shape the archives give a sender with no address."""
    mbox_file = mbox_data / "ia/no.name.without.email.mbox"

    (message,) = extract_messages_from_mbox_file(mbox_file)

    assert message.from_name_hash == make_hash("HOLDEJ")
    assert message.from_email_hash is None


def test_unparseable_date_is_stored_as_null(mbox_data):
    mbox_file = mbox_data / "ia/no.unparseable.date.mbox"

    (message,) = extract_messages_from_mbox_file(mbox_file)

    assert message.date is None


def test_identical_bodies_hash_equal_across_archives(mbox_data):
    (ia_message,) = extract_messages_from_mbox_file(
        mbox_data / "ia/no.identical.body.mbox"
    )
    (nb_message,) = extract_messages_from_mbox_file(
        mbox_data / "nb/no.identical.body.mbox"
    )

    # Different senders, same body text
    assert ia_message.body_hash == nb_message.body_hash


def test_extracted_message_holds_no_plaintext_fields(mbox_data):
    """Only hashes leave the parse, so no plain text is carried between the
    worker processes and the database."""
    mbox_file = mbox_data / "ia/no.full.message.mbox"

    (message,) = extract_messages_from_mbox_file(mbox_file)

    assert not hasattr(message, "message_id")
    assert not hasattr(message, "from_name")
    assert not hasattr(message, "from_email")
