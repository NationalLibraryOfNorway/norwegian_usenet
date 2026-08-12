from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.build import (
    ExtractedMessage,
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


def test_sender_is_reused_from_an_existing_database(mbox_data, database):
    """A build that continues into an existing database reads the users back out
    of it, so a sender already stored keeps the id it was given."""
    insert_messages(
        database,
        extract_messages_from_mbox_file(
            (mbox_data / "ia/no.repeated.sender.mbox", IA_ARCHIVE)
        ),
        load_user_ids(database),
    )

    insert_messages(
        database,
        extract_messages_from_mbox_file(
            (mbox_data / "nb/no.repeated.sender.mbox", NB_ARCHIVE)
        ),
        load_user_ids(database),
    )

    user_ids = database.execute("SELECT id FROM users").fetchall()
    message_user_ids = database.execute(
        "SELECT DISTINCT user_id FROM messages"
    ).fetchall()

    assert user_ids == [(1,)]
    assert message_user_ids == [(1,)]


def test_same_email_with_different_names_are_separate_users(mbox_data, database):
    mbox_file = mbox_data / "ia/no.same.email.two.names.mbox"

    insert_messages(
        database,
        extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE)),
        load_user_ids(database),
    )

    users = database.execute(
        "SELECT name_hash, email_hash FROM users ORDER BY name_hash"
    ).fetchall()
    (emails,) = database.execute(
        "SELECT COUNT(DISTINCT email_hash) FROM users"
    ).fetchone()

    assert users == sorted(
        [
            (make_hash("Kari Nordmann"), make_hash("k@example.no")),
            (make_hash("kari"), make_hash("k@example.no")),
        ]
    )
    assert emails == 1


def test_message_without_sender_has_no_user(database):
    """Built directly: mailbox always synthesises a MAILER-DAEMON envelope, so a
    message with no sender at all cannot be produced from an mbox file."""
    message = ExtractedMessage(
        archive=IA_ARCHIVE,
        newsgroup="no.test",
        message_id_hash=None,
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


def test_database_holds_no_plaintext_columns(database):
    """The file is the one that can be published, so its schema must not carry
    name, email, message id or body columns in plain text."""
    columns = {
        (table, column)
        for (table,) in database.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
        for column in [
            row[1] for row in database.execute(f"PRAGMA table_info({table})")
        ]
    }

    plaintext_columns = {column for _table, column in columns}
    assert "name" not in plaintext_columns
    assert "email" not in plaintext_columns
    assert "message_id" not in plaintext_columns
    assert "body" not in plaintext_columns


def test_messages_table_holds_no_free_text_columns(database):
    """Subject and the Newsgroups header were dropped because both carried
    addresses and message ids in the clear, which the hashed columns withhold.
    Pinning the column set keeps a new free text column from reopening that."""
    columns = {row[1] for row in database.execute("PRAGMA table_info(messages)")}

    assert columns == {
        "id",
        "archive",
        "newsgroup",
        "message_id_hash",
        "user_id",
        "date",
        "body_hash",
    }
