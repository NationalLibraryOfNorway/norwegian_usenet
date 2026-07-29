"""Tests for concat_textfiles in usenet_no.archives.parse_norwegian_web_archive.

The key behavior under test is multi-archive accumulation: multiple tar archives
can contribute messages to the same newsgroup output file, so the function must
append (not overwrite) and only skip files that pre-existed before the current run.
"""

import mailbox

from usenet_no.mbox_utils import message_factory
from usenet_no.archives.parse_norwegian_web_archive import (
    concat_textfiles,
    correct_stem,
)


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


def test_corrections_rename_a_sub_group_file(tmp_path):
    """A cut-off subdirectory name is written under its corrected stem."""
    newsgroup_dir = tmp_path / "source" / "ALT"
    sub_dir = newsgroup_dir / "DISKUSJO"
    sub_dir.mkdir(parents=True)
    _write_message_file(sub_dir / "001")

    out_dir = tmp_path / "output"
    out_dir.mkdir()

    concat_textfiles(
        newsgroup_dir,
        out_dir / "no.alt.mbox",
        pre_existing=set(),
        corrections={"no.alt.diskusjo": "no.alt.diskusjoner"},
    )

    assert _count_messages(out_dir / "no.alt.diskusjoner.mbox") == 1
    assert not (out_dir / "no.alt.diskusjo.mbox").exists()


def test_corrections_merge_cut_off_source_into_full_name_file(tmp_path):
    """A cut-off source and a full-name source end up in the same output file."""
    cut_off_dir = tmp_path / "kz" / "ELEKTRON"
    full_dir = tmp_path / "other" / "elektronikk"
    cut_off_dir.mkdir(parents=True)
    full_dir.mkdir(parents=True)
    _write_message_file(cut_off_dir / "001", body="from the cut-off source")
    _write_message_file(full_dir / "001", body="from the full-name source")

    out_dir = tmp_path / "output"
    out_dir.mkdir()
    corrections = {"no.elektron": "no.elektronikk"}
    pre_existing = set()

    # The top-level stem is corrected by the caller, as in 02_parse_nb_archive
    for source_dir in (cut_off_dir, full_dir):
        stem = correct_stem(f"no.{source_dir.name.lower()}", corrections)
        concat_textfiles(
            source_dir,
            out_dir / f"{stem}.mbox",
            pre_existing=pre_existing,
            corrections=corrections,
        )

    assert _count_messages(out_dir / "no.elektronikk.mbox") == 2
    assert not (out_dir / "no.elektron.mbox").exists()
