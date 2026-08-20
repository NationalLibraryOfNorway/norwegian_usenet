"""Making good the header lines email's parser would stop at."""

from email import policy
from email.parser import BytesParser

import pytest

from usenet_no.mbox_utils import BLANK_LINE, repair_mangled_header_lines


def field_names(raw):
    """The fields email's parser reads, which is what the pipeline gets."""
    return list(
        BytesParser(policy=policy.default.clone(utf8=True)).parsebytes(raw).keys()
    )


def test_an_unindented_continuation_is_folded_into_the_line_above():
    """Google Groups wrote a few Received values with the fold at column 0."""
    raw = (
        b"Received: by 10.66.76.38 with SMTP id h6;\n"
        b"        Thu, 26 Jul 2012 07:30:24 -0700 (PDT)\n"
        b"Thu, 26 Jul 2012 07: 30:23 -0700 (PDT)\n"
        b"Date: i dag\n\nkropp\n"
    )

    repaired = repair_mangled_header_lines(raw)

    assert b"\n Thu, 26 Jul 2012 07: 30:23 -0700 (PDT)\n" in repaired
    assert field_names(repaired) == ["Received", "Date"]


def test_junk_in_front_of_a_field_name_is_taken_off():
    """One IA message carries control bytes in front of an otherwise good header."""
    raw = b"X-Google-Attributes: public\n\xef\xbf\xbd\x01\x18\x08Reply-To: a@uio.no\nFrom: a@uio.no\n\nkropp\n"

    repaired = repair_mangled_header_lines(raw)

    assert b"\nReply-To: a@uio.no\n" in repaired
    assert field_names(repaired) == ["X-Google-Attributes", "Reply-To", "From"]


def test_a_field_name_that_is_not_ascii_is_folded_away():
    """The name cannot be saved, so the fields below it are what is recovered."""
    raw = "X-Newsreader: Gnus\nX-gåte: på\nDate: i dag\n\nkropp\n".encode("utf-8")

    repaired = repair_mangled_header_lines(raw)

    assert field_names(repaired) == ["X-Newsreader", "Date"]


def test_a_clean_header_block_is_unchanged():
    raw = b"From 1\nFrom: a@uio.no\nSubject: Hei\n\nkropp\n"

    assert repair_mangled_header_lines(raw) == raw


def test_a_folded_value_is_left_as_it_is():
    raw = b"From 1\nContent-Type: text/plain;\n\tcharset=iso-8859-1\n\nkropp\n"

    assert repair_mangled_header_lines(raw) == raw


def test_the_envelope_line_is_not_folded_away():
    """It is no header, and folding it would take the message's first field with it."""
    raw = b"From -4408095069344159779\nFrom: a@uio.no\n\nkropp\n"

    assert repair_mangled_header_lines(raw) == raw


def test_a_mangled_line_with_no_field_above_it_is_left_alone():
    """There is nothing to fold it into."""
    raw = b"From 1\nrubbish\nFrom: a@uio.no\n\nkropp\n"

    assert repair_mangled_header_lines(raw) == raw


def test_a_message_whose_headers_no_blank_line_ends_is_left_alone():
    """Its body cannot be told from its headers, so nothing is folded."""
    raw = b"From 1\nFrom: a@uio.no\nrubbish\n"

    assert repair_mangled_header_lines(raw) == raw


def test_the_body_is_never_touched():
    raw = b"From 1\nFrom: a@uio.no\n\nrubbish\nFrom what I gather\n\nmer\n"

    assert repair_mangled_header_lines(raw) == raw


def test_crlf_line_endings():
    raw = b"From 1\r\nReceived: by 10.66.76.38;\r\nThu, 26 Jul 2012\r\n\r\nkropp\r\n"

    repaired = repair_mangled_header_lines(raw)

    assert (
        repaired
        == b"From 1\r\nReceived: by 10.66.76.38;\r\n Thu, 26 Jul 2012\r\n\r\nkropp\r\n"
    )


def test_a_field_name_with_no_space_after_the_colon():
    raw = b"From 1\nX-No-Arcive:Yes\n\nkropp\n"

    assert repair_mangled_header_lines(raw) == raw


MESSAGES = [
    b"From 1\nFrom: a@uio.no\n\nkropp\n",
    b"From 1\nFrom: a@uio.no\n\nFrom now on\n",
    b"From 1\nFrom: a@uio.no\n\n>From a quoted post\n",
    b"From 1\nReceived: by 10.66.76.38;\nThu, 26 Jul 2012\n\nFrom now on\n",
    b"From 1\nX-A: b\n\xef\xbf\xbd\x01Reply-To: a@uio.no\n\nFrom now on\n",
    "From 1\nX-A: b\nX-gåte: på\nDate: i dag\n\nkropp\n".encode("utf-8"),
    b"From 1\nX-A: b\nFrom nobody\nDate: i dag\n\nkropp\n",
    b"From 1\r\nX-A: b\r\nrubbish\r\n\r\nkropp\r\n",
    b"From 1\n\nkropp\n",
    b"From 1\nSubject: Hei\n",
]


def body_of(raw):
    """The message from its blank line on, or None when it is all headers."""
    blank_line = BLANK_LINE.search(raw)
    return raw[blank_line.start() :] if blank_line else None


@pytest.mark.parametrize("raw", MESSAGES)
def test_the_body_is_never_changed(raw):
    assert body_of(repair_mangled_header_lines(raw)) == body_of(raw)


@pytest.mark.parametrize("raw", MESSAGES)
def test_no_line_beginning_with_from_and_a_space_is_made(raw):
    """Those lines delimit messages, so the repair must not manufacture one."""
    repaired = repair_mangled_header_lines(raw)

    assert repaired.count(b"\nFrom ") <= raw.count(b"\nFrom ")


@pytest.mark.parametrize("raw", MESSAGES)
def test_every_field_the_parser_could_read_before_it_still_reads(raw):
    assert set(field_names(raw)) <= set(field_names(repair_mangled_header_lines(raw)))
