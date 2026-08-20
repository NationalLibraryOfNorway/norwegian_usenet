"""Reading the header blocks out of an IA source file, which holds one newsgroup's mbox."""

from usenet_no.archives.header_fields import iter_mbox_message_headers
from usenet_no.mbox_utils import IA_SOURCE_ENVELOPE, WRITTEN_ENVELOPE

TWO_MESSAGES = (
    "From 6214288843448422964\n"
    "From: ola@uio.no\n"
    "Subject: first\n"
    "\n"
    "Blåbær\n"
    "\n"
    "From -3831648075992104022\n"
    "From: kari@uio.no\n"
    "Subject: second\n"
    "\n"
    "Rømmegrøt\n"
)


def read(mbox_file, encoding="utf-8", envelope_pattern=IA_SOURCE_ENVELOPE):
    return [
        (message.line_number, message.header_block)
        for message in iter_mbox_message_headers(mbox_file, encoding, envelope_pattern)
    ]


def test_yields_one_header_block_per_message_with_the_line_it_starts_on(tmp_path):
    mbox_file = tmp_path / "no.two.mbox"
    mbox_file.write_bytes(TWO_MESSAGES.encode("latin-1"))

    assert read(mbox_file, "latin-1") == [
        (1, "From: ola@uio.no\nSubject: first\n"),
        (7, "From: kari@uio.no\nSubject: second\n"),
    ]


def test_the_envelope_line_is_not_a_header(tmp_path):
    mbox_file = tmp_path / "no.envelope.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: hei\n\nkropp\n")

    assert read(mbox_file) == [(1, "Subject: hei\n")]


def test_the_body_is_left_out(tmp_path):
    mbox_file = tmp_path / "no.body.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: hei\n\nSubject: in the body\n")

    [(_, header_block)] = read(mbox_file)

    assert "in the body" not in header_block


def test_a_from_line_in_a_body_does_not_start_a_message(tmp_path):
    """Only the envelope lines the IA sources carry, a "From " and a number, delimit messages."""
    mbox_file = tmp_path / "no.from.in.body.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: hei\n\nFrom what I hear\n")

    assert read(mbox_file) == [(1, "Subject: hei\n")]


def test_lines_ahead_of_the_first_message_are_skipped(tmp_path):
    mbox_file = tmp_path / "no.preamble.mbox"
    mbox_file.write_bytes(b"noise\n\nFrom 1\nSubject: hei\n\nkropp\n")

    assert read(mbox_file) == [(3, "Subject: hei\n")]


def test_a_message_that_is_all_headers(tmp_path):
    mbox_file = tmp_path / "no.headers.only.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: hei\n")

    assert read(mbox_file) == [(1, "Subject: hei\n")]


def test_a_message_with_no_headers_at_all(tmp_path):
    mbox_file = tmp_path / "no.headerless.mbox"
    mbox_file.write_bytes(b"From 1\n\nkropp\n")

    assert read(mbox_file) == [(1, "")]


def test_crlf_line_endings(tmp_path):
    mbox_file = tmp_path / "no.crlf.mbox"
    mbox_file.write_bytes(b"From 1\r\nSubject: hei\r\n\r\nkropp\r\n")

    assert read(mbox_file) == [(1, "Subject: hei\r\n")]


def test_decodes_with_the_given_encoding(tmp_path):
    mbox_file = tmp_path / "no.latin1.mbox"
    mbox_file.write_bytes("From 1\nSubject: Blåbær\n\nkropp\n".encode("latin-1"))

    assert read(mbox_file, "latin-1") == [(1, "Subject: Blåbær\n")]


def test_empty_file_yields_nothing(tmp_path):
    mbox_file = tmp_path / "no.empty.mbox"
    mbox_file.write_bytes(b"")

    assert read(mbox_file) == []


def test_a_written_mbox_is_read_with_its_own_envelope_pattern(tmp_path):
    """write_mbox gives a message whose source had no envelope line a placeholder one."""
    mbox_file = tmp_path / "no.written.mbox"
    mbox_file.write_bytes(b"From MAILER-DAEMON\nSubject: hei\n\nkropp\n")

    assert read(mbox_file, envelope_pattern=WRITTEN_ENVELOPE) == [(1, "Subject: hei\n")]
    assert read(mbox_file, envelope_pattern=IA_SOURCE_ENVELOPE) == []


def test_the_headers_do_not_resume_after_a_blank_line_in_the_body(tmp_path):
    """A quoted header in the body is body text, however much it reads like a header."""
    mbox_file = tmp_path / "no.quoted.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: hei\n\nhan skrev:\n\nDate: i gaar\n")

    assert read(mbox_file) == [(1, "Subject: hei\n")]


def test_a_file_that_does_not_end_in_a_newline(tmp_path):
    mbox_file = tmp_path / "no.unterminated.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: hei")

    assert read(mbox_file) == [(1, "Subject: hei")]


def test_two_envelope_lines_in_a_row(tmp_path):
    """The first message holds nothing at all, and is a message all the same."""
    mbox_file = tmp_path / "no.empty.message.mbox"
    mbox_file.write_bytes(b"From 1\nFrom 2\nSubject: hei\n\nkropp\n")

    assert read(mbox_file) == [(1, ""), (2, "Subject: hei\n")]


def test_a_file_that_is_one_envelope_line(tmp_path):
    mbox_file = tmp_path / "no.envelope.only.mbox"
    mbox_file.write_bytes(b"From 1\n")

    assert read(mbox_file) == [(1, "")]


def test_a_lone_carriage_return_does_not_end_a_line_here(tmp_path):
    """The block is read line by line, so both fields come out on the one line."""
    mbox_file = tmp_path / "no.cr.mbox"
    mbox_file.write_bytes(b"From 1\nKeywords: World\rX-No-Archive: Yes\n\nkropp\n")

    assert read(mbox_file) == [(1, "Keywords: World\rX-No-Archive: Yes\n")]
