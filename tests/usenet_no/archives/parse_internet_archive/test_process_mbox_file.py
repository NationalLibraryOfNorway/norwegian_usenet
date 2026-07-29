"""process_mbox_file is the whole IA parse step for one newsgroup file.

It detects one charset for the file, decodes every message with it, and writes
them back out as UTF-8 through write_mbox. These read the output as bytes,
since the point of the step is which bytes end up on disk.
"""

import mailbox

from usenet_no.archives.parse_internet_archive import process_mbox_file
from usenet_no.mbox_utils import message_factory

TWO_MESSAGES = (
    "From ola@uio.no Mon Jan  1 00:00:00 1996\n"
    "From: ola@uio.no\n"
    "Subject: first\n"
    "\n"
    "Blåbær\n"
    "\n"
    "From kari@uio.no Tue Jan  2 00:00:00 1996\n"
    "From: kari@uio.no\n"
    "Subject: second\n"
    "\n"
    "Rømmegrøt\n"
)


def test_writes_every_message(tmp_path):
    mbox_file = tmp_path / "no.two.mbox"
    mbox_file.write_bytes(TWO_MESSAGES.encode("utf-8"))
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile, "backslashreplace")

    written = mailbox.mbox(str(outfile), factory=message_factory)
    assert len(written.keys()) == 2


def test_returns_stem_and_encoding(tmp_path):
    mbox_file = tmp_path / "no.alpha.mbox"
    mbox_file.write_bytes(b"From a\nSubject: t\n\nbody\n")

    assert process_mbox_file(mbox_file, tmp_path / "out.mbox", "replace") == (
        "no.alpha",
        "utf-8",
    )


def test_utf8_input_survives_the_round_trip(tmp_path):
    mbox_file = tmp_path / "no.utf8.mbox"
    mbox_file.write_bytes("From a\nSubject: t\n\nBlåbær\n".encode("utf-8"))
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile, "backslashreplace")

    assert "Blåbær".encode("utf-8") in outfile.read_bytes()


def test_latin1_input_is_mangled_by_the_utf8_shortcut(tmp_path):
    """Snapshot of today's behavior, not an endorsement of it.

    detect_encoding only reaches chardet when a "From " envelope line holds
    non-ASCII bytes, so a Latin-1 file with an ASCII envelope is decoded as
    utf-8 and its Norwegian characters come out as backslash escapes. See
    test_detect_encoding for the same case at the detection seam.
    """
    mbox_file = tmp_path / "no.latin1.mbox"
    mbox_file.write_bytes("From a\nSubject: t\n\nBlåbær\n".encode("latin-1"))
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile, "backslashreplace")

    assert rb"Bl\xe5b\xe6r" in outfile.read_bytes()
