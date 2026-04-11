"""Tests for concat_textfiles in usenet_no.parse_norwegian_web_archive.

The key behavior under test is multi-archive accumulation: multiple tar archives
can contribute messages to the same newsgroup output file, so the function must
append (not overwrite) and only skip files that pre-existed before the current run.
"""

import mailbox

from usenet_no.mbox_utils import message_factory
from usenet_no.parse_norwegian_web_archive import concat_textfiles


MESSAGE_TEMPLATE = """\
From: {sender}
Subject: {subject}

{body}
"""


def _write_message_file(path, sender="a@example.com", subject="Test", body="Hello"):
    path.write_text(MESSAGE_TEMPLATE.format(sender=sender, subject=subject, body=body))


def _count_messages(path):
    return len(mailbox.mbox(str(path), factory=message_factory))


def test_writes_messages_from_directory(tmp_path):
    newsgroup_dir = tmp_path / "source"
    newsgroup_dir.mkdir()
    _write_message_file(newsgroup_dir / "001")
    _write_message_file(newsgroup_dir / "002")

    out = tmp_path / "output" / "no.test.mbox"
    out.parent.mkdir()

    concat_textfiles(newsgroup_dir, out, pre_existing=set())
    assert _count_messages(out) == 2


def test_multiple_archives_accumulate(tmp_path):
    """Two archives with the same newsgroup name both contribute to the output file."""
    archive1 = tmp_path / "archive1" / "diskusjoner"
    archive2 = tmp_path / "archive2" / "diskusjoner"
    archive1.mkdir(parents=True)
    archive2.mkdir(parents=True)

    _write_message_file(archive1 / "001", body="from archive 1")
    _write_message_file(archive2 / "001", body="from archive 2")

    out_dir = tmp_path / "output"
    out_dir.mkdir()
    out = out_dir / "no.diskusjoner.mbox"

    pre_existing = set()

    concat_textfiles(archive1, out, pre_existing=pre_existing)
    concat_textfiles(archive2, out, pre_existing=pre_existing)

    assert _count_messages(out) == 2


def test_skips_pre_existing_files(tmp_path):
    """Files that existed before this run are not re-processed on re-run."""
    newsgroup_dir = tmp_path / "source"
    newsgroup_dir.mkdir()
    _write_message_file(newsgroup_dir / "001")

    out_dir = tmp_path / "output"
    out_dir.mkdir()
    out = out_dir / "no.test.mbox"

    concat_textfiles(newsgroup_dir, out, pre_existing=set())
    assert _count_messages(out) == 1

    _write_message_file(newsgroup_dir / "002")
    concat_textfiles(newsgroup_dir, out, pre_existing={out.name})
    assert _count_messages(out) == 1  # still 1, not 2


def test_subdirectory_creates_sub_mbox(tmp_path):
    """Messages in subdirectories go to a separate sub-group mbox file."""
    newsgroup_dir = tmp_path / "source" / "alt"
    sub_dir = newsgroup_dir / "sub"
    newsgroup_dir.mkdir(parents=True)
    sub_dir.mkdir()

    _write_message_file(newsgroup_dir / "001")
    _write_message_file(sub_dir / "001")

    out_dir = tmp_path / "output"
    out_dir.mkdir()
    out = out_dir / "no.alt.mbox"

    concat_textfiles(newsgroup_dir, out, pre_existing=set())

    assert _count_messages(out) == 1
    assert _count_messages(out_dir / "no.alt.sub.mbox") == 1
