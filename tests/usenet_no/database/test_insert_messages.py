from usenet_no.database import (
    IA_ARCHIVE,
    ExtractedMessage,
    NB_ARCHIVE,
    extract_messages_from_mbox_file,
    insert_messages,
    load_user_ids,
)
from usenet_no.hash import make_hash


def test_inserts_messages_and_references(mbox_data, database):
    mbox_file = mbox_data / "ia/no.with.references.mbox"

    insert_messages(
        database,
        extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE)),
        load_user_ids(database),
    )

    (message_count,) = database.execute("SELECT COUNT(*) FROM messages").fetchone()
    referenced_ids = database.execute(
        "SELECT referenced_id_hash FROM message_references ORDER BY referenced_id_hash"
    ).fetchall()

    assert message_count == 1
    assert referenced_ids == sorted(
        [(make_hash("<grandparent@example.no>"),), (make_hash("<parent@example.no>"),)]
    )


def test_insert_assigns_unique_ids_across_calls(mbox_data, database):
    user_ids = load_user_ids(database)

    insert_messages(
        database,
        extract_messages_from_mbox_file(
            (mbox_data / "ia/no.two.batches.mbox", IA_ARCHIVE)
        ),
        user_ids,
    )
    insert_messages(
        database,
        extract_messages_from_mbox_file(
            (mbox_data / "nb/no.two.batches.mbox", NB_ARCHIVE)
        ),
        user_ids,
    )

    ids = database.execute("SELECT id FROM messages ORDER BY id").fetchall()
    # Each reference must point at a distinct message row
    reference_row_ids = database.execute(
        "SELECT DISTINCT message_row_id FROM message_references"
    ).fetchall()

    assert ids == [(1,), (2,)]
    assert len(reference_row_ids) == 2


def test_repeated_sender_becomes_one_user_row(mbox_data, database):
    user_ids = load_user_ids(database)

    # Two separate batches, so the sender must be reused across calls
    insert_messages(
        database,
        extract_messages_from_mbox_file(
            (mbox_data / "ia/no.repeated.sender.mbox", IA_ARCHIVE)
        ),
        user_ids,
    )
    insert_messages(
        database,
        extract_messages_from_mbox_file(
            (mbox_data / "nb/no.repeated.sender.mbox", NB_ARCHIVE)
        ),
        user_ids,
    )

    (user_count,) = database.execute("SELECT COUNT(*) FROM users").fetchone()
    message_user_ids = database.execute(
        "SELECT DISTINCT user_id FROM messages"
    ).fetchall()

    assert user_count == 1
    assert len(message_user_ids) == 1


def test_same_email_with_different_names_are_separate_users(mbox_data, database):
    mbox_file = mbox_data / "ia/no.same.email.two.names.mbox"

    insert_messages(
        database,
        extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE)),
        load_user_ids(database),
    )

    names = database.execute("SELECT name FROM users ORDER BY name").fetchall()
    (emails,) = database.execute("SELECT COUNT(DISTINCT email) FROM users").fetchone()

    assert names == [("Kari Nordmann",), ("kari",)]
    assert emails == 1


def test_message_without_sender_has_no_user(database):
    """Built directly: mailbox always synthesises a MAILER-DAEMON envelope, so a
    message with no sender at all cannot be produced from an mbox file."""
    message = ExtractedMessage(
        archive=IA_ARCHIVE,
        newsgroup="no.test",
        message_id="<a@example.no>",
        message_id_hash=None,
        from_name=None,
        from_email=None,
        from_name_hash=None,
        from_email_hash=None,
        date=None,
        body_hash=None,
        referenced_id_hashes=[],
    )

    insert_messages(database, [message], load_user_ids(database))

    (user_count,) = database.execute("SELECT COUNT(*) FROM users").fetchone()
    (user_id,) = database.execute("SELECT user_id FROM messages").fetchone()

    assert user_count == 0
    assert user_id is None


def test_user_hashes_are_stored_on_the_user_row(mbox_data, database):
    mbox_file = mbox_data / "ia/no.uppercase.email.mbox"

    insert_messages(
        database,
        extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE)),
        load_user_ids(database),
    )

    name, email, name_hash, email_hash = database.execute(
        "SELECT name, email, name_hash, email_hash FROM users"
    ).fetchone()

    assert email == "kari@example.no"
    assert email_hash == make_hash("kari@example.no")
    assert name_hash == make_hash(name)
