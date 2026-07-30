"""iter_newsgroup_sources walks a newsgroup directory, without reading any of it.

It decides which source files belong to which output mbox stem, so these cover
the nesting and the cut-off name corrections that decide the stems.
"""

from usenet_no.archives.parse_nb_archive import iter_newsgroup_sources


def test_yields_the_message_files_of_one_directory(tmp_path, write_message_file):
    newsgroup_dir = tmp_path / "alt"
    first = write_message_file(newsgroup_dir / "001")
    second = write_message_file(newsgroup_dir / "002")

    assert list(iter_newsgroup_sources(newsgroup_dir, "no.alt")) == [
        ("no.alt", [first, second])
    ]


def test_yields_a_subgroup_under_its_own_stem(tmp_path, write_message_file):
    newsgroup_dir = tmp_path / "alt"
    write_message_file(newsgroup_dir / "001")
    sub_message = write_message_file(newsgroup_dir / "sub" / "001")

    sources = dict(iter_newsgroup_sources(newsgroup_dir, "no.alt"))

    assert sources["no.alt.sub"] == [sub_message]


def test_nested_subgroups_get_dotted_stems(tmp_path, write_message_file):
    newsgroup_dir = tmp_path / "alt"
    write_message_file(newsgroup_dir / "sub" / "deeper" / "001")

    assert [stem for stem, _ in iter_newsgroup_sources(newsgroup_dir, "no.alt")] == [
        "no.alt.sub.deeper"
    ]


def test_directory_names_are_lowercased(tmp_path, write_message_file):
    """The NB sources are upper case on some of the CDs."""
    newsgroup_dir = tmp_path / "ALT"
    write_message_file(newsgroup_dir / "DISKUSJONER" / "001")

    assert [stem for stem, _ in iter_newsgroup_sources(newsgroup_dir, "no.alt")] == [
        "no.alt.diskusjoner"
    ]


def test_corrections_rename_a_subgroup_stem(tmp_path, write_message_file):
    newsgroup_dir = tmp_path / "ALT"
    write_message_file(newsgroup_dir / "DISKUSJO" / "001")

    sources = dict(
        iter_newsgroup_sources(
            newsgroup_dir, "no.alt", {"no.alt.diskusjo": "no.alt.diskusjoner"}
        )
    )

    assert set(sources) == {"no.alt.diskusjoner"}


def test_a_directory_without_message_files_is_not_yielded(tmp_path, write_message_file):
    """A newsgroup that only holds subgroups gets no mbox file of its own."""
    newsgroup_dir = tmp_path / "alt"
    write_message_file(newsgroup_dir / "sub" / "001")

    assert [stem for stem, _ in iter_newsgroup_sources(newsgroup_dir, "no.alt")] == [
        "no.alt.sub"
    ]


def test_an_empty_directory_yields_nothing(tmp_path):
    newsgroup_dir = tmp_path / "alt"
    newsgroup_dir.mkdir()

    assert list(iter_newsgroup_sources(newsgroup_dir, "no.alt")) == []
