"""escape_from_lines, unescape_from_lines and split_envelope."""

import pytest

from usenet_no.mbox_utils import (
    escape_from_lines,
    split_envelope,
    unescape_from_lines,
)

BODIES = [
    "From now on I'm thinking only of me.\n",
    "Hei\n\nFrom now on I'm thinking only of me.\n",
    # Already carries the ">" that escaping uses, as 485 IA body lines do
    ">From Webster's Revised Unabridged Dictionary\n",
    ">>From a doubly quoted line\n",
    "Nothing to escape here\n",
    "A line mentioning From: as a header name\n",
    "",
]


def test_escapes_a_body_line_starting_with_from():
    assert escape_from_lines("From now on\n") == ">From now on\n"


def test_escapes_every_such_line():
    assert escape_from_lines("From a\nx\nFrom b\n") == ">From a\nx\n>From b\n"


def test_doubles_a_leading_marker_so_the_escape_can_be_undone():
    assert escape_from_lines(">From a\n") == ">>From a\n"


def test_leaves_a_from_header_alone():
    """ "From:" has no space after it, so it is not a delimiter."""
    assert escape_from_lines("From: ola@uio.no\n") == "From: ola@uio.no\n"


def test_leaves_from_mid_line_alone():
    assert escape_from_lines("sent From here\n") == "sent From here\n"


@pytest.mark.parametrize("body", BODIES)
def test_unescaping_undoes_escaping(body):
    assert unescape_from_lines(escape_from_lines(body)) == body


def test_split_envelope_separates_the_first_line():
    assert split_envelope("From ola 1996\nFrom: ola@uio.no\n") == (
        "From ola 1996",
        "From: ola@uio.no\n",
    )


def test_split_envelope_returns_none_without_an_envelope_line():
    assert split_envelope("From: ola@uio.no\n") == (None, "From: ola@uio.no\n")


def test_split_envelope_handles_an_envelope_with_nothing_after_it():
    assert split_envelope("From \n") == ("From ", "")
