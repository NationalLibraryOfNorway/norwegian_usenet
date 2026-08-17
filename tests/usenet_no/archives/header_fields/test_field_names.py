"""The header field names one message carries."""

from usenet_no.archives.header_fields import field_names


def test_returns_the_fields_in_the_order_they_appear():
    header_block = (
        "Path: uio.no\nFrom: a@example.com\nDate: Wed, 12 Feb 1997 09:04:49 +0100\n"
    )

    assert field_names(header_block) == ["Path", "From", "Date"]


def test_a_repeated_field_is_returned_once():
    header_block = "Received: first\nFrom: a@example.com\nReceived: second\n"

    assert field_names(header_block) == ["Received", "From"]


def test_a_repeated_field_keeps_the_spelling_it_first_appears_with():
    header_block = "Message-ID: <1@example.com>\nMessage-Id: <1@example.com>\n"

    assert field_names(header_block) == ["Message-ID"]


def test_a_folded_value_is_not_a_field():
    header_block = "Newsgroups: no.ai,\n\tno.alt.flame\nSubject: Hei\n"

    assert field_names(header_block) == ["Newsgroups", "Subject"]


def test_text_with_no_headers_has_no_fields():
    assert field_names("just some text\n") == []
