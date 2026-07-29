from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE
from usenet_no.database.replacement_chars import load_replacement_char_pairs


def test_loads_the_damaged_pair_from_the_database(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.replacement.chars.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.replacement.chars.mbox", NB_ARCHIVE),
        ],
    )

    # The same message the count calls equal_with_char_replacement, now with
    # its two body texts
    (pair,) = load_replacement_char_pairs(
        connection, mbox_data / "ia", mbox_data / "nb", show_progress=False
    )

    assert pair.newsgroup == "no.replacement.chars"
    assert pair.nb_body == "Blåbærsyltetøy på loffen. ØL OG PØLSER."
    assert pair.ia_body == "Bl�b�rsyltet�y p� loffen. �L OG P�LSER."


def test_archives_that_agree_have_no_pairs(mbox_data, database, load_archives):
    connection = load_archives(
        database,
        [
            (mbox_data / "ia/no.identical.across.archives.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.identical.across.archives.mbox", NB_ARCHIVE),
        ],
    )

    assert (
        list(
            load_replacement_char_pairs(
                connection, mbox_data / "ia", mbox_data / "nb", show_progress=False
            )
        )
        == []
    )
