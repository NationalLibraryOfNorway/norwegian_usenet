import mailbox

from usenet_no.mbox_utils import (
    RawMessage,
    get_message_body,
    message_factory,
    write_mbox,
)

MESSAGE_A = RawMessage(
    envelope="From sender@example.com",
    text="From: sender@example.com\nSubject: Message A\n\nBody of message A\n",
)

MESSAGE_B = RawMessage(
    envelope="From other@example.com",
    text="From: other@example.com\nSubject: Message B\n\nBody of message B\n",
)

MESSAGE_WITHOUT_ENVELOPE = RawMessage(
    envelope=None,
    text="From: sender@example.com\nSubject: No envelope\n\nBody without envelope line\n",
)

MESSAGE_WITH_TRAILING_WHITESPACE = RawMessage(
    envelope="From sender@example.com",
    text=(
        "From: sender@example.com\n"
        "Subject: Trailing whitespace\n"
        "\n"
        "Body with trailing whitespace\n"
        "\n"
    ),
)

MESSAGE_WITH_NORWEGIAN = RawMessage(
    envelope="From sender@example.com",
    text="From: sender@example.com\nSubject: Norwegian chars\n\nHei, dette er æøå.\n",
)

# An envelope line with nothing after it, which the archives hold where the
# "From " line carries no sender.
BARE_ENVELOPE_MESSAGE = RawMessage(envelope="From ", text="")


def _count_messages(path):
    return len(mailbox.mbox(str(path), factory=message_factory))


def test_writes_correct_message_count(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_A, MESSAGE_B], out)
    assert _count_messages(out) == 2


def test_keeps_the_source_envelope_line(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_A], out)
    assert out.read_bytes().startswith(b"From sender@example.com\n")


def test_writes_the_placeholder_envelope_when_the_source_has_none(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_WITHOUT_ENVELOPE], out)

    assert out.read_bytes().startswith(b"From MAILER-DAEMON\n")
    assert _count_messages(out) == 1


def test_keeps_trailing_blank_lines_in_the_body(tmp_path):
    """The blank line separating two messages is written on top of the body's own."""
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_WITH_TRAILING_WHITESPACE, MESSAGE_A], out)

    assert b"Body with trailing whitespace\n\n\n" in out.read_bytes()
    assert _count_messages(out) == 2


def test_a_message_that_is_only_an_envelope_line_is_still_a_message(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_A, BARE_ENVELOPE_MESSAGE, MESSAGE_B], out)

    assert _count_messages(out) == 3


def test_a_bare_envelope_line_does_not_leak_into_the_previous_body(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_A, BARE_ENVELOPE_MESSAGE, MESSAGE_B], out)

    mbox = mailbox.mbox(str(out), factory=message_factory)
    assert get_message_body(mbox[0]) == "Body of message A"


def test_append_accumulates_messages(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_A], out, append=True)
    write_mbox([MESSAGE_B], out, append=True)
    assert _count_messages(out) == 2


def test_append_false_overwrites(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_A, MESSAGE_B], out)
    write_mbox([MESSAGE_A], out, append=False)
    assert _count_messages(out) == 1


def test_writes_utf8_bytes(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_WITH_NORWEGIAN], out)
    assert "æøå" in out.read_bytes().decode("utf-8")
    assert _count_messages(out) == 1
