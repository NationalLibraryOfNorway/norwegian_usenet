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


def test_a_folded_value_held_over_a_space_is_not_a_field():
    header_block = "Newsgroups: no.ai,\n no.alt.flame\nSubject: Hei\n"

    assert field_names(header_block) == ["Newsgroups", "Subject"]


def test_a_lone_carriage_return_in_a_value_does_not_hide_the_fields_below_it():
    """Some IA messages carry one inside a display name, splitting the line in two."""
    header_block = 'From: "(\r" <a@example.com>\nSubject: Hei\nDate: 1997/05/15\n'

    assert field_names(header_block) == ["From", "Subject", "Date"]


def test_crlf_line_endings():
    header_block = "From: a@example.com\r\nSubject: Hei\r\n"

    assert field_names(header_block) == ["From", "Subject"]


def test_a_field_name_the_source_mangled_does_not_hide_the_fields_below_it():
    header_block = "X-Javel-Så-Glemte-Jeg: joda\nNewsgroups: no.general\n"

    assert field_names(header_block) == ["Newsgroups"]


def test_an_unindented_continuation_does_not_hide_the_fields_below_it():
    header_block = (
        "Received: by 10.224.100.137 with SMTP id y9;\n"
        "Thu, 26 Jul 2012 08: 52:54 -0700 (PDT)\n"
        "From: a@example.com\n"
    )

    assert field_names(header_block) == ["Received", "From"]


def test_a_name_with_a_space_in_it_is_not_a_field():
    assert field_names("Thu, 26 Jul 2012 08: 52:54 -0700\n") == []


def test_a_field_with_no_space_after_the_colon():
    header_block = "X-No-Arcive:Yes\nSubject: Hei\n"

    assert field_names(header_block) == ["X-No-Arcive", "Subject"]


def test_an_envelope_line_is_not_a_field():
    """It has no colon, so a block still holding one contributes nothing."""
    header_block = "From 6214288843448422964\nSubject: Hei\n"

    assert field_names(header_block) == ["Subject"]


def test_a_line_that_opens_with_the_colon_is_not_a_field():
    header_block = ": nothing named it\nSubject: Hei\n"

    assert field_names(header_block) == ["Subject"]


def test_an_empty_header_block_has_no_fields():
    assert field_names("") == []
