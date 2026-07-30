"""detect_file_encoding is the streaming path, used for the large IA mbox files.

It feeds the file to the detector in chunks rather than holding it in memory,
so these check that chunking does not change the answer, including when the
evidence sits past the first chunk.
"""

from usenet_no.archives import encoding
from usenet_no.archives.encoding import FALLBACK_ENCODING, detect_file_encoding

NORWEGIAN = "Jeg spiste rømmegrøt på hytta, og blåbær til dessert."


def test_latin1_file(tmp_path):
    mbox_file = tmp_path / "no.latin1.mbox"
    mbox_file.write_bytes(f"From a\nSubject: t\n\n{NORWEGIAN}\n".encode("latin-1"))

    assert detect_file_encoding(mbox_file) != "utf-8"


def test_utf8_file(tmp_path):
    mbox_file = tmp_path / "no.utf8.mbox"
    mbox_file.write_bytes(f"From a\nSubject: t\n\n{NORWEGIAN}\n".encode("utf-8"))

    assert detect_file_encoding(mbox_file) == "UTF-8"


def test_empty_file_falls_back(tmp_path):
    mbox_file = tmp_path / "no.empty.mbox"
    mbox_file.write_bytes(b"")

    assert detect_file_encoding(mbox_file) == FALLBACK_ENCODING


def test_evidence_past_the_first_chunk_is_still_read(monkeypatch, tmp_path):
    """A file whose Norwegian text starts after megabytes of ASCII."""
    monkeypatch.setattr(encoding, "_CHUNK_SIZE", 64)
    mbox_file = tmp_path / "no.late.mbox"
    mbox_file.write_bytes(b"a" * 4096 + NORWEGIAN.encode("latin-1"))

    assert detect_file_encoding(mbox_file) != "utf-8"


def test_matches_the_in_memory_detector(tmp_path):
    mbox_file = tmp_path / "no.same.mbox"
    raw = f"From a\nSubject: t\n\n{NORWEGIAN}\n".encode("latin-1")
    mbox_file.write_bytes(raw)

    assert detect_file_encoding(mbox_file) == encoding.detect_chunk_encoding(raw)
