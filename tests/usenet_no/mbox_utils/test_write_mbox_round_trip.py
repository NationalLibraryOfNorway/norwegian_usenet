"""A message whose body holds a line starting with "From " survives a write.

Without escaping, mailbox.mbox reads that line as a delimiter, so one message
comes back as two and the body is cut off at the line.
"""

import mailbox

from usenet_no.mbox_utils import (
    RawMessage,
    get_message_body,
    message_factory,
    split_envelope,
    unescape_from_lines,
    write_mbox,
)

# A signature line starting with "From " is unescaped in the IA mbox files, as
# are quoted dictionary entries and news excerpts.
MESSAGE_WITH_FROM_LINE_IN_BODY = RawMessage(
    envelope="From 6051272061054231474",
    text=(
        "From: ola@uio.no\n"
        "Date: Sat, 06 Jan 1996 12:00:00 +0000\n"
        "Subject: nick\n"
        "\n"
        "Frank Geronimo?\n"
        "\n"
        "From now on I'm thinking only of me.\n"
    ),
)

BODY_ONLY_MESSAGE_STARTING_WITH_FROM = RawMessage(
    envelope=None, text="From now on I'm thinking only of me.\n"
)


def _read_messages(path):
    mbox = mailbox.mbox(str(path), factory=message_factory)
    return [mbox[key] for key in mbox.keys()]


def test_a_from_line_in_the_body_does_not_split_the_message(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_WITH_FROM_LINE_IN_BODY], out)

    assert len(_read_messages(out)) == 1


def test_a_from_line_in_the_body_stays_in_the_body(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_WITH_FROM_LINE_IN_BODY], out)

    [message] = _read_messages(out)
    assert "From now on I'm thinking only of me." in get_message_body(message)


def test_every_written_message_keeps_its_sender_and_date(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_WITH_FROM_LINE_IN_BODY], out)

    messages = _read_messages(out)
    assert [message["From"] for message in messages] == ["ola@uio.no"]
    assert [message["Date"] for message in messages] == [
        "Sat, 06 Jan 1996 12:00:00 +0000"
    ]


def test_a_body_only_message_starting_with_from_keeps_its_text(tmp_path):
    """The caller says there is no envelope, so the leading "From " is body text."""
    out = tmp_path / "out.mbox"
    write_mbox([BODY_ONLY_MESSAGE_STARTING_WITH_FROM], out)

    [message] = _read_messages(out)
    assert get_message_body(message) == "From now on I'm thinking only of me."


def test_the_written_message_reads_back_unchanged(tmp_path):
    """Reading the file and writing it again is what the filter step does."""
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_WITH_FROM_LINE_IN_BODY], out)

    mbox = mailbox.mbox(str(out), factory=message_factory)
    [key] = mbox.keys()
    envelope, text = split_envelope(mbox.get_bytes(key, from_=True).decode("utf-8"))

    read_back = RawMessage(envelope, unescape_from_lines(text))
    assert read_back == MESSAGE_WITH_FROM_LINE_IN_BODY
