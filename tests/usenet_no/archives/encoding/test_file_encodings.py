"""The encodings file both parse scripts write: one entry per source file.

Keys are paths below unzipped_data, flat for IA and nested for NB. Loading is
what lets a re-run keep the entries for the newsgroups it skips.
"""

from usenet_no.archives.encoding import (
    load_file_encodings,
    source_key,
    write_file_encodings,
)


def test_source_key_is_the_path_below_the_unzipped_dir(tmp_path):
    unzipped_dir = tmp_path / "unzipped_data"
    message_file = unzipped_dir / "KZ2001-0147" / "NEWS" / "alt" / "001"

    assert source_key(message_file, unzipped_dir) == "KZ2001-0147/NEWS/alt/001"


def test_source_key_of_a_file_directly_in_the_unzipped_dir(tmp_path):
    """The IA sources are flat: unzipped_data holds one mbox file per newsgroup."""
    unzipped_dir = tmp_path / "unzipped_data"

    assert source_key(unzipped_dir / "no.ai.mbox", unzipped_dir) == "no.ai.mbox"


def test_write_then_load_round_trips(tmp_path):
    encodings = {
        "no.ai.mbox": "ISO-8859-1",
        "KZ2001-0147/NEWS/alt/001": "UTF-8",
    }
    encodings_file = tmp_path / "encodings.json"

    write_file_encodings(encodings, encodings_file)

    assert load_file_encodings(encodings_file) == encodings


def test_load_missing_file_is_empty(tmp_path):
    """The first run of a parse has no encodings file to read."""
    assert load_file_encodings(tmp_path / "not_written_yet.json") == {}


def test_nothing_detected_writes_no_file(tmp_path):
    """An NB run that skips every output file detects nothing to report."""
    encodings_file = tmp_path / "encodings.json"

    write_file_encodings({}, encodings_file)

    assert not encodings_file.exists()


def test_nothing_detected_leaves_an_existing_file_alone(tmp_path):
    encodings_file = tmp_path / "encodings.json"
    write_file_encodings({"no.ai.mbox": "UTF-8"}, encodings_file)

    write_file_encodings({}, encodings_file)

    assert load_file_encodings(encodings_file) == {"no.ai.mbox": "UTF-8"}


def test_load_drops_entries_from_the_earlier_ia_format(tmp_path):
    """The IA parse used to key newsgroup stems to a {"encoding": ...} object."""
    encodings_file = tmp_path / "encodings.json"
    encodings_file.write_text(
        '{"no.ai": {"encoding": "utf-8"}, "no.ai.mbox": "UTF-8"}', encoding="utf-8"
    )

    assert load_file_encodings(encodings_file) == {"no.ai.mbox": "UTF-8"}


def test_write_creates_the_parent_directory(tmp_path):
    encodings_file = tmp_path / "nb" / "encodings.json"

    write_file_encodings({"no.test.mbox": "UTF-8"}, encodings_file)

    assert load_file_encodings(encodings_file) == {"no.test.mbox": "UTF-8"}
