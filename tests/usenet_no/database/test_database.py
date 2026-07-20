from usenet_no.database import (
    IA_ARCHIVE,
    ExtractedMessage,
    NB_ARCHIVE,
    connect,
    create_schema,
    extract_messages_from_mbox_file,
    insert_messages,
    load_user_ids,
)
from usenet_no.hash import make_hash
from usenet_no.mbox_utils import write_mbox


def _make_mbox(path, messages):
    """Write a list of header/body dicts as an mbox file."""
    texts = []
    for message in messages:
        headers = "".join(
            f"{header}: {value}\n"
            for header, value in message.items()
            if header != "body"
        )
        texts.append(f"From sender@example.com\n{headers}\n{message['body']}\n")
    write_mbox(texts, path)


def _database(tmp_path):
    connection = connect(tmp_path / "test.db")
    create_schema(connection)
    return connection


def test_extracts_message_fields(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {
                "From": "Tita Enstad <Tita@Example.NO>",
                "Date": "Mon, 01 Jan 1996 12:00:00 +0000",
                "Message-ID": "<abc@example.no>",
                "body": "hello",
            }
        ],
    )

    (message,) = extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE))

    assert message.archive == IA_ARCHIVE
    assert message.newsgroup == "no.test"
    assert message.message_id == "<abc@example.no>"
    assert message.from_name == "Tita Enstad"
    assert message.date == "1996-01-01"
    assert message.body_hash is not None


def test_lowercases_email_but_keeps_name_case(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {
                "From": "Tita Enstad <Tita@Example.NO>",
                "Date": "Mon, 01 Jan 1996 12:00:00 +0000",
                "body": "hello",
            }
        ],
    )

    (message,) = extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE))

    assert message.from_email == "tita@example.no"
    assert message.from_name == "Tita Enstad"


def test_hashes_the_stored_name_and_email(tmp_path):
    """The hash must match the value actually stored, i.e. the lowercased email."""
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [{"From": "Tita Enstad <Tita@Example.NO>", "body": "hello"}],
    )

    (message,) = extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE))

    assert message.from_email_hash == make_hash(message.from_email)
    assert message.from_name_hash == make_hash(message.from_name)
    # Address variants must hash alike, since they are one user
    assert message.from_email_hash == make_hash("tita@example.no")


def test_missing_sender_hashes_to_null(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(mbox_file, [{"From": "a@b.no", "body": "no display name"}])

    (message,) = extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE))

    assert message.from_name is None
    assert message.from_name_hash is None
    assert message.from_email_hash is not None


def test_unparseable_date_is_stored_as_null(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [{"From": "a@b.no", "Date": "not a date at all", "body": "hello"}],
    )

    (message,) = extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE))

    assert message.date is None


def test_identical_bodies_hash_equal_across_archives(tmp_path):
    ia_file = tmp_path / "ia.mbox"
    nb_file = tmp_path / "nb.mbox"
    _make_mbox(ia_file, [{"From": "a@b.no", "body": "same text"}])
    _make_mbox(nb_file, [{"From": "c@d.no", "body": "same text"}])

    (ia_message,) = extract_messages_from_mbox_file((ia_file, IA_ARCHIVE))
    (nb_message,) = extract_messages_from_mbox_file((nb_file, NB_ARCHIVE))

    assert ia_message.body_hash == nb_message.body_hash


def test_inserts_messages_and_references(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {
                "From": "a@b.no",
                "Message-ID": "<child@example.no>",
                "References": "<parent@example.no> <grandparent@example.no>",
                "body": "a reply",
            }
        ],
    )
    connection = _database(tmp_path)

    insert_messages(
        connection,
        extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE)),
        load_user_ids(connection),
    )

    (message_count,) = connection.execute("SELECT COUNT(*) FROM messages").fetchone()
    referenced_ids = connection.execute(
        "SELECT referenced_id FROM message_references ORDER BY referenced_id"
    ).fetchall()

    assert message_count == 1
    assert referenced_ids == [("<grandparent@example.no>",), ("<parent@example.no>",)]


