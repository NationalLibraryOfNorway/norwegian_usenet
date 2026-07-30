"""detect_and_decode_file detects one file's encoding from its own bytes and decodes it.

This is the read-whole path, used for the NB message files, and it hands back
the encoding for the parse to report.
"""

from usenet_no.archives.encoding import FALLBACK_ENCODING, detect_and_decode_file

NORWEGIAN = "Jeg spiste rømmegrøt på hytta, og blåbær til dessert."


def test_latin1_file_round_trips(tmp_path):
    text_file = tmp_path / "message"
    text_file.write_bytes(NORWEGIAN.encode("latin-1"))

    text, _ = detect_and_decode_file(text_file)

    assert text == NORWEGIAN


def test_utf8_file_round_trips(tmp_path):
    text_file = tmp_path / "message"
    text_file.write_bytes(NORWEGIAN.encode("utf-8"))

    text, encoding = detect_and_decode_file(text_file)

    assert text == NORWEGIAN
    assert encoding == "UTF-8"


def test_returns_the_encoding_the_text_was_decoded_with(tmp_path):
    text_file = tmp_path / "message"
    raw = NORWEGIAN.encode("latin-1")
    text_file.write_bytes(raw)

    text, encoding = detect_and_decode_file(text_file)

    assert text == raw.decode(encoding)


def test_undecodable_bytes_do_not_raise(tmp_path):
    """Latin-1 maps every byte, so the fallback always produces some text."""
    text_file = tmp_path / "message"
    text_file.write_bytes(b"\x81\x8d\x9d")

    text, encoding = detect_and_decode_file(text_file)

    assert encoding == FALLBACK_ENCODING
    assert isinstance(text, str)


def test_empty_file_falls_back(tmp_path):
    text_file = tmp_path / "message"
    text_file.write_bytes(b"")

    assert detect_and_decode_file(text_file) == ("", FALLBACK_ENCODING)
