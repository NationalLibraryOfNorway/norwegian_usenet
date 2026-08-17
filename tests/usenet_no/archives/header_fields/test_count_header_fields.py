"""Counting the messages that carry each header field."""

from usenet_no.archives.header_fields import count_header_fields


def test_counts_the_messages_carrying_each_field():
    header_blocks = [
        "From: a@example.com\nSubject: Hei\n",
        "From: b@example.com\n",
    ]

    counts = count_header_fields(header_blocks)

    assert counts.message_count == 2
    assert counts.field_counts == {"From": 2, "Subject": 1}


def test_a_field_repeated_within_a_message_counts_once():
    counts = count_header_fields(["Received: first\nReceived: second\n"])

    assert counts.field_counts == {"Received": 1}


def test_fields_are_matched_case_insensitively():
    header_blocks = ["Message-ID: <1@example.com>\n", "Message-Id: <2@example.com>\n"]

    assert count_header_fields(header_blocks).field_counts == {"Message-ID": 2}


def test_a_field_is_reported_under_its_most_common_spelling():
    header_blocks = [
        "Message-Id: <1@example.com>\n",
        "Message-Id: <2@example.com>\n",
        "Message-ID: <3@example.com>\n",
    ]

    assert count_header_fields(header_blocks).field_counts == {"Message-Id": 3}


def test_fields_are_ordered_by_descending_count_then_by_name():
    header_blocks = [
        "From: a@example.com\nDate: today\nSubject: Hei\n",
        "From: b@example.com\nDate: today\n",
        "From: c@example.com\n",
    ]

    assert list(count_header_fields(header_blocks).field_counts) == [
        "From",
        "Date",
        "Subject",
    ]


def test_a_message_with_no_fields_is_still_counted():
    counts = count_header_fields(["just some text\n"])

    assert counts.message_count == 1
    assert counts.field_counts == {}


def test_no_messages_have_no_fields():
    counts = count_header_fields([])

    assert counts.message_count == 0
    assert counts.field_counts == {}