def test_insert_assigns_unique_ids_across_calls(tmp_path):
    first = tmp_path / "first.mbox"
    second = tmp_path / "second.mbox"
    _make_mbox(first, [{"From": "a@b.no", "References": "<x@y.no>", "body": "one"}])
    _make_mbox(second, [{"From": "c@d.no", "References": "<z@y.no>", "body": "two"}])
    connection = _database(tmp_path)
    user_ids = load_user_ids(connection)

    insert_messages(
        connection, extract_messages_from_mbox_file((first, IA_ARCHIVE)), user_ids
    )
    insert_messages(
        connection, extract_messages_from_mbox_file((second, NB_ARCHIVE)), user_ids
    )

    ids = connection.execute("SELECT id FROM messages ORDER BY id").fetchall()
    # Each reference must point at a distinct message row
    reference_row_ids = connection.execute(
        "SELECT DISTINCT message_row_id FROM message_references"
    ).fetchall()

    assert ids == [(1,), (2,)]
    assert len(reference_row_ids) == 2


def test_repeated_sender_becomes_one_user_row(tmp_path):
    first = tmp_path / "no.first.mbox"
    second = tmp_path / "no.second.mbox"
    _make_mbox(first, [{"From": "Tita <t@x.no>", "body": "one"}])
    _make_mbox(second, [{"From": "Tita <t@x.no>", "body": "two"}])
    connection = _database(tmp_path)
    user_ids = load_user_ids(connection)

    # Two separate batches, so the sender must be reused across calls
    insert_messages(
        connection, extract_messages_from_mbox_file((first, IA_ARCHIVE)), user_ids
    )
    insert_messages(
        connection, extract_messages_from_mbox_file((second, NB_ARCHIVE)), user_ids
    )

    (user_count,) = connection.execute("SELECT COUNT(*) FROM users").fetchone()
    message_user_ids = connection.execute(
        "SELECT DISTINCT user_id FROM messages"
    ).fetchall()

    assert user_count == 1
    assert len(message_user_ids) == 1


def test_same_email_with_different_names_are_separate_users(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {"From": "Tita Enstad <t@x.no>", "body": "one"},
            {"From": "tita <t@x.no>", "body": "two"},
        ],
    )
    connection = _database(tmp_path)

    insert_messages(
        connection,
        extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE)),
        load_user_ids(connection),
    )

    names = connection.execute("SELECT name FROM users ORDER BY name").fetchall()
    (emails,) = connection.execute("SELECT COUNT(DISTINCT email) FROM users").fetchone()

    assert names == [("Tita Enstad",), ("tita",)]
    assert emails == 1


def test_message_without_sender_has_no_user(tmp_path):
    """Built directly: mailbox always synthesises a MAILER-DAEMON envelope, so a
    message with no sender at all cannot be produced from an mbox file."""
    connection = _database(tmp_path)
    message = ExtractedMessage(
        archive=IA_ARCHIVE,
        newsgroup="no.test",
        message_id="<a@x.no>",
        from_name=None,
        from_email=None,
        from_name_hash=None,
        from_email_hash=None,
        date=None,
        body_hash=None,
        references=[],
    )

    insert_messages(connection, [message], load_user_ids(connection))

    (user_count,) = connection.execute("SELECT COUNT(*) FROM users").fetchone()
    (user_id,) = connection.execute("SELECT user_id FROM messages").fetchone()

    assert user_count == 0
    assert user_id is None


def test_user_hashes_are_stored_on_the_user_row(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(mbox_file, [{"From": "Tita <Tita@X.NO>", "body": "one"}])
    connection = _database(tmp_path)

    insert_messages(
        connection,
        extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE)),
        load_user_ids(connection),
    )

    name, email, name_hash, email_hash = connection.execute(
        "SELECT name, email, name_hash, email_hash FROM users"
    ).fetchone()

    assert email == "tita@x.no"
    assert email_hash == make_hash("tita@x.no")
    assert name_hash == make_hash(name)
