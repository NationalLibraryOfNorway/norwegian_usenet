"""find_newsgroups_parent_dir walks down to the directory holding the newsgroups.

The NB sources nest it differently per CD, so it descends until it finds one, and
which subdirectory it descends into has to follow from the names rather than from
the order the filesystem returns them in.
"""

from usenet_no.archives.parse_nb_archive import find_newsgroups_parent_dir


def test_finds_a_directory_named_no(tmp_path):
    newsgroups = tmp_path / "cd" / "no"
    (newsgroups / "alt").mkdir(parents=True)

    assert find_newsgroups_parent_dir(tmp_path / "cd") == newsgroups


def test_finds_a_news_directory_below_a_kz_directory(tmp_path):
    newsgroups = tmp_path / "KZ2001-0147" / "NEWS"
    (newsgroups / "alt").mkdir(parents=True)

    assert find_newsgroups_parent_dir(tmp_path / "KZ2001-0147") == newsgroups


def test_descends_into_the_first_subdirectory_by_name(tmp_path):
    """Created last-first, so a filesystem that returns creation order would differ."""
    source = tmp_path / "cd"
    for name in ("zzz", "mmm", "aaa"):
        (source / name / "no" / "alt").mkdir(parents=True)

    assert find_newsgroups_parent_dir(source) == source / "aaa" / "no"


def test_ignores_files_beside_the_subdirectories(tmp_path):
    source = tmp_path / "cd"
    (source / "no" / "alt").mkdir(parents=True)
    (source / "AUTORUN.INF").write_text("", encoding="utf-8")

    assert find_newsgroups_parent_dir(source) == source / "no"
