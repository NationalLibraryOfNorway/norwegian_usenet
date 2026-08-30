"""connect_archive opens one archive through the views connect_archives builds."""

from usenet_no.database import IA_ARCHIVE, NB_ARCHIVE, connect_archive


def test_the_archive_column_is_there(mbox_data, load_archives, tmp_path):
    """A query written for both archives reads the single archive the same way."""
    load_archives([(mbox_data / "nb/no.graph.same.reply.mbox", NB_ARCHIVE)])

    connection = connect_archive(tmp_path / f"{NB_ARCHIVE}.db", NB_ARCHIVE)

    assert connection.execute("SELECT archive, newsgroup FROM messages").fetchall() == [
        (NB_ARCHIVE, "no.graph.same.reply")
    ]


def test_the_other_archive_is_not_read(mbox_data, load_archives, tmp_path):
    """Both archives hold the same reply, and only the opened one is counted."""
    load_archives(
        [
            (mbox_data / "ia/no.graph.same.reply.mbox", IA_ARCHIVE),
            (mbox_data / "nb/no.graph.same.reply.mbox", NB_ARCHIVE),
        ],
    )

    connection = connect_archive(tmp_path / f"{NB_ARCHIVE}.db", NB_ARCHIVE)

    assert connection.execute("SELECT COUNT(*) FROM messages").fetchone() == (1,)
    assert connection.execute(
        "SELECT archive, referenced_id_hash IS NOT NULL FROM message_references"
    ).fetchall() == [(NB_ARCHIVE, 1)]
