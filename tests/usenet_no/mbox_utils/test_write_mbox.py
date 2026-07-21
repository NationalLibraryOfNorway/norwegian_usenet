import mailbox

from usenet_no.mbox_utils import message_factory, write_mbox


MESSAGE_A = """\
From sender@example.com
From: sender@example.com
Subject: Message A

Body of message A
"""

MESSAGE_B = """\
From other@example.com
From: other@example.com
Subject: Message B

Body of message B
"""

MESSAGE_WITHOUT_ENVELOPE = """\
From: sender@example.com
Subject: No envelope

Body without envelope line
"""

MESSAGE_WITH_TRAILING_WHITESPACE = """\
From sender@example.com
From: sender@example.com
Subject: Trailing whitespace

Body with trailing whitespace

"""

MESSAGE_WITH_NORWEGIAN = """\
From sender@example.com
From: sender@example.com
Subject: Norwegian chars

Hei, dette er æøå.
"""


def _count_messages(path):
    return len(mailbox.mbox(str(path), factory=message_factory))


def test_writes_correct_message_count(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_A, MESSAGE_B], out)
    assert _count_messages(out) == 2


def test_adds_envelope_when_missing(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_WITHOUT_ENVELOPE], out)
    assert _count_messages(out) == 1


def test_strips_trailing_whitespace(tmp_path):
    out = tmp_path / "out.mbox"
    write_mbox([MESSAGE_WITH_TRAILING_WHITESPACE, MESSAGE_A], out)
    content = out.read_bytes()
    # Each message should be separated by exactly one blank line (two newlines)
    assert b"\n\n\n" not in content
    assert _count_messages(out) == 2


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
