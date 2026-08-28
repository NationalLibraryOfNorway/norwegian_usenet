"""collect_source_files_per_newsgroup maps each mbox file stem to the files behind it.

A file's place in its list is the message's position in the mbox file, so these
cover the order the files come back in as well as which stem they land under.
"""

from usenet_no.archives.parse_nb_archive import collect_source_files_per_newsgroup


def test_message_files_come_back_under_their_stem(tmp_path, write_message_file):
    first = write_message_file(tmp_path / "cd1/no/alt/001")
    second = write_message_file(tmp_path / "cd1/no/alt/002")

    assert collect_source_files_per_newsgroup(tmp_path, {}) == {
        "no.alt": [first, second]
    }


def test_the_sources_are_read_in_directory_order(tmp_path, write_message_file):
    """The parse appends one tar archive after the other, in sorted order."""
    second_cd = write_message_file(tmp_path / "cd2/no/alt/001")
    first_cd = write_message_file(tmp_path / "cd1/no/alt/002")

    assert collect_source_files_per_newsgroup(tmp_path, {}) == {
        "no.alt": [first_cd, second_cd]
    }


def test_a_cut_off_name_lands_under_the_full_one(tmp_path, write_message_file):
    """The cut-off CD is read first, sorting before the others by name."""
    full = write_message_file(tmp_path / "cd1/no/diskusjoner/001")
    cut_off = write_message_file(tmp_path / "KZ2001-0147/NEWS/DISKUSJO/002")

    sources = collect_source_files_per_newsgroup(
        tmp_path, {"no.diskusjo": "no.diskusjoner"}
    )

    assert sources == {"no.diskusjoner": [cut_off, full]}
