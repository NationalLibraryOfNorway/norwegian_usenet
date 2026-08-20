"""Making good the lone carriage returns in a message's header block."""

import pytest

from usenet_no.mbox_utils import BLANK_LINE, repair_header_line_endings

# Every shape the IA sources put a carriage return, a "From " line, or both in.
MESSAGES = [
    b"From 1\nFrom: a@uio.no\n\nkropp\n",
    b"From 1\nFrom: a@uio.no\n\nFrom now on\n",
    b"From 1\nFrom: a@uio.no\n\n>From a quoted post\n",
    b"From 1\nFrom: a@uio.no\n\nhan skrev\rFrom what I gather\n",
    b'From 1\nFrom: "(\r" <a@uio.no>\nSubject: Hei\n\nFrom now on\n',
    b"From 1\nKeywords: World\rX-No-Archive: Yes\n\nFrom now on\n",
    b"From 1\nSubject: Hei\rFrom: a@uio.no\n\nFrom now on\n",
    b"From 1\nSubject: Hei\rFrom what I gather\n\nkropp\n",
    b"From 1\r\nFrom: a@uio.no\r\n\r\nFrom now on\r\n",
    b"From 1\n\nFrom now on\rand on\n",
    b"From 1\nSubject: Hei\n",
]


def test_a_carriage_return_inside_a_header_value_is_dropped():
    raw = b'From: "(\r" <a@example.com>\nSubject: Hei\n\nkropp\n'

    assert repair_header_line_endings(raw) == (
        b'From: "(" <a@example.com>\nSubject: Hei\n\nkropp\n'
    )


def test_a_carriage_return_before_a_header_line_becomes_a_newline():
    """Some posters' clients ended a header line with a carriage return alone."""
    raw = b"Distribution: world\rApproved: au@usenet.no\nSubject: Hei\n\nkropp\n"

    assert repair_header_line_endings(raw) == (
        b"Distribution: world\nApproved: au@usenet.no\nSubject: Hei\n\nkropp\n"
    )


def test_a_header_line_with_no_space_after_the_colon():
    raw = b"Keywords: World\rX-No-Arcive:Yes\n\nkropp\n"

    assert (
        repair_header_line_endings(raw)
        == b"Keywords: World\nX-No-Arcive:Yes\n\nkropp\n"
    )


def test_both_kinds_in_one_message():
    raw = b'From: "(\r" <a@example.com>\nKeywords: World\rX-No-Archive: Yes\n\nkropp\n'

    assert repair_header_line_endings(raw) == (
        b'From: "(" <a@example.com>\nKeywords: World\nX-No-Archive: Yes\n\nkropp\n'
    )


def test_a_carriage_return_in_the_body_is_left_alone():
    raw = b"From: a@example.com\n\nfirst\rsecond\n"

    assert repair_header_line_endings(raw) == raw


def test_a_body_line_that_looks_like_a_header_is_left_alone():
    raw = b"From: a@example.com\n\nSubject: quoted\rX-Faked: yes\n"

    assert repair_header_line_endings(raw) == raw


def test_crlf_line_endings_are_left_alone():
    raw = b"From: a@example.com\r\nSubject: Hei\r\n\r\nkropp\r\n"

    assert repair_header_line_endings(raw) == raw


def test_a_message_with_none_is_unchanged():
    raw = b"From: a@example.com\nSubject: Hei\n\nkropp\n"

    assert repair_header_line_endings(raw) == raw


def test_a_message_that_is_all_headers():
    raw = b"Keywords: World\rX-No-Archive: Yes\n"

    assert repair_header_line_endings(raw) == b"Keywords: World\nX-No-Archive: Yes\n"


def test_the_envelope_line_is_part_of_the_header_block():
    raw = b"From 1\nFrom: a\rb@example.com\n\nkropp\n"

    assert repair_header_line_endings(raw) == b"From 1\nFrom: ab@example.com\n\nkropp\n"


def test_carriage_returns_in_a_row():
    """The one before the header line ends it, and the one before that ends up a CRLF."""
    raw = b"Subject: Hei\r\rDate: i dag\n\nkropp\n"

    assert repair_header_line_endings(raw) == b"Subject: Hei\r\nDate: i dag\n\nkropp\n"


def test_a_carriage_return_at_the_end_of_the_header_block():
    raw = b"Subject: Hei\r\n\nkropp\n"

    assert repair_header_line_endings(raw) == raw


def test_a_message_with_no_headers_keeps_its_body():
    raw = b"From 1\n\nkropp\rmer\n"

    assert repair_header_line_endings(raw) == raw


def test_a_url_after_a_carriage_return_reads_as_a_header_line():
    """A scheme is a field name to this rule, so the value is broken in two."""
    raw = b"Subject: se\rhttp://uio.no/a\n\nkropp\n"

    assert repair_header_line_endings(raw) == b"Subject: se\nhttp://uio.no/a\n\nkropp\n"


def test_a_carriage_return_before_a_from_header_makes_a_header_line():
    """A "From:" has no space after it, so the repaired line is a header, not an envelope."""
    raw = b"Subject: Hei\rFrom: ola@uio.no\n\nkropp\n"

    repaired = repair_header_line_endings(raw)

    assert repaired == b"Subject: Hei\nFrom: ola@uio.no\n\nkropp\n"
    assert b"\nFrom " not in repaired


def test_a_carriage_return_before_prose_starting_with_from():
    """The prose is no header line, so the carriage return goes rather than becoming one."""
    raw = b"Subject: Hei\rFrom what I gather\n\nkropp\n"

    repaired = repair_header_line_endings(raw)

    assert repaired == b"Subject: HeiFrom what I gather\n\nkropp\n"
    assert b"\nFrom " not in repaired


def test_a_body_from_line_is_left_alone_while_the_headers_are_repaired():
    raw = b"From 1\nKeywords: World\rX-No-Archive: Yes\n\nFrom what I gather\n"

    assert repair_header_line_endings(raw) == (
        b"From 1\nKeywords: World\nX-No-Archive: Yes\n\nFrom what I gather\n"
    )


def test_a_carriage_return_in_the_body_before_a_from_line_is_left_alone():
    raw = b"Subject: Hei\n\nhan skrev\rFrom what I gather\n"

    assert repair_header_line_endings(raw) == raw


def test_an_escaped_body_from_line_is_left_alone():
    raw = b"Subject: Hei\n\n>From what I gather\n"

    assert repair_header_line_endings(raw) == raw


def body_of(raw):
    """The message from its blank line on, or None when it is all headers."""
    blank_line = BLANK_LINE.search(raw)
    return raw[blank_line.start() :] if blank_line else None


@pytest.mark.parametrize("raw", MESSAGES)
def test_the_body_is_never_touched(raw):
    """Only the header block is repaired, so a "From " line below it cannot be moved."""
    assert body_of(repair_header_line_endings(raw)) == body_of(raw)


@pytest.mark.parametrize("raw", MESSAGES)
def test_no_line_beginning_with_from_and_a_space_is_made_or_lost(raw):
    """Those lines delimit messages, so the repair must leave every one of them where it is."""
    assert repair_header_line_endings(raw).count(b"\nFrom ") == raw.count(b"\nFrom ")


@pytest.mark.parametrize("raw", MESSAGES)
def test_no_byte_of_the_message_but_a_carriage_return_is_changed(raw):
    """The repair drops carriage returns and turns them into newlines, and does nothing else."""
    repaired = repair_header_line_endings(raw)

    assert repaired.replace(b"\r", b"").replace(b"\n", b"") == raw.replace(
        b"\r", b""
    ).replace(b"\n", b"")
