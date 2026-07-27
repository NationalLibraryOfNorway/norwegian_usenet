"""detect_encoding decides which charset process_mbox_file reads a file with.

These pin the current behavior: a file is called utf-8 unless mailbox parsing
raises UnicodeDecodeError, which it does not for Latin-1. Both pass; the second
documents the surprising case, which a future encoding fix may revisit.
"""

from usenet_no.parse_internet_archive import detect_encoding


def test_utf8_file_detected_as_utf8(tmp_path):
    mbox_file = tmp_path / "no.utf8.mbox"
    mbox_file.write_bytes("From a\n\nBlåbær\n".encode("utf-8"))

    assert detect_encoding(mbox_file) == "utf-8"


def test_latin1_file_currently_detected_as_utf8(tmp_path):
    # mailbox iteration does not raise on Latin-1 bytes, so the chardet branch is
    # not reached and the file is (mis)labelled utf-8. Snapshot of today's behavior.
    mbox_file = tmp_path / "no.latin1.mbox"
    mbox_file.write_bytes("From a\n\nBl\xe5b\xe6r\n".encode("latin-1"))

    assert detect_encoding(mbox_file) == "utf-8"
