from usenet_no.duplicates import find_true_duplicates_in_mbox_file


def test_counts_every_copy_of_a_repeated_message(mbox_data):
    mbox_file = mbox_data / "nb/no.repeated.message.mbox"

    (duplicate,) = find_true_duplicates_in_mbox_file((mbox_file, "nb"))

    # Both copies are counted, not just the redundant one
    assert duplicate.count == 2
    assert duplicate.message_id == "<a@example.no>"
    assert duplicate.source_archive == "nb"
    assert duplicate.newsgroup == "no.repeated.message"


def test_same_id_different_body_is_not_a_true_duplicate(mbox_data):
    mbox_file = mbox_data / "nb/no.same.id.different.body.mbox"

    assert find_true_duplicates_in_mbox_file((mbox_file, "nb")) == []


def test_messages_without_id_are_never_duplicates(mbox_data):
    mbox_file = mbox_data / "ia/no.without.message.id.mbox"

    assert find_true_duplicates_in_mbox_file((mbox_file, "ia")) == []


def test_reports_one_row_per_duplicated_message_id(mbox_data):
    mbox_file = mbox_data / "ia/no.many.duplicates.mbox"

    duplicates = find_true_duplicates_in_mbox_file((mbox_file, "ia"))

    # Sorted by message id, and the unique message is absent
    assert [(d.message_id, d.count) for d in duplicates] == [
        ("<a@example.no>", 2),
        ("<b@example.no>", 3),
    ]
