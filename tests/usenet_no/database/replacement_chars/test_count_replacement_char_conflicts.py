from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.replacement_chars import count_replacement_char_conflicts


def test_counts_conflicts_per_newsgroup(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.replacement.chars.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.replacement.chars.mbox", NB_ARCHIVE),
        ],
    )

    (counts,) = count_replacement_char_conflicts(
        connection, mbox_data / "ia", mbox_data / "nb", show_progress=False
    )

    assert counts.newsgroup == "no.replacement.chars"
    # <damaged>, <damaged-and-rewritten> and <rewritten> conflict;
    # <identical> agrees and the padding message is ia-only
    assert counts.message_body_conflict == 3
    # <damaged> and <damaged-and-rewritten> hold U+FFFD in the ia copy
    assert counts.ia_contains_replacement_char == 2
    # only <damaged> agrees once æøåÆØÅ and U+FFFD become "_"
    assert counts.equal_with_char_replacement == 1


def test_newsgroups_without_conflicts_are_left_out(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.identical.across.archives.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.identical.across.archives.mbox", NB_ARCHIVE),
        ],
    )

    assert (
        count_replacement_char_conflicts(
            connection, mbox_data / "ia", mbox_data / "nb", show_progress=False
        )
        == []
    )


def test_counts_multiple_newsgroups(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.across.archives.mbox", IA_ARCHIVE),
            (mbox_data / "ia/no.replacement.chars.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.across.archives.mbox", NB_ARCHIVE),
            (mbox_data / "nb/no.replacement.chars.mbox", NB_ARCHIVE),
        ],
    )

    counts = count_replacement_char_conflicts(
        connection, mbox_data / "ia", mbox_data / "nb", show_progress=False
    )

    assert [
        (
            count.newsgroup,
            count.message_body_conflict,
            count.ia_contains_replacement_char,
            count.equal_with_char_replacement,
        )
        for count in counts
    ] == [
        ("no.across.archives", 1, 0, 0),
        ("no.replacement.chars", 3, 2, 1),
    ]
