"""detect_chunk_encoding reads bytes held in memory and says what to decode them with.

Both archives are detected the same way, so these cover the cases the two of
them run into: real Norwegian text in either encoding, and the samples chardet
cannot place.
"""

from usenet_no.archives.encoding import FALLBACK_ENCODING, detect_chunk_encoding

NORWEGIAN = "Jeg spiste rømmegrøt på hytta, og blåbær til dessert."


def test_utf8_norwegian_text():
    assert detect_chunk_encoding(NORWEGIAN.encode("utf-8")) == "UTF-8"


def test_latin1_norwegian_text_is_not_called_utf8():
    """The bug the shared detector fixes: this used to come back as utf-8."""
    detected = detect_chunk_encoding(NORWEGIAN.encode("latin-1"))

    assert detected != "utf-8"
    assert "8859" in detected or detected == FALLBACK_ENCODING


def test_undetectable_bytes_fall_back():
    assert detect_chunk_encoding(b"") == FALLBACK_ENCODING


def test_pure_ascii_is_decodable_either_way():
    """Chardet calls plain ASCII ASCII; decoding with it round-trips."""
    raw = b"From a\nSubject: plain\n\nno accents here\n"

    assert raw.decode(detect_chunk_encoding(raw)) == raw.decode("ascii")
