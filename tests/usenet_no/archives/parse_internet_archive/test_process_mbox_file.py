"""process_mbox_file is the whole IA parse step for one newsgroup file.

It detects one charset for the file, decodes every message with it, and writes
them back out as UTF-8 through write_mbox. These read the output as bytes,
since the point of the step is which bytes end up on disk.
"""

import mailbox

from usenet_no.archives.parse_internet_archive import process_mbox_file
from usenet_no.mbox_utils import message_factory

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


def test_writes_every_message(tmp_path):
    mbox_file = tmp_path / "no.two.mbox"
    mbox_file.write_bytes(TWO_MESSAGES.encode("utf-8"))
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    written = mailbox.mbox(str(outfile), factory=message_factory)
    assert len(written.keys()) == 2


def test_keeps_the_source_envelope_line(tmp_path):
    """The IA envelope holds a Google Groups id, so it is carried over as-is."""
    mbox_file = tmp_path / "no.envelope.mbox"
    mbox_file.write_bytes(
        b"From 6214288843448422964\nFrom: ola@uio.no\nSubject: t\n\nBody\n"
    )
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    assert outfile.read_bytes().startswith(b"From 6214288843448422964\n")


def test_returns_the_detected_encoding(tmp_path):
    """The caller keys it on the source file, so only the encoding comes back."""
    mbox_file = tmp_path / "no.alpha.mbox"
    mbox_file.write_bytes("From 1\nSubject: t\n\nBlåbær\n".encode("utf-8"))

    assert process_mbox_file(mbox_file, tmp_path / "out.mbox") == "UTF-8"


def test_utf8_input_survives_the_round_trip(tmp_path):
    mbox_file = tmp_path / "no.utf8.mbox"
    mbox_file.write_bytes("From 1\nSubject: t\n\nBlåbær\n".encode("utf-8"))
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    assert "Blåbær".encode("utf-8") in outfile.read_bytes()


def test_latin1_input_survives_the_round_trip(tmp_path):
    """A Latin-1 file with an ASCII envelope line is detected and re-encoded.

    This is what the shared detector fixed: the old probe called such a file
    utf-8 without reading its content, and the Norwegian characters came out
    as literal backslash escapes.
    """
    mbox_file = tmp_path / "no.latin1.mbox"
    mbox_file.write_bytes("From 1\nSubject: t\n\nBlåbær\n".encode("latin-1"))
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    written = outfile.read_bytes()
    assert "Blåbær".encode("utf-8") in written
    assert rb"\xe5" not in written
