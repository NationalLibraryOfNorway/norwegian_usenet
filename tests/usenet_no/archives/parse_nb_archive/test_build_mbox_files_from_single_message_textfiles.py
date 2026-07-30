"""build_mbox_files_from_single_message_textfiles writes one newsgroup directory,
and its subgroups, to mbox files.

The traversal and the writing are covered on their own (see
test_iter_newsgroup_sources and test_write_messages_to_mbox); what is left here
is what this function adds: one output file per newsgroup, appended to, so that
several tar archives can contribute to the same newsgroup.
"""

from usenet_no.archives.parse_nb_archive import (
    build_mbox_files_from_single_message_textfiles,
    correct_stem,
)


def test_writes_messages_from_directory(tmp_path, write_message_file, count_messages):
    newsgroup_dir = tmp_path / "source"
    write_message_file(newsgroup_dir / "001")
    write_message_file(newsgroup_dir / "002")
    out = tmp_path / "output" / "no.test.mbox"
    out.parent.mkdir()

    build_mbox_files_from_single_message_textfiles(newsgroup_dir, out)

    assert count_messages(out) == 2


def test_multiple_archives_accumulate(tmp_path, write_message_file, count_messages):
    """Two archives with the same newsgroup name both contribute to the output file."""
    archive1 = tmp_path / "archive1" / "diskusjoner"
    archive2 = tmp_path / "archive2" / "diskusjoner"
    write_message_file(archive1 / "001", body="from archive 1")
    write_message_file(archive2 / "001", body="from archive 2")

    out_dir = tmp_path / "output"
    out_dir.mkdir()
    out = out_dir / "no.diskusjoner.mbox"

    build_mbox_files_from_single_message_textfiles(archive1, out)
    build_mbox_files_from_single_message_textfiles(archive2, out)

    assert count_messages(out) == 2


def test_subdirectory_creates_sub_mbox(tmp_path, write_message_file, count_messages):
    """Messages in subdirectories go to a separate sub-group mbox file."""
    newsgroup_dir = tmp_path / "source" / "alt"
    message = write_message_file(newsgroup_dir / "001")
    sub_message = write_message_file(newsgroup_dir / "sub" / "001")
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    out = out_dir / "no.alt.mbox"

    encodings = build_mbox_files_from_single_message_textfiles(newsgroup_dir, out)

    assert count_messages(out) == 1
    assert count_messages(out_dir / "no.alt.sub.mbox") == 1
    assert set(encodings) == {message, sub_message}


def test_corrections_rename_a_sub_group_file(
    tmp_path, write_message_file, count_messages
):
    """A cut-off subdirectory name is written under its corrected stem."""
    newsgroup_dir = tmp_path / "source" / "ALT"
    write_message_file(newsgroup_dir / "DISKUSJO" / "001")
    out_dir = tmp_path / "output"
    out_dir.mkdir()

    build_mbox_files_from_single_message_textfiles(
        newsgroup_dir,
        out_dir / "no.alt.mbox",
        corrections={"no.alt.diskusjo": "no.alt.diskusjoner"},
    )

    assert count_messages(out_dir / "no.alt.diskusjoner.mbox") == 1
    assert not (out_dir / "no.alt.diskusjo.mbox").exists()


def test_corrections_merge_cut_off_source_into_full_name_file(
    tmp_path, write_message_file, count_messages
):
    """A cut-off source and a full-name source end up in the same output file."""
    cut_off_dir = tmp_path / "kz" / "ELEKTRON"
    full_dir = tmp_path / "other" / "elektronikk"
    write_message_file(cut_off_dir / "001", body="from the cut-off source")
    write_message_file(full_dir / "001", body="from the full-name source")

    out_dir = tmp_path / "output"
    out_dir.mkdir()
    corrections = {"no.elektron": "no.elektronikk"}

    # The top-level stem is corrected by the caller, as in 02_parse_nb_archive
    for source_dir in (cut_off_dir, full_dir):
        stem = correct_stem(f"no.{source_dir.name.lower()}", corrections)
        build_mbox_files_from_single_message_textfiles(
            source_dir,
            out_dir / f"{stem}.mbox",
            corrections=corrections,
        )

    assert count_messages(out_dir / "no.elektronikk.mbox") == 2
    assert not (out_dir / "no.elektron.mbox").exists()
