"""Reading the header block of an NB source file, which holds one message and no envelope line."""

from usenet_no.archives.header_fields import read_header_block


def test_reads_up_to_the_first_blank_line(tmp_path):
    message_file = tmp_path / "001"
    message_file.write_bytes(
        b"From: a@example.com\nSubject: Hei\n\nFrom: not a header\n"
    )

    assert (
        read_header_block(message_file, "utf-8")
        == "From: a@example.com\nSubject: Hei\n"
    )


def test_reads_a_file_that_is_all_headers(tmp_path):
    message_file = tmp_path / "001"
    message_file.write_bytes(b"From: a@example.com\n")

    assert read_header_block(message_file, "utf-8") == "From: a@example.com\n"


def test_a_crlf_line_ends_the_header_block(tmp_path):
    message_file = tmp_path / "001"
    message_file.write_bytes(b"From: a@example.com\r\n\r\nSubject: in the body\r\n")

    assert read_header_block(message_file, "utf-8") == "From: a@example.com\r\n"


def test_decodes_with_the_given_encoding(tmp_path):
    message_file = tmp_path / "001"
    message_file.write_bytes("Subject: Blåbær\n\nbody\n".encode("latin-1"))

    assert read_header_block(message_file, "latin-1") == "Subject: Blåbær\n"
