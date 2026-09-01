from usenet_no.database.build import (
    ExtractedMessage,
    extract_messages_from_mbox_file,
    insert_messages,
    load_email_ids,
    load_email_names,
)
from usenet_no.hash import make_hash


def insert_mbox_file(database, mbox_file, email_ids=None, email_names=None):
    """Insert one sample mbox file, reading the sender lookups back by default."""
    insert_messages(
        database,
        extract_messages_from_mbox_file(mbox_file),
        load_email_ids(database) if email_ids is None else email_ids,
        load_email_names(database) if email_names is None else email_names,
    )


def test_inserts_messages_and_references(mbox_data, database):
    insert_mbox_file(database, mbox_data / "ia/no.with.references.mbox")

    (message_count,) = database.execute("SELECT COUNT(*) FROM messages").fetchone()
    referenced_ids = database.execute(
        "SELECT referenced_id_hash FROM message_references ORDER BY referenced_id_hash"
    ).fetchall()

    assert message_count == 1
    assert referenced_ids == sorted(
        [(make_hash("<grandparent@example.no>"),), (make_hash("<parent@example.no>"),)]
    )


def test_insert_assigns_unique_ids_across_calls(mbox_data, database):
    email_ids = load_email_ids(database)
    email_names = load_email_names(database)

    insert_mbox_file(
        database, mbox_data / "ia/no.two.batches.mbox", email_ids, email_names
    )
    insert_mbox_file(
        database, mbox_data / "nb/no.two.batches.mbox", email_ids, email_names
    )

    ids = database.execute("SELECT id FROM messages ORDER BY id").fetchall()
    # Each reference must point at a distinct message row
    reference_row_ids = database.execute(
        "SELECT DISTINCT message_row_id FROM message_references"
    ).fetchall()

    assert ids == [(1,), (2,)]
    assert len(reference_row_ids) == 2


def test_repeated_sender_becomes_one_email_row(mbox_data, database):
    email_ids = load_email_ids(database)
    email_names = load_email_names(database)

    # Two separate batches, so the sender must be reused across calls
    insert_mbox_file(
        database, mbox_data / "ia/no.repeated.sender.mbox", email_ids, email_names
    )
    insert_mbox_file(
        database, mbox_data / "nb/no.repeated.sender.mbox", email_ids, email_names
    )

    (email_count,) = database.execute("SELECT COUNT(*) FROM users.emails").fetchone()
    message_email_ids = database.execute(
        "SELECT DISTINCT email_id FROM messages"
    ).fetchall()

    assert email_count == 1
    assert len(message_email_ids) == 1


def test_sender_is_reused_from_an_existing_database(mbox_data, database):
    """A build that continues into an existing database reads the addresses back
    out of it, so a sender already stored keeps the id it was given."""
    insert_mbox_file(database, mbox_data / "ia/no.repeated.sender.mbox")
    insert_mbox_file(database, mbox_data / "nb/no.repeated.sender.mbox")

    email_ids = database.execute("SELECT id FROM users.emails").fetchall()
    message_email_ids = database.execute(
        "SELECT DISTINCT email_id FROM messages"
    ).fetchall()

    assert email_ids == [(1,)]
    assert message_email_ids == [(1,)]


def test_same_email_with_different_names_is_one_user(mbox_data, database):
    """A user is an address, so the names it posted under hang off the one row
    rather than making a user of each."""
    insert_mbox_file(database, mbox_data / "ia/no.same.email.two.names.mbox")

    emails = database.execute("SELECT id, email_hash FROM users.emails").fetchall()
    names = database.execute(
        "SELECT email_id, name_hash FROM users.email_names ORDER BY name_hash"
    ).fetchall()

    assert emails == [(1, make_hash("k@example.no"))]
    assert names == sorted(
        [(1, make_hash("Kari Nordmann")), (1, make_hash("kari"))],
        key=lambda row: row[1],
    )


def test_a_name_is_stored_once_however_often_it_posts(mbox_data, database):
    email_ids = load_email_ids(database)
    email_names = load_email_names(database)

    # The same (name, address) pair in two batches, so the pair must be reused
    insert_mbox_file(
        database, mbox_data / "ia/no.repeated.sender.mbox", email_ids, email_names
    )
    insert_mbox_file(
        database, mbox_data / "nb/no.repeated.sender.mbox", email_ids, email_names
    )

    (name_count,) = database.execute(
        "SELECT COUNT(*) FROM users.email_names"
    ).fetchone()

    assert name_count == 1


def test_message_without_sender_has_no_email_id(database):
    """Built directly: mailbox always synthesises a MAILER-DAEMON envelope, so a
    message with no sender at all cannot be produced from an mbox file."""
    message = ExtractedMessage(
        newsgroup="no.test",
        message_id_hash=make_hash("<1@example.no>"),
        from_name_hash=None,
        from_email_hash=None,
        date=None,
        body_hash=None,
        referenced_id_hashes=[],
    )

    insert_messages(database, [message], load_email_ids(database), set())

    (email_count,) = database.execute("SELECT COUNT(*) FROM users.emails").fetchone()
    (email_id,) = database.execute("SELECT email_id FROM messages").fetchone()

    assert email_count == 0
    assert email_id is None


def test_a_name_without_an_address_gets_no_user(mbox_data, database):
    """A user is an address, so a sender who gave only a display name is no user,
    and the name is not stored: there is no row for it to hang off."""
    insert_mbox_file(database, mbox_data / "ia/no.name.without.email.mbox")

    (email_count,) = database.execute("SELECT COUNT(*) FROM users.emails").fetchone()
    (name_count,) = database.execute(
        "SELECT COUNT(*) FROM users.email_names"
    ).fetchone()
    (email_id,) = database.execute("SELECT email_id FROM messages").fetchone()

    assert email_count == 0
    assert name_count == 0
    assert email_id is None


def test_archive_database_holds_no_hashed_address(mbox_data, database):
    """The published file refers to a sender by id alone. A hashed address is
    guessable from an address, so keeping it out of this file is the point of
    holding it in the user database instead."""
    insert_mbox_file(database, mbox_data / "ia/no.full.message.mbox")

    columns = {
        column
        for (table,) in database.execute(
            "SELECT name FROM main.sqlite_master WHERE type = 'table'"
        )
        for column in [
            row[1] for row in database.execute(f"PRAGMA main.table_info({table})")
        ]
    }

    assert "email_hash" not in columns
    assert "name_hash" not in columns


def test_database_holds_no_plaintext_columns(database):
    """The file is the one that can be published, so its schema must not carry
    name, email, message id or body columns in plain text."""
    columns = {
        column
        for (table,) in database.execute(
            "SELECT name FROM main.sqlite_master WHERE type = 'table'"
        )
        for column in [
            row[1] for row in database.execute(f"PRAGMA main.table_info({table})")
        ]
    }

    assert "name" not in columns
    assert "email" not in columns
    assert "message_id" not in columns
    assert "body" not in columns


def test_messages_table_holds_no_free_text_columns(database):
    """Subject and the Newsgroups header were dropped because both carried
    addresses and message ids in the clear, which the hashed columns withhold.
    Pinning the column set keeps a new free text column from reopening that."""
    columns = {row[1] for row in database.execute("PRAGMA table_info(messages)")}

    assert columns == {
        "id",
        "newsgroup",
        "message_id_hash",
        "email_id",
        "date",
        "body_hash",
    }
