import mailbox

from usenet_no.mbox_utils import ensure_mbox_envelope


MESSAGE_WITHOUT_ENVELOPE = """\
From: sender@example.com
Subject: Test message

Body text
"""

MESSAGE_WITH_ENVELOPE = """\
From sender@example.com
From: sender@example.com
Subject: Test message

Body text
"""


def test_adds_from_line_when_missing(tmp_path):
    mbox_file = tmp_path / "test.mbox"
    mbox_file.write_text(ensure_mbox_envelope(MESSAGE_WITHOUT_ENVELOPE))
    mbox = mailbox.mbox(str(mbox_file))
    assert len(list(mbox)) == 1


def test_uses_from_header_value_in_envelope():
    result = ensure_mbox_envelope(MESSAGE_WITHOUT_ENVELOPE)
    assert result.startswith("From sender@example.com\n")


def test_does_not_add_from_line_when_already_present(tmp_path):
    mbox_file = tmp_path / "test.mbox"
    mbox_file.write_text(ensure_mbox_envelope(MESSAGE_WITH_ENVELOPE))
    mbox = mailbox.mbox(str(mbox_file))
    assert len(list(mbox)) == 1
