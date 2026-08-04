"""Filtering reads an mbox file and writes one, so it unescapes and escapes again.

The input here is written by write_mbox rather than read from tests/data, since
what the filter reads in the pipeline is always a file write_mbox produced.
"""

from usenet_no.filter_archive_by_date import filter_mbox_by_date
from usenet_no.mbox_utils import RawMessage, get_message_body, open_mbox, write_mbox

SPAN = ("1990-01-01", "2000-12-31")

MESSAGES = [
    RawMessage(
        envelope="From 6051272061054231474",
        text=(
            "From: ola@uio.no\n"
            "Date: Sat, 06 Jan 1996 12:00:00 +0000\n"
            "Subject: nick\n"
            "\n"
            "Stian\n"
            "\n"
            "From now on I'm thinking only of me.\n"
        ),
    ),
    # A body line the source already wrote with a ">", which escaping doubles
    RawMessage(
        envelope="From -3831648075992104022",
        text=(
            "From: kari@uio.no\n"
            "Date: Sat, 20 Jan 1996 12:00:00 +0000\n"
            "Subject: sitat\n"
            "\n"
            ">From Webster's Revised Unabridged Dictionary\n"
        ),
    ),
]

BODIES = [
    "Stian From now on I'm thinking only of me.",
    ">From Webster's Revised Unabridged Dictionary",
]


def _written(tmp_path):
    source = tmp_path / "no.round.trip.mbox"
    write_mbox(MESSAGES, source)
    return source


def _filter(source, out):
    filter_mbox_by_date(source, out, *SPAN)
    return out


def test_keeping_every_message_reproduces_the_input(tmp_path):
    source = _written(tmp_path)

    out = _filter(source, tmp_path / "filtered.mbox")

    assert out.read_bytes() == source.read_bytes()


def test_filtering_the_output_again_changes_nothing(tmp_path):
    first = _filter(_written(tmp_path), tmp_path / "first.mbox")

    second = _filter(first, tmp_path / "second.mbox")

    assert second.read_bytes() == first.read_bytes()


def test_the_escape_marker_does_not_accumulate(tmp_path):
    """Escaping without unescaping first would add one ">" per pass."""
    second = _filter(
        _filter(_written(tmp_path), tmp_path / "first.mbox"), tmp_path / "second.mbox"
    )

    content = second.read_bytes()
    assert content.count(b"\n>From now on") == 1
    assert content.count(b"\n>>From Webster's") == 1
    assert b">>>From" not in content


def test_the_bodies_survive_two_passes(tmp_path):
    second = _filter(
        _filter(_written(tmp_path), tmp_path / "first.mbox"), tmp_path / "second.mbox"
    )

    mbox = open_mbox(second)
    assert [get_message_body(mbox[key]) for key in mbox.keys()] == BODIES


def test_the_message_count_survives_two_passes(tmp_path):
    second = _filter(
        _filter(_written(tmp_path), tmp_path / "first.mbox"), tmp_path / "second.mbox"
    )

    assert len(open_mbox(second)) == len(MESSAGES)


def test_the_envelope_lines_survive_two_passes(tmp_path):
    second = _filter(
        _filter(_written(tmp_path), tmp_path / "first.mbox"), tmp_path / "second.mbox"
    )

    content = second.read_bytes()
    assert b"From 6051272061054231474\n" in content
    assert b"From -3831648075992104022\n" in content
    assert b"From MAILER-DAEMON" not in content
