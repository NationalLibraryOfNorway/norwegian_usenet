"""iter_raw_messages splits an mbox file into one bytestring per message.

The bytes are yielded undecoded, headers and body together, which is what lets
process_mbox_file apply a single detected charset to the whole message.
"""

from usenet_no.archives.parse_internet_archive import iter_raw_messages

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


def test_yields_one_bytestring_per_message(tmp_path):
    mbox_file = tmp_path / "no.two.mbox"
    mbox_file.write_bytes(TWO_MESSAGES.encode("latin-1"))

    assert len(list(iter_raw_messages(mbox_file))) == 2


def test_yields_undecoded_bytes(tmp_path):
    """The message keeps its original bytes: latin-1 Blåbær, not utf-8 or text."""
    mbox_file = tmp_path / "no.latin1.mbox"
    mbox_file.write_bytes("From a\nSubject: t\n\nBlåbær\n".encode("latin-1"))

    [raw] = list(iter_raw_messages(mbox_file))

    assert isinstance(raw, bytes)
    assert "Blåbær".encode("latin-1") in raw


def test_yields_headers_with_the_body(tmp_path):
    mbox_file = tmp_path / "no.headers.mbox"
    mbox_file.write_bytes(b"From a\nSubject: hei\n\nkropp\n")

    [raw] = list(iter_raw_messages(mbox_file))

    assert b"Subject: hei" in raw
    assert b"kropp" in raw


def test_empty_file_yields_nothing(tmp_path):
    mbox_file = tmp_path / "no.empty.mbox"
    mbox_file.write_bytes(b"")

    assert list(iter_raw_messages(mbox_file)) == []
