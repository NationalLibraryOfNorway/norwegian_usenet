"""Reading the header blocks out of an IA source file, which holds one newsgroup's mbox."""

from usenet_no.archives.header_fields import iter_mbox_header_blocks

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


def test_yields_one_header_block_per_message(tmp_path):
    mbox_file = tmp_path / "no.two.mbox"
    mbox_file.write_bytes(TWO_MESSAGES.encode("latin-1"))

    assert list(iter_mbox_header_blocks(mbox_file, "latin-1")) == [
        "From: ola@uio.no\nSubject: first",
        "From: kari@uio.no\nSubject: second",
    ]


def test_the_envelope_line_is_not_a_header(tmp_path):
    """mailbox holds the "From " line separately, so it is not part of the headers."""
    mbox_file = tmp_path / "no.envelope.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: hei\n\nkropp\n")

    [header_block] = iter_mbox_header_blocks(mbox_file, "utf-8")

    assert header_block == "Subject: hei"


def test_the_body_is_left_out(tmp_path):
    mbox_file = tmp_path / "no.body.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: hei\n\nSubject: in the body\n")

    [header_block] = iter_mbox_header_blocks(mbox_file, "utf-8")

    assert "in the body" not in header_block


def test_a_message_that_is_all_headers(tmp_path):
    """With no blank line to cut at, the message is yielded as it stands."""
    mbox_file = tmp_path / "no.headers.only.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: hei\n")

    assert list(iter_mbox_header_blocks(mbox_file, "utf-8")) == ["Subject: hei\n"]


def test_decodes_with_the_given_encoding(tmp_path):
    mbox_file = tmp_path / "no.latin1.mbox"
    mbox_file.write_bytes("From 1\nSubject: Blåbær\n\nkropp\n".encode("latin-1"))

    assert list(iter_mbox_header_blocks(mbox_file, "latin-1")) == ["Subject: Blåbær"]


def test_empty_file_yields_nothing(tmp_path):
    mbox_file = tmp_path / "no.empty.mbox"
    mbox_file.write_bytes(b"")

    assert list(iter_mbox_header_blocks(mbox_file, "utf-8")) == []
