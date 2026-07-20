from usenet_no.database import (
    IA_ARCHIVE,
    NB_ARCHIVE,
    connect,
    create_schema,
    extract_messages_from_mbox_file,
    insert_messages,
)
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
        connection, extract_messages_from_mbox_file((mbox_file, IA_ARCHIVE))
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

    insert_messages(connection, extract_messages_from_mbox_file((first, IA_ARCHIVE)))
    insert_messages(connection, extract_messages_from_mbox_file((second, NB_ARCHIVE)))

    ids = connection.execute("SELECT id FROM messages ORDER BY id").fetchall()
    # Each reference must point at a distinct message row
    reference_row_ids = connection.execute(
        "SELECT DISTINCT message_row_id FROM message_references"
    ).fetchall()

    assert ids == [(1,), (2,)]
    assert len(reference_row_ids) == 2
