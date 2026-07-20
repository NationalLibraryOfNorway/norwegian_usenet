import mailbox

from usenet_no.mbox_utils import get_from_field, message_factory

DUMMY_MBOX_WITH_FROM_HEADER = """\
From envelope_sender@example.com
From: header_sender@example.com
Subject: Test message

Body text
"""

DUMMY_MBOX_WITHOUT_FROM_HEADER = """\
From envelope_sender@example.com
Subject: Test message

Body text
"""


def _first_message(tmp_path, text):
    """Read with the same factory the pipeline uses.

    The factory matters: mailbox.Mailbox.__getitem__ skips get_message when one
    is set, so the envelope line is never attached to the message.
    """
    mbox_file = tmp_path / "test.mbox"
    mbox_file.write_text(text)
    return next(iter(mailbox.mbox(str(mbox_file), factory=message_factory)))


def test_returns_the_from_header(tmp_path):
    message = _first_message(tmp_path, DUMMY_MBOX_WITH_FROM_HEADER)

    assert get_from_field(message) == "header_sender@example.com"


def test_returns_none_when_there_is_no_from_header(tmp_path):
    """The envelope sender is deliberately not used as a fallback."""
    message = _first_message(tmp_path, DUMMY_MBOX_WITHOUT_FROM_HEADER)

    assert get_from_field(message) is None


def test_does_not_return_the_mailer_daemon_placeholder(tmp_path):
    """mboxMessage.__init__ stamps 'MAILER-DAEMON <current time>' on every message.

    Reading it would invent a sender and make two runs disagree.
    """
    message = _first_message(tmp_path, DUMMY_MBOX_WITHOUT_FROM_HEADER)

    assert "MAILER-DAEMON" in message.get_from()
    assert get_from_field(message) is None
