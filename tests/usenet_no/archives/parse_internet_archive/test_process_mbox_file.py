"""process_mbox_file is the whole IA parse step for one newsgroup file.

It detects one charset for the file, decodes every message with it, and writes
them back out as UTF-8 through write_mbox. These read the output as bytes,
since the point of the step is which bytes end up on disk.
"""

import mailbox

from usenet_no.archives.parse_internet_archive import process_mbox_file
from usenet_no.mbox_utils import (
    get_message_bodies_at_positions,
    message_factory,
    open_mbox,
)

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


def test_a_lone_carriage_return_in_the_headers_is_dropped(tmp_path):
    """It ends the header line for every parser, hiding the fields below it."""
    mbox_file = tmp_path / "no.cr.mbox"
    mbox_file.write_bytes(
        b'From 1\nFrom: "(\r" <ola@uio.no>\nSubject: Hei\nDate: 1997/05/15\n\nkropp\n'
    )
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    [written] = mailbox.mbox(str(outfile), factory=message_factory).values()
    assert written.keys() == ["From", "Subject", "Date"]


def test_a_lone_carriage_return_in_the_body_is_kept(tmp_path):
    mbox_file = tmp_path / "no.body.cr.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: Hei\n\nfirst\rsecond\n")
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    assert b"first\rsecond" in outfile.read_bytes()


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


def test_a_body_line_beginning_with_from_stays_in_its_message(tmp_path):
    """The source does not escape them, so the step has to, or the message splits in two."""
    mbox_file = tmp_path / "no.from.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: t\n\nFrom what I gather\n")
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    written = mailbox.mbox(str(outfile), factory=message_factory)
    assert len(written.keys()) == 1
    assert b">From what I gather" in outfile.read_bytes()


def test_a_message_with_no_body(tmp_path):
    mbox_file = tmp_path / "no.bodyless.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: t\nDate: i dag\n")
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    [written] = mailbox.mbox(str(outfile), factory=message_factory).values()
    assert written.keys() == ["Subject", "Date"]


def test_a_message_with_no_headers(tmp_path):
    mbox_file = tmp_path / "no.headerless.mbox"
    mbox_file.write_bytes(b"From 1\n\nkropp\n")
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    assert outfile.read_bytes() == b"From 1\n\nkropp\n\n"


def test_an_unindented_continuation_is_folded_into_the_line_above(tmp_path):
    """Left as it stands it would cost the message every field below it."""
    headers = b"Received: by 10.224.100.137;\nThu, 26 Jul 2012 08:52:54\nDate: i dag\n"
    mbox_file = tmp_path / "no.continuation.mbox"
    mbox_file.write_bytes(b"From 1\n" + headers + b"\nkropp\n")
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    [written] = mailbox.mbox(str(outfile), factory=message_factory).values()
    assert written.keys() == ["Received", "Date"]


def test_a_field_name_the_source_mangled_costs_only_its_own_field(tmp_path):
    mbox_file = tmp_path / "no.mangled.mbox"
    mbox_file.write_bytes("From 1\nX-A: b\nX-gåte: på\nDate: i dag\n\nkropp\n".encode())
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    [written] = mailbox.mbox(str(outfile), factory=message_factory).values()
    assert written.keys() == ["X-A", "Date"]


def test_an_empty_file_writes_an_empty_file(tmp_path):
    mbox_file = tmp_path / "no.empty.mbox"
    mbox_file.write_bytes(b"")
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    assert outfile.read_bytes() == b""


BODY_FROM_LINES = (
    "From 6051272061054231474\n"
    'From: "(\r" <ola@uio.no>\n'
    "Subject: nick\n"
    "\n"
    "From now on I'm thinking only of me.\n"
    ">From a quoted post\n"
    "\n"
    "From -3831648075992104022\n"
    "From: kari@uio.no\n"
    "Subject: svar\n"
    "\n"
    "From what I gather\n"
)


def test_repairing_the_headers_leaves_the_body_from_lines_alone(tmp_path):
    """The repair works on the header block, which the body's "From " lines are not in."""
    mbox_file = tmp_path / "no.both.mbox"
    mbox_file.write_bytes(BODY_FROM_LINES.encode("utf-8"))
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    written = outfile.read_bytes()
    assert b'From: "(" <ola@uio.no>\n' in written
    assert b">From now on I'm thinking only of me.\n" in written
    assert b">>From a quoted post\n" in written
    assert b">From what I gather\n" in written


def test_repairing_the_headers_does_not_change_the_message_count(tmp_path):
    mbox_file = tmp_path / "no.both.mbox"
    mbox_file.write_bytes(BODY_FROM_LINES.encode("utf-8"))
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    assert len(open_mbox(outfile)) == 2
    assert len(mailbox.mbox(str(outfile), factory=message_factory)) == 2


def test_the_body_reads_back_as_the_source_wrote_it(tmp_path):
    mbox_file = tmp_path / "no.both.mbox"
    mbox_file.write_bytes(BODY_FROM_LINES.encode("utf-8"))
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    bodies = get_message_bodies_at_positions(outfile, [0, 1])
    assert bodies[0] == "From now on I'm thinking only of me. >From a quoted post"
    assert bodies[1] == "From what I gather"


def test_a_carriage_return_in_the_headers_does_not_make_a_new_envelope_line(tmp_path):
    """A repaired header line reads "From:", with no space, so it delimits nothing."""
    mbox_file = tmp_path / "no.cr.from.mbox"
    mbox_file.write_bytes(b"From 1\nSubject: nick\rFrom: ola@uio.no\n\nkropp\n")
    outfile = tmp_path / "out.mbox"

    process_mbox_file(mbox_file, outfile)

    assert (
        outfile.read_bytes() == b"From 1\nSubject: nick\nFrom: ola@uio.no\n\nkropp\n\n"
    )
    assert len(open_mbox(outfile)) == 1
