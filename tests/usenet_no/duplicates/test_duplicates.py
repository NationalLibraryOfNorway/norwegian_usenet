from usenet_no.duplicates import find_true_duplicates_in_mbox_file
from usenet_no.mbox_utils import write_mbox


def _make_mbox(path, messages):
    texts = []
    for message in messages:
        headers = "".join(
            f"{header}: {value}\n"
            for header, value in message.items()
            if header != "body"
        )
        texts.append(f"From sender@example.com\n{headers}\n{message['body']}\n")
    write_mbox(texts, path)


def test_counts_every_copy_of_a_repeated_message(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {"Message-ID": "<a@x.no>", "body": "hello"},
            {"Message-ID": "<a@x.no>", "body": "hello"},
            {"Message-ID": "<b@x.no>", "body": "other"},
        ],
    )

    (duplicate,) = find_true_duplicates_in_mbox_file((mbox_file, "nb"))

    # Both copies are counted, not just the redundant one
    assert duplicate.count == 2
    assert duplicate.message_id == "<a@x.no>"
    assert duplicate.source_archive == "nb"
    assert duplicate.newsgroup == "no.test"


def test_same_id_different_body_is_not_a_true_duplicate(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {"Message-ID": "<a@x.no>", "body": "hello"},
            {"Message-ID": "<a@x.no>", "body": "DIFFERENT"},
        ],
    )

    assert find_true_duplicates_in_mbox_file((mbox_file, "nb")) == []


def test_messages_without_id_are_never_duplicates(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(mbox_file, [{"body": "hello"}, {"body": "hello"}])

    assert find_true_duplicates_in_mbox_file((mbox_file, "ia")) == []


def test_reports_one_row_per_duplicated_message_id(tmp_path):
    mbox_file = tmp_path / "no.test.mbox"
    _make_mbox(
        mbox_file,
        [
            {"Message-ID": "<b@x.no>", "body": "second"},
            {"Message-ID": "<b@x.no>", "body": "second"},
            {"Message-ID": "<b@x.no>", "body": "second"},
            {"Message-ID": "<a@x.no>", "body": "first"},
            {"Message-ID": "<a@x.no>", "body": "first"},
            {"Message-ID": "<c@x.no>", "body": "unique"},
        ],
    )

    duplicates = find_true_duplicates_in_mbox_file((mbox_file, "ia"))

    # Sorted by message id, and the unique message is absent
    assert [(d.message_id, d.count) for d in duplicates] == [
        ("<a@x.no>", 2),
        ("<b@x.no>", 3),
    ]
