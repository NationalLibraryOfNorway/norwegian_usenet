"""Source files as the NB archives hold them: one message per file, no envelope line."""

import mailbox

import pytest

from usenet_no.mbox_utils import message_factory

MESSAGE_TEMPLATE = """\
From: {sender}
Subject: {subject}

{body}
"""


def _write_message_file(
    path,
    body="Blåbær og rømmegrøt",
    encoding="utf-8",
    sender="a@example.com",
    subject="Test",
):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        MESSAGE_TEMPLATE.format(sender=sender, subject=subject, body=body).encode(
            encoding
        )
    )
    return path


def _count_messages(path):
    return len(mailbox.mbox(str(path), factory=message_factory))


@pytest.fixture
def write_message_file():
    """Write one message file, creating its directory."""
    return _write_message_file


@pytest.fixture
def count_messages():
    """The number of messages in a written mbox file."""
    return _count_messages
