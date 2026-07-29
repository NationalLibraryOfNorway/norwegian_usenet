"""decode_message_text is the pure per-message decode seam of the parse step:
raw bytes plus a charset in, text out. It decodes with a single charset and does
not resolve any Content-Transfer-Encoding."""

from usenet_no.archives.parse_internet_archive import decode_message_text


def test_decodes_latin1_bytes():
    assert decode_message_text("Blåbær".encode("latin-1"), "iso-8859-1", "replace") == (
        "Blåbær"
    )


def test_decodes_utf8_bytes():
    assert decode_message_text("Blåbær".encode("utf-8"), "utf-8", "replace") == "Blåbær"


def test_quoted_printable_escapes_pass_through():
    """The parse stage leaves =XX escapes untouched; QP is resolved later, if at all."""
    assert decode_message_text(b"p=E5 loffen", "utf-8", "replace") == "p=E5 loffen"
