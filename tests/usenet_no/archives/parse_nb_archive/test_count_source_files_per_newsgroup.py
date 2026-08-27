"""count_source_files_per_newsgroup counts the source files behind each mbox file stem.

The count is taken over every extracted tar archive at once, so these cover a
newsgroup spread across two of them and the corrections that decide the stems.
"""

from usenet_no.archives.parse_nb_archive import count_source_files_per_newsgroup


def test_counts_the_message_files_of_a_newsgroup(tmp_path, write_message_file):
    write_message_file(tmp_path / "cd1/no/alt/001")
    write_message_file(tmp_path / "cd1/no/alt/002")

    assert count_source_files_per_newsgroup(tmp_path, {}) == {"no.alt": 2}


def test_subgroups_are_counted_under_their_own_stem(tmp_path, write_message_file):
    write_message_file(tmp_path / "cd1/no/alt/001")
    write_message_file(tmp_path / "cd1/no/alt/sub/001")

    assert count_source_files_per_newsgroup(tmp_path, {}) == {
        "no.alt": 1,
        "no.alt.sub": 1,
    }


def test_a_newsgroup_on_two_cds_is_counted_once(tmp_path, write_message_file):
    write_message_file(tmp_path / "cd1/no/alt/001")
    write_message_file(tmp_path / "cd2/no/alt/002")

    assert count_source_files_per_newsgroup(tmp_path, {}) == {"no.alt": 2}


def test_corrections_merge_a_cut_off_name_into_the_full_one(
    tmp_path, write_message_file
):
    write_message_file(tmp_path / "cd1/no/diskusjoner/001")
    write_message_file(tmp_path / "KZ2001-0147/NEWS/DISKUSJO/002")

    counts = count_source_files_per_newsgroup(
        tmp_path, {"no.diskusjo": "no.diskusjoner"}
    )

    assert counts == {"no.diskusjoner": 2}


def test_a_directory_without_a_newsgroups_dir_is_skipped(tmp_path, write_message_file):
    write_message_file(tmp_path / "cd1/no/alt/001")
    (tmp_path / "empty").mkdir()

    assert count_source_files_per_newsgroup(tmp_path, {}) == {"no.alt": 1}
