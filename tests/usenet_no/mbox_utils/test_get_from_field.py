import mailbox

from usenet_no.mbox_utils import get_from_field


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


def test_prefers_from_header_over_envelope(tmp_path):
    mbox_file = tmp_path / "test.mbox"
    mbox_file.write_text(DUMMY_MBOX_WITH_FROM_HEADER)

    mbox = mailbox.mbox(str(mbox_file))
    message = next(iter(mbox))

    assert get_from_field(message) == "header_sender@example.com"


def test_falls_back_to_envelope_when_no_from_header(tmp_path):
    mbox_file = tmp_path / "test.mbox"
    mbox_file.write_text(DUMMY_MBOX_WITHOUT_FROM_HEADER)

    mbox = mailbox.mbox(str(mbox_file))
    message = next(iter(mbox))

    assert get_from_field(message) == "envelope_sender@example.com"
